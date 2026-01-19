'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Image from 'next/image';
import { useConversationStore, useUIStore, useAuthStore } from '@/hooks/useAppState';
import { conversationApi } from '@/services/api';
import { Conversation } from '@/types';
import { formatConversationTime, truncateText, getInitials, stringToColor, formatPhoneNumber, isContactOnline } from '@/utils/formatters';
import { messageApi, getMediaUrl } from '@/services/api';

interface ConversationItemProps {
  conversation: Conversation;
  isSelected: boolean;
  unreadCount: number;
  onClick: () => void;
}

const ConversationItem: React.FC<ConversationItemProps> = ({
  conversation,
  isSelected,
  unreadCount,
  onClick,
}) => {
  // Handle both nested contact object and flat contact_name/contact_phone fields
  const contactName = conversation.contact_name || conversation.contact?.name || 'Unknown Contact';
  const contactPhone = conversation.contact_phone || conversation.contact?.phone_number || '';
  const contactAvatar = conversation.contact_avatar || conversation.contact?.avatar_url;
  const lastMessage = conversation.last_message || 'No messages yet';
  const lastMessageTime = conversation.last_message_at;
  
  // Check if contact is online based on recent inbound message activity
  const isOnline = isContactOnline(
    lastMessageTime,
    conversation.last_message_sender_type,
    5 // 5 minutes threshold
  );

  return (
    <div
      onClick={onClick}
      className={`flex items-center gap-3 p-3 cursor-pointer transition-colors ${
        isSelected 
          ? 'bg-green-50 border-l-4 border-l-green-500' 
          : 'hover:bg-gray-50 border-l-4 border-l-transparent'
      }`}
    >
      {/* Avatar */}
      <div className="relative flex-shrink-0">
        <div 
          className="w-12 h-12 rounded-full flex items-center justify-center text-white font-medium"
          style={{ backgroundColor: stringToColor(contactName) }}
        >
          {contactAvatar ? (
            <Image 
              src={getMediaUrl(contactAvatar)} 
              alt={contactName}
              width={48}
              height={48}
              className="w-12 h-12 rounded-full object-cover"
              unoptimized
              onError={(e) => {
                // Fallback to initials if image fails to load
                const target = e.target as HTMLImageElement;
                target.style.display = 'none';
                const parent = target.parentElement;
                if (parent) {
                  const initials = getInitials(contactName);
                  if (!parent.textContent || parent.textContent.trim() === '') {
                    parent.textContent = initials;
                  }
                }
              }}
            />
          ) : (
            getInitials(contactName)
          )}
        </div>
        
        {/* Online indicator - shows green dot if contact sent a message recently */}
        {isOnline && (
          <span className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 border-2 border-white rounded-full" title="Online" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <h3 className={`font-medium truncate ${unreadCount > 0 ? 'text-gray-900' : 'text-gray-700'}`}>
            {contactName}
          </h3>
          {lastMessageTime && (
            <span className={`text-xs flex-shrink-0 ml-2 ${
              unreadCount > 0 ? 'text-green-600 font-medium' : 'text-gray-500'
            }`}>
              {formatConversationTime(lastMessageTime)}
            </span>
          )}
        </div>
        
        <div className="flex items-center justify-between">
          <p className={`text-sm truncate ${
            unreadCount > 0 ? 'text-gray-900 font-medium' : 'text-gray-500'
          }`}>
            {truncateText(lastMessage, 40)}
          </p>
          
          {/* Unread badge */}
          {unreadCount > 0 && (
            <span className="ml-2 flex-shrink-0 min-w-[20px] h-5 px-1.5 bg-green-500 text-white text-xs font-medium rounded-full flex items-center justify-center">
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          )}
        </div>
        
        {/* Phone number */}
        <p className="text-xs text-gray-400 mt-0.5">
          {formatPhoneNumber(contactPhone)}
        </p>
      </div>
    </div>
  );
};

// Search input component
interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

const SearchInput: React.FC<SearchInputProps> = ({ value, onChange, placeholder = 'Search conversations...' }) => (
  <div className="relative">
    <svg 
      className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" 
      fill="none" 
      viewBox="0 0 24 24" 
      stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full pl-10 pr-4 py-2 bg-gray-100 border border-transparent rounded-lg focus:outline-none focus:bg-white focus:border-green-500 transition-colors"
    />
    {value && (
      <button
        onClick={() => onChange('')}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    )}
  </div>
);

// Filter tabs component
type FilterType = 'all' | 'active' | 'unread';

interface FilterTabsProps {
  activeFilter: FilterType;
  onChange: (filter: FilterType) => void;
}

const FilterTabs: React.FC<FilterTabsProps> = ({ activeFilter, onChange }) => {
  const tabs: { key: FilterType; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'active', label: 'Active' },
    { key: 'unread', label: 'Unread' },
  ];

  return (
    <div className="flex gap-1 p-1 bg-gray-100 rounded-lg">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onChange(tab.key)}
          className={`flex-1 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
            activeFilter === tab.key
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
};

// Send message by phone modal component
interface SendMessageModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const SendMessageModal: React.FC<SendMessageModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [contactName, setContactName] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { selectConversation } = useConversationStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!phoneNumber.trim() || !message.trim()) {
      setError('Phone number and message are required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await messageApi.sendMessageByPhone({
        phone_number: phoneNumber.trim(),
        content: message.trim(),
        contact_name: contactName.trim() || undefined,
      });

      if (response.success && response.data) {
        // Find the conversation that was created/used
        // The backend creates/uses a conversation, so we need to refresh and find it
        // For now, just close and refresh - the user can find it in the list
        onSuccess();
        onClose();
        setPhoneNumber('');
        setContactName('');
        setMessage('');
      } else {
        setError(response.error || 'Failed to send message');
      }
    } catch (err) {
      setError('Failed to send message. Please try again.');
      console.error('Error sending message:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Send Message to Phone Number</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label htmlFor="phone_number" className="block text-sm font-medium text-gray-700 mb-2">
                Phone Number <span className="text-red-500">*</span>
              </label>
              <input
                type="tel"
                id="phone_number"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder="+1234567890"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                required
                disabled={loading}
              />
            </div>

            <div className="mb-4">
              <label htmlFor="contact_name" className="block text-sm font-medium text-gray-700 mb-2">
                Contact Name <span className="text-gray-400 text-xs">(optional)</span>
              </label>
              <input
                type="text"
                id="contact_name"
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
                placeholder="John Doe"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                disabled={loading}
              />
            </div>

            <div className="mb-6">
              <label htmlFor="message" className="block text-sm font-medium text-gray-700 mb-2">
                Message <span className="text-red-500">*</span>
              </label>
              <textarea
                id="message"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Type your message here..."
                rows={4}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 resize-none"
                required
                disabled={loading}
              />
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={onClose}
                disabled={loading}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading || !phoneNumber.trim() || !message.trim()}
                className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Sending...
                  </>
                ) : (
                  'Send Message'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

// Main ConversationList component
const ConversationList: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState<FilterType>('all');
  const [isSendModalOpen, setIsSendModalOpen] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  
  const { 
    conversations, 
    selectedConversationId, 
    isLoading, 
    error,
    setConversations, 
    selectConversation,
    setLoading,
    setError,
  } = useConversationStore();
  
  const { unreadCounts, clearUnread } = useUIStore();
  const { token } = useAuthStore();
  
  const isDemoMode = token?.startsWith('demo-token-');

  const loadConversations = useCallback(async () => {
    // Skip API call in demo mode - data is loaded by Dashboard
    if (isDemoMode) {
      setLoading(false);
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await conversationApi.getConversations();
      if (response.success && response.data) {
        // API returns a direct list, not paginated
        const conversations = Array.isArray(response.data) ? response.data : (response.data as { items?: Conversation[] }).items || [];
        setConversations(conversations);
      } else {
        setError(response.error || 'Failed to load conversations');
      }
    } catch (err) {
      setError('Failed to load conversations');
      console.error('Error loading conversations:', err);
    } finally {
      setLoading(false);
    }
  }, [isDemoMode, setLoading, setError, setConversations]);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const handleSelectConversation = (conversationId: number) => {
    selectConversation(conversationId);
    // Clear unread count for selected conversation
    clearUnread(conversationId);
  };

  // Filter and search conversations
  const filteredConversations = (conversations || []).filter((conv) => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const matchesName = conv.contact?.name?.toLowerCase().includes(query);
      const matchesPhone = conv.contact?.phone_number?.includes(query);
      const matchesMessage = conv.last_message?.toLowerCase().includes(query);
      if (!matchesName && !matchesPhone && !matchesMessage) {
        return false;
      }
    }
    
    // Tab filter
    if (activeFilter === 'active' && !conv.is_active) {
      return false;
    }
    if (activeFilter === 'unread' && !unreadCounts[conv.id]) {
      return false;
    }
    
    return true;
  });

  // Sort by most recent message
  const sortedConversations = [...filteredConversations].sort((a, b) => {
    const dateA = new Date(a.last_message_at || a.created_at || 0).getTime();
    const dateB = new Date(b.last_message_at || b.created_at || 0).getTime();
    return dateB - dateA;
  });

  const totalUnread = Object.values(unreadCounts).reduce((sum, count) => sum + count, 0);

  return (
    <div className="w-80 bg-white border-r border-gray-200 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl font-bold text-gray-900">Messages</h1>
          
          {/* New conversation button */}
          <button 
            onClick={() => setIsSendModalOpen(true)}
            className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-full transition-colors"
            title="Send message to phone number"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>
        
        {/* Search */}
        <SearchInput value={searchQuery} onChange={setSearchQuery} />
        
        {/* Filters */}
        <div className="mt-3">
          <FilterTabs activeFilter={activeFilter} onChange={setActiveFilter} />
        </div>
      </div>

      {/* Conversation stats */}
      <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-between text-sm">
        <span className="text-gray-600">
          {filteredConversations.length} conversation{filteredConversations.length !== 1 ? 's' : ''}
        </span>
        {totalUnread > 0 && (
          <span className="text-green-600 font-medium">
            {totalUnread} unread
          </span>
        )}
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto">
        {/* Loading state */}
        {isLoading && conversations.length === 0 && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500" />
          </div>
        )}
        
        {/* Error state */}
        {error && (
          <div className="p-4 text-center">
            <p className="text-red-500 mb-2">{error}</p>
            <button
              onClick={loadConversations}
              className="text-green-600 hover:text-green-700 font-medium"
            >
              Try again
            </button>
          </div>
        )}
        
        {/* Empty state */}
        {!isLoading && !error && sortedConversations.length === 0 && (
          <div className="p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <h3 className="text-gray-900 font-medium mb-1">No conversations</h3>
            <p className="text-gray-500 text-sm">
              {searchQuery 
                ? 'No conversations match your search' 
                : 'Start a new conversation to get started'}
            </p>
          </div>
        )}
        
        {/* Conversations */}
        {sortedConversations.map((conversation) => (
          <ConversationItem
            key={conversation.id}
            conversation={conversation}
            isSelected={conversation.id === selectedConversationId}
            unreadCount={unreadCounts[conversation.id] || 0}
            onClick={() => handleSelectConversation(conversation.id)}
          />
        ))}
      </div>
      
      {/* Action buttons */}
      <div className="p-3 border-t border-gray-200 space-y-2">
        <button
          onClick={loadConversations}
          disabled={isLoading}
          className="w-full py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          <svg 
            className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {isLoading ? 'Refreshing...' : 'Refresh'}
        </button>
        
        <button
          onClick={() => setShowClearConfirm(true)}
          disabled={isLoading || isClearing || (conversations && conversations.length === 0)}
          className="w-full py-2 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
          Clear All History
        </button>
      </div>
      
      {/* Clear confirmation modal */}
      {showClearConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                  <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <h2 className="text-xl font-semibold text-gray-900">Clear All Conversation History?</h2>
              </div>
              
              <p className="text-gray-700 mb-6">
                This will permanently delete all your conversations and messages. This action cannot be undone.
                Your contacts will be preserved.
              </p>
              
              <div className="flex gap-3">
                <button
                  onClick={() => setShowClearConfirm(false)}
                  disabled={isClearing}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={async () => {
                    setIsClearing(true);
                    try {
                      const response = await conversationApi.clearAllConversations();
                      if (response.success) {
                        setShowClearConfirm(false);
                        // Clear conversations from store
                        setConversations([]);
                        // Clear selected conversation
                        selectConversation(null);
                        // Reload to show empty state
                        await loadConversations();
                      } else {
                        alert(response.error || 'Failed to clear conversations');
                      }
                    } catch (err) {
                      console.error('Error clearing conversations:', err);
                      alert('Failed to clear conversations. Please try again.');
                    } finally {
                      setIsClearing(false);
                    }
                  }}
                  disabled={isClearing}
                  className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                >
                  {isClearing ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Clearing...
                    </>
                  ) : (
                    'Clear All'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Send message modal */}
      <SendMessageModal
        isOpen={isSendModalOpen}
        onClose={() => setIsSendModalOpen(false)}
        onSuccess={() => {
          loadConversations();
        }}
      />
    </div>
  );
};

export default ConversationList;
