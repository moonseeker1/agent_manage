# Agent 管理系统架构设计文档

## 概述

本文档描述 Agent 管理系统的两种应用模式和整体架构设计：
- **模式 A**: Claude Code 配套 MCP Server - 为用户提供 RAG 检索增强能力
- **模式 B**: 多 Claude Code 集群管理 - 通过 MCP 统一调度多个 Claude Code 实例

---

## 模式 A: Claude Code 配套 MCP Server

### 1. 业务场景

用户在使用 Claude Code 进行开发时，需要：
- 查询项目文档、技术规范
- 检索代码库中的相关实现
- 获取业务知识库信息
- 将检索结果注入到 Claude Code 上下文中

### 2. 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                         Claude Code                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    MCP Client                            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │ rag-search  │  │rag-enhanced │  │  knowledge  │     │   │
│  │  │             │  │   -chat     │  │   -base     │     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────┘
                               │ MCP Protocol (stdio/SSE)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RAG MCP Server                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    MCP Tools                             │   │
│  │  • search_documents(query, collection)                   │   │
│  │  • search_code(query, language, repo)                    │   │
│  │  • get_context(topic, depth)                             │   │
│  │  • list_collections()                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   RAG Engine                             │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │   │
│  │  │ Embedding│  │  Vector  │  │  Rerank  │              │   │
│  │  │  Model   │──│  Store   │──│  Model   │              │   │
│  │  └──────────┘  └──────────┘  └──────────┘              │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
   ┌──────────┐         ┌──────────┐         ┌──────────┐
   │ Milvus/  │         │PostgreSQL│         │  MinIO/  │
   │Qdrant    │         │  (元数据) │         │  S3      │
   │(向量库)   │         │          │         │ (文件存储)│
   └──────────┘         └──────────┘         └──────────┘
```

### 3. MCP Server 实现

#### 3.1 配置文件 (settings.json)

```json
{
  "mcpServers": {
    "rag-server": {
      "command": "/path/to/python3",
      "args": ["/path/to/rag_mcp_server.py"],
      "env": {
        "RAG_API_URL": "http://your-rag-server:8000/api",
        "RAG_API_TOKEN": "your-jwt-token",
        "DEFAULT_COLLECTION": "project_docs",
        "MAX_RESULTS": 10
      }
    }
  }
}
```

#### 3.2 MCP Tools 定义

| 工具名称 | 功能 | 参数 |
|---------|------|------|
| `search_documents` | 搜索文档库 | query, collection, top_k |
| `search_code` | 搜索代码库 | query, language, repo |
| `get_context` | 获取上下文 | topic, depth |
| `list_collections` | 列出知识库 | - |
| `add_document` | 添加文档 | content, metadata |
| `get_similar` | 相似文档 | doc_id, top_k |

#### 3.3 使用流程

```
用户提问 → Claude Code 调用 MCP 工具
                ↓
         search_documents(query)
                ↓
         RAG Server 检索
                ↓
         返回相关文档片段
                ↓
         Claude Code 整合回答
```

### 4. 与现有系统集成

```python
# rag_mcp_server.py 核心逻辑

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import httpx
import os

RAG_API_URL = os.getenv("RAG_API_URL", "http://localhost:8000/api")
RAG_API_TOKEN = os.getenv("RAG_API_TOKEN", "")

app = Server("rag-server")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="search_documents",
            description="搜索文档知识库，返回与查询最相关的文档片段",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索查询"},
                    "collection": {"type": "string", "description": "知识库集合名"},
                    "top_k": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="search_code",
            description="搜索代码库，查找相关代码实现",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "代码搜索查询"},
                    "language": {"type": "string", "description": "编程语言"},
                    "repo": {"type": "string", "description": "代码仓库名"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="enhanced_chat",
            description="RAG增强对话，结合知识库生成回答",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "用户问题"},
                    "use_context": {"type": "boolean", "default": True}
                },
                "required": ["query"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    headers = {
        "Authorization": f"Bearer {RAG_API_TOKEN}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        if name == "search_documents":
            response = await client.post(
                f"{RAG_API_URL}/search",
                headers=headers,
                json={
                    "query": arguments["query"],
                    "collection": arguments.get("collection", "default"),
                    "top_k": arguments.get("top_k", 5)
                }
            )
        elif name == "search_code":
            response = await client.post(
                f"{RAG_API_URL}/code/search",
                headers=headers,
                json=arguments
            )
        elif name == "enhanced_chat":
            response = await client.post(
                f"{RAG_API_URL}/chat/enhanced",
                headers=headers,
                json=arguments
            )

        result = response.json()
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 模式 B: 多 Claude Code 集群管理

### 1. 业务场景

- 统一管理多个 Claude Code 实例
- 下发任务到不同的 Agent
- 监控执行状态和结果
- 实现任务编排和工作流

### 2. 架构设计

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           管理控制台 (Web UI)                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │  Dashboard │  │ Agents  │  │Commands │  │Monitor  │  │Workflows│     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Agent Manager Backend                                │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         API Layer                                     │  │
│  │  • REST API (FastAPI)  • WebSocket (实时推送)  • MCP Protocol       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      Service Layer                                    │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐        │  │
│  │  │   Agent    │ │  Command   │ │  Workflow  │ │   Task     │        │  │
│  │  │  Service   │ │  Service   │ │  Service   │ │  Scheduler │        │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      Message Queue (Redis)                            │  │
│  │  ┌─────────────────────────────────────────────────────────────┐    │  │
│  │  │  Priority Queue (ZSET)  │  Result Queue  │  Timeout Monitor │    │  │
│  │  └─────────────────────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
     ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
     │  Claude Code #1 │    │  Claude Code #2 │    │  Claude Code #N │
     │  ┌───────────┐  │    │  ┌───────────┐  │    │  ┌───────────┐  │
     │  │    MCP    │  │    │  │    MCP    │  │    │  │    MCP    │  │
     │  │  Client   │  │    │  │  Client   │  │    │  │  Client   │  │
     │  └───────────┘  │    │  └───────────┘  │    │  └───────────┘  │
     │  ┌───────────┐  │    │  ┌───────────┐  │    │  ┌───────────┐  │
     │  │  Agent    │  │    │  │  Agent    │  │    │  │  Agent    │  │
     │  │  Manager  │  │    │  │  Manager  │  │    │  │  Manager  │  │
     │  │  MCP      │  │    │  │  MCP      │  │    │  │  MCP      │  │
     │  │  Server   │  │    │  │  Server   │  │    │  │  Server   │  │
     │  └───────────┘  │    │  └───────────┘  │    │  └───────────┘  │
     │  Agent ID: A1   │    │  Agent ID: A2   │    │  Agent ID: AN   │
     └─────────────────┘    └─────────────────┘    └─────────────────┘
              │                       │                       │
              └───────────────────────┼───────────────────────┘
                                      │
                                      ▼
                           ┌─────────────────┐
                           │     Redis       │
                           │  Message Queue  │
                           └─────────────────┘
```

### 3. 核心流程

#### 3.1 指令下发流程

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  用户   │────▶│ 管理后台 │────▶│  API    │────▶│  Redis  │────▶│ Agent   │
│         │     │         │     │         │     │  Queue  │     │         │
└─────────┘     └─────────┘     └─────────┘     └─────────┘     └─────────┘
    │               │               │               │               │
    │  创建任务     │               │               │               │
    │──────────────▶               │               │               │
    │               │  POST /commands              │               │
    │               │──────────────▶               │               │
    │               │               │  LPUSH/ZADD  │               │
    │               │               │──────────────▶               │
    │               │               │               │  轮询获取    │
    │               │               │               │◀──────────────│
    │               │               │               │  执行任务    │
    │               │               │               │◀──────────────│
    │               │  WebSocket 推送状态          │               │
    │               │◀──────────────               │  提交结果    │
    │               │               │               │◀──────────────│
    │  查看结果     │               │               │               │
    │◀──────────────│               │               │               │
```

#### 3.2 Agent 状态同步

```python
# Claude Code 端 MCP Server 配置
{
  "mcpServers": {
    "agent-manager": {
      "command": "python3",
      "args": ["/path/to/agent_manager_mcp.py"],
      "env": {
        "AGENT_MANAGER_URL": "http://manager-server:8000/api",
        "AGENT_MANAGER_TOKEN": "jwt-token",
        "AGENT_ID": "unique-agent-id",
        "POLL_INTERVAL": "30"  # 轮询间隔(秒)
      }
    }
  }
}
```

#### 3.3 Agent 生命周期

```
┌────────────────────────────────────────────────────────────────────┐
│                        Agent 生命周期                               │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐        │
│  │  注册   │───▶│  在线   │───▶│  工作   │───▶│  离线   │        │
│  │Register │    │ Online  │    │ Working │    │Offline  │        │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘        │
│       │              │              │              │               │
│       │              │              │              │               │
│       ▼              ▼              ▼              ▼               │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐        │
│  │上报配置 │    │心跳保活 │    │执行任务 │    │任务重分配│        │
│  │同步权限 │    │获取指令 │    │上报进度 │    │清理资源 │        │
│  │注册MCP  │    │状态同步 │    │提交结果 │    │         │        │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘        │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 4. 任务调度模型

#### 4.1 优先级队列

```python
# Redis ZSET 实现优先级队列
class CommandQueue:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def push_command(self, agent_id: str, command: dict, priority: int = 0):
        """
        priority: 0-100, 数值越大优先级越高
        - 0-20: 低优先级 (日常任务)
        - 21-50: 普通优先级 (常规任务)
        - 51-80: 高优先级 (紧急任务)
        - 81-100: 最高优先级 (系统指令)
        """
        score = priority * 1000000 + time.time()
        await self.redis.zadd(f"cmd:{agent_id}", {json.dumps(command): score})

    async def pop_command(self, agent_id: str) -> Optional[dict]:
        # 获取最高优先级(最大score)的命令
        result = await self.redis.zpopmax(f"cmd:{agent_id}")
        if result:
            return json.loads(result[0][0])
        return None
```

#### 4.2 任务类型定义

```python
class CommandType(Enum):
    # 系统控制类
    PAUSE = "pause"           # 暂停当前工作
    RESUME = "resume"         # 恢复工作
    CANCEL = "cancel"         # 取消当前任务
    RELOAD_CONFIG = "reload"  # 重载配置

    # 开发任务类
    CODE_REVIEW = "code_review"      # 代码审查
    FIX_BUG = "fix_bug"              # 修复Bug
    IMPLEMENT_FEATURE = "feature"    # 实现功能
    WRITE_TEST = "write_test"        # 编写测试
    REFACTOR = "refactor"            # 重构代码

    # 通用任务类
    SHELL_COMMAND = "shell"   # 执行Shell命令
    FILE_OPERATION = "file"   # 文件操作
    API_CALL = "api"          # API调用

    # 工作流类
    WORKFLOW = "workflow"     # 执行工作流
    PARALLEL = "parallel"     # 并行任务
```

### 5. 工作流编排

#### 5.1 工作流定义

```yaml
# workflow_example.yaml
name: "代码审查和修复流程"
version: "1.0"
description: "自动化的代码审查、问题修复和测试流程"

triggers:
  - type: schedule
    cron: "0 9 * * *"  # 每天早上9点
  - type: webhook
    path: "/webhook/pr-created"

steps:
  - id: review
    agent: "code-reviewer"
    action: "code_review"
    input:
      repo: "${trigger.repo}"
      branch: "${trigger.branch}"
    on_success: fix_issues
    on_failure: notify

  - id: fix_issues
    agent: "bug-fixer"
    action: "fix_bug"
    input:
      issues: "${review.result.issues}"
    on_success: run_tests
    on_failure: notify

  - id: run_tests
    agent: "tester"
    action: "write_test"
    input:
      changed_files: "${fix_issues.result.changed_files}"
    on_success: notify
    on_failure: notify

output:
  success:
    message: "工作流完成"
    details: "${run_tests.result}"
  failure:
    message: "工作流失败"
    step: "${failed_step}"
```

#### 5.2 工作流执行引擎

```
┌─────────────────────────────────────────────────────────────────┐
│                     Workflow Engine                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Workflow Parser                       │   │
│  │  • YAML/JSON 解析  • 步骤依赖分析  • 变量替换           │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    State Machine                         │   │
│  │  ┌───────┐   ┌───────┐   ┌───────┐   ┌───────┐        │   │
│  │  │ Init  │──▶│Running│──▶│Waiting│──▶│ Done  │        │   │
│  │  └───────┘   └───────┘   └───────┘   └───────┘        │   │
│  │                   │           │                         │   │
│  │                   ▼           ▼                         │   │
│  │              ┌───────┐   ┌───────┐                     │   │
│  │              │ Error │   │Paused │                     │   │
│  │              └───────┘   └───────┘                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Task Dispatcher                       │   │
│  │  • Agent 选择  • 负载均衡  • 失败重试  • 超时控制     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 6. 监控与可观测性

#### 6.1 监控指标

```python
# Prometheus 指标定义
from prometheus_client import Counter, Histogram, Gauge

# Agent 指标
agent_total = Gauge('agent_total', 'Total number of agents', ['status'])
agent_heartbeat = Gauge('agent_heartbeat_timestamp', 'Last heartbeat time', ['agent_id'])

# 任务指标
command_total = Counter('command_total', 'Total commands', ['type', 'status'])
command_duration = Histogram('command_duration_seconds', 'Command execution time', ['type'])
command_queue_size = Gauge('command_queue_size', 'Pending commands in queue', ['agent_id'])

# 工作流指标
workflow_total = Counter('workflow_total', 'Total workflows', ['name', 'status'])
workflow_duration = Histogram('workflow_duration_seconds', 'Workflow execution time', ['name'])
```

#### 6.2 日志采集

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Agent     │     │   Backend   │     │   Redis     │
│   Logs      │     │   Logs      │     │   Logs      │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Filebeat   │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │Logstash/    │
                    │Vector       │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │Elasticsearch│
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Kibana/   │
                    │Grafana Loki │
                    └─────────────┘
```

---

## 系统集成方案

### 1. 两种模式融合架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              统一管理平台                                    │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                           Web Console                                  │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │ │
│  │  │RAG管理  │ │Agent管理│ │任务中心 │ │监控大屏 │ │工作流   │        │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘        │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
     ┌───────────────────────────────┐   ┌───────────────────────────────┐
     │      RAG Service (模式A)       │   │   Agent Manager (模式B)       │
     │  ┌─────────────────────────┐  │   │  ┌─────────────────────────┐  │
     │  │  Document Ingestion     │  │   │  │  Command Queue (Redis)  │  │
     │  │  Vector Embedding       │  │   │  │  Task Scheduler         │  │
     │  │  Semantic Search        │  │   │  │  Workflow Engine        │  │
     │  │  Reranking              │  │   │  │  Timeout Monitor        │  │
     │  └─────────────────────────┘  │   │  └─────────────────────────┘  │
     └───────────────────────────────┘   └───────────────────────────────┘
                    │                                   │
                    └─────────────────┬─────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
     ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
     │  Claude Code    │    │  Claude Code    │    │  Claude Code    │
     │  (RAG MCP)      │    │  (Agent MCP)    │    │  (Both MCP)     │
     │                 │    │                 │    │                 │
     │  search_docs    │    │  get_commands   │    │  search_docs    │
     │  search_code    │    │  submit_result  │    │  get_commands   │
     │                 │    │  report_status  │    │  submit_result  │
     └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2. MCP Server 配置合并

```json
{
  "mcpServers": {
    "rag-server": {
      "command": "/root/miniconda3/bin/python3",
      "args": ["/path/to/rag_mcp_server.py"],
      "env": {
        "RAG_API_URL": "http://your-rag-server:8000/api",
        "RAG_API_TOKEN": "your-rag-token"
      }
    },
    "agent-manager": {
      "command": "/root/miniconda3/bin/python3",
      "args": ["/path/to/agent_manager_mcp.py"],
      "env": {
        "AGENT_MANAGER_URL": "http://localhost:8000/api",
        "AGENT_MANAGER_TOKEN": "your-agent-token",
        "AGENT_ID": "unique-agent-id"
      }
    }
  }
}
```

### 3. 典型使用场景

#### 场景 1: 知识库增强的代码生成

```
1. 用户: "帮我实现用户认证模块"
2. Claude Code:
   - 调用 rag-server.search_docs("用户认证 最佳实践")
   - 获取项目规范和认证流程文档
   - 调用 rag-server.search_code("auth", language="python")
   - 参考现有代码实现
   - 生成符合项目规范的代码
```

#### 场景 2: 分布式任务执行

```
1. 管理员下发任务: "在所有前端Agent上执行 npm test"
2. Agent Manager:
   - 筛选所有前端类型的Agent
   - 创建优先级命令推送到各Agent队列
3. 各 Claude Code:
   - 通过 MCP 轮询获取命令
   - 执行 npm test
   - 上报执行结果
4. 管理员查看汇总报告
```

#### 场景 3: RAG + 任务编排

```
1. 用户: "根据最新的API文档，为用户模块生成测试用例"
2. Claude Code:
   - RAG检索最新API文档
   - 生成测试用例代码
   - 上报任务进度到管理系统
   - 管理系统记录审计日志
```

---

## 部署架构

### 1. 容器化部署

```yaml
# docker-compose.yml
version: '3.8'

services:
  # 后端服务
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/agent_manager
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  # 前端服务
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  # PostgreSQL
  postgres:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=agent_manager
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass

  # Redis
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  # RAG服务 (模式A)
  rag-server:
    build: ./rag-server
    ports:
      - "8001:8001"
    environment:
      - MILVUS_HOST=milvus
      - MILVUS_PORT=19530
    depends_on:
      - milvus

  # 向量数据库
  milvus:
    image: milvusdb/milvus:latest
    ports:
      - "19530:19530"
    volumes:
      - milvus_data:/var/lib/milvus

volumes:
  postgres_data:
  redis_data:
  milvus_data:
```

### 2. 高可用部署

```
                              ┌─────────────┐
                              │   Nginx     │
                              │  (LB/SSL)   │
                              └──────┬──────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
             ┌───────────┐   ┌───────────┐   ┌───────────┐
             │  Backend  │   │  Backend  │   │  Backend  │
             │   #1      │   │   #2      │   │   #3      │
             └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
                   │               │               │
                   └───────────────┼───────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
             ┌───────────┐ ┌───────────┐ ┌───────────┐
             │PostgreSQL │ │   Redis   │ │  Milvus   │
             │  Cluster  │ │  Cluster  │ │  Cluster  │
             └───────────┘ └───────────┘ └───────────┘
```

---

## 安全设计

### 1. 认证与授权

```
┌─────────────────────────────────────────────────────────────────┐
│                        安全架构                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     API Gateway                          │   │
│  │  • JWT Token 验证  • Rate Limiting  • IP 白名单         │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     RBAC 系统                            │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────────────────────┐ │   │
│  │  │  User   │──│  Role   │──│     Permission          │ │   │
│  │  └─────────┘  └─────────┘  │  • agent:create         │ │   │
│  │                            │  • command:send          │ │   │
│  │                            │  • workflow:execute      │ │   │
│  │                            │  • rag:search            │ │   │
│  │                            └─────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Agent 权限控制                         │   │
│  │  • allowed_commands  • allowed_paths  • blocked_paths  │   │
│  │  • max_execution_time  • rate_limiting                 │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2. 数据安全

- **传输加密**: HTTPS/TLS 1.3
- **存储加密**: 敏感数据 AES-256 加密
- **密钥管理**: 环境变量 + 密钥轮换
- **审计日志**: 所有操作可追溯

---

## 总结

| 特性 | 模式 A (RAG MCP) | 模式 B (Agent Manager) |
|------|-----------------|----------------------|
| 主要功能 | 知识检索增强 | 多Agent任务调度 |
| 使用场景 | 单用户知识辅助 | 多Agent集群管理 |
| 核心组件 | RAG Server, Vector DB | Redis Queue, Scheduler |
| 通信方式 | MCP (stdio) | MCP + WebSocket |
| 部署复杂度 | 低 | 中高 |
| 扩展性 | 知识库扩展 | Agent水平扩展 |

两种模式可以独立使用，也可以融合部署，实现**知识增强的多Agent协作系统**。
