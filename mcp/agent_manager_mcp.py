#!/usr/bin/env python3
"""
智能体管理系统 MCP Server
用于 Claude Code 通过 MCP 协议管理智能体

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
           "AGENT_MANAGER_TOKEN": "your-jwt-token"
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
                response = await client.post(url, headers=headers, json=data)
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
        # ========== 智能体管理 ==========
        Tool(
            name="agent_list",
            description="📋 列出所有智能体（龙虾池）",
            inputSchema={
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "description": "页码", "default": 1},
                    "page_size": {"type": "integer", "description": "每页数量", "default": 20},
                    "agent_type": {"type": "string", "description": "类型筛选: openai/anthropic/mcp/custom"},
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
            description="🦞 创建新的智能体（养一只新龙虾）",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "智能体名称"},
                    "description": {"type": "string", "description": "描述"},
                    "agent_type": {"type": "string", "description": "类型: openai/anthropic/mcp/custom"},
                    "config": {"type": "object", "description": "配置（JSON）"}
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
            description="🗑️ 删除智能体（放生龙虾）",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "智能体ID"}
                },
                "required": ["agent_id"]
            }
        ),
        Tool(
            name="agent_toggle",
            description="🔄 启用/禁用智能体",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "智能体ID"},
                    "enabled": {"type": "boolean", "description": "true=启用, false=禁用"}
                },
                "required": ["agent_id", "enabled"]
            }
        ),

        # ========== 智能体执行 ==========
        Tool(
            name="agent_execute",
            description="🚀 执行智能体（派龙虾干活）",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "智能体ID"},
                    "message": {"type": "string", "description": "输入消息/任务"},
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
            name="execution_logs",
            description="📝 查看执行日志",
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
                    "agent_id": {"type": "string", "description": "按智能体筛选"},
                    "status": {"type": "string", "description": "按状态筛选: pending/running/completed/failed"}
                }
            }
        ),
        Tool(
            name="execution_cancel",
            description="❌ 取消执行",
            inputSchema={
                "type": "object",
                "properties": {
                    "execution_id": {"type": "string", "description": "执行ID"}
                },
                "required": ["execution_id"]
            }
        ),

        # ========== 群组管理 ==========
        Tool(
            name="group_list",
            description="👥 列出智能体群组（龙虾群）",
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
            description="🦐 创建智能体群组（组建龙虾群）",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "群组名称"},
                    "description": {"type": "string", "description": "描述"},
                    "execution_mode": {"type": "string", "description": "执行模式: sequential/parallel"},
                    "agent_ids": {"type": "array", "items": {"type": "string"}, "description": "成员Agent ID列表"}
                },
                "required": ["name", "agent_ids"]
            }
        ),
        Tool(
            name="group_execute",
            description="🚀 执行群组（派遣龙虾群）",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_id": {"type": "string", "description": "群组ID"},
                    "message": {"type": "string", "description": "输入消息/任务"}
                },
                "required": ["group_id", "message"]
            }
        ),

        # ========== 配置管理 ==========
        Tool(
            name="config_export",
            description="💾 导出所有配置",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="config_import",
            description="📥 导入配置",
            inputSchema={
                "type": "object",
                "properties": {
                    "config": {"type": "object", "description": "配置JSON"}
                },
                "required": ["config"]
            }
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
        Tool(
            name="agent_metrics",
            description="📊 获取智能体指标",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "智能体ID"}
                },
                "required": ["agent_id"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    """执行工具调用"""
    result = None

    try:
        # ========== 智能体管理 ==========
        if name == "agent_list":
            result = await api_request("GET", "/agents", params={
                "page": arguments.get("page", 1),
                "page_size": arguments.get("page_size", 20),
                "agent_type": arguments.get("agent_type"),
                "enabled": arguments.get("enabled")
            })

        elif name == "agent_get":
            result = await api_request("GET", f"/agents/{arguments['agent_id']}")

        elif name == "agent_create":
            result = await api_request("POST", "/agents", data={
                "name": arguments["name"],
                "description": arguments.get("description", ""),
                "agent_type": arguments["agent_type"],
                "config": arguments["config"]
            })

        elif name == "agent_update":
            data = {"agent_id": arguments.pop("agent_id")}
            result = await api_request("PUT", f"/agents/{data['agent_id']}", data=arguments)

        elif name == "agent_delete":
            result = await api_request("DELETE", f"/agents/{arguments['agent_id']}")

        elif name == "agent_toggle":
            action = "enable" if arguments["enabled"] else "disable"
            result = await api_request("POST", f"/agents/{arguments['agent_id']}/{action}")

        # ========== 智能体执行 ==========
        elif name == "agent_execute":
            result = await api_request(
                "POST",
                f"/executions/agents/{arguments['agent_id']}/execute",
                data={"input_data": {"message": arguments["message"], **arguments.get("context", {})}}
            )

        elif name == "execution_status":
            result = await api_request("GET", f"/executions/{arguments['execution_id']}")

        elif name == "execution_logs":
            result = await api_request("GET", f"/executions/{arguments['execution_id']}/logs")

        elif name == "execution_list":
            result = await api_request("GET", "/executions", params=arguments)

        elif name == "execution_cancel":
            result = await api_request("POST", f"/executions/{arguments['execution_id']}/cancel")

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

        # ========== 配置管理 ==========
        elif name == "config_export":
            result = await api_request("GET", "/config/export")

        elif name == "config_import":
            result = await api_request("POST", "/config/import", data=arguments["config"])

        # ========== 监控统计 ==========
        elif name == "metrics_summary":
            result = await api_request("GET", "/metrics/executions", params=arguments)

        elif name == "agent_metrics":
            result = await api_request("GET", f"/metrics/agents/{arguments['agent_id']}")

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
