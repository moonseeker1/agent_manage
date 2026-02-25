# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agent Management System (智能体管理系统) - A full-stack application for managing and monitoring AI agents. Supports MCP Server, OpenAI API, and custom agent types with RBAC permission control and agent-level configuration.

**Tech Stack:**
- Frontend: React 18 + TypeScript + Ant Design 5 + Vite + Zustand
- Backend: Python 3.9+ + FastAPI + SQLAlchemy (async) + PostgreSQL
- Deploy Path: `/agent/` (via Nginx reverse proxy)

## Development Commands

### Backend
```bash
cd backend

# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
pytest

# Database: Uses async SQLAlchemy with PostgreSQL
# Tables auto-created on startup via init_db()
```

### Frontend
```bash
cd frontend

# Setup
npm install

# Run development server (proxies API to backend:8000)
npm run dev

# Production build (outputs to dist/)
npm run build

# Lint
npm run lint
```

### MCP Server
```bash
cd mcp
pip install -r requirements.txt

# Configure in Claude Code settings:
# "agent-manager": {
#   "command": "python3",
#   "args": ["/path/to/mcp/agent_manager_mcp.py"],
#   "env": {
#     "AGENT_MANAGER_URL": "http://localhost:8000/api",
#     "AGENT_MANAGER_TOKEN": "jwt-token-here"
#   }
# }
```

## Architecture

### Backend Structure
```
backend/app/
├── main.py              # FastAPI app entry, CORS, lifespan
├── core/
│   ├── config.py        # Settings from env vars
│   ├── database.py      # Async session factory
│   ├── security.py      # JWT + bcrypt
│   └── deps.py          # Auth dependencies (get_current_user, get_current_superuser)
├── api/v1/endpoints/    # Route handlers
│   ├── agents.py        # Agent CRUD
│   ├── executions.py    # Execute agents/groups
│   ├── permissions.py   # RBAC (skills, roles, permissions)
│   ├── agent_config.py  # Agent-level permissions & MCP bindings
│   ├── mcp_servers.py   # MCP Server management
│   └── ...
├── models/              # SQLAlchemy models
│   ├── agent.py         # Agent, AgentGroup, AgentGroupMember
│   ├── execution.py     # Execution, ExecutionLog, Metric
│   ├── permission.py    # Skill, Permission, Role, AgentSkillBinding, AuditLog
│   ├── agent_config.py  # AgentPermission, AgentMCPBinding
│   ├── mcp_server.py    # MCPServer, MCPTool
│   └── user.py          # User
├── schemas/             # Pydantic validation models
│   ├── agent_config.py  # Agent permission & MCP binding schemas
│   ├── mcp_server.py    # MCP server schemas
│   └── ...
└── services/
    ├── executor.py      # Agent executors (OpenAI, MCP, Custom) + background tasks
    ├── agent_service.py # Agent business logic
    └── execution_service.py
```

### Frontend Structure
```
frontend/src/
├── pages/               # Route pages
│   ├── Dashboard/       # System overview
│   ├── Agents/          # Agent management + AgentConfig component
│   ├── Groups/          # Agent groups
│   ├── Executions/      # Execution history
│   ├── Monitor/         # Real-time monitoring
│   ├── Skills/          # Skill management
│   ├── Permissions/     # Permission & Role management
│   ├── MCP/             # MCP Server management
│   └── Login/           # Authentication
├── components/Layout/   # Main layout with navigation
├── services/
│   ├── api.ts           # Axios client (baseURL: '/agent/api')
│   └── websocket.ts     # WebSocket for real-time updates
├── stores/              # Zustand state (authStore, agent store)
└── types/               # TypeScript interfaces
    ├── index.ts         # Core types
    └── mcp.ts           # MCP server types
```

### Key Execution Flow

1. **Agent Execution**: `POST /api/executions/agents/{id}/execute`
   - Creates Execution record (status: pending)
   - Uses `asyncio.create_task()` for background execution
   - Executor selected by agent_type: `openai` → OpenAIExecutor, `mcp` → MCPExecutor, `custom` → CustomExecutor
   - Status updates: pending → running → completed/failed
   - Logs stored in execution_logs table

2. **RBAC System**:
   - Permissions: granular access control (e.g., `agent:create`, `skill:manage`)
   - Roles: group permissions, assigned to users
   - Skills: capabilities that can be bound to agents with priority
   - AuditLog: tracks all privileged operations

3. **Agent-Level Configuration**:
   - AgentPermission: Controls what each agent can do (bash, file ops, network)
   - AgentMCPBinding: Binds MCP servers to agents with tool selection
   - AgentSkillBinding: Binds skills to agents with priority

### Database Relationships
```
agents ──< agent_group_members >── agent_groups
   │
   ├──< executions ──< execution_logs
   │                └──< metrics
   │
   ├──< agent_permissions (1:1)
   │
   ├──< agent_mcp_bindings >── mcp_servers ──< mcp_tools
   │
   └──< agent_skill_bindings >── skills

users ──< user_roles >── roles ──< role_permissions >── permissions
```

## API Endpoints

### Agent Configuration
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agents/{id}/permission` | Get agent permission config |
| PUT | `/agents/{id}/permission` | Update agent permission |
| GET | `/agents/{id}/mcp-bindings` | List MCP bindings |
| POST | `/agents/{id}/mcp-bindings` | Create MCP binding |
| DELETE | `/agents/{id}/mcp-bindings/{bid}` | Remove MCP binding |
| GET | `/agents/{id}/config` | Get complete config |

### MCP Server Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/mcp/servers` | List MCP servers |
| POST | `/mcp/servers` | Create MCP server |
| PUT | `/mcp/servers/{id}` | Update MCP server |
| DELETE | `/mcp/servers/{id}` | Delete MCP server |
| POST | `/mcp/servers/{id}/sync` | Sync tools from server |
| GET | `/mcp/servers/{id}/tools` | List server tools |

### Skills & Permissions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/rbac/skills` | List/Create skills |
| GET/POST | `/rbac/permissions` | List/Create permissions |
| GET/POST | `/rbac/roles` | List/Create roles |
| POST/DELETE | `/rbac/agents/{id}/skills/{sid}` | Bind/Unbind skill |

## Agent Permission Configuration

Each agent can be configured with:

### Tool Permissions
- `allow_bash` - Execute shell commands
- `allow_read` - Read files
- `allow_write` - Write new files
- `allow_edit` - Edit existing files
- `allow_web` - Network access

### Path Restrictions
- `allowed_paths` - List of allowed paths
- `blocked_paths` - List of blocked paths

### Command Restrictions
- `allowed_commands` - List of allowed commands
- `blocked_commands` - List of blocked commands

### Execution Limits
- `max_execution_time` - Maximum execution time (seconds)
- `max_output_size` - Maximum output size (KB)

## Important Patterns

### Adding New Agent Type
1. Create executor class in `backend/app/services/executor.py` extending `BaseExecutor`
2. Register in `get_executor()` function
3. Add type to frontend `AgentType` and form options

### Adding New API Endpoint
1. Create route in `backend/app/api/v1/endpoints/`
2. Register in `backend/app/api/v1/endpoints/__init__.py`
3. Add Pydantic schema in `backend/app/schemas/`
4. Add frontend API method in `frontend/src/services/api.ts`

### Authentication
- JWT tokens via `python-jose`
- Token in `Authorization: Bearer <token>` header
- Frontend stores in Zustand with localStorage persistence
- `get_current_user` dependency for protected routes
- `get_current_superuser` for admin-only routes

## Deployment Notes

- Frontend builds to `frontend/dist/`, served by Nginx at `/agent/`
- API at `/agent/api/` proxied to backend:8000
- WebSocket at `/agent/ws/` proxied to backend:8000
- Database: PostgreSQL container named `agent-postgres`
- Default credentials: admin / admin123

## Frontend Navigation

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | System overview |
| `/agents` | Agents | Agent management with config modal |
| `/groups` | Groups | Agent group management |
| `/skills` | Skills | Skill management |
| `/permissions` | Permissions | Permission & Role management |
| `/mcp` | MCP Servers | MCP server management |
| `/executions` | Executions | Execution history |
| `/monitor` | Monitor | Real-time monitoring |
