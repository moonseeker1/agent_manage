# MCP 集成指南

本文档说明如何让 Claude Code 通过 MCP 协议与管理系统集成，实现配置下发、权限控制和实时监控。

## 架构概述

```
┌─────────────────┐      MCP Protocol       ┌─────────────────┐
│  管理系统        │ ◄──────────────────────► │  Claude Code    │
│  (Backend API)  │                          │  (Agent)        │
├─────────────────┤                          ├─────────────────┤
│ • Agent配置      │  1. get_my_config        │ • 启动时获取配置 │
│ • 权限控制       │  2. check_permission     │ • 执行前检查权限 │
│ • Skill/MCP绑定  │  3. report_activity      │ • 上报活动日志   │
│ • 实时指令       │  4. get_pending_commands │ • 拉取待执行指令 │
│ (Redis 队列)     │  5. submit_command_result│ • 提交执行结果   │
│                 │  6. report_command_progress│ • 报告执行进度  │
└─────────────────┘                          └─────────────────┘
```

## 指令下发架构

系统使用 Redis 作为消息队列中间件，实现指令的持久化和优先级管理：

```
管理员 UI → 后端 API → Redis 优先级队列 → MCP Server → Claude Code Agent
                                      ↓           ↓
                              (get_pending_commands)
                                      ↓
                              Agent 执行指令
                                      ↓
                              (submit_command_result)
                                      ↓
                              后端 API → 管理员 UI (WebSocket)
```

**Redis 数据结构**：
- `agent:commands:{agent_id}`: Sorted Set (优先级队列)
- `command:timeout:{agent_id}`: Sorted Set (超时监控)
- `command:result:{command_id}`: String (执行结果)

## 配置步骤

### 1. 在管理系统中创建 Agent

通过前端界面或 API 创建一个 Agent 记录，获取 Agent ID。

```bash
curl -X POST http://localhost:8000/api/agents \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Claude Code Instance 1",
    "description": "开发环境 Claude Code",
    "agent_type": "mcp",
    "config": {},
    "enabled": true
  }'
```

### 2. 配置 Agent 权限

在管理系统中配置 Agent 的权限、技能和 MCP 绑定：

- **权限**: bash/文件操作/网络访问
- **技能**: 代码生成、文件操作等
- **MCP绑定**: 可使用的 MCP 服务器

### 3. 配置 Claude Code

在 Claude Code 的配置文件中添加 MCP Server：

**macOS/Linux**: `~/.config/claude-code/settings.json`

```json
{
  "mcpServers": {
    "agent-manager": {
      "command": "python3",
      "args": ["/path/to/open-claude-ui/mcp/agent_manager_mcp.py"],
      "env": {
        "AGENT_MANAGER_URL": "http://localhost:8000/api",
        "AGENT_MANAGER_TOKEN": "your-jwt-token-here",
        "AGENT_ID": "your-agent-id-here"
      }
    }
  }
}
```

### 4. 获取 Token 和 Agent ID

```bash
# 登录获取 Token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 返回: {"access_token": "eyJ..."}

# 列出 Agent 获取 ID
curl http://localhost:8000/api/agents \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## MCP 工具列表

### 自我配置工具

| 工具 | 描述 |
|------|------|
| `get_my_config` | 获取当前 Agent 的完整配置 |
| `check_permission` | 检查是否有执行某操作的权限 |
| `report_activity` | 上报活动状态到管理系统 |
| `check_commands` | 检查待执行指令（旧版，建议使用 get_pending_commands） |
| `get_pending_commands` | 从 Redis 队列获取待执行指令（优先级排序） |
| `submit_command_result` | 提交指令执行结果 |
| `report_command_progress` | 报告指令执行进度 |
| `get_allowed_tools` | 获取允许使用的 MCP 工具列表 |
| `get_skill_config` | 获取指定技能的详细配置 |

### 管理工具

| 工具 | 描述 |
|------|------|
| `agent_list` | 列出所有智能体 |
| `agent_get` | 获取智能体详情 |
| `agent_create` | 创建新的智能体 |
| `agent_execute` | 执行智能体 |
| `group_list` | 列出智能体群组 |
| `group_execute` | 执行群组 |
| `skill_list` | 列出所有技能 |
| `mcp_server_list` | 列出 MCP 服务器 |

## 使用示例

### 1. 启动时获取配置

```
调用 get_my_config 工具获取:
- permission: 操作权限
- skills: 绑定的技能
- mcp_bindings: MCP 服务器绑定
- allowed_tools: 允许的工具
```

### 2. 执行前检查权限

```
调用 check_permission 工具:
{
  "action": "bash",
  "command": "npm install"
}

返回:
{
  "allowed": true,
  "reason": ""
}
```

### 3. 上报活动

```
调用 report_activity 工具:
{
  "action": "reading_file",
  "thought": "需要读取配置文件了解项目结构",
  "status": "progress"
}
```

### 4. 检查指令

```
调用 get_pending_commands 工具，从 Redis 队列获取指令:
{
  "limit": 10  // 可选，默认10条
}

返回:
{
  "commands": [
    {
      "id": "uuid-xxx",
      "type": "task",
      "content": {"command": "check logs"},
      "priority": 10,
      "timeout": 300,
      "timestamp": 1708857600000
    }
  ],
  "count": 1
}
```

### 5. 提交指令结果

```
执行完指令后，调用 submit_command_result 工具:
{
  "command_id": "uuid-xxx",
  "output": "日志检查完成，发现 5 个警告",
  "status": "success",  // 或 "error"
  "error_message": null
}
```

### 6. 报告进度

```
对于长耗时任务，可以定期调用 report_command_progress:
{
  "command_id": "uuid-xxx",
  "progress": 50,  // 0-100
  "message": "正在处理日志文件..."
}
```

## 权限配置说明

### 操作权限

| 权限 | 描述 |
|------|------|
| `allow_bash` | 允许执行 Bash 命令 |
| `allow_read` | 允许读取文件 |
| `allow_write` | 允许写入新文件 |
| `allow_edit` | 允许编辑现有文件 |
| `allow_web` | 允许网络访问 |

### 路径限制

- `allowed_paths`: 允许访问的路径列表
- `blocked_paths`: 禁止访问的路径列表

### 命令限制

- `allowed_commands`: 允许执行的命令列表
- `blocked_commands`: 禁止执行的命令列表

## Skill 配置

Skill 的 `config` 字段可以定义具体行为：

```json
{
  "name": "文件操作",
  "code": "file_operations",
  "config": {
    "allowed_extensions": [".py", ".js", ".ts", ".json"],
    "max_file_size": "1MB",
    "require_confirmation": true
  }
}
```

## 管理系统下发指令

管理员可以通过 API 或前端界面向 Agent 发送指令：

### API 发送指令

```bash
curl -X POST http://localhost:8000/api/agents/{agent_id}/commands \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "task",
    "content": {"command": "check logs"},
    "priority": 10,
    "timeout": 300,
    "max_retries": 3
  }'
```

**参数说明**：
- `type`: 指令类型
  - `pause`: 暂停当前工作
  - `cancel`: 取消当前任务
  - `task`: 下发新任务
  - `config_reload`: 要求重新加载配置
- `content`: 指令内容（JSON 对象）
- `priority`: 优先级（0-100，默认 0，数值越大越优先）
- `timeout`: 超时时间（秒，默认 300）
- `max_retries`: 最大重试次数（默认 3）

### 前端界面发送

访问 `/commands` 页面：
1. 点击"发送指令"按钮
2. 选择目标 Agent
3. 选择指令类型
4. 填写指令内容（JSON 格式）
5. 设置优先级和超时时间
6. 点击确认发送

### 查看指令状态

```bash
# 查询指令历史
curl http://localhost:8000/api/commands?agent_id={agent_id}&status=success

# 获取指令统计
curl http://localhost:8000/api/commands/stats/summary

# 重试失败的指令
curl -X POST http://localhost:8000/api/commands/{command_id}/retry

# 取消待执行的指令
curl -X POST http://localhost:8000/api/commands/{command_id}/cancel
```

### 指令状态

| 状态 | 说明 |
|------|------|
| `pending` | 待处理（在 Redis 队列中） |
| `executing` | 执行中 |
| `success` | 执行成功 |
| `error` | 执行失败 |
| `timeout` | 执行超时 |
| `cancelled` | 已取消 |

### 超时与重试

- 系统每 10 秒检查一次超时指令
- 超时指令会自动重试（最多 max_retries 次）
- 超过最大重试次数后状态变为 `timeout`

## 前端管理

访问管理系统前端进行可视化配置：

- **智能体管理**: `/agents` - 管理所有 Agent
- **配置面板**: 点击 Agent 的"配置"按钮
  - 操作权限标签页
  - 技能绑定标签页
  - MCP 服务标签页

## 故障排查

### Agent 无法连接管理系统

1. 检查 `AGENT_MANAGER_URL` 是否正确
2. 检查 `AGENT_MANAGER_TOKEN` 是否有效
3. 检查网络连接

### 配置不生效

1. 确认 `AGENT_ID` 配置正确
2. 调用 `get_my_config` 检查返回的配置
3. 配置有 60 秒缓存，等待缓存刷新

### 权限检查失败

1. 检查管理系统中 Agent 的权限配置
2. 确认路径/命令限制设置正确
3. 查看 `check_permission` 返回的 reason 字段
