# 智能体管理系统 (Agent Management System)

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18+-blue.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.109+-green.svg)](https://fastapi.tiangolo.com/)

一个全栈应用，用于管理和监控 AI 智能体。支持 MCP Server、OpenAI API 和自定义智能体类型，提供 RBAC 权限控制和智能体级别配置。

---

## 目录

1. [系统架构](#系统架构)
2. [业务逻辑](#业务逻辑)
3. [执行流程](#执行流程)
4. [数据模型](#数据模型)
5. [API 接口](#api-接口)
6. [前端页面](#前端页面)
7. [MCP 集成](#mcp-集成)
8. [开发指南](#开发指南)
9. [部署说明](#部署说明)

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户层 (User Layer)                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  Web 浏览器  │    │ Claude Code │    │  其他客户端  │    │  管理员界面  │  │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘  │
└─────────┼──────────────────┼──────────────────┼──────────────────┼─────────┘
          │                  │                  │                  │
          ▼                  ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           接入层 (Access Layer)                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         Nginx 反向代理                                 │  │
│  │  /agent/* → Frontend    /agent/api/* → Backend:8000                  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
          │                                           │
          ▼                                           ▼
┌─────────────────────────────┐    ┌─────────────────────────────────────────┐
│       前端 (Frontend)        │    │              后端 (Backend)              │
│  ┌───────────────────────┐  │    │  ┌───────────────────────────────────┐  │
│  │  React 18 + TS        │  │    │  │        FastAPI Application        │  │
│  │  Ant Design 5         │  │    │  ├───────────────────────────────────┤  │
│  │  Vite + Zustand       │  │    │  │  • REST API Endpoints             │  │
│  ├───────────────────────┤  │    │  │  • WebSocket Real-time            │  │
│  │  Pages:               │  │    │  │  • JWT Authentication             │  │
│  │  • Dashboard          │  │    │  │  • Async SQLAlchemy ORM           │  │
│  │  • Agents/Config      │  │    │  ├───────────────────────────────────┤  │
│  │  • Groups             │  │    │  │  Services:                        │  │
│  │  • Skills             │  │    │  │  • Executor (OpenAI/MCP/Custom)   │  │
│  │  • Permissions        │  │    │  │  • AgentService                   │  │
│  │  • MCP Servers        │  │    │  │  • ExecutionService               │  │
│  │  • Executions         │  │    │  └───────────────────────────────────┘  │
│  │  • Monitor            │  │    └─────────────────────────────────────────┘
│  └───────────────────────┘  │                    │
└─────────────────────────────┘                    │
                                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           数据层 (Data Layer)                                │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │   PostgreSQL    │    │     Redis       │    │    MCP Server   │         │
│  │   (主数据库)     │    │  (消息队列)     │    │   (MCP 协议)    │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                          ┌─────────────────┐                                │
│                          │  External API   │                                │
│                          │   (OpenAI等)    │                                │
│                          └─────────────────┘                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Ant Design 5 + Vite + Zustand |
| 后端 | Python 3.9+ + FastAPI + SQLAlchemy (async) + PostgreSQL + Redis |
| 通信 | REST API + WebSocket + MCP Protocol |
| 消息 | Redis Sorted Set (优先级队列) |
| 认证 | JWT (python-jose) + bcrypt |
| 部署 | Docker + Nginx |

---

## 业务逻辑

### 核心业务实体关系

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           用户与权限体系                                      │
│                                                                              │
│   User ──────< user_roles >────── Role ──────< role_permissions >──────     │
│     │                               │                               │        │
│     │                               │                               │        │
│     └───────────────────────────────┴───────────────────────────────┘        │
│                                       │                                      │
│                                       ▼                                      │
│                                Permission                                     │
│                                    │                                          │
│   Skill ──────< skill_permissions >┘                                         │
│     │                                                                         │
│     └────────────< agent_skill_bindings >──────────┐                         │
│                                                     │                         │
└─────────────────────────────────────────────────────┼─────────────────────────┘
                                                      │
┌─────────────────────────────────────────────────────┼─────────────────────────┐
│                           智能体体系                │                         │
│                                                     │                         │
│   Agent ────────────────────────────────────────────┤                         │
│     │                                               │                         │
│     ├──< agent_permission (1:1) >──────────────────┤ 操作权限控制             │
│     │                                               │                         │
│     ├──< agent_skill_bindings >────────────────────┘ 技能绑定                 │
│     │                                                                         │
│     ├──< agent_mcp_bindings >────── MCPServer ────< mcp_tools                 │
│     │                                                                         │
│     ├──< agent_commands >─────────── AgentCommand (Redis Queue)               │
│     │                                                                         │
│     ├──< agent_group_members >───── AgentGroup                                │
│     │                                                                         │
│     └──< executions >────────────── Execution ────< execution_logs           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 智能体配置体系

```
┌─────────────────────────────────────────────────────────────────┐
│                      Agent Configuration                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  AgentPermission                         │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ 工具权限                                          │    │   │
│  │  │ • allow_bash   - 允许执行Bash命令                 │    │   │
│  │  │ • allow_read   - 允许读取文件                     │    │   │
│  │  │ • allow_write  - 允许写入文件                     │    │   │
│  │  │ • allow_edit   - 允许编辑文件                     │    │   │
│  │  │ • allow_web    - 允许网络访问                     │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ 路径限制                                          │    │   │
│  │  │ • allowed_paths  - 允许访问的路径                 │    │   │
│  │  │ • blocked_paths  - 禁止访问的路径                 │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │ 执行限制                                          │    │   │
│  │  │ • max_execution_time - 最大执行时间(秒)           │    │   │
│  │  │ • max_output_size    - 最大输出大小(KB)           │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  MCP Bindings                            │   │
│  │  MCPServer ── tools: [tool1, tool2] ── enabled          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 执行流程

### 1. 智能体执行流程

```
用户请求                 后端处理                      执行器                    外部服务
   │                        │                           │                          │
   │  POST /executions/     │                           │                          │
   │  agents/{id}/execute   │                           │                          │
   │───────────────────────►│                           │                          │
   │                        │                           │                          │
   │                        │ 1. 验证权限               │                          │
   │                        │ 2. 创建 Execution         │                          │
   │                        │    (status: pending)      │                          │
   │                        │ 3. asyncio.create_task()  │                          │
   │                        │──────────────────────────►│                          │
   │                        │                           │                          │
   │  返回 execution_id     │                           │ 4. 选择执行器            │
   │◄───────────────────────│                           │    openai/mcp/custom    │
   │                        │                           │                          │
   │                        │                           │ 5. 执行任务 ────────────►│
   │                        │                           │                          │
   │                        │                           │ 6. 获取结果 ◄────────────│
   │                        │                           │                          │
   │                        │ 7. 更新状态: completed    │                          │
   │                        │◄──────────────────────────│                          │
   │                        │                           │                          │
   │  WebSocket 推送状态    │                           │                          │
   │◄───────────────────────│                           │                          │
```

### 2. MCP 配置同步流程

```
Claude Code                    MCP Server                    管理系统后端
     │                             │                              │
     │ get_my_config()             │                              │
     │────────────────────────────►│ GET /agents/{id}/config      │
     │                             │─────────────────────────────►│
     │                             │                              │
     │                             │◄─────────────────────────────│
     │◄────────────────────────────│  返回: permission, skills    │
     │                             │          mcp_bindings        │
     │                             │                              │
     │ check_permission(action)    │                              │
     │────────────────────────────►│ POST /agents/{id}/           │
     │                             │      check-permission        │
     │                             │─────────────────────────────►│
     │                             │◄─────────────────────────────│
     │◄────────────────────────────│  {allowed: true/false}       │
     │                             │                              │
     │ report_activity()           │                              │
     │────────────────────────────►│ POST /agents/{id}/activities │
     │                             │─────────────────────────────►│
```

### 3. 指令下发流程 (Redis 消息队列)

```
管理员                    管理系统后端                    Redis                    Claude Code
   │                           │                           │                           │
   │ POST /agents/{id}/commands│                           │                           │
   │──────────────────────────►│                           │                           │
   │                           │                           │                           │
   │                           │ ZADD (priority queue)     │                           │
   │                           │──────────────────────────►│                           │
   │                           │                           │                           │
   │  {command_id}             │                           │                           │
   │◄──────────────────────────│                           │                           │
   │                           │                           │                           │
   │                           │                           │  get_pending_commands()   │
   │                           │                           │◄──────────────────────────│
   │                           │                           │                           │
   │                           │                           │ ZPOPMAX (highest priority)│
   │                           │                           │───────────────────────────►│
   │                           │                           │                           │
   │                           │                           │         command data      │
   │                           │                           │◄──────────────────────────│
   │                           │                           │                           │
   │                           │                           │  submit_command_result()  │
   │                           │                           │◄──────────────────────────│
   │                           │                           │                           │
   │                           │ POST /commands/{id}/result│                           │
   │                           │◄──────────────────────────│                           │
   │                           │                           │                           │
   │  WebSocket 推送结果       │                           │                           │
   │◄──────────────────────────│                           │                           │
```

---

## 数据模型

### 主要数据表

| 表名 | 描述 |
|------|------|
| users | 用户表 |
| roles | 角色表 |
| permissions | 权限表 |
| skills | 技能表 |
| agents | 智能体表 |
| agent_permissions | 智能体权限配置 |
| agent_skill_bindings | 智能体技能绑定 |
| agent_mcp_bindings | 智能体MCP绑定 |
| agent_commands | 指令队列 (PostgreSQL 持久化) |
| mcp_servers | MCP服务器表 |
| mcp_tools | MCP工具表 |
| agent_groups | 智能体群组表 |
| executions | 执行记录表 |
| execution_logs | 执行日志表 |
| audit_logs | 审计日志表 |

---

## API 接口

### 接口概览

```
/api
├── /auth                    # 认证
│   ├── POST /login          # 登录
│   └── GET /me              # 当前用户
│
├── /agents                  # 智能体管理
│   ├── GET /                # 列表
│   ├── POST /               # 创建
│   ├── GET /{id}/config     # 获取完整配置 ⭐
│   ├── PUT /{id}/permission # 更新权限
│   ├── GET /{id}/mcp-bindings
│   ├── POST /{id}/check-permission ⭐
│   ├── POST /{id}/activities     ⭐
│   ├── POST /{id}/commands       ⭐ 发送指令
│   └── GET /{id}/commands        ⭐ 获取指令 (Redis)
│
├── /commands                # 指令管理 ⭐
│   ├── GET /                # 指令历史
│   ├── GET /{id}            # 指令详情
│   ├── POST /{id}/result    # 提交结果
│   ├── POST /{id}/progress  # 更新进度
│   ├── POST /{id}/retry     # 重试指令
│   ├── POST /{id}/cancel    # 取消指令
│   └── GET /stats/summary   # 统计信息
│
├── /mcp                     # MCP服务器管理
│   ├── GET /servers
│   ├── POST /servers/{id}/sync
│   └── GET /servers/{id}/tools
│
├── /rbac                    # 权限管理
│   ├── /skills
│   ├── /permissions
│   └── /roles
│
└── /executions              # 执行管理
    ├── POST /agents/{id}/execute
    └── GET /{id}/logs

⭐ = MCP 协议使用的主要接口
```

---

## 前端页面

### 页面导航

| 路由 | 页面 | 功能描述 |
|------|------|----------|
| `/` | Dashboard | 系统概览 |
| `/agents` | Agents | 智能体管理 + 配置弹窗 |
| `/groups` | Groups | 群组管理 |
| `/skills` | Skills | 技能管理 |
| `/permissions` | Permissions | 权限和角色管理 |
| `/mcp` | MCP Servers | MCP服务器管理 |
| `/commands` | Commands | 指令管理 + 统计 |
| `/executions` | Executions | 执行历史 |
| `/monitor` | Monitor | 实时监控 |

### 智能体配置弹窗

点击智能体的"配置"按钮可配置：
- **操作权限**: Bash、文件读写、网络访问等
- **技能绑定**: 绑定技能并设置优先级
- **MCP服务**: 绑定MCP服务器和工具

---

## MCP 集成

### MCP 工具列表

#### 自我配置工具

| 工具 | 描述 |
|------|------|
| `get_my_config` | 获取当前Agent的完整配置 |
| `check_permission` | 检查是否有执行某操作的权限 |
| `report_activity` | 上报活动状态到管理系统 |
| `check_commands` | 检查待执行的指令 |
| `get_allowed_tools` | 获取允许使用的工具列表 |
| `get_skill_config` | 获取技能详细配置 |

#### 管理工具

| 工具 | 描述 |
|------|------|
| `agent_list/get/create/delete` | 智能体管理 |
| `group_list/create/execute` | 群组管理 |
| `skill_list/create` | 技能管理 |
| `execution_list/status` | 执行管理 |

### Claude Code 配置

```json
{
  "mcpServers": {
    "agent-manager": {
      "command": "python3",
      "args": ["/path/to/mcp/agent_manager_mcp.py"],
      "env": {
        "AGENT_MANAGER_URL": "http://localhost:8000/api",
        "AGENT_MANAGER_TOKEN": "your-jwt-token",
        "AGENT_ID": "your-agent-id"
      }
    }
  }
}
```

详细配置请参考 [mcp/MCP_INTEGRATION.md](mcp/MCP_INTEGRATION.md)

---

## 开发指南

### 本地开发环境

```bash
# 1. 启动 PostgreSQL
docker run -d --name agent-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=agent_manager \
  -p 5432:5432 postgres:14-alpine

# 2. 启动后端
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. 启动前端
cd frontend
npm install && npm run dev

# 4. 访问
# 前端: http://localhost:5173
# API文档: http://localhost:8000/docs
```

### 默认凭据

- 用户名: `admin`
- 密码: `admin123`

---

## 部署说明

### Docker Compose

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: agent_manager
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:${DB_PASSWORD}@postgres:5432/agent_manager
      SECRET_KEY: ${SECRET_KEY}
    depends_on:
      - postgres

  frontend:
    build: ./frontend
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - frontend
      - backend

volumes:
  postgres_data:
```

---

## 更新日志

### v1.2.0 (2026-02-25)
- ✨ 新增智能体级别配置（权限、技能、MCP绑定）
- ✨ 新增 MCP 服务器管理功能
- ✨ 新增可视化配置界面
- ✨ 新增 MCP 自我配置工具 (get_my_config, check_permission等)
- ✨ 新增活动上报和指令下发功能

### v1.1.0
- 🐛 修复执行状态一直为 pending 的问题
- ✨ 添加中文本地化
- ✨ 添加技能管理功能

### v1.0.0
- 🎉 初始版本发布

---

**仓库**: https://github.com/moonseeker1/agent_manage
