"""WebSocket connection manager."""

import asyncio
from collections import defaultdict
from typing import Optional

from fastapi import WebSocket

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time messaging."""
    
    def __init__(self):
        """Initialize connection manager."""
        # Map conversation_id -> list of WebSocket connections
        self.active_connections: dict[int, list[WebSocket]] = defaultdict(list)
        
        # Map WebSocket -> conversation_id (for cleanup)
        self.connection_to_conversation: dict[WebSocket, int] = {}
        
        # Global connections (not tied to specific conversation)
        self.global_connections: list[WebSocket] = []
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def connect(
        self,
        websocket: WebSocket,
        conversation_id: Optional[int] = None,
    ) -> None:
        """Accept and register a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection.
            conversation_id: Optional conversation ID to subscribe to.
        """
        await websocket.accept()
        
        async with self._lock:
            if conversation_id is not None:
                self.active_connections[conversation_id].append(websocket)
                self.connection_to_conversation[websocket] = conversation_id
                logger.info(
                    f"WebSocket connected to conversation {conversation_id}. "
                    f"Total connections: {len(self.active_connections[conversation_id])}"
                )
            else:
                self.global_connections.append(websocket)
                logger.info(
                    f"WebSocket connected globally. "
                    f"Total global connections: {len(self.global_connections)}"
                )
    
    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to remove.
        """
        async with self._lock:
            # Check if it's a conversation-specific connection
            if websocket in self.connection_to_conversation:
                conversation_id = self.connection_to_conversation[websocket]
                
                if websocket in self.active_connections[conversation_id]:
                    self.active_connections[conversation_id].remove(websocket)
                
                del self.connection_to_conversation[websocket]
                
                # Clean up empty conversation lists
                if not self.active_connections[conversation_id]:
                    del self.active_connections[conversation_id]
                
                logger.info(f"WebSocket disconnected from conversation {conversation_id}")
            
            # Check if it's a global connection
            elif websocket in self.global_connections:
                self.global_connections.remove(websocket)
                logger.info("WebSocket disconnected from global")
    
    async def broadcast_to_conversation(
        self,
        conversation_id: int,
        message: str,
    ) -> None:
        """Broadcast a message to all connections in a conversation.
        
        Args:
            conversation_id: The conversation ID.
            message: JSON message string to send.
        """
        connections = self.active_connections.get(conversation_id, [])
        
        if not connections:
            logger.debug(f"No active connections for conversation {conversation_id}")
            return
        
        disconnected = []
        
        for websocket in connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected:
            await self.disconnect(websocket)
    
    async def broadcast_global(self, message: str) -> None:
        """Broadcast a message to all global connections.
        
        Args:
            message: JSON message string to send.
        """
        disconnected = []
        
        for websocket in self.global_connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send global message: {e}")
                disconnected.append(websocket)
        
        for websocket in disconnected:
            await self.disconnect(websocket)
    
    async def broadcast_to_all(self, message: str) -> None:
        """Broadcast a message to all connections (global and conversation-specific).
        
        Args:
            message: JSON message string to send.
        """
        await self.broadcast_global(message)
        
        for conversation_id in list(self.active_connections.keys()):
            await self.broadcast_to_conversation(conversation_id, message)
    
    async def send_personal(
        self,
        websocket: WebSocket,
        message: str,
    ) -> bool:
        """Send a message to a specific WebSocket.
        
        Args:
            websocket: The target WebSocket.
            message: JSON message string to send.
        
        Returns:
            True if sent successfully, False otherwise.
        """
        try:
            await websocket.send_text(message)
            return True
        except Exception as e:
            logger.warning(f"Failed to send personal message: {e}")
            await self.disconnect(websocket)
            return False
    
    def get_connection_count(self, conversation_id: Optional[int] = None) -> int:
        """Get the number of active connections.
        
        Args:
            conversation_id: Optional conversation ID to filter by.
        
        Returns:
            Number of active connections.
        """
        if conversation_id is not None:
            return len(self.active_connections.get(conversation_id, []))
        
        total = len(self.global_connections)
        for connections in self.active_connections.values():
            total += len(connections)
        
        return total
    
    def get_active_conversations(self) -> list[int]:
        """Get list of conversation IDs with active connections.
        
        Returns:
            List of conversation IDs.
        """
        return list(self.active_connections.keys())


# Singleton instance
ws_manager = ConnectionManager()
