from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.redis import redis_service
from app.services.command_monitor import command_monitor
from app.api.v1.endpoints import api_router
from app.api.websocket import websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting up...")
    await init_db()
    logger.info("Database initialized")

    # Initialize Redis
    await redis_service.init()
    logger.info("Redis connection initialized")

    # Start command timeout monitor
    monitor_task = asyncio.create_task(command_monitor.start())
    logger.info("Command timeout monitor started")

    yield

    # Shutdown
    logger.info("Shutting down...")

    # Stop command monitor
    command_monitor.stop()
    try:
        await asyncio.wait_for(monitor_task, timeout=5.0)
    except asyncio.TimeoutError:
        logger.warning("Command monitor did not stop gracefully")
    logger.info("Command monitor stopped")

    await close_db()
    logger.info("Database connection closed")

    # Close Redis
    await redis_service.close()
    logger.info("Redis connection closed")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A comprehensive system for managing and monitoring AI agents",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.API_PREFIX)

# Include WebSocket routes
app.include_router(websocket_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api": settings.API_PREFIX
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
