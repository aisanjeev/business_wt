// Contact types
export interface Contact {
  id: number;
  phone_number: string;
  name: string;
  email?: string;
  avatar_url?: string;
  business_account_id?: string;
  status: 'active' | 'inactive';
  created_at: string;
  updated_at: string;
}

// Conversation types
export interface Conversation {
  id: number;
  contact_id: number;
  contact?: Contact;
  thread_id?: string;
  last_message_at: string;
  last_message?: string;
  is_active: boolean;
  assigned_to?: number;
  tags?: string[];
  unread_count?: number;
  created_at: string;
}

// Message types
export type MessageStatus = 'pending' | 'sent' | 'delivered' | 'read' | 'failed';
export type MessageType = 'text' | 'image' | 'document' | 'audio' | 'video';
export type SenderType = 'inbound' | 'outbound';

export interface Message {
  id: number;
  conversation_id: number;
  message_id: string;
  sender_type: SenderType;
  message_type: MessageType;
  content: string;
  media_url?: string;
  status: MessageStatus;
  timestamp: string;
  created_at: string;
}

// Message Template types
export interface MessageTemplate {
  id: number;
  name: string;
  template_id: string;
  content: string;
  category: 'marketing' | 'utility' | 'authentication';
  language: string;
  created_at: string;
}

// WebSocket event types
export type WebSocketEventType = 
  | 'message'
  | 'typing'
  | 'read'
  | 'status_update'
  | 'reconnect'
  | 'connected'
  | 'disconnected';

export interface WebSocketMessage {
  type: WebSocketEventType;
  payload: unknown;
  conversation_id?: number;
  timestamp?: string;
}

export interface TypingIndicator {
  conversation_id: number;
  is_typing: boolean;
  user_id?: number;
}

export interface StatusUpdate {
  message_id: string;
  status: MessageStatus;
  timestamp: string;
}

// API Response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

// Authentication types
export interface AuthUser {
  id: number;
  email: string;
  name: string;
  role: string;
}

export interface AuthState {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
}

// App State types
export interface AppState {
  // Conversations
  conversations: Conversation[];
  selectedConversationId: number | null;
  
  // Messages
  messages: Record<number, Message[]>;
  
  // Connection
  isConnected: boolean;
  connectionError: string | null;
  
  // Typing indicators
  typingIndicators: Record<number, boolean>;
  
  // Unread counts
  unreadCounts: Record<number, number>;
  
  // Draft messages
  draftMessages: Record<number, string>;
  
  // Loading states
  isLoadingConversations: boolean;
  isLoadingMessages: boolean;
  isSendingMessage: boolean;
}

// Send message request
export interface SendMessageRequest {
  conversation_id: number;
  content: string;
  message_type?: MessageType;
  phone_number?: string;
}

// WebSocket connection options
export interface WebSocketOptions {
  url: string;
  token: string;
  conversationId?: number;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  reconnectAttempts?: number;
  reconnectDelay?: number;
}
