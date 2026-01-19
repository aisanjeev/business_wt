// Contact types
export interface Contact {
  id: number;
  phone_number: string;
  name: string;
  email?: string;
  avatar_url?: string;
  business_account_id?: string;
  status: 'active' | 'inactive' | 'blocked';
  source?: 'imported' | 'chat' | 'manual';
  tags?: string[];
  list_ids?: number[];
  blocked_at?: string;
  created_at: string;
  updated_at: string;
}

// Conversation types
export interface Conversation {
  id: number;
  contact_id: number;
  contact?: Contact;
  // Fields from ConversationListItem (sidebar list response)
  contact_name?: string;
  contact_phone?: string;
  contact_avatar?: string | null;
  last_message_type?: string;
  last_message_sender_type?: string; // "inbound" or "outbound"
  // Common fields
  thread_id?: string;
  last_message_at: string;
  last_message?: string;
  is_active: boolean;
  assigned_to?: number;
  tags?: string[];
  unread_count?: number;
  created_at?: string;
}

// Message types
export type MessageStatus = 'pending' | 'sent' | 'delivered' | 'read' | 'failed';
export type MessageType = 'text' | 'image' | 'document' | 'audio' | 'video' | 'sticker';
export type SenderType = 'inbound' | 'outbound';

export interface Message {
  id: number;
  conversation_id: number;
  message_id: string;
  sender_type: SenderType;
  message_type: MessageType;
  content: string;
  media_url?: string;
  media_mime_type?: string;
  media_filename?: string;
  status: MessageStatus;
  timestamp: string;
  created_at: string;
}

// Message Template types
export interface MessageTemplate {
  id: number;
  user_id: number;
  name: string;
  template_id?: string; // Legacy field
  meta_template_id?: string; // Meta API template ID
  waba_id?: string; // WhatsApp Business Account ID
  category: 'marketing' | 'utility' | 'authentication';
  language: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'DISABLED' | 'FLAGGED' | 'active' | 'inactive'; // Legacy statuses included
  // Template structure
  header_type?: 'TEXT' | 'IMAGE' | 'VIDEO' | 'DOCUMENT' | null;
  header_content?: string | null;
  body_text?: string;
  footer_text?: string | null;
  buttons?: {
    type?: 'QUICK_REPLY' | 'CALL_TO_ACTION' | 'URL';
    buttons?: Array<{
      type?: string;
      text?: string;
      url?: string;
      phone_number?: string;
    }>;
  } | null;
  variables?: Record<string, string>; // Variable definitions and sample data
  rejection_reason?: string | null;
  // Legacy fields
  content?: string; // Legacy field, use body_text instead
  created_at: string;
  updated_at: string;
}

// WebSocket event types
export type WebSocketEventType = 
  | 'message'
  | 'new_message'
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

// Meta Account Connection types
export interface MetaAccountConnection {
  id: number;
  user_id: number;
  meta_business_account_id: string;
  phone_number_id: string;
  business_phone_number?: string;
  status: 'connected' | 'disconnected' | 'pending_verification';
  business_verification_status: 'verified' | 'unverified';
  webhook_url?: string;
  usage_tracking_enabled: boolean;
  connected_at?: string;
  created_at: string;
  updated_at: string;
}

// Contact List Folder types
export interface ContactListFolder {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  color?: string;
  parent_folder_id?: number;
  lists_count?: number;
  created_at: string;
  updated_at: string;
}

// Contact List types
export interface ContactList {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  color?: string;
  folder_id?: number;
  contacts_count?: number;
  created_at: string;
  updated_at: string;
}

// Contact Import types
export interface ContactImport {
  id: number;
  user_id: number;
  filename: string;
  file_format: 'csv' | 'excel' | 'json';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total_rows: number;
  successful_rows: number;
  failed_rows: number;
  error_log?: Record<string, any>;
  contact_list_id?: number;
  created_at: string;
  completed_at?: string;
}

export interface ContactImportStatus {
  id: number;
  status: string;
  total_rows: number;
  successful_rows: number;
  failed_rows: number;
  progress_percentage: number;
}

// Bulk Message Campaign types
export interface BulkMessageCampaign {
  id: number;
  user_id: number;
  name: string;
  template_id?: number;
  template_variables?: Record<string, string>;
  target_contacts?: Record<string, any>;
  message_content: string;
  status: 'draft' | 'scheduled' | 'sending' | 'completed' | 'failed';
  total_recipients: number;
  sent_count: number;
  failed_count: number;
  scheduled_at?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface BulkMessageCampaignCreate {
  name: string;
  template_id?: number;
  template_variables?: Record<string, string>;
  target_contacts?: Record<string, any>;
  list_ids?: number[];
  tag_names?: string[];
  contact_ids?: number[];
  message_content: string;
  scheduled_at?: string;
}

export interface CampaignStatus {
  id: number;
  status: string;
  total_recipients: number;
  sent_count: number;
  failed_count: number;
  progress_percentage: number;
  started_at?: string;
  completed_at?: string;
}

// API Usage types
export interface ApiUsage {
  id: number;
  user_id: number;
  meta_phone_number_id?: string;
  message_type: string;
  api_endpoint: string;
  response_status: number;
  estimated_cost?: string;
  request_id?: string;
  timestamp: string;
}

export interface UsageStats {
  user_id: number;
  total_messages: number;
  total_api_calls: number;
  total_cost: number;
  period_start: string;
  period_end: string;
  breakdown_by_type: Record<string, number>;
}

export interface UsageCost {
  user_id: number;
  total_cost: number;
  period_start: string;
  period_end: string;
  cost_breakdown: Record<string, number>;
}

// OAuth Exchange types
export interface BusinessAccount {
  id: string;
  name?: string;
  timezone_id?: string;
  primary_page_id?: string;
}

export interface PhoneNumberOption {
  id: string;
  display_phone_number?: string;
  verified_name?: string;
  code_verification_status?: string;
  eligibility_for_api_business_global_search?: string;
}

export interface OAuthExchangeResponse {
  access_token: string;
  expires_in: number;
  business_accounts: BusinessAccount[];
  phone_numbers: PhoneNumberOption[];
}

export interface ConnectionCompleteRequest {
  business_account_id: string;
  phone_number_id: string;
  access_token: string;
  business_phone_number?: string;
}