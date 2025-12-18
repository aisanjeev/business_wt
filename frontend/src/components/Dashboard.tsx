'use client';

import React, { useEffect } from 'react';
import ConversationList from './ConversationList';
import ChatWindow from './ChatWindow';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUIStore, useConversationStore, useMessageStore, useAuthStore } from '@/hooks/useAppState';
import { Message, StatusUpdate } from '@/types';

// Header component with user profile and settings
const DashboardHeader: React.FC = () => {
  const { isConnected, connectionError } = useUIStore();
  const { user, logout } = useAuthStore();

  return (
    <header className="h-14 bg-green-600 text-white flex items-center justify-between px-4 shadow-sm">
      {/* Logo and title */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center">
          <svg className="w-5 h-5 text-green-600" viewBox="0 0 24 24" fill="currentColor">
            <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
          </svg>
        </div>
        <span className="font-semibold text-lg">WhatsApp Business</span>
      </div>

      {/* Connection status and user menu */}
      <div className="flex items-center gap-4">
        {/* Connection indicator */}
        <div className="flex items-center gap-2 px-3 py-1 bg-green-700/50 rounded-full">
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-300' : 'bg-red-400'}`} />
          <span className="text-sm">
            {connectionError ? 'Error' : isConnected ? 'Connected' : 'Connecting...'}
          </span>
        </div>

        {/* Settings button */}
        <button 
          className="p-2 hover:bg-green-700/50 rounded-full transition-colors"
          title="Settings"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>

        {/* User menu */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-green-700 rounded-full flex items-center justify-center text-sm font-medium">
            {user?.name?.charAt(0).toUpperCase() || 'U'}
          </div>
          <button
            onClick={logout}
            className="text-sm hover:underline"
            title="Logout"
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  );
};

// Connection error banner
const ConnectionBanner: React.FC = () => {
  const { connectionError, isConnected } = useUIStore();
  
  if (isConnected || !connectionError) return null;
  
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

// Main Dashboard component
const Dashboard: React.FC = () => {
  const { setConnected, setConnectionError, incrementUnread, setTyping, clearTyping } = useUIStore();
  const { updateConversation, selectedConversationId } = useConversationStore();
  const { addMessage, updateMessageStatus } = useMessageStore();

  // Global WebSocket connection for receiving messages
  const { isConnected, error } = useWebSocket({
    onMessage: (message: Message) => {
      // Add message to the store
      addMessage(message.conversation_id, message);
      
      // Update conversation's last message
      updateConversation(message.conversation_id, {
        last_message: message.content,
        last_message_at: message.timestamp || message.created_at,
      });
      
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
    enabled: true,
  });

  // Update connection state
  useEffect(() => {
    setConnected(isConnected);
    if (error) {
      setConnectionError(error);
    }
  }, [isConnected, error, setConnected, setConnectionError]);

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Header */}
      <DashboardHeader />
      
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

export default Dashboard;
