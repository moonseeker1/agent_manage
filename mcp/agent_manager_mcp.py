#!/usr/bin/env python3
"""
智能体管理系统 MCP Server
用于 Claude Code 通过 MCP 协议与管理系统交互

核心功能:
1. 自我配置 - Claude Code 获取自己的权限、技能、MCP绑定
2. 权限检查 - 执行操作前检查是否被允许
3. 活动上报 - 实时上报执行状态到管理系统
4. 指令接收 - 从管理系统接收待执行的指令

使用方法:
1. 安装依赖: pip install mcp httpx
2. 在 Claude Code 配置中添加:
   {
     "mcpServers": {
       "agent-manager": {
         "command": "python3",
         "args": ["/path/to/agent_manager_mcp.py"],
         "env": {
           "AGENT_MANAGER_URL": "http://localhost:8000/api",
           "AGENT_MANAGER_TOKEN": "your-jwt-token",
           "AGENT_ID": "your-agent-id"
         }
       }
     }
   }
"""

import asyncio
import os
import json
from datetime import datetime
from typing import Any, Optional

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource, ResourceTemplate

# ============== 配置 ==============
API_BASE = os.getenv("AGENT_MANAGER_URL", "http://localhost:8000/api")
API_TOKEN = os.getenv("AGENT_MANAGER_TOKEN", "")
AGENT_ID = os.getenv("AGENT_ID", "")  # 当前Agent的ID

# ============== 缓存 ==============
_config_cache = None
_config_cache_time = None
CACHE_TTL = 60  # 缓存60秒

# ============== HTTP 客户端 ==============
async def api_request(
    method: str,
    path: str,
    data: Optional[dict] = None,
    params: Optional[dict] = None
) -> dict:
    """调用 Agent Manager API"""
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        url = f"{API_BASE}{path}"

        try:
            if method == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=data, params=params)
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=data)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                return {"error": f"Unknown method: {method}"}

            if response.status_code in [200, 201]:
                return response.json()
            else:
                return {"error": response.text, "status_code": response.status_code}
        except Exception as e:
            return {"error": str(e)}


# ============== MCP Server ==============
app = Server("agent-manager")

@app.list_tools()
async def list_tools():
    """列出所有可用工具"""
    return [
        # ========== 自我配置工具 (Claude Code 专用) ==========
        Tool(
            name="get_my_config",
            description="""🔐 获取当前Agent的完整配置

返回内容包括:
- permission: 操作权限 (bash/文件/网络等)
- skills: 绑定的技能列表
- mcp_bindings: 绑定的MCP服务器
- allowed_tools: 允许使用的工具列表
- restrictions: 路径和命令限制

建议在开始任务前调用此工具了解自己的能力边界。""",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="check_permission",
            description="""🔍 检查是否有执行某操作的权限

用于在执行敏感操作前进行权限检查:
- action: bash/read/write/edit/web
- path: 文件路径 (可选)
- command: 要执行的命令 (可选)

返回: {"allowed": true/false, "reason": "原因"}""",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "操作类型: bash/read/write/edit/web",
                        "enum": ["bash", "read", "write", "edit", "web"]
                    },
                    "path": {"type": "string", "description": "文件路径（文件操作时必填）"},
                    "command": {"type": "string", "description": "要执行的命令（bash操作时必填）"}
                },
                "required": ["action"]
            }
        ),
        Tool(
            name="report_activity",
            description="""📡 上报当前活动状态到管理系统

用于实时监控和审计:
- action: 当前操作名称
- thought: 操作原因/思考过程
- status: progress/success/failed
- detail: 详细信息 (可选)

建议在执行重要操作前后调用此工具。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "操作名称 (如: reading_file, running_test)"},
                    "thought": {"type": "string", "description": "为什么要执行此操作"},
                    "status": {
                        "type": "string",
                        "description": "状态",
                        "enum": ["progress", "success", "failed"],
                        "default": "progress"
                    },
                    "detail": {"type": "object", "description": "详细信息"}
                },
                "required": ["action"]
            }
        ),
        Tool(
            name="check_commands",
            description="""📥 检查来自管理系统的待执行指令（推荐使用 get_pending_commands）

返回一个指令队列，可能包含:
- 暂停指令: 要求暂停当前工作
- 取消指令: 要求取消当前任务
- 新任务: 管理员下发的新任务
- 配置更新: 要求重新加载配置

建议定期调用此工具检查是否有新指令。""",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_pending_commands",
            description="""📥 从 Redis 队列获取待执行的指令（优先级排序）

从 Redis 优先级队列获取指令，高优先级指令优先返回。
每次调用会获取最多 10 条指令。

返回的指令包含:
- id: 指令唯一标识
- type: 指令类型 (pause/cancel/task/config_reload)
- content: 指令内容
- priority: 优先级
- timeout: 超时时间（秒）

建议每 30 秒调用一次此工具检查新指令。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "获取数量（默认 10，最大 50）",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="submit_command_result",
            description="""📤 提交指令执行结果

执行完指令后，必须调用此工具提交结果:
- command_id: 指令 ID（从 get_pending_commands 获取）
- output: 执行输出/结果
- status: 执行状态 (success/error)
- error_message: 错误信息（如果失败）

这会完成指令的闭环反馈，管理系统会记录结果并通知管理员。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "command_id": {
                        "type": "string",
                        "description": "指令 ID"
                    },
                    "output": {
                        "type": "string",
                        "description": "执行输出/结果"
                    },
                    "status": {
                        "type": "string",
                        "description": "执行状态",
                        "enum": ["success", "error"]
                    },
                    "error_message": {
                        "type": "string",
                        "description": "错误信息（如果失败）"
                    }
                },
                "required": ["command_id", "status"]
            }
        ),
        Tool(
            name="report_command_progress",
            description="""📊 报告指令执行进度

对于长耗时的指令，可以定期报告进度:
- command_id: 指令 ID
- progress: 进度百分比 (0-100)
- message: 进度消息

这允许管理系统实时监控长时间运行的任务。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "command_id": {
                        "type": "string",
                        "description": "指令 ID"
                    },
                    "progress": {
                        "type": "integer",
                        "description": "进度百分比 (0-100)",
                        "minimum": 0,
                        "maximum": 100
                    },
                    "message": {
                        "type": "string",
                        "description": "进度消息"
                    }
                },
                "required": ["command_id", "progress"]
            }
        ),
        Tool(
            name="get_allowed_tools",
            description="""🛠️ 获取允许使用的MCP工具列表

返回当前Agent被允许使用的所有MCP工具:
- 工具名称
- 所属MCP服务器
- 工具描述
- 使用限制

在调用其他MCP工具前，建议先检查是否在允许列表中。""",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_skill_config",
            description="""🎯 获取指定技能的详细配置

根据技能代码获取:
- 技能描述和使用说明
- 具体配置参数
- 相关权限要求""",
            inputSchema={
                "type": "object",
                "properties": {
                    "skill_code": {"type": "string", "description": "技能代码 (如: code_generation, file_operations)"}
                },
                "required": ["skill_code"]
            }
        ),

        # ========== 智能体管理 ==========
        Tool(
            name="agent_list",
            description="📋 列出所有智能体",
            inputSchema={
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "description": "页码", "default": 1},
                    "page_size": {"type": "integer", "description": "每页数量", "default": 20},
                    "agent_type": {"type": "string", "description": "类型筛选"},
                    "enabled": {"type": "boolean", "description": "状态筛选"}
                }
            }
        ),
        Tool(
            name="agent_get",
            description="🔍 获取智能体详情",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "智能体ID"}
                },
                "required": ["agent_id"]
            }
        ),
        Tool(
            name="agent_create",
            description="🦞 创建新的智能体",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "智能体名称"},
                    "description": {"type": "string", "description": "描述"},
                    "agent_type": {"type": "string", "description": "类型"},
                    "config": {"type": "object", "description": "配置"}
                },
                "required": ["name", "agent_type", "config"]
            }
        ),
        Tool(
            name="agent_update",
            description="✏️ 更新智能体配置",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "智能体ID"},
                    "name": {"type": "string", "description": "名称"},
                    "description": {"type": "string", "description": "描述"},
                    "config": {"type": "object", "description": "配置"}
                },
                "required": ["agent_id"]
            }
        ),
        Tool(
            name="agent_delete",
            description="🗑️ 删除智能体",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "智能体ID"}
                },
                "required": ["agent_id"]
            }
        ),

        # ========== 执行管理 ==========
        Tool(
            name="agent_execute",
            description="🚀 执行智能体",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "智能体ID"},
                    "message": {"type": "string", "description": "输入消息"},
                    "context": {"type": "object", "description": "额外上下文"}
                },
                "required": ["agent_id", "message"]
            }
        ),
        Tool(
            name="execution_status",
            description="📊 查看执行状态",
            inputSchema={
                "type": "object",
                "properties": {
                    "execution_id": {"type": "string", "description": "执行ID"}
                },
                "required": ["execution_id"]
            }
        ),
        Tool(
            name="execution_list",
            description="📜 列出执行记录",
            inputSchema={
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "default": 1},
                    "page_size": {"type": "integer", "default": 20},
                    "status": {"type": "string", "description": "状态筛选"}
                }
            }
        ),

        # ========== 群组管理 ==========
        Tool(
            name="group_list",
            description="👥 列出智能体群组",
            inputSchema={
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "default": 1},
                    "page_size": {"type": "integer", "default": 20}
                }
            }
        ),
        Tool(
            name="group_create",
            description="🦐 创建智能体群组",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "群组名称"},
                    "description": {"type": "string", "description": "描述"},
                    "agent_ids": {"type": "array", "items": {"type": "string"}, "description": "成员ID列表"}
                },
                "required": ["name", "agent_ids"]
            }
        ),
        Tool(
            name="group_execute",
            description="🚀 执行群组",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_id": {"type": "string", "description": "群组ID"},
                    "message": {"type": "string", "description": "输入消息"}
                },
                "required": ["group_id", "message"]
            }
        ),

        # ========== MCP服务器管理 ==========
        Tool(
            name="mcp_server_list",
            description="🔌 列出MCP服务器",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="mcp_server_tools",
            description="🔧 获取MCP服务器的工具列表",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string", "description": "服务器ID"}
                },
                "required": ["server_id"]
            }
        ),

        # ========== 技能管理 ==========
        Tool(
            name="skill_list",
            description="🎯 列出所有技能",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "按分类筛选"}
                }
            }
        ),
        Tool(
            name="skill_create",
            description="➕ 创建技能",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "技能名称"},
                    "code": {"type": "string", "description": "技能代码"},
                    "description": {"type": "string", "description": "描述"},
                    "category": {"type": "string", "description": "分类"},
                    "config": {"type": "object", "description": "配置"}
                },
                "required": ["name", "code"]
            }
        ),

        # ========== 权限管理 ==========
        Tool(
            name="permission_list",
            description="🔑 列出所有权限",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="role_list",
            description="👥 列出所有角色",
            inputSchema={"type": "object", "properties": {}}
        ),

        # ========== 监控统计 ==========
        Tool(
            name="metrics_summary",
            description="📈 获取执行统计",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "统计天数", "default": 7}
                }
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    """执行工具调用"""
    global _config_cache, _config_cache_time

    result = None

    try:
        # ========== 自我配置工具 ==========
        if name == "get_my_config":
            if not AGENT_ID:
                result = {"error": "AGENT_ID 未配置，无法获取配置"}
            else:
                # 检查缓存
                now = datetime.now()
                if _config_cache and _config_cache_time:
                    if (now - _config_cache_time).total_seconds() < CACHE_TTL:
                        result = _config_cache
                    else:
                        _config_cache = None

                if not _config_cache:
                    result = await api_request("GET", f"/agents/{AGENT_ID}/config")
                    _config_cache = result
                    _config_cache_time = now

        elif name == "check_permission":
            if not AGENT_ID:
                result = {"allowed": False, "reason": "AGENT_ID 未配置"}
            else:
                # check-permission uses Query parameters, not JSON body
                result = await api_request("POST", f"/agents/{AGENT_ID}/check-permission", params=arguments)

        elif name == "report_activity":
            if not AGENT_ID:
                result = {"error": "AGENT_ID 未配置"}
            else:
                result = await api_request("POST", f"/agents/{AGENT_ID}/activities", data={
                    "action": arguments.get("action"),
                    "thought": arguments.get("thought", ""),
                    "status": arguments.get("status", "progress"),
                    "detail": arguments.get("detail", {}),
                    "timestamp": datetime.now().isoformat()
                })

        elif name == "check_commands":
            if not AGENT_ID:
                result = {"commands": [], "error": "AGENT_ID 未配置"}
            else:
                result = await api_request("GET", f"/agents/{AGENT_ID}/commands")

        elif name == "get_pending_commands":
            if not AGENT_ID:
                result = {"commands": [], "count": 0, "error": "AGENT_ID 未配置"}
            else:
                limit = arguments.get("limit", 10)
                result = await api_request("GET", f"/agents/{AGENT_ID}/commands", params={"limit": limit})

        elif name == "submit_command_result":
            command_id = arguments.get("command_id")
            if not command_id:
                result = {"success": False, "error": "command_id 必填"}
            else:
                result = await api_request("POST", f"/commands/{command_id}/result", data={
                    "output": arguments.get("output"),
                    "status": arguments.get("status", "success"),
                    "error_message": arguments.get("error_message")
                })

        elif name == "report_command_progress":
            command_id = arguments.get("command_id")
            if not command_id:
                result = {"success": False, "error": "command_id 必填"}
            else:
                result = await api_request("POST", f"/commands/{command_id}/progress", data={
                    "progress": arguments.get("progress"),
                    "message": arguments.get("message", "")
                })

        elif name == "get_allowed_tools":
            if not AGENT_ID:
                result = {"tools": [], "error": "AGENT_ID 未配置"}
            else:
                result = await api_request("GET", f"/agents/{AGENT_ID}/allowed-tools")

        elif name == "get_skill_config":
            skill_code = arguments.get("skill_code")
            if not skill_code:
                result = {"error": "skill_code 必填"}
            else:
                # 先获取我的配置，然后找对应技能
                config = await api_request("GET", f"/agents/{AGENT_ID}/config") if AGENT_ID else {}
                skills = config.get("skill_bindings", [])
                for skill in skills:
                    if skill.get("skill_code") == skill_code or skill.get("code") == skill_code:
                        result = skill
                        break
                else:
                    result = {"error": f"未找到技能: {skill_code}"}

        # ========== 智能体管理 ==========
        elif name == "agent_list":
            result = await api_request("GET", "/agents", params=arguments)

        elif name == "agent_get":
            result = await api_request("GET", f"/agents/{arguments['agent_id']}")

        elif name == "agent_create":
            result = await api_request("POST", "/agents", data=arguments)

        elif name == "agent_update":
            agent_id = arguments.pop("agent_id")
            result = await api_request("PUT", f"/agents/{agent_id}", data=arguments)

        elif name == "agent_delete":
            result = await api_request("DELETE", f"/agents/{arguments['agent_id']}")

        # ========== 执行管理 ==========
        elif name == "agent_execute":
            result = await api_request(
                "POST",
                f"/executions/agents/{arguments['agent_id']}/execute",
                data={"input_data": {"message": arguments["message"], **arguments.get("context", {})}}
            )

        elif name == "execution_status":
            result = await api_request("GET", f"/executions/{arguments['execution_id']}")

        elif name == "execution_list":
            result = await api_request("GET", "/executions", params=arguments)

        # ========== 群组管理 ==========
        elif name == "group_list":
            result = await api_request("GET", "/groups", params=arguments)

        elif name == "group_create":
            result = await api_request("POST", "/groups", data=arguments)

        elif name == "group_execute":
            result = await api_request(
                "POST",
                f"/executions/groups/{arguments['group_id']}/execute",
                data={"input_data": {"message": arguments["message"]}}
            )

        # ========== MCP服务器管理 ==========
        elif name == "mcp_server_list":
            result = await api_request("GET", "/mcp/servers")

        elif name == "mcp_server_tools":
            result = await api_request("GET", f"/mcp/servers/{arguments['server_id']}/tools")

        # ========== 技能管理 ==========
        elif name == "skill_list":
            result = await api_request("GET", "/rbac/skills", params=arguments)

        elif name == "skill_create":
            result = await api_request("POST", "/rbac/skills", data=arguments)

        # ========== 权限管理 ==========
        elif name == "permission_list":
            result = await api_request("GET", "/rbac/permissions")

        elif name == "role_list":
            result = await api_request("GET", "/rbac/roles")

        # ========== 监控统计 ==========
        elif name == "metrics_summary":
            result = await api_request("GET", "/metrics/executions", params=arguments)

        else:
            result = {"error": f"Unknown tool: {name}"}

    except Exception as e:
        result = {"error": str(e)}

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def main():
    """启动 MCP Server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
