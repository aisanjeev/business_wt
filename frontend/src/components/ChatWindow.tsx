'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import Image from 'next/image';
import { useConversationStore, useMessageStore, useUIStore, useAuthStore } from '@/hooks/useAppState';
import { useWebSocket } from '@/hooks/useWebSocket';
import { messageApi, mediaApi, contactApi, getMediaUrl } from '@/services/api';
import { Message, MessageStatus, MessageType, Contact } from '@/types';
import { formatMessageTime, getInitials, stringToColor } from '@/utils/formatters';
import ContactInfo from './ContactInfo';

// Message status icons
const MessageStatusIcon: React.FC<{ status: MessageStatus }> = ({ status }) => {
  switch (status) {
    case 'pending':
      return (
        <svg className="w-4 h-4 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <circle cx="12" cy="12" r="10" strokeWidth="2" />
        </svg>
      );
    case 'sent':
      return (
        <svg className="w-4 h-4 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      );
    case 'delivered':
      return (
        <svg className="w-4 h-4 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="18 6 7 17 2 12" />
          <polyline points="22 6 11 17" />
        </svg>
      );
    case 'read':
      return (
        <svg className="w-4 h-4 text-blue-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="18 6 7 17 2 12" />
          <polyline points="22 6 11 17" />
        </svg>
      );
    case 'failed':
      return (
        <svg className="w-4 h-4 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="15" y1="9" x2="9" y2="15" />
          <line x1="9" y1="9" x2="15" y2="15" />
        </svg>
      );
    default:
      return null;
  }
};

// Single message bubble component
interface MessageBubbleProps {
  message: Message;
  showAvatar?: boolean;
  contactName?: string;
  conversationId?: number;
  onDelete?: (messageId: number) => void;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, showAvatar, contactName, conversationId, onDelete }) => {
  const isOutbound = message.sender_type === 'outbound';
  const [showDeleteConfirm, setShowDeleteConfirm] = React.useState(false);
  const [isDeleting, setIsDeleting] = React.useState(false);
  const [showDeleteButton, setShowDeleteButton] = React.useState(false);
  
  const handleDelete = async () => {
    if (!message.id || !onDelete) return;
    
    setIsDeleting(true);
    try {
      await onDelete(message.id);
      setShowDeleteConfirm(false);
    } catch (error) {
      console.error('Failed to delete message:', error);
    } finally {
      setIsDeleting(false);
    }
  };
  
  return (
    <div 
      className={`flex ${isOutbound ? 'justify-end' : 'justify-start'} mb-3 group`}
      onMouseEnter={() => isOutbound && setShowDeleteButton(true)}
      onMouseLeave={() => setShowDeleteButton(false)}
    >
      {/* Avatar for inbound messages */}
      {!isOutbound && showAvatar && (
        <div 
          className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium mr-2 flex-shrink-0"
          style={{ backgroundColor: stringToColor(contactName || '') }}
        >
          {getInitials(contactName || 'Unknown')}
        </div>
      )}
      
      {!isOutbound && !showAvatar && <div className="w-8 mr-2" />}
      
      <div className={`max-w-[70%] ${isOutbound ? 'order-1' : ''}`}>
        {/* Message content */}
        <div
          className={`px-4 py-2 rounded-2xl ${
            isOutbound
              ? 'bg-green-500 text-white rounded-br-md'
              : 'bg-white text-gray-900 rounded-bl-md shadow-sm border border-gray-100'
          }`}
        >
          {/* Text message */}
          {message.message_type === 'text' && (
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          )}
          
          {/* Image message */}
          {message.message_type === 'image' && message.media_url && (
            <div>
              <Image 
                src={getMediaUrl(message.media_url)} 
                alt="Image" 
                width={300}
                height={200}
                className="max-w-full rounded-lg cursor-pointer hover:opacity-90"
                onClick={() => window.open(getMediaUrl(message.media_url), '_blank')}
                unoptimized
              />
              {message.content && (
                <p className="mt-2 whitespace-pre-wrap break-words">{message.content}</p>
              )}
            </div>
          )}
          
          {/* Document message */}
          {message.message_type === 'document' && message.media_url && (
            <a 
              href={getMediaUrl(message.media_url)} 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-current hover:underline"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span>{message.media_filename || message.content || 'Document'}</span>
            </a>
          )}
          
          {/* Audio message */}
          {message.message_type === 'audio' && message.media_url && (
            <audio controls className="max-w-full">
              <source src={getMediaUrl(message.media_url)} type={message.media_mime_type || "audio/mpeg"} />
              Your browser does not support the audio element.
            </audio>
          )}
          
          {/* Video message */}
          {message.message_type === 'video' && message.media_url && (
            <div>
              <video 
                controls 
                className="max-w-full rounded-lg"
                style={{ maxWidth: '300px' }}
              >
                <source src={getMediaUrl(message.media_url)} type={message.media_mime_type || "video/mp4"} />
                Your browser does not support the video element.
              </video>
              {message.content && (
                <p className="mt-2 whitespace-pre-wrap break-words">{message.content}</p>
              )}
            </div>
          )}
          
          {/* Sticker message */}
          {message.message_type === 'sticker' && message.media_url && (
            <div>
              <Image 
                src={getMediaUrl(message.media_url)} 
                alt="Sticker" 
                width={256}
                height={256}
                className="max-w-full rounded-lg cursor-pointer hover:opacity-90"
                style={{ maxWidth: '256px', maxHeight: '256px' }}
                onClick={() => window.open(getMediaUrl(message.media_url), '_blank')}
                unoptimized
              />
            </div>
          )}
        </div>
        
        {/* Timestamp and status */}
        <div className={`flex items-center gap-1 mt-1 ${isOutbound ? 'justify-end' : 'justify-start'}`}>
          <span className="text-xs text-gray-500">
            {formatMessageTime(message.timestamp || message.created_at)}
          </span>
          {isOutbound && <MessageStatusIcon status={message.status} />}
          {isOutbound && showDeleteButton && message.id && (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="ml-1 p-1 text-gray-400 hover:text-red-500 transition-colors"
              title="Delete message"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
        </div>
      </div>
      
      {/* Delete confirmation modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-2">Delete Message</h3>
            <p className="text-gray-600 mb-4">
              {message.media_url 
                ? "Are you sure you want to delete this message? The media file will also be deleted."
                : "Are you sure you want to delete this message? This action cannot be undone."}
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={isDeleting}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="px-4 py-2 text-white bg-red-500 rounded-lg hover:bg-red-600 transition-colors disabled:opacity-50"
              >
                {isDeleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Typing indicator component
const TypingIndicator: React.FC<{ contactName?: string }> = ({ contactName }) => (
  <div className="flex items-center gap-2 mb-3">
    <div 
      className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium"
      style={{ backgroundColor: stringToColor(contactName || '') }}
    >
      {getInitials(contactName || 'Unknown')}
    </div>
    <div className="bg-white px-4 py-3 rounded-2xl rounded-bl-md shadow-sm border border-gray-100">
      <div className="flex gap-1">
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
    </div>
  </div>
);

// Main ChatWindow component
const ChatWindow: React.FC = () => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [inputValue, setInputValue] = useState('');
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [showContactInfo, setShowContactInfo] = useState(false);
  const [contactDetails, setContactDetails] = useState<Contact | null>(null);
  const [loadingContactDetails, setLoadingContactDetails] = useState(false);
  
  // Store hooks
  const { selectedConversationId, conversations } = useConversationStore();
  const { messages, setMessages, addMessage, replaceMessage, updateMessage, isLoading, setLoading, isSending, setSending, drafts, setDraft, clearDraft } = useMessageStore();
  
  const handleDeleteMessage = async (messageId: number) => {
    if (!selectedConversationId) return;
    
    try {
      const response = await messageApi.deleteMessage(messageId);
      if (response.success) {
        // Remove message from local state
        const updatedMessages = (messages[selectedConversationId] || []).filter(
          m => m.id !== messageId
        );
        setMessages(selectedConversationId, updatedMessages);
      } else {
        alert(response.error || 'Failed to delete message');
      }
    } catch (error) {
      console.error('Error deleting message:', error);
      alert('Failed to delete message');
    }
  };
  const { typingIndicators, setTyping, clearTyping, isConnected } = useUIStore();
  const { token } = useAuthStore();
  
  const isDemoMode = token?.startsWith('demo-token-');
  
  // Get selected conversation and its messages
  const selectedConversation = (conversations || []).find(c => c.id === selectedConversationId);
  const conversationMessages = selectedConversationId ? (messages[selectedConversationId] || []) : [];
  const isTyping = selectedConversationId ? typingIndicators[selectedConversationId] : false;
  
  // WebSocket hook
  const { sendTypingIndicator, markAsRead } = useWebSocket({
    conversationId: selectedConversationId || undefined,
    onMessage: (message) => {
      if (selectedConversationId && message.conversation_id === selectedConversationId) {
        addMessage(selectedConversationId, message);
      }
    },
    onTyping: (convId, typing) => {
      if (typing) {
        setTyping(convId, true);
      } else {
        clearTyping(convId);
      }
    },
    enabled: !!selectedConversationId,
  });

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const loadMessages = useCallback(async () => {
    if (!selectedConversationId) return;
    
    // In demo mode, messages are already loaded by Dashboard
    if (isDemoMode) {
      setLoading(selectedConversationId, false);
      return;
    }
    
    setLoading(selectedConversationId, true);
    try {
      const response = await messageApi.getMessages(selectedConversationId);
      if (response.success && response.data) {
        setMessages(selectedConversationId, response.data.items);
        
        // Mark messages as read
        const unreadMessageIds = response.data.items
          .filter(m => m.sender_type === 'inbound' && m.status !== 'read')
          .map(m => m.message_id);
        
        if (unreadMessageIds.length > 0) {
          markAsRead(selectedConversationId, unreadMessageIds);
        }
      }
    } catch (error) {
      console.error('Failed to load messages:', error);
    } finally {
      setLoading(selectedConversationId, false);
    }
  }, [selectedConversationId, setLoading, setMessages, markAsRead, isDemoMode]);

  // Load messages when conversation changes
  useEffect(() => {
    if (selectedConversationId && !isDemoMode && !messages[selectedConversationId]) {
      loadMessages();
    }
    
    // Restore draft
    if (selectedConversationId && drafts[selectedConversationId]) {
      setInputValue(drafts[selectedConversationId]);
    } else {
      setInputValue('');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedConversationId]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    scrollToBottom();
  }, [conversationMessages.length, scrollToBottom]);

  // Focus input when conversation changes
  useEffect(() => {
    if (selectedConversationId && inputRef.current) {
      inputRef.current.focus();
    }
  }, [selectedConversationId]);

  const loadMoreMessages = async () => {
    if (!selectedConversationId || isLoadingMore) return;
    
    setIsLoadingMore(true);
    try {
      const currentMessages = messages[selectedConversationId] || [];
      
      // You would pass a cursor/page here in a real implementation
      const response = await messageApi.getMessages(selectedConversationId, 2);
      if (response.success && response.data && response.data.items.length > 0) {
        // Prepend older messages
        const newMessages = response.data.items.filter(
          m => !currentMessages.some(cm => cm.message_id === m.message_id)
        );
        if (newMessages.length > 0) {
          setMessages(selectedConversationId, [...newMessages, ...currentMessages]);
        }
      }
    } catch (error) {
      console.error('Failed to load more messages:', error);
    } finally {
      setIsLoadingMore(false);
    }
  };

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop } = e.currentTarget;
    // Load more when scrolled to top
    if (scrollTop === 0 && conversationMessages.length >= 50) {
      loadMoreMessages();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setInputValue(value);
    
    // Save draft
    if (selectedConversationId) {
      if (value) {
        setDraft(selectedConversationId, value);
      } else {
        clearDraft(selectedConversationId);
      }
    }
    
    // Send typing indicator
    if (selectedConversationId && value) {
      sendTypingIndicator(selectedConversationId, true);
    }
  };

  const handleSendMessage = async () => {
    if ((!inputValue.trim() && !selectedFile) || !selectedConversationId || isSending || uploadingFile) return;
    
    const content = inputValue.trim();
    let mediaUrl: string | undefined;
    let mediaMimeType: string | undefined;
    let messageType: MessageType = 'text';
    
    // Upload file if selected
    if (selectedFile) {
      setUploadingFile(true);
      try {
        const uploadResponse = await mediaApi.uploadFile(selectedFile);
        if (uploadResponse.success && uploadResponse.data) {
          mediaUrl = uploadResponse.data.url;
          mediaMimeType = uploadResponse.data.content_type;
          
          // Determine message type from MIME type
          if (mediaMimeType.startsWith('image/')) {
            messageType = 'image';
          } else if (mediaMimeType.startsWith('video/')) {
            messageType = 'video';
          } else if (mediaMimeType.startsWith('audio/')) {
            messageType = 'audio';
          } else {
            messageType = 'document';
          }
        } else {
          alert(uploadResponse.error || 'Failed to upload file');
          setUploadingFile(false);
          return;
        }
      } catch (error) {
        console.error('File upload error:', error);
        alert('Failed to upload file');
        setUploadingFile(false);
        return;
      }
      setUploadingFile(false);
    }
    
    setInputValue('');
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    clearDraft(selectedConversationId);
    setSending(true);
    
    // Stop typing indicator
    sendTypingIndicator(selectedConversationId, false);
    
    // Create optimistic message
    const optimisticMessage: Message = {
      id: Date.now(),
      conversation_id: selectedConversationId,
      message_id: `temp-${Date.now()}`,
      sender_type: 'outbound',
      message_type: messageType,
      content: content || '',
      media_url: mediaUrl,
      media_mime_type: mediaMimeType,
      status: 'pending',
      timestamp: new Date().toISOString(),
      created_at: new Date().toISOString(),
    };
    
    addMessage(selectedConversationId, optimisticMessage);
    
    // In demo mode, simulate sending
    if (isDemoMode) {
      setTimeout(() => {
        const updatedMessages = (messages[selectedConversationId] || []).map(m =>
          m.message_id === optimisticMessage.message_id 
            ? { ...m, status: 'delivered' as MessageStatus } 
            : m
        );
        setMessages(selectedConversationId, updatedMessages);
        setSending(false);
        
        // Simulate "read" status after a short delay
        setTimeout(() => {
          const readMessages = (messages[selectedConversationId] || []).map(m =>
            m.message_id === optimisticMessage.message_id 
              ? { ...m, status: 'read' as MessageStatus } 
              : m
          );
          setMessages(selectedConversationId, readMessages);
        }, 1500);
      }, 500);
      return;
    }
    
    try {
      const response = await messageApi.sendMessage({
        conversation_id: selectedConversationId,
        content: content || '',
        message_type: messageType,
        media_url: mediaUrl,
        media_mime_type: mediaMimeType,
      });
      
      if (response.success && response.data) {
        // Replace the optimistic message with real data from server
        // Use store function that accesses current state
        replaceMessage(
          selectedConversationId,
          optimisticMessage.message_id,
          { ...response.data, status: response.data.status || 'sent' }
        );
      } else {
        // Mark message as failed if API call failed
        updateMessage(selectedConversationId, optimisticMessage.message_id, { 
          status: 'failed' as MessageStatus 
        });
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      // Mark message as failed
      updateMessage(selectedConversationId, optimisticMessage.message_id, { 
        status: 'failed' as MessageStatus 
      });
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // No conversation selected
  if (!selectedConversationId || !selectedConversation) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-gray-200 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-1">No conversation selected</h3>
          <p className="text-gray-500">Select a conversation from the sidebar to start chatting</p>
        </div>
      </div>
    );
  }

  // Handle both nested contact object and flat contact_name/contact_phone fields
  const contactName = selectedConversation?.contact_name || selectedConversation?.contact?.name || 'Unknown Contact';
  const contactPhone = selectedConversation?.contact_phone || selectedConversation?.contact?.phone_number || '';
  const contactAvatar = selectedConversation?.contact_avatar || selectedConversation?.contact?.avatar_url;

  return (
    <div className="flex-1 flex flex-col bg-gray-50">
      {/* Header */}
      <div className="h-16 px-4 flex items-center justify-between bg-white border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div 
            className="w-10 h-10 rounded-full flex items-center justify-center text-white font-medium flex-shrink-0"
            style={{ backgroundColor: stringToColor(contactName) }}
          >
            {contactAvatar ? (
              <Image
                src={getMediaUrl(contactAvatar)}
                alt={contactName}
                width={40}
                height={40}
                className="w-10 h-10 rounded-full object-cover"
                unoptimized
                onError={(e) => {
                  // Fallback to initials if image fails to load
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                  const parent = target.parentElement;
                  if (parent) {
                    parent.textContent = getInitials(contactName);
                  }
                }}
              />
            ) : (
              getInitials(contactName)
            )}
          </div>
          <div>
            <h2 className="font-semibold text-gray-900">{contactName}</h2>
            <p className="text-sm text-gray-500">{contactPhone}</p>
          </div>
        </div>
        
        {/* Connection status */}
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-gray-500">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Messages */}
      <div 
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto px-4 py-4"
        onScroll={handleScroll}
      >
        {/* Loading indicator */}
        {isLoadingMore && (
          <div className="text-center py-2">
            <span className="text-sm text-gray-500">Loading older messages...</span>
          </div>
        )}
        
        {/* Loading state */}
        {isLoading[selectedConversationId] && conversationMessages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500" />
          </div>
        )}
        
        {/* Messages list */}
        {conversationMessages.map((message, index) => {
          const prevMessage = conversationMessages[index - 1];
          const showAvatar = 
            message.sender_type === 'inbound' && 
            (!prevMessage || prevMessage.sender_type !== 'inbound');
          
          return (
            <MessageBubble
              key={message.message_id || message.id}
              message={message}
              showAvatar={showAvatar}
              contactName={contactName}
              conversationId={selectedConversationId}
              onDelete={handleDeleteMessage}
            />
          );
        })}
        
        {/* Typing indicator */}
        {isTyping && <TypingIndicator contactName={contactName} />}
        
        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="p-4 bg-white border-t border-gray-200">
        <div className="flex items-end gap-2">
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,video/*,audio/*,.pdf,.doc,.docx"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) {
                setSelectedFile(file);
              }
            }}
          />
          
          {/* Attachment button */}
          <button 
            onClick={() => fileInputRef.current?.click()}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors"
            title="Attach file"
            disabled={uploadingFile}
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
            </svg>
          </button>
          
          {/* Selected file indicator */}
          {selectedFile && (
            <div className="flex items-center gap-2 px-3 py-1 bg-blue-50 rounded-lg text-sm">
              <span className="text-blue-700 truncate max-w-[150px]">{selectedFile.name}</span>
              <button
                onClick={() => setSelectedFile(null)}
                className="text-blue-700 hover:text-blue-900"
              >
                ×
              </button>
            </div>
          )}
          
          {/* Text input */}
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Type a message..."
              className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-2xl resize-none focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
              rows={1}
              style={{ maxHeight: '120px' }}
            />
            
            {/* Emoji button */}
            <button 
              className="absolute right-3 bottom-3 text-gray-500 hover:text-gray-700"
              title="Add emoji"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </button>
          </div>
          
          {/* Send button */}
          <button
            onClick={handleSendMessage}
            disabled={(!inputValue.trim() && !selectedFile) || isSending || uploadingFile}
            className={`p-3 rounded-full transition-colors ${
              (inputValue.trim() || selectedFile) && !isSending && !uploadingFile
                ? 'bg-green-500 text-white hover:bg-green-600'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
            title="Send message"
          >
            {isSending ? (
              <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatWindow;
