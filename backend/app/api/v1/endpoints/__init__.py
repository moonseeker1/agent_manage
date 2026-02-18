from fastapi import APIRouter
from app.api.v1.endpoints import agents, groups, executions, metrics

api_router = APIRouter()

api_router.include_router(agents.router)
api_router.include_router(groups.router)
api_router.include_router(executions.router)
api_router.include_router(metrics.router)
