from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
from uuid import UUID
import json
import asyncio
from loguru import logger

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections"""

    def __init__(self):
        # General connections
        self.active_connections: Set[WebSocket] = set()
        # Execution-specific connections
        self.execution_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        """Accept a new connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")

    async def connect_execution(self, websocket: WebSocket, execution_id: str):
        """Connect to a specific execution channel"""
        await websocket.accept()
        if execution_id not in self.execution_connections:
            self.execution_connections[execution_id] = set()
        self.execution_connections[execution_id].add(websocket)
        logger.info(f"New connection for execution {execution_id}")

    def disconnect(self, websocket: WebSocket):
        """Remove a connection"""
        self.active_connections.discard(websocket)
        # Remove from execution connections
        for execution_id in list(self.execution_connections.keys()):
            self.execution_connections[execution_id].discard(websocket)
            if not self.execution_connections[execution_id]:
                del self.execution_connections[execution_id]

    async def broadcast(self, message: dict):
        """Broadcast message to all connections"""
        message_json = json.dumps(message)
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception:
                disconnected.add(connection)

        for conn in disconnected:
            self.active_connections.discard(conn)

    async def broadcast_to_execution(self, execution_id: str, message: dict):
        """Broadcast message to connections subscribed to an execution"""
        if execution_id not in self.execution_connections:
            return

        message_json = json.dumps(message)
        disconnected = set()
        for connection in self.execution_connections[execution_id]:
            try:
                await connection.send_text(message_json)
            except Exception:
                disconnected.add(connection)

        for conn in disconnected:
            self.execution_connections[execution_id].discard(conn)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """General WebSocket endpoint for global updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                # Handle ping/pong for keepalive
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket disconnected")


@router.websocket("/ws/executions/{execution_id}")
async def execution_websocket_endpoint(websocket: WebSocket, execution_id: str):
    """WebSocket endpoint for execution-specific updates"""
    await manager.connect_execution(websocket, execution_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"Execution WebSocket disconnected: {execution_id}")


# Helper functions to broadcast updates
async def broadcast_execution_update(execution_id: str, status: str, data: dict = None):
    """Broadcast execution status update"""
    message = {
        "type": "execution_update",
        "execution_id": execution_id,
        "status": status,
        "data": data
    }
    await manager.broadcast(message)
    await manager.broadcast_to_execution(execution_id, message)


async def broadcast_log_update(execution_id: str, log: dict):
    """Broadcast new log entry"""
    message = {
        "type": "log_update",
        "execution_id": execution_id,
        "log": log
    }
    await manager.broadcast_to_execution(execution_id, message)


# Export router
websocket_router = router
