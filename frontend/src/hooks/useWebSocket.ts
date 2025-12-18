'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { WebSocketMessage, Message, StatusUpdate } from '@/types';

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

interface UseWebSocketReturn {
  isConnected: boolean;
  error: string | null;
  sendMessage: (data: WebSocketMessage) => void;
  sendTypingIndicator: (conversationId: number, isTyping: boolean) => void;
  markAsRead: (conversationId: number, messageIds: string[]) => void;
  reconnect: () => void;
  disconnect: () => void;
}

interface UseWebSocketProps {
  conversationId?: number;
  onMessage?: (message: Message) => void;
  onStatusUpdate?: (update: StatusUpdate) => void;
  onTyping?: (conversationId: number, isTyping: boolean) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  enabled?: boolean;
}

const MAX_RECONNECT_ATTEMPTS = 5;
const BASE_RECONNECT_DELAY = 3000; // 3 seconds

export function useWebSocket({
  conversationId,
  onMessage,
  onStatusUpdate,
  onTyping,
  onConnect,
  onDisconnect,
  enabled = true,
}: UseWebSocketProps = {}): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  
  // Store callbacks in refs to avoid re-renders triggering reconnections
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);
  const onMessageRef = useRef(onMessage);
  const onStatusUpdateRef = useRef(onStatusUpdate);
  const onTypingRef = useRef(onTyping);
  
  // Update refs when callbacks change
  useEffect(() => {
    onConnectRef.current = onConnect;
    onDisconnectRef.current = onDisconnect;
    onMessageRef.current = onMessage;
    onStatusUpdateRef.current = onStatusUpdate;
    onTypingRef.current = onTyping;
  }, [onConnect, onDisconnect, onMessage, onStatusUpdate, onTyping]);
  
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get auth token from localStorage
  const getToken = useCallback((): string | null => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('auth_token');
    }
    return null;
  }, []);

  // Build WebSocket URL with token and conversation ID
  const buildWsUrl = useCallback((): string => {
    const token = getToken();
    // Use /ws/global for global notifications, /ws/chat/{id} for specific conversation
    const baseUrl = conversationId 
      ? `${WS_BASE_URL}/ws/chat/${conversationId}`
      : `${WS_BASE_URL}/ws/global`;
    
    if (token) {
      return `${baseUrl}?token=${token}`;
    }
    return baseUrl;
  }, [conversationId, getToken]);

  // Handle incoming WebSocket messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data: WebSocketMessage = JSON.parse(event.data);
      
      switch (data.type) {
        case 'message':
        case 'new_message':
          // Handle both 'message' and 'new_message' types
          // Backend sends 'new_message', extract the message from payload or data.message
          const messageData = data.payload || (data as unknown as { message: Message }).message;
          if (onMessageRef.current && messageData) {
            onMessageRef.current(messageData as Message);
          }
          break;
          
        case 'status_update':
          if (onStatusUpdateRef.current && data.payload) {
            onStatusUpdateRef.current(data.payload as StatusUpdate);
          }
          break;
          
        case 'typing':
          if (onTypingRef.current && data.conversation_id !== undefined && data.payload) {
            const payload = data.payload as { is_typing?: boolean };
            if (typeof payload.is_typing === 'boolean') {
              onTypingRef.current(data.conversation_id, payload.is_typing);
            }
          }
          break;
          
        case 'connected':
          console.log('WebSocket: Connected event received');
          break;
          
        default:
          console.log('WebSocket: Unknown message type', data.type);
      }
    } catch (err) {
      console.error('WebSocket: Error parsing message', err);
    }
  }, []);

  // Schedule reconnection with exponential backoff
  const scheduleReconnect = useCallback((connectFn: () => void) => {
    if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      setError(`Failed to reconnect after ${MAX_RECONNECT_ATTEMPTS} attempts`);
      return;
    }

    const delay = BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttemptsRef.current);
    console.log(`WebSocket: Scheduling reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1})`);

    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectAttemptsRef.current += 1;
      connectFn();
    }, delay);
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!enabled) return;
    
    const token = getToken();
    if (!token) {
      setError('No authentication token available');
      return;
    }

    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close();
    }

    const wsUrl = buildWsUrl();
    console.log('WebSocket: Connecting to', wsUrl);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket: Connection opened');
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        onConnectRef.current?.();
      };

      ws.onmessage = handleMessage;

      ws.onerror = () => {
        // WebSocket errors often have no useful info - the close event usually has more details
        // Only log if we're not already disconnected
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          console.warn('WebSocket: Connection error');
          setError('WebSocket connection error');
        }
      };

      ws.onclose = (event) => {
        console.log('WebSocket: Connection closed', event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;
        onDisconnectRef.current?.();

        // Attempt to reconnect if not a normal close
        if (event.code !== 1000 && enabled) {
          scheduleReconnect(connect);
        }
      };
    } catch (err) {
      console.error('WebSocket: Failed to create connection', err);
      setError('Failed to create WebSocket connection');
    }
  }, [enabled, buildWsUrl, getToken, handleMessage, scheduleReconnect]);

  // Send message through WebSocket
  const sendMessage = useCallback((data: WebSocketMessage) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket: Cannot send message, connection not open');
    }
  }, []);

  // Send typing indicator
  const sendTypingIndicator = useCallback((convId: number, isTyping: boolean) => {
    sendMessage({
      type: 'typing',
      conversation_id: convId,
      payload: { is_typing: isTyping },
    });
  }, [sendMessage]);

  // Mark messages as read
  const markAsRead = useCallback((convId: number, messageIds: string[]) => {
    sendMessage({
      type: 'read',
      conversation_id: convId,
      payload: { message_ids: messageIds },
    });
  }, [sendMessage]);

  // Manual reconnect
  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    connect();
  }, [connect]);

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnecting');
      wsRef.current = null;
    }
    
    setIsConnected(false);
  }, []);

  // Track connection state
  const initialConnectRef = useRef(false);
  const prevConversationIdRef = useRef<number | undefined>(conversationId);
  const mountedRef = useRef(true);
  const connectionTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    mountedRef.current = true;
    
    if (!initialConnectRef.current && enabled) {
      // Delay initial connection to allow React to settle
      connectionTimeoutRef.current = setTimeout(() => {
        if (mountedRef.current && !initialConnectRef.current) {
          initialConnectRef.current = true;
          connect();
        }
      }, 500);
    }

    return () => {
      mountedRef.current = false;
      
      if (connectionTimeoutRef.current) {
        clearTimeout(connectionTimeoutRef.current);
        connectionTimeoutRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting');
        wsRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  // Reconnect when conversationId actually changes (not on initial mount)
  useEffect(() => {
    if (prevConversationIdRef.current !== conversationId && initialConnectRef.current && mountedRef.current) {
      prevConversationIdRef.current = conversationId;
      // Reconnect to new conversation
      if (wsRef.current) {
        wsRef.current.close(1000, 'Switching conversation');
        wsRef.current = null;
      }
      setTimeout(() => {
        if (mountedRef.current) {
          connect();
        }
      }, 100);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  return {
    isConnected,
    error,
    sendMessage,
    sendTypingIndicator,
    markAsRead,
    reconnect,
    disconnect,
  };
}

export default useWebSocket;
