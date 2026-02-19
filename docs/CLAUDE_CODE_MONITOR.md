# Claude Code 监控方案

本文档详细说明如何使用智能体管理系统监控 Claude Code 的执行过程。

## 架构概览

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   Claude Code   │─────▶│   MCP Server     │─────▶│  Agent Manager  │
│   (本地/服务器)  │      │   (桥接服务)      │      │   (管理系统)     │
└─────────────────┘      └──────────────────┘      └─────────────────┘
                                                          │
                                                          ▼
                                                   ┌─────────────────┐
                                                   │   PostgreSQL    │
                                                   │   (数据存储)     │
                                                   └─────────────────┘
```

## 方案一：MCP Server 监控（推荐）

### 步骤1：创建监控 MCP Server

创建文件 `/opt/claude-monitor/mcp_server.py`：

```python
#!/usr/bin/env python3
"""
Claude Code Monitor MCP Server
用于监控 Claude Code 的执行过程
"""

import asyncio
import httpx
import json
from datetime import datetime
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 配置 - 修改为你的 Agent Manager 地址和Token
API_BASE = "http://localhost:8000/api"
API_TOKEN = "your-jwt-token-here"  # 从登录接口获取

app = Server("claude-monitor")

# 会话管理
current_session = None

async def api_request(method: str, path: str, data: dict = None):
    """调用 Agent Manager API"""
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{API_BASE}{path}"
        if method == "GET":
            response = await client.get(url, headers=headers)
        elif method == "POST":
            response = await client.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = await client.put(url, headers=headers, json=data)
        return response.json() if response.status_code == 200 else {"error": response.text}

@app.list_tools()
async def list_tools():
    return [
        # 会话管理
        Tool(
            name="start_session",
            description="开始一个新的 Claude Code 监控会话",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_description": {"type": "string", "description": "任务描述"},
                    "working_directory": {"type": "string", "description": "工作目录"}
                },
                "required": ["task_description"]
            }
        ),
        Tool(
            name="end_session",
            description="结束当前监控会话",
            inputSchema={
                "type": "object",
                "properties": {
                    "result": {"type": "string", "description": "执行结果摘要"}
                }
            }
        ),

        # 日志记录
        Tool(
            name="log_info",
            description="记录信息日志",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "日志内容"}
                },
                "required": ["message"]
            }
        ),
        Tool(
            name="log_action",
            description="记录执行动作（如读取文件、执行命令等）",
            inputSchema={
                "type": "object",
                "properties": {
                    "action_type": {"type": "string", "description": "动作类型：read, write, execute, api_call"},
                    "action_detail": {"type": "string", "description": "动作详情"},
                    "file_path": {"type": "string", "description": "相关文件路径（如有）"}
                },
                "required": ["action_type", "action_detail"]
            }
        ),
        Tool(
            name="log_error",
            description="记录错误日志",
            inputSchema={
                "type": "object",
                "properties": {
                    "error_message": {"type": "string", "description": "错误信息"},
                    "error_type": {"type": "string", "description": "错误类型"}
                },
                "required": ["error_message"]
            }
        ),

        # 代码变更追踪
        Tool(
            name="track_file_change",
            description="追踪文件变更",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "文件路径"},
                    "change_type": {"type": "string", "description": "变更类型：created, modified, deleted"},
                    "diff_summary": {"type": "string", "description": "变更摘要"}
                },
                "required": ["file_path", "change_type"]
            }
        ),

        # 指标记录
        Tool(
            name="record_metrics",
            description="记录执行指标",
            inputSchema={
                "type": "object",
                "properties": {
                    "tokens_used": {"type": "integer", "description": "使用的Token数量"},
                    "files_modified": {"type": "integer", "description": "修改的文件数量"},
                    "commands_executed": {"type": "integer", "description": "执行的命令数量"}
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    global current_session

    try:
        if name == "start_session":
            # 创建执行记录
            result = await api_request("POST", "/executions/agents/{agent_id}/execute", {
                "input_data": {
                    "task": arguments["task_description"],
                    "working_directory": arguments.get("working_directory", "."),
                    "started_at": datetime.now().isoformat()
                }
            })
            current_session = result.get("id")
            return [TextContent(type="text", text=f"监控会话已启动: {current_session}")]

        elif name == "end_session":
            if current_session:
                await api_request("POST", f"/executions/{current_session}/complete", {
                    "output_data": {
                        "result": arguments.get("result", "completed"),
                        "ended_at": datetime.now().isoformat()
                    }
                })
                session_id = current_session
                current_session = None
                return [TextContent(type="text", text=f"监控会话已结束: {session_id}")]
            return [TextContent(type="text", text="没有活动的监控会话")]

        elif name == "log_info":
            if current_session:
                await api_request("POST", f"/executions/{current_session}/logs", {
                    "level": "info",
                    "message": arguments["message"]
                })
            return [TextContent(type="text", text=f"[INFO] {arguments['message']}")]

        elif name == "log_action":
            if current_session:
                await api_request("POST", f"/executions/{current_session}/logs", {
                    "level": "info",
                    "message": f"[{arguments['action_type'].upper()}] {arguments['action_detail']}",
                    "metadata": {
                        "action_type": arguments["action_type"],
                        "file_path": arguments.get("file_path")
                    }
                })
            return [TextContent(type="text", text=f"[ACTION] {arguments['action_type']}: {arguments['action_detail']}")]

        elif name == "log_error":
            if current_session:
                await api_request("POST", f"/executions/{current_session}/logs", {
                    "level": "error",
                    "message": arguments["error_message"],
                    "metadata": {
                        "error_type": arguments.get("error_type", "unknown")
                    }
                })
            return [TextContent(type="text", text=f"[ERROR] {arguments['error_message']}")]

        elif name == "track_file_change":
            if current_session:
                await api_request("POST", f"/executions/{current_session}/logs", {
                    "level": "info",
                    "message": f"[FILE_{arguments['change_type'].upper()}] {arguments['file_path']}",
                    "metadata": {
                        "change_type": arguments["change_type"],
                        "file_path": arguments["file_path"],
                        "diff_summary": arguments.get("diff_summary", "")
                    }
                })
            return [TextContent(type="text", text=f"[FILE] {arguments['change_type']}: {arguments['file_path']}")]

        elif name == "record_metrics":
            if current_session:
                for key, value in arguments.items():
                    if value is not None:
                        await api_request("POST", f"/executions/{current_session}/metrics", {
                            "metric_name": key,
                            "metric_value": float(value),
                            "unit": "count"
                        })
            return [TextContent(type="text", text=f"[METRICS] {arguments}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

    return [TextContent(type="text", text="Unknown tool")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

### 步骤2：配置 Claude Code

编辑 Claude Code 配置文件 `~/.claude/config.json`：

```json
{
  "mcpServers": {
    "claude-monitor": {
      "command": "python3",
      "args": ["/opt/claude-monitor/mcp_server.py"],
      "env": {
        "API_BASE": "http://your-server:8000/api",
        "API_TOKEN": "your-jwt-token"
      }
    }
  }
}
```

### 步骤3：在 Agent Manager 中创建监控 Agent

通过 API 或界面创建一个监控类型的 Agent：

```bash
curl -X POST http://localhost:8000/api/agents \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Claude Code Monitor",
    "description": "监控 Claude Code 执行过程",
    "agent_type": "mcp",
    "config": {
      "server_command": "python3 /opt/claude-monitor/mcp_server.py"
    }
  }'
```

### 步骤4：使用监控

启动 Claude Code 后，系统会自动记录：

- 执行的任务描述
- 读取/修改的文件
- 执行的命令
- 错误信息
- Token 使用量

---

## 方案二：直接 API 调用监控

如果你想在 Claude Code 执行过程中手动记录，可以直接调用 API：

### 获取 Token

```bash
# 登录获取 Token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### 创建执行记录

```bash
# 开始执行
curl -X POST http://localhost:8000/api/executions/agents/{agent_id}/execute \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_data": {"task": "修复登录页面的bug"}}'

# 添加日志
curl -X POST http://localhost:8000/api/executions/{execution_id}/logs \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"level": "info", "message": "读取文件: src/login.tsx"}'
```

---

## 方案三：Webhook 实时推送

配置 Agent Manager 的 WebSocket 接收实时更新：

### 前端监控页面

访问 `http://your-server/agent/monitor` 可以实时查看：

- 正在执行的 Claude Code 任务
- 实时日志滚动
- 文件变更列表
- 执行统计

### WebSocket 连接

```javascript
// 连接 WebSocket
const ws = new WebSocket('ws://your-server/agent/ws');

// 接收实时更新
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('收到更新:', data);

  if (data.type === 'execution_update') {
    // 更新执行状态
  } else if (data.type === 'log_update') {
    // 添加新日志
  }
};
```

---

## 监控数据示例

### 执行记录

```json
{
  "id": "uuid",
  "status": "running",
  "input_data": {
    "task": "实现用户登录功能",
    "working_directory": "/project"
  },
  "started_at": "2026-02-19T12:00:00",
  "logs": [
    {"level": "info", "message": "[READ] src/auth.ts"},
    {"level": "info", "message": "[EXECUTE] npm test"},
    {"level": "info", "message": "[FILE_MODIFIED] src/login.tsx"}
  ]
}
```

### 统计指标

- 总执行次数
- 成功率
- 平均执行时间
- Token 消耗统计
- 文件修改频率

---

## 最佳实践

1. **每次 Claude Code 任务开始时调用 `start_session`**
2. **每个重要操作后调用 `log_action`**
3. **文件变更时调用 `track_file_change`**
4. **遇到错误时调用 `log_error`**
5. **任务结束时调用 `end_session` 并传入结果**

这样可以在 Agent Manager 中完整追踪 Claude Code 的执行过程！
