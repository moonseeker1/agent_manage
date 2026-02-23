# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agent Management System (智能体管理系统) - A full-stack application for managing and monitoring AI agents. Supports MCP Server, OpenAI API, and custom agent types with RBAC permission control.

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
│   └── ...
├── models/              # SQLAlchemy models
│   ├── agent.py         # Agent, AgentGroup, AgentGroupMember
│   ├── execution.py     # Execution, ExecutionLog, Metric
│   ├── permission.py    # Skill, Permission, Role, AgentSkillBinding, AuditLog
│   └── user.py          # User
├── schemas/             # Pydantic validation models
└── services/
    ├── executor.py      # Agent executors (OpenAI, MCP, Custom) + background tasks
    ├── agent_service.py # Agent business logic
    └── execution_service.py
```

### Frontend Structure
```
frontend/src/
├── pages/               # Route pages (Dashboard, Agents, Groups, Executions, Monitor, Login)
├── components/Layout/   # Main layout with navigation
├── services/
│   ├── api.ts           # Axios client (baseURL: '/agent/api')
│   └── websocket.ts     # WebSocket for real-time updates
├── stores/              # Zustand state (authStore, agent store)
└── types/               # TypeScript interfaces
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

### Database Relationships
```
agents ──< agent_group_members >── agent_groups
   │
   └──< executions ──< execution_logs
                    └──< metrics

users ──< user_roles >── roles ──< role_permissions >── permissions
                                                   >── skills
agents ──< agent_skill_bindings >── skills
```

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
