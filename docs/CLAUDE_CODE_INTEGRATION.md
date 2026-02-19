# Claude Code 对接指南

本文档介绍如何将 Claude Code 与智能体管理系统对接。

## 方式一：通过 MCP Server 对接（推荐）

Claude Code 支持 Model Context Protocol (MCP)，可以创建 MCP Server 来提供工具调用能力。

### 1. MCP Server 文件

完整的 MCP Server 已创建在 `mcp/agent_manager_mcp.py`，提供以下工具：

| 工具名称 | 说明 |
|---------|------|
| `agent_list` | 列出所有智能体（龙虾池） |
| `agent_get` | 获取智能体详情 |
| `agent_create` | 创建新的智能体（养一只新龙虾） |
| `agent_update` | 更新智能体配置 |
| `agent_delete` | 删除智能体（放生龙虾） |
| `agent_toggle` | 启用/禁用智能体 |
| `agent_execute` | 执行智能体（派龙虾干活） |
| `execution_status` | 查看执行状态 |
| `execution_logs` | 查看执行日志 |
| `execution_list` | 列出执行记录 |
| `execution_cancel` | 取消执行 |
| `group_list` | 列出智能体群组（龙虾群） |
| `group_create` | 创建智能体群组 |
| `group_execute` | 执行群组（派遣龙虾群） |
| `config_export` | 导出所有配置 |
| `config_import` | 导入配置 |
| `metrics_summary` | 获取执行统计 |
| `agent_metrics` | 获取智能体指标 |

### 2. 安装依赖

```bash
pip install mcp httpx
```

### 3. 配置 Claude Code

在 Claude Code 配置文件中添加 MCP Server：

```json
// ~/.claude/settings.json 或项目级 .claude/settings.local.json
{
  "mcpServers": {
    "agent-manager": {
      "command": "python3",
      "args": ["/mnt/pzm/open-claude-ui/mcp/agent_manager_mcp.py"],
      "env": {
        "AGENT_MANAGER_URL": "http://localhost:8000/api",
        "AGENT_MANAGER_TOKEN": "your-jwt-token-here"
      }
    }
  }
}
```

**配置说明：**
- `AGENT_MANAGER_URL`: Agent Manager API 地址
- `AGENT_MANAGER_TOKEN`: JWT 认证令牌（通过登录 API 获取）

### 4. 获取 JWT Token

```bash
# 登录获取 token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}' \
  | jq -r '.access_token'
```

### 5. 使用示例

启动 Claude Code 后，可以直接调用：

```bash
# Claude Code 中使用
> 请列出所有可用的智能体
> 请执行ID为xxx的智能体，输入消息为"帮我分析这段代码"
> 查看执行ID为yyy的状态
> 创建一个新的OpenAI类型智能体
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

## MCP Server 源码

完整的 MCP Server 实现位于: `mcp/agent_manager_mcp.py`

### 工具列表

| 类别 | 工具 | 说明 |
|------|------|------|
| 智能体管理 | agent_list, agent_get, agent_create, agent_update, agent_delete, agent_toggle | CRUD操作 |
| 智能体执行 | agent_execute | 派龙虾干活 |
| 执行管理 | execution_status, execution_logs, execution_list, execution_cancel | 执行监控 |
| 群组管理 | group_list, group_create, group_execute | 龙虾群管理 |
| 配置管理 | config_export, config_import | 配置导入导出 |
| 监控统计 | metrics_summary, agent_metrics | 统计指标 |

### 在本项目中使用

本项目已配置 MCP Server，Claude Code 可以直接管理智能体：

```bash
# 在当前项目中，Claude Code 可以使用以下命令：
> 使用 agent_list 工具查看所有智能体
> 使用 agent_create 工具创建一个新智能体
> 使用 agent_execute 工具派智能体执行任务
```
