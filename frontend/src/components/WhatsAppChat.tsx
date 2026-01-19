'use client';

import React, { useEffect } from 'react';
import ConversationList from './ConversationList';
import ChatWindow from './ChatWindow';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUIStore, useConversationStore, useMessageStore, useAuthStore } from '@/hooks/useAppState';
import { conversationApi } from '@/services/api';
import { Message, StatusUpdate } from '@/types';
import { mockConversations, mockMessages, mockUnreadCounts } from '@/utils/mockData';

// Connection error banner
const ConnectionBanner: React.FC = () => {
  const { connectionError, isConnected } = useUIStore();
  const { token } = useAuthStore();
  const isDemoMode = token?.startsWith('demo-token-');
  
  // Don't show error banner in demo mode
  if (isDemoMode || isConnected || !connectionError) return null;
  
  return (
    <div className="bg-red-500 text-white px-4 py-2 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span>{connectionError}</span>
      </div>
      <button 
        onClick={() => window.location.reload()}
        className="px-3 py-1 bg-white/20 hover:bg-white/30 rounded text-sm transition-colors"
      >
        Retry
      </button>
    </div>
  );
};

// Main WhatsApp Chat component
const WhatsAppChat: React.FC = () => {
  const { setConnected, setConnectionError, incrementUnread, setTyping, clearTyping, setUnreadCount } = useUIStore();
  const { updateConversation, addOrUpdateConversation, selectedConversationId, setConversations, conversations } = useConversationStore();
  const { addMessage, updateMessageStatus, setMessages } = useMessageStore();
  const { token } = useAuthStore();
  
  // Memoize isDemoMode to prevent re-renders from triggering WebSocket reconnections
  const isDemoMode = React.useMemo(() => token?.startsWith('demo-token-') ?? false, [token]);
  
  // Function to refresh conversation list (for new conversations)
  const refreshConversations = React.useCallback(async () => {
    try {
      const response = await conversationApi.getConversations();
      if (response.success && response.data) {
        const convList = Array.isArray(response.data) ? response.data : [];
        setConversations(convList);
      }
    } catch (err) {
      console.error('Failed to refresh conversations:', err);
    }
  }, [setConversations]);

  // Load mock data in demo mode
  useEffect(() => {
    if (isDemoMode) {
      // Load mock conversations
      setConversations(mockConversations);
      
      // Load mock messages for each conversation
      Object.entries(mockMessages).forEach(([convId, msgs]) => {
        setMessages(parseInt(convId), msgs);
      });
      
      // Set mock unread counts
      Object.entries(mockUnreadCounts).forEach(([convId, count]) => {
        setUnreadCount(parseInt(convId), count);
      });
      
      // Set connected state for demo
      setConnected(true);
    }
  }, [isDemoMode, setConversations, setMessages, setUnreadCount, setConnected]);

  // Global WebSocket connection for receiving messages (only when not in demo mode)
  const { isConnected, error } = useWebSocket({
    onMessage: (message: Message) => {
      console.log('WebSocket: Received message', message);
      
      // Add message to the store
      addMessage(message.conversation_id, message);
      
      // Check if conversation exists
      const conversationExists = conversations?.some(c => c.id === message.conversation_id);
      
      if (conversationExists) {
        // Update existing conversation's last message
        updateConversation(message.conversation_id, {
          last_message: message.content,
          last_message_at: message.timestamp || message.created_at,
        });
      } else {
        // New conversation - refresh the list to get it
        console.log('WebSocket: New conversation detected, refreshing list');
        refreshConversations();
      }
      
      // Increment unread count if not the selected conversation
      if (message.sender_type === 'inbound' && message.conversation_id !== selectedConversationId) {
        incrementUnread(message.conversation_id);
      }
    },
    onStatusUpdate: (update: StatusUpdate) => {
      updateMessageStatus(update.message_id, update.status);
    },
    onTyping: (conversationId: number, isTyping: boolean) => {
      if (isTyping) {
        setTyping(conversationId, true);
        // Auto-clear typing indicator after 3 seconds
        setTimeout(() => clearTyping(conversationId), 3000);
      } else {
        clearTyping(conversationId);
      }
    },
    onConnect: () => {
      setConnected(true);
      setConnectionError(null);
    },
    onDisconnect: () => {
      setConnected(false);
    },
    enabled: !isDemoMode, // Disable WebSocket in demo mode
  });

  // Update connection state (only when not in demo mode)
  useEffect(() => {
    if (!isDemoMode) {
      setConnected(isConnected);
      if (error) {
        setConnectionError(error);
      }
    }
  }, [isConnected, error, setConnected, setConnectionError, isDemoMode]);

  return (
    <div className="h-full flex flex-col bg-gray-100">
      {/* Connection error banner */}
      <ConnectionBanner />
      
      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar with conversation list */}
        <ConversationList />
        
        {/* Chat area */}
        <ChatWindow />
      </div>
    </div>
  );
};

export default WhatsAppChat;
