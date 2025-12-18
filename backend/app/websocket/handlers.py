"""WebSocket event handlers."""

import json
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.schemas import WSMessage, WSTypingIndicator
from app.services.auth import verify_websocket_token
from app.utils.constants import WSEventType
from app.utils.logger import get_logger
from app.websocket.manager import ws_manager

logger = get_logger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    conversation_id: int,
    token: Optional[str] = Query(default=None),
):
    """WebSocket endpoint for real-time chat.
    
    Clients connect to this endpoint to receive real-time updates
    for a specific conversation.
    
    Args:
        websocket: The WebSocket connection.
        conversation_id: The conversation to subscribe to.
        token: JWT authentication token.
    """
    # Verify token
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return
    
    user_id = verify_websocket_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return
    
    # Accept connection and register
    await ws_manager.connect(websocket, conversation_id)
    
    # Send connection confirmation
    await websocket.send_json({
        "type": WSEventType.CONNECTED.value,
        "payload": {
            "conversation_id": conversation_id,
            "message": "Connected to chat",
        },
    })
    
    logger.info(f"User {user_id} connected to conversation {conversation_id}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_client_message(
                    websocket,
                    conversation_id,
                    message,
                    user_id,
                )
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": WSEventType.ERROR.value,
                    "payload": {"error": "Invalid JSON"},
                })
                
    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected from conversation {conversation_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await ws_manager.disconnect(websocket)


@router.websocket("/ws/global")
async def websocket_global_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None),
):
    """WebSocket endpoint for global notifications.
    
    Clients connect to this endpoint to receive global updates
    across all conversations (new messages, status updates).
    
    Args:
        websocket: The WebSocket connection.
        token: JWT authentication token.
    """
    # Verify token
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return
    
    user_id = verify_websocket_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return
    
    # Accept connection without conversation ID (global)
    await ws_manager.connect(websocket, conversation_id=None)
    
    await websocket.send_json({
        "type": WSEventType.CONNECTED.value,
        "payload": {"message": "Connected to global notifications"},
    })
    
    logger.info(f"User {user_id} connected to global notifications")
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Handle ping/pong for connection keep-alive
                if message.get("type") == WSEventType.PING.value:
                    await websocket.send_json({
                        "type": WSEventType.PONG.value,
                        "payload": {},
                    })
                    
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected from global notifications")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await ws_manager.disconnect(websocket)


async def handle_client_message(
    websocket: WebSocket,
    conversation_id: int,
    message: dict,
    user_id: str,
) -> None:
    """Handle incoming WebSocket messages from clients.
    
    Args:
        websocket: The WebSocket connection.
        conversation_id: Current conversation ID.
        message: Parsed message data.
        user_id: Authenticated user ID.
    """
    msg_type = message.get("type")
    payload = message.get("payload", {})
    
    if msg_type == WSEventType.TYPING.value:
        # Broadcast typing indicator to other clients in conversation
        typing_event = WSTypingIndicator(
            type=WSEventType.TYPING.value,
            conversation_id=conversation_id,
            is_typing=payload.get("is_typing", True),
        )
        
        await ws_manager.broadcast_to_conversation(
            conversation_id,
            typing_event.model_dump_json(),
        )
        
    elif msg_type == WSEventType.READ.value:
        # Mark messages as read - this is handled by API endpoint
        # Just broadcast read status to other clients
        await ws_manager.broadcast_to_conversation(
            conversation_id,
            json.dumps({
                "type": WSEventType.READ.value,
                "payload": {
                    "conversation_id": conversation_id,
                    "reader_id": user_id,
                },
            }),
        )
        
    elif msg_type == WSEventType.PING.value:
        # Respond to ping with pong
        await websocket.send_json({
            "type": WSEventType.PONG.value,
            "payload": {},
        })
        
    else:
        logger.debug(f"Unknown message type: {msg_type}")
