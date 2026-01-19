import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  ApiResponse,
  PaginatedResponse,
  Conversation,
  Message,
  Contact,
  SendMessageRequest,
  MessageTemplate,
  MetaAccountConnection,
  ContactImport,
  ContactImportStatus,
  BulkMessageCampaign,
  BulkMessageCampaignCreate,
  CampaignStatus,
  ApiUsage,
  UsageStats,
  UsageCost,
  OAuthExchangeResponse,
  ConnectionCompleteRequest,
  ContactList,
  ContactListFolder,
} from '@/types';

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Get the proper media URL for displaying attachments.
 * - Local URLs (/api/media/...) get the full backend URL prepended
 * - WhatsApp URLs (lookaside.fbsbx.com, etc.) get proxied through our backend
 * - Other URLs are returned as-is
 */
export function getMediaUrl(mediaUrl: string | undefined | null): string {
  if (!mediaUrl) return '';
  
  // If it's a local media path, prepend the API base URL
  if (mediaUrl.startsWith('/api/media/')) {
    return `${API_BASE_URL}${mediaUrl}`;
  }
  
  // If it's a WhatsApp URL, proxy it through our backend
  const whatsappDomains = ['lookaside.fbsbx.com', 'scontent.whatsapp.net', 'mmg.whatsapp.net'];
  if (whatsappDomains.some(domain => mediaUrl.includes(domain))) {
    return `${API_BASE_URL}/api/media/proxy?url=${encodeURIComponent(mediaUrl)}`;
  }
  
  // For other URLs, return as-is (e.g., external image URLs)
  return mediaUrl;
}

// Create axios instance with default config
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - redirect to login or refresh token
      if (typeof window !== 'undefined') {
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Helper function to handle API errors
const handleApiError = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.message || error.message || 'An error occurred';
  }
  return 'An unexpected error occurred';
};

// ============================================
// Conversation API
// ============================================

export const conversationApi = {
  /**
   * Get all conversations (list for sidebar)
   */
  async getConversations(
    limit: number = 50
  ): Promise<ApiResponse<Conversation[]>> {
    try {
      const response = await apiClient.get(`/api/contacts/conversations/list?limit=${limit}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get a single conversation by ID
   */
  async getConversation(conversationId: number): Promise<ApiResponse<Conversation>> {
    try {
      const response = await apiClient.get(`/api/contacts/conversations/${conversationId}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Create a new conversation with a contact
   */
  async createConversation(contactId: number): Promise<ApiResponse<Conversation>> {
    try {
      const response = await apiClient.post('/api/contacts', { contact_id: contactId });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Update conversation (e.g., assign to user, add tags)
   */
  async updateConversation(
    conversationId: number,
    data: Partial<Conversation>
  ): Promise<ApiResponse<Conversation>> {
    try {
      const response = await apiClient.patch(`/api/contacts/conversations/${conversationId}`, data);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Clear all conversation history for the current user
   */
  async clearAllConversations(): Promise<ApiResponse<{ message: string }>> {
    try {
      const response = await apiClient.delete('/api/contacts/conversations/clear-all');
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },
};

// ============================================
// Media API
// ============================================

export const mediaApi = {
  /**
   * Upload a media file
   */
  async uploadFile(file: File): Promise<ApiResponse<{ url: string; filename: string; content_type: string; size: number }>> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await apiClient.post('/api/media/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },
};

// ============================================
// Message API
// ============================================

export const messageApi = {
  /**
   * Get messages for a conversation
   */
  async getMessages(
    conversationId: number,
    page: number = 1,
    pageSize: number = 50
  ): Promise<ApiResponse<PaginatedResponse<Message>>> {
    try {
      const params = new URLSearchParams({
        conversation_id: conversationId.toString(),
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      
      const response = await apiClient.get(`/api/messages?${params}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Send a new message
   */
  async sendMessage(data: SendMessageRequest & { media_url?: string; media_mime_type?: string }): Promise<ApiResponse<Message>> {
    try {
      const response = await apiClient.post('/api/messages/send', data);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Send a message by phone number (creates/finds contact and conversation)
   */
  async sendMessageByPhone(data: { phone_number: string; content: string; contact_name?: string }): Promise<ApiResponse<Message>> {
    try {
      const response = await apiClient.post('/api/messages/send-by-phone', data);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Update message status (e.g., mark as read)
   */
  async updateMessageStatus(
    messageId: string,
    status: string
  ): Promise<ApiResponse<Message>> {
    try {
      const response = await apiClient.patch(`/api/messages/${messageId}/status`, { status });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Send a template message
   */
  async sendTemplateMessage(
    conversationId: number,
    templateId: number,
    variables?: Record<string, string>
  ): Promise<ApiResponse<Message>> {
    try {
      const response = await apiClient.post('/api/messages/template', {
        conversation_id: conversationId,
        template_id: templateId,
        variables,
      });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Delete a message
   */
  async deleteMessage(messageId: number): Promise<ApiResponse<{ message: string }>> {
    try {
      const response = await apiClient.delete(`/api/messages/${messageId}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },
};

// ============================================
// Contact API
// ============================================

export const contactApi = {
  /**
   * Get all contacts with pagination
   */
  async getContacts(
    page: number = 1,
    pageSize: number = 20,
    search?: string,
    source?: 'imported' | 'chat' | 'manual' | 'all',
    tags?: string
  ): Promise<ApiResponse<PaginatedResponse<Contact>>> {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      if (search) {
        params.append('search', search);
      }
      if (source && source !== 'all') {
        params.append('source', source);
      }
      if (tags) {
        params.append('tags', tags);
      }
      
      const response = await apiClient.get(`/api/contacts?${params}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get a single contact by ID with full details
   */
  async getContactDetails(contactId: number): Promise<ApiResponse<Contact & { last_message?: string; last_message_at?: string; unread_count?: number }>> {
    try {
      const response = await apiClient.get(`/api/contacts/${contactId}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get a single contact by ID
   */
  async getContact(contactId: number): Promise<ApiResponse<Contact>> {
    try {
      const response = await apiClient.get(`/api/contacts/${contactId}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Create a new contact
   */
  async createContact(data: Partial<Contact>): Promise<ApiResponse<Contact>> {
    try {
      const response = await apiClient.post('/api/contacts', data);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Update a contact
   */
  async updateContact(
    contactId: number,
    data: Partial<Contact>
  ): Promise<ApiResponse<Contact>> {
    try {
      const response = await apiClient.patch(`/api/contacts/${contactId}`, data);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Delete a contact
   */
  async deleteContact(contactId: number): Promise<ApiResponse<void>> {
    try {
      await apiClient.delete(`/api/contacts/${contactId}`);
      return { success: true };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Update contact tags
   */
  async updateContactTags(contactId: number, tags: string[]): Promise<ApiResponse<Contact>> {
    try {
      const response = await apiClient.patch(`/api/contacts/${contactId}/tags`, null, {
        params: { tags: tags.join(',') },
      });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },
};

// ============================================
// Template API
// ============================================

export const templateApi = {
  /**
   * Get all message templates
   */
  async getTemplates(): Promise<ApiResponse<MessageTemplate[]>> {
    try {
      const response = await apiClient.get('/api/templates');
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get a single template by ID
   */
  async getTemplate(templateId: number): Promise<ApiResponse<MessageTemplate>> {
    try {
      const response = await apiClient.get(`/api/templates/${templateId}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },
};

// ============================================
// Authentication API
// ============================================

export const authApi = {
  /**
   * Login user
   */
  async login(email: string, password: string): Promise<ApiResponse<{ token: string; user: unknown }>> {
    try {
      const response = await apiClient.post('/api/auth/login', { email, password });
      const token = response.data.access_token || response.data.token;
      if (token && typeof window !== 'undefined') {
        localStorage.setItem('auth_token', token);
      }
      // Fetch user profile after successful login
      const profileResponse = await apiClient.get('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` }
      });
      return { 
        success: true, 
        data: { 
          token, 
          user: profileResponse.data 
        } 
      };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Logout user
   */
  async logout(): Promise<void> {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
    }
  },

  /**
   * Get current user profile
   */
  async getProfile(): Promise<ApiResponse<unknown>> {
    try {
      const response = await apiClient.get('/api/auth/profile');
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Refresh auth token
   */
  async refreshToken(): Promise<ApiResponse<{ token: string }>> {
    try {
      const response = await apiClient.post('/api/auth/refresh');
      if (response.data.token && typeof window !== 'undefined') {
        localStorage.setItem('auth_token', response.data.token);
      }
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },
};

// ============================================
// Meta OAuth API
// ============================================

export const metaApi = {
  /**
   * Get Meta OAuth authorization URL
   */
  async getOAuthUrl(): Promise<ApiResponse<{ auth_url: string; state: string }>> {
    try {
      const response = await apiClient.get('/api/meta/oauth/url');
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get current Meta connection status
   */
  async getConnection(): Promise<ApiResponse<MetaAccountConnection>> {
    try {
      const response = await apiClient.get('/api/meta/connection');
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Disconnect Meta account
   */
  async disconnect(): Promise<ApiResponse<{ message: string }>> {
    try {
      const response = await apiClient.delete('/api/meta/connection');
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Exchange OAuth authorization code for access token and get business accounts/phone numbers
   * Note: This may take longer due to fetching from multiple business accounts
   */
  async exchangeCode(code: string): Promise<ApiResponse<OAuthExchangeResponse>> {
    try {
      // Use longer timeout for OAuth exchange (60 seconds) as it processes multiple business accounts
      const response = await apiClient.post('/api/meta/oauth/exchange', { code }, { timeout: 60000 });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Complete Meta connection with selected phone number
   */
  async completeConnection(data: ConnectionCompleteRequest): Promise<ApiResponse<MetaAccountConnection>> {
    try {
      const response = await apiClient.post('/api/meta/connection/complete', data);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },
};

// ============================================
// Contact Import API
// ============================================

export const contactImportApi = {
  /**
   * Import contacts from file
   */
  async importContacts(file: File, contactListId?: number): Promise<ApiResponse<ContactImport>> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const params = new URLSearchParams();
      if (contactListId) {
        params.append('contact_list_id', contactListId.toString());
      }

      const response = await apiClient.post(`/api/contacts/import?${params}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get import status
   */
  async getImportStatus(importId: number): Promise<ApiResponse<ContactImportStatus>> {
    try {
      const response = await apiClient.get(`/api/contacts/import/${importId}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },
};

// ============================================
// Bulk Messaging Campaigns API
// ============================================

export const campaignApi = {
  /**
   * Create a new campaign
   */
  async createCampaign(campaign: BulkMessageCampaignCreate): Promise<ApiResponse<BulkMessageCampaign>> {
    try {
      const response = await apiClient.post('/api/campaigns', campaign);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get campaigns
   */
  async getCampaigns(page: number = 1, pageSize: number = 20, status?: string): Promise<ApiResponse<PaginatedResponse<BulkMessageCampaign>>> {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      if (status) params.append('status', status);

      const response = await apiClient.get(`/api/campaigns?${params}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get campaign by ID
   */
  async getCampaign(campaignId: number): Promise<ApiResponse<BulkMessageCampaign>> {
    try {
      const response = await apiClient.get(`/api/campaigns/${campaignId}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Update campaign
   */
  async updateCampaign(campaignId: number, updates: Partial<BulkMessageCampaign>): Promise<ApiResponse<BulkMessageCampaign>> {
    try {
      const response = await apiClient.patch(`/api/campaigns/${campaignId}`, updates);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Start campaign
   */
  async startCampaign(campaignId: number): Promise<ApiResponse<{ message: string }>> {
    try {
      const response = await apiClient.post(`/api/campaigns/${campaignId}/start`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get campaign status
   */
  async getCampaignStatus(campaignId: number): Promise<ApiResponse<CampaignStatus>> {
    try {
      const response = await apiClient.get(`/api/campaigns/${campaignId}/status`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get campaign recipient logs
   */
  async getCampaignLogs(
    campaignId: number,
    page: number = 1,
    pageSize: number = 50,
    status?: string,
    search?: string
  ): Promise<ApiResponse<PaginatedResponse<any>>> {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      if (status) params.append('status', status);
      if (search) params.append('search', search);

      const response = await apiClient.get(`/api/campaigns/${campaignId}/logs?${params}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Export campaign logs
   */
  async exportCampaignLogs(campaignId: number, format: 'csv' | 'json' = 'csv'): Promise<Blob> {
    const response = await apiClient.get(`/api/campaigns/${campaignId}/logs/export?format=${format}`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

// ============================================
// Usage Tracking API
// ============================================

export const usageApi = {
  /**
   * Get storage usage for current user
   */
  async getStorage(): Promise<ApiResponse<{ user_id: number; storage_used_bytes: number; storage_formatted: string }>> {
    try {
      const response = await apiClient.get('/api/usage/storage');
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },
  /**
   * Get usage statistics
   */
  async getStats(periodStart?: string, periodEnd?: string): Promise<ApiResponse<UsageStats>> {
    try {
      const params = new URLSearchParams();
      if (periodStart) params.append('period_start', periodStart);
      if (periodEnd) params.append('period_end', periodEnd);

      const response = await apiClient.get(`/api/usage/stats?${params}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get usage costs
   */
  async getCosts(periodStart?: string, periodEnd?: string): Promise<ApiResponse<UsageCost>> {
    try {
      const params = new URLSearchParams();
      if (periodStart) params.append('period_start', periodStart);
      if (periodEnd) params.append('period_end', periodEnd);

      const response = await apiClient.get(`/api/usage/costs?${params}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get usage records
   */
  async getUsageRecords(page: number = 1, pageSize: number = 50, messageType?: string): Promise<ApiResponse<PaginatedResponse<ApiUsage>>> {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      if (messageType) params.append('message_type', messageType);

      const response = await apiClient.get(`/api/usage/records?${params}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Export usage data
   */
  async exportUsage(format: 'csv' | 'json' = 'csv', periodStart?: string, periodEnd?: string): Promise<Blob> {
    const params = new URLSearchParams({ format });
    if (periodStart) params.append('period_start', periodStart);
    if (periodEnd) params.append('period_end', periodEnd);

    const response = await apiClient.get(`/api/usage/export?${params}`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

// ============================================
// Admin API
// ============================================

export const adminApi = {
  /**
   * Get all users (admin only)
   */
  async getUsers(page: number = 1, pageSize: number = 20, search?: string): Promise<ApiResponse<PaginatedResponse<any>>> {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      if (search) params.append('search', search);

      const response = await apiClient.get(`/api/admin/users?${params}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get user details (admin only)
   */
  async getUserDetails(userId: number): Promise<ApiResponse<any>> {
    try {
      const response = await apiClient.get(`/api/admin/users/${userId}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get platform overview (admin only)
   */
  async getOverview(): Promise<ApiResponse<any>> {
    try {
      const response = await apiClient.get('/api/admin/overview');
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Create a new user (admin only)
   */
  async createUser(userData: {
    email: string;
    username: string;
    full_name?: string;
    password: string;
    is_superuser?: boolean;
    is_active?: boolean;
  }): Promise<ApiResponse<any>> {
    try {
      const response = await apiClient.post('/api/admin/users', userData);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },
};

// ============================================
// Contact List Folder API
// ============================================

export const contactListFolderApi = {
  /**
   * Create a folder
   */
  async createFolder(data: { name: string; description?: string; color?: string; parent_folder_id?: number }): Promise<ApiResponse<ContactListFolder>> {
    try {
      const response = await apiClient.post('/api/contact-lists/folders', data);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get all folders
   */
  async getFolders(): Promise<ApiResponse<ContactListFolder[]>> {
    try {
      const response = await apiClient.get('/api/contact-lists/folders');
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get folder by ID
   */
  async getFolder(folderId: number): Promise<ApiResponse<ContactListFolder>> {
    try {
      const response = await apiClient.get(`/api/contact-lists/folders/${folderId}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Update folder
   */
  async updateFolder(folderId: number, data: Partial<ContactListFolder>): Promise<ApiResponse<ContactListFolder>> {
    try {
      const response = await apiClient.patch(`/api/contact-lists/folders/${folderId}`, data);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Move folder to another folder
   */
  async moveFolder(folderId: number, parentFolderId: number | null): Promise<ApiResponse<ContactListFolder>> {
    try {
      const params = new URLSearchParams();
      if (parentFolderId !== null) {
        params.append('parent_folder_id', parentFolderId.toString());
      }
      const response = await apiClient.patch(`/api/contact-lists/folders/${folderId}/move?${params}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Delete folder
   */
  async deleteFolder(folderId: number): Promise<ApiResponse<{ message: string }>> {
    try {
      const response = await apiClient.delete(`/api/contact-lists/folders/${folderId}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },
};

// ============================================
// Contact List API
// ============================================

export const contactListApi = {
  /**
   * Create a list
   */
  async createList(data: { name: string; description?: string; color?: string; folder_id?: number }): Promise<ApiResponse<ContactList>> {
    try {
      const response = await apiClient.post('/api/contact-lists', data);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get all lists
   */
  async getLists(page: number = 1, pageSize: number = 20, folderId?: number): Promise<ApiResponse<PaginatedResponse<ContactList>>> {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      if (folderId) {
        params.append('folder_id', folderId.toString());
      }
      const response = await apiClient.get(`/api/contact-lists?${params}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get list by ID
   */
  async getList(listId: number): Promise<ApiResponse<ContactList>> {
    try {
      const response = await apiClient.get(`/api/contact-lists/${listId}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Update list
   */
  async updateList(listId: number, data: Partial<ContactList>): Promise<ApiResponse<ContactList>> {
    try {
      const response = await apiClient.patch(`/api/contact-lists/${listId}`, data);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Move list to another folder
   */
  async moveList(listId: number, folderId: number | null): Promise<ApiResponse<ContactList>> {
    try {
      const response = await apiClient.patch(`/api/contact-lists/${listId}`, {
        folder_id: folderId,
      });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Delete list
   */
  async deleteList(listId: number): Promise<ApiResponse<{ message: string }>> {
    try {
      const response = await apiClient.delete(`/api/contact-lists/${listId}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Add contact to list
   */
  async addContactToList(listId: number, contactId: number): Promise<ApiResponse<{ message: string }>> {
    try {
      const response = await apiClient.post(`/api/contact-lists/${listId}/contacts/${contactId}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Remove contact from list
   */
  async removeContactFromList(listId: number, contactId: number): Promise<ApiResponse<{ message: string }>> {
    try {
      const response = await apiClient.delete(`/api/contact-lists/${listId}/contacts/${contactId}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },

  /**
   * Get contacts in list
   */
  async getListContacts(listId: number, page: number = 1, pageSize: number = 20): Promise<ApiResponse<PaginatedResponse<Contact>>> {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      const response = await apiClient.get(`/api/contact-lists/${listId}/contacts?${params}`);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  },
};

// Export default API client for custom requests
export default apiClient;
