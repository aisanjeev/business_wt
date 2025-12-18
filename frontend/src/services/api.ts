import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  ApiResponse,
  PaginatedResponse,
  Conversation,
  Message,
  Contact,
  SendMessageRequest,
  MessageTemplate,
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
  async sendMessage(data: SendMessageRequest): Promise<ApiResponse<Message>> {
    try {
      const response = await apiClient.post('/api/messages/send', data);
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
    search?: string
  ): Promise<ApiResponse<PaginatedResponse<Contact>>> {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      if (search) {
        params.append('search', search);
      }
      
      const response = await apiClient.get(`/api/contacts?${params}`);
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

// Export default API client for custom requests
export default apiClient;
