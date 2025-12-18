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
    const baseUrl = conversationId 
      ? `${WS_BASE_URL}/ws/chat/${conversationId}`
      : `${WS_BASE_URL}/ws/chat`;
    
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
          if (onMessage && data.payload) {
            onMessage(data.payload as Message);
          }
          break;
          
        case 'status_update':
          if (onStatusUpdate && data.payload) {
            onStatusUpdate(data.payload as StatusUpdate);
          }
          break;
          
        case 'typing':
          if (onTyping && data.conversation_id !== undefined) {
            const payload = data.payload as { is_typing: boolean };
            onTyping(data.conversation_id, payload.is_typing);
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
  }, [onMessage, onStatusUpdate, onTyping]);

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
        onConnect?.();
      };

      ws.onmessage = handleMessage;

      ws.onerror = (event) => {
        console.error('WebSocket: Error', event);
        setError('WebSocket connection error');
      };

      ws.onclose = (event) => {
        console.log('WebSocket: Connection closed', event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;
        onDisconnect?.();

        // Attempt to reconnect if not a normal close
        if (event.code !== 1000 && enabled) {
          scheduleReconnect(connect);
        }
      };
    } catch (err) {
      console.error('WebSocket: Failed to create connection', err);
      setError('Failed to create WebSocket connection');
    }
  }, [enabled, buildWsUrl, getToken, handleMessage, onConnect, onDisconnect, scheduleReconnect]);

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

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting');
      }
    };
  }, [connect]);

  // Reconnect when conversationId changes
  useEffect(() => {
    if (conversationId !== undefined && isConnected) {
      // Reconnect to new conversation
      disconnect();
      setTimeout(() => connect(), 100);
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
