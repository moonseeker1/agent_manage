from fastapi import APIRouter
from app.api.v1.endpoints import agents, groups, executions, metrics, auth, templates, config, permissions, mcp_servers, agent_config, commands

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(templates.router)
api_router.include_router(config.router)
api_router.include_router(permissions.router)
api_router.include_router(mcp_servers.router)
api_router.include_router(agents.router)
api_router.include_router(agent_config.router)
api_router.include_router(commands.router)
api_router.include_router(groups.router)
api_router.include_router(executions.router)
api_router.include_router(metrics.router)
