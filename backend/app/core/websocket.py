"""
WebSocket Manager - Real-time updates for the scanner.
"""
from fastapi import WebSocket
from typing import List, Dict, Any
import asyncio
import json
from datetime import datetime


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts.
    
    Features:
    - Track active connections
    - Broadcast updates to all clients
    - Handle connection/disconnection gracefully
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Accept and track a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        print(f"🔌 Client connected. Total: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        print(f"🔌 Client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return

        message_json = json.dumps(message, default=str)

        # Send to all connections, remove dead ones inside the lock
        async with self._lock:
            dead_connections = []
            for connection in self.active_connections:
                try:
                    await connection.send_text(message_json)
                except Exception:
                    dead_connections.append(connection)

            # Remove dead connections while holding the lock
            for conn in dead_connections:
                if conn in self.active_connections:
                    self.active_connections.remove(conn)
                    print(f"🔌 Dead connection removed. Total: {len(self.active_connections)}")
    
    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a message to a specific client."""
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception:
            await self.disconnect(websocket)
    
    @property
    def connection_count(self) -> int:
        """Number of active connections."""
        return len(self.active_connections)


# Singleton instance
manager = ConnectionManager()


# Message types for WebSocket communication
class MessageTypes:
    SIGNALS_UPDATE = "signals_update"
    WHALE_TRADE = "whale_trade"
    MARKET_UPDATE = "market_update"
    CONNECTION_ACK = "connection_ack"
    PING = "ping"
    PONG = "pong"
