"""WebSocket connection manager for real-time notifications."""

import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections for users and admins.

    Provides methods to send targeted messages to specific users
    and broadcast messages to all connected admin users.
    """

    def __init__(self):
        # Maps user_id -> set of active WebSockets
        self.active_connections: dict[int, set[WebSocket]] = {}
        # Set of WebSockets for active admins
        self.admin_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, user_id: int, is_admin: bool):
        """Accept a WebSocket connection and register it."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

        if is_admin:
            self.admin_connections.add(websocket)

        logger.info(f"WS connected: user_id={user_id}, is_admin={is_admin}")

    def disconnect(self, websocket: WebSocket, user_id: int, is_admin: bool):
        """Remove a WebSocket connection from all tracking sets."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        if is_admin:
            self.admin_connections.discard(websocket)

        logger.info(f"WS disconnected: user_id={user_id}")

    def _remove_dead(self, websocket: WebSocket):
        """Remove a dead WebSocket from all tracking structures."""
        # Remove from user connections
        for user_id in list(self.active_connections):
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        # Remove from admin connections
        self.admin_connections.discard(websocket)

    async def send_personal_message(self, message: dict, user_id: int):
        """Send a message to all connections of a specific user."""
        if user_id not in self.active_connections:
            return

        dead: list[WebSocket] = []
        for connection in list(self.active_connections[user_id]):
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)

        # BUG-3 FIX: Clean up dead connections
        for ws in dead:
            self._remove_dead(ws)

    async def broadcast_to_admins(self, message: dict):
        """Broadcast a message to all connected admins."""
        dead: list[WebSocket] = []
        for connection in list(self.admin_connections):
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)

        # BUG-3 FIX: Clean up dead connections
        for ws in dead:
            self._remove_dead(ws)


manager = ConnectionManager()
