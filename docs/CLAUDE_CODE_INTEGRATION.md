# Claude Code 对接指南

本文档介绍如何将 Claude Code 与智能体管理系统对接。

## 方式一：通过 MCP Server 对接（推荐）

Claude Code 支持 Model Context Protocol (MCP)，可以创建 MCP Server 来提供工具调用能力。

### 1. 创建 MCP Server

在服务器上创建一个 MCP Server：

```python
# mcp_server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import asyncio

app = Server("agent-manager")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="execute_agent",
            description="执行智能体管理系统中的Agent",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID"},
                    "input": {"type": "object", "description": "输入参数"}
                },
                "required": ["agent_id"]
            }
        ),
        Tool(
            name="list_agents",
            description="列出所有可用的智能体",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_execution_status",
            description="获取执行状态",
            inputSchema={
                "type": "object",
                "properties": {
                    "execution_id": {"type": "string", "description": "Execution ID"}
                },
                "required": ["execution_id"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    import httpx

    base_url = "http://localhost:8000/api"

    async with httpx.AsyncClient() as client:
        if name == "execute_agent":
            response = await client.post(
                f"{base_url}/executions/agents/{arguments['agent_id']}/execute",
                json={"input_data": arguments.get("input", {})}
            )
            return [TextContent(type="text", text=response.text)]

        elif name == "list_agents":
            response = await client.get(f"{base_url}/agents")
            return [TextContent(type="text", text=response.text)]

        elif name == "get_execution_status":
            response = await client.get(
                f"{base_url}/executions/{arguments['execution_id']}"
            )
            return [TextContent(type="text", text=response.text)]

    return [TextContent(type="text", text="Unknown tool")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. 配置 Claude Code

在 Claude Code 配置文件中添加 MCP Server：

```json
// ~/.claude/config.json
{
  "mcpServers": {
    "agent-manager": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"],
      "env": {}
    }
  }
}
```

### 3. 使用

启动 Claude Code 后，可以直接调用：

```bash
# Claude Code 中使用
> 请列出所有可用的智能体
> 请执行ID为xxx的智能体，输入参数为...
```

---

## 方式二：通过 Anthropic API 对接

创建一个 Anthropic/Claude 类型的 Agent。

### 1. 后端添加 Claude Agent 类型

已在系统中支持，配置示例：

```json
{
  "name": "Claude 3.5 Sonnet",
  "description": "使用 Claude 3.5 Sonnet 模型",
  "agent_type": "anthropic",
  "config": {
    "api_key": "sk-ant-xxx",
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 4096,
    "temperature": 0.7,
    "system_prompt": "你是一个有帮助的AI助手。"
  }
}
```

### 2. 后端执行器实现

```python
# backend/app/services/execution_service.py

async def execute_anthropic_agent(self, agent: Agent, input_data: dict) -> dict:
    """执行 Anthropic Claude Agent"""
    import anthropic

    client = anthropic.Anthropic(api_key=agent.config.get("api_key"))

    message = client.messages.create(
        model=agent.config.get("model", "claude-3-5-sonnet-20241022"),
        max_tokens=agent.config.get("max_tokens", 4096),
        temperature=agent.config.get("temperature", 0.7),
        system=agent.config.get("system_prompt", ""),
        messages=[
            {"role": "user", "content": input_data.get("message", "")}
        ]
    )

    return {
        "response": message.content[0].text,
        "usage": {
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens
        }
    }
```

---

## 方式三：通过 CLI 命令对接

直接调用 Claude Code CLI 工具。

### 1. 创建 CLI 类型 Agent

```json
{
  "name": "Claude Code CLI",
  "description": "调用 Claude Code CLI 执行任务",
  "agent_type": "cli",
  "config": {
    "command": "claude",
    "args": ["--print"],
    "timeout": 300,
    "env": {
      "ANTHROPIC_API_KEY": "sk-ant-xxx"
    }
  }
}
```

### 2. 后端执行器实现

```python
# backend/app/services/execution_service.py

import asyncio

async def execute_cli_agent(self, agent: Agent, input_data: dict) -> dict:
    """执行 CLI 类型 Agent"""
    config = agent.config
    command = config.get("command", "")
    args = config.get("args", [])
    timeout = config.get("timeout", 300)
    env = config.get("env", {})

    # 准备输入
    input_text = input_data.get("message", "")

    # 执行命令
    process = await asyncio.create_subprocess_exec(
        command,
        *args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, **env}
    )

    stdout, stderr = await asyncio.wait_for(
        process.communicate(input_text.encode()),
        timeout=timeout
    )

    return {
        "stdout": stdout.decode(),
        "stderr": stderr.decode(),
        "return_code": process.returncode
    }
```

---

## 方式四：Webhook 对接

通过 Webhook 调用 Claude Code 服务。

### 1. 部署 Claude Code 服务

创建一个简单的 Flask/FastAPI 服务包装 Claude Code：

```python
# claude_service.py
from fastapi import FastAPI
from pydantic import BaseModel
import subprocess

app = FastAPI()

class ExecuteRequest(BaseModel):
    message: str
    timeout: int = 300

@app.post("/execute")
async def execute(req: ExecuteRequest):
    result = subprocess.run(
        ["claude", "--print"],
        input=req.message,
        capture_output=True,
        text=True,
        timeout=req.timeout
    )
    return {
        "output": result.stdout,
        "error": result.stderr
    }
```

### 2. 创建 Webhook Agent

```json
{
  "name": "Claude Code Webhook",
  "description": "通过 Webhook 调用 Claude Code",
  "agent_type": "custom",
  "config": {
    "webhook_url": "http://your-server:8080/execute",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json"
    },
    "timeout": 300
  }
}
```

---

## 使用示例

### 在 Claude Code 中使用

```bash
# 1. 配置 MCP Server
claude config set mcp.agent-manager.command "python /path/to/mcp_server.py"

# 2. 启动 Claude Code
claude

# 3. 在对话中使用
> 使用 list_agents 工具查看所有智能体
> 使用 execute_agent 工具执行智能体 ID 为 xxx 的任务
```

### 通过 API 调用

```bash
# 执行 Agent
curl -X POST http://localhost:8000/api/executions/agents/{agent_id}/execute \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"input_data": {"message": "请帮我分析这段代码..."}}'

# 查看执行结果
curl http://localhost:8000/api/executions/{execution_id} \
  -H "Authorization: Bearer {token}"
```

---

## 推荐方案

| 场景 | 推荐方案 |
|------|---------|
| Claude Code 本地使用 | MCP Server 对接 |
| 服务器端批量执行 | Anthropic API 对接 |
| 已有 Claude Code CLI | CLI 命令对接 |
| 分布式部署 | Webhook 对接 |

---

## 完整示例：MCP Server 集成

创建完整的 MCP Server 与 Agent Manager 集成：

```python
#!/usr/bin/env python3
"""
Agent Manager MCP Server
用于 Claude Code 与智能体管理系统的集成
"""

import asyncio
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 配置
API_BASE = "http://localhost:8000/api"
API_TOKEN = "your-jwt-token"

app = Server("agent-manager")

# HTTP 客户端
async def api_request(method: str, path: str, data: dict = None):
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    async with httpx.AsyncClient() as client:
        if method == "GET":
            response = await client.get(f"{API_BASE}{path}", headers=headers)
        elif method == "POST":
            response = await client.post(
                f"{API_BASE}{path}",
                headers=headers,
                json=data
            )
        return response.json()

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="agent_list",
            description="列出所有智能体",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="agent_get",
            description="获取智能体详情",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"}
                },
                "required": ["agent_id"]
            }
        ),
        Tool(
            name="agent_execute",
            description="执行智能体",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "message": {"type": "string"}
                },
                "required": ["agent_id", "message"]
            }
        ),
        Tool(
            name="execution_status",
            description="获取执行状态",
            inputSchema={
                "type": "object",
                "properties": {
                    "execution_id": {"type": "string"}
                },
                "required": ["execution_id"]
            }
        ),
        Tool(
            name="execution_logs",
            description="获取执行日志",
            inputSchema={
                "type": "object",
                "properties": {
                    "execution_id": {"type": "string"}
                },
                "required": ["execution_id"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "agent_list":
            result = await api_request("GET", "/agents")
            return [TextContent(type="text", text=str(result))]

        elif name == "agent_get":
            result = await api_request(
                "GET",
                f"/agents/{arguments['agent_id']}"
            )
            return [TextContent(type="text", text=str(result))]

        elif name == "agent_execute":
            result = await api_request(
                "POST",
                f"/executions/agents/{arguments['agent_id']}/execute",
                {"input_data": {"message": arguments["message"]}}
            )
            return [TextContent(type="text", text=str(result))]

        elif name == "execution_status":
            result = await api_request(
                "GET",
                f"/executions/{arguments['execution_id']}"
            )
            return [TextContent(type="text", text=str(result))]

        elif name == "execution_logs":
            result = await api_request(
                "GET",
                f"/executions/{arguments['execution_id']}/logs"
            )
            return [TextContent(type="text", text=str(result))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

    return [TextContent(type="text", text="Unknown tool")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

保存为 `mcp_agent_manager.py`，然后在 Claude Code 配置中添加即可使用。
