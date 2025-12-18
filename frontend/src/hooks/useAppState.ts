'use client';

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { 
  Conversation, 
  Message, 
  Contact,
  AuthUser,
  MessageStatus 
} from '@/types';

// ============================================
// Auth Store
// ============================================

interface AuthStore {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  
  // Actions
  setUser: (user: AuthUser | null) => void;
  setToken: (token: string | null) => void;
  login: (user: AuthUser, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      setUser: (user) => set({ user, isAuthenticated: !!user }),
      
      setToken: (token) => {
        if (token && typeof window !== 'undefined') {
          localStorage.setItem('auth_token', token);
        } else if (typeof window !== 'undefined') {
          localStorage.removeItem('auth_token');
        }
        set({ token });
      },
      
      login: (user, token) => {
        if (typeof window !== 'undefined') {
          localStorage.setItem('auth_token', token);
        }
        set({ user, token, isAuthenticated: true });
      },
      
      logout: () => {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth_token');
        }
        set({ user: null, token: null, isAuthenticated: false });
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ user: state.user, token: state.token }),
    }
  )
);

// ============================================
// Conversation Store
// ============================================

interface ConversationStore {
  conversations: Conversation[];
  selectedConversationId: number | null;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setConversations: (conversations: Conversation[]) => void;
  addConversation: (conversation: Conversation) => void;
  addOrUpdateConversation: (conversation: Conversation) => void;
  updateConversation: (id: number, updates: Partial<Conversation>) => void;
  removeConversation: (id: number) => void;
  selectConversation: (id: number | null) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  
  // Selectors
  getSelectedConversation: () => Conversation | undefined;
}

export const useConversationStore = create<ConversationStore>((set, get) => ({
  conversations: [],
  selectedConversationId: null,
  isLoading: false,
  error: null,

  setConversations: (conversations) => set({ conversations }),
  
  addConversation: (conversation) => 
    set((state) => ({
      conversations: [conversation, ...state.conversations],
    })),
  
  addOrUpdateConversation: (conversation) =>
    set((state) => {
      const exists = state.conversations.some((c) => c.id === conversation.id);
      if (exists) {
        // Update existing conversation
        return {
          conversations: state.conversations.map((conv) =>
            conv.id === conversation.id ? { ...conv, ...conversation } : conv
          ),
        };
      } else {
        // Add new conversation at the top
        return {
          conversations: [conversation, ...state.conversations],
        };
      }
    }),
  
  updateConversation: (id, updates) =>
    set((state) => ({
      conversations: state.conversations.map((conv) =>
        conv.id === id ? { ...conv, ...updates } : conv
      ),
    })),
  
  removeConversation: (id) =>
    set((state) => ({
      conversations: state.conversations.filter((conv) => conv.id !== id),
      selectedConversationId: 
        state.selectedConversationId === id ? null : state.selectedConversationId,
    })),
  
  selectConversation: (id) => set({ selectedConversationId: id }),
  
  setLoading: (isLoading) => set({ isLoading }),
  
  setError: (error) => set({ error }),
  
  getSelectedConversation: () => {
    const state = get();
    return state.conversations.find((c) => c.id === state.selectedConversationId);
  },
}));

// ============================================
// Message Store
// ============================================

interface MessageStore {
  // Messages keyed by conversation ID
  messages: Record<number, Message[]>;
  isLoading: Record<number, boolean>;
  isSending: boolean;
  error: string | null;
  
  // Draft messages keyed by conversation ID
  drafts: Record<number, string>;
  
  // Actions
  setMessages: (conversationId: number, messages: Message[]) => void;
  addMessage: (conversationId: number, message: Message) => void;
  updateMessage: (conversationId: number, messageId: string, updates: Partial<Message>) => void;
  replaceMessage: (conversationId: number, oldMessageId: string, newMessage: Message) => void;
  updateMessageStatus: (messageId: string, status: MessageStatus) => void;
  prependMessages: (conversationId: number, messages: Message[]) => void;
  clearMessages: (conversationId: number) => void;
  
  setLoading: (conversationId: number, isLoading: boolean) => void;
  setSending: (isSending: boolean) => void;
  setError: (error: string | null) => void;
  
  // Draft actions
  setDraft: (conversationId: number, content: string) => void;
  clearDraft: (conversationId: number) => void;
  
  // Selectors
  getMessages: (conversationId: number) => Message[];
  getDraft: (conversationId: number) => string;
}

export const useMessageStore = create<MessageStore>((set, get) => ({
  messages: {},
  isLoading: {},
  isSending: false,
  error: null,
  drafts: {},

  setMessages: (conversationId, messages) =>
    set((state) => ({
      messages: { ...state.messages, [conversationId]: messages },
    })),
  
  addMessage: (conversationId, message) =>
    set((state) => {
      const existing = state.messages[conversationId] || [];
      // Check if message already exists
      if (existing.some((m) => m.message_id === message.message_id)) {
        return state;
      }
      return {
        messages: {
          ...state.messages,
          [conversationId]: [...existing, message],
        },
      };
    }),
  
  updateMessage: (conversationId, messageId, updates) =>
    set((state) => ({
      messages: {
        ...state.messages,
        [conversationId]: (state.messages[conversationId] || []).map((msg) =>
          msg.message_id === messageId ? { ...msg, ...updates } : msg
        ),
      },
    })),
  
  replaceMessage: (conversationId, oldMessageId, newMessage) =>
    set((state) => ({
      messages: {
        ...state.messages,
        [conversationId]: (state.messages[conversationId] || []).map((msg) =>
          msg.message_id === oldMessageId ? newMessage : msg
        ),
      },
    })),
  
  updateMessageStatus: (messageId, status) =>
    set((state) => {
      const newMessages = { ...state.messages };
      for (const convId in newMessages) {
        newMessages[convId] = newMessages[convId].map((msg) =>
          msg.message_id === messageId ? { ...msg, status } : msg
        );
      }
      return { messages: newMessages };
    }),
  
  prependMessages: (conversationId, messages) =>
    set((state) => ({
      messages: {
        ...state.messages,
        [conversationId]: [...messages, ...(state.messages[conversationId] || [])],
      },
    })),
  
  clearMessages: (conversationId) =>
    set((state) => {
      const newMessages = { ...state.messages };
      delete newMessages[conversationId];
      return { messages: newMessages };
    }),
  
  setLoading: (conversationId, isLoading) =>
    set((state) => ({
      isLoading: { ...state.isLoading, [conversationId]: isLoading },
    })),
  
  setSending: (isSending) => set({ isSending }),
  
  setError: (error) => set({ error }),
  
  setDraft: (conversationId, content) =>
    set((state) => ({
      drafts: { ...state.drafts, [conversationId]: content },
    })),
  
  clearDraft: (conversationId) =>
    set((state) => {
      const newDrafts = { ...state.drafts };
      delete newDrafts[conversationId];
      return { drafts: newDrafts };
    }),
  
  getMessages: (conversationId) => get().messages[conversationId] || [],
  
  getDraft: (conversationId) => get().drafts[conversationId] || '',
}));

// ============================================
// UI Store
// ============================================

interface UIStore {
  // Connection status
  isConnected: boolean;
  connectionError: string | null;
  
  // Typing indicators keyed by conversation ID
  typingIndicators: Record<number, boolean>;
  
  // Unread counts keyed by conversation ID
  unreadCounts: Record<number, number>;
  
  // Sidebar state
  isSidebarOpen: boolean;
  
  // Actions
  setConnected: (isConnected: boolean) => void;
  setConnectionError: (error: string | null) => void;
  
  setTyping: (conversationId: number, isTyping: boolean) => void;
  clearTyping: (conversationId: number) => void;
  
  setUnreadCount: (conversationId: number, count: number) => void;
  incrementUnread: (conversationId: number) => void;
  clearUnread: (conversationId: number) => void;
  
  toggleSidebar: () => void;
  setSidebarOpen: (isOpen: boolean) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  isConnected: false,
  connectionError: null,
  typingIndicators: {},
  unreadCounts: {},
  isSidebarOpen: true,

  setConnected: (isConnected) => set({ isConnected }),
  
  setConnectionError: (connectionError) => set({ connectionError }),
  
  setTyping: (conversationId, isTyping) =>
    set((state) => ({
      typingIndicators: { ...state.typingIndicators, [conversationId]: isTyping },
    })),
  
  clearTyping: (conversationId) =>
    set((state) => {
      const newIndicators = { ...state.typingIndicators };
      delete newIndicators[conversationId];
      return { typingIndicators: newIndicators };
    }),
  
  setUnreadCount: (conversationId, count) =>
    set((state) => ({
      unreadCounts: { ...state.unreadCounts, [conversationId]: count },
    })),
  
  incrementUnread: (conversationId) =>
    set((state) => ({
      unreadCounts: {
        ...state.unreadCounts,
        [conversationId]: (state.unreadCounts[conversationId] || 0) + 1,
      },
    })),
  
  clearUnread: (conversationId) =>
    set((state) => {
      const newCounts = { ...state.unreadCounts };
      delete newCounts[conversationId];
      return { unreadCounts: newCounts };
    }),
  
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  
  setSidebarOpen: (isSidebarOpen) => set({ isSidebarOpen }),
}));

// ============================================
// Contact Store
// ============================================

interface ContactStore {
  contacts: Contact[];
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setContacts: (contacts: Contact[]) => void;
  addContact: (contact: Contact) => void;
  updateContact: (id: number, updates: Partial<Contact>) => void;
  removeContact: (id: number) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  
  // Selectors
  getContactById: (id: number) => Contact | undefined;
  getContactByPhone: (phone: string) => Contact | undefined;
}

export const useContactStore = create<ContactStore>((set, get) => ({
  contacts: [],
  isLoading: false,
  error: null,

  setContacts: (contacts) => set({ contacts }),
  
  addContact: (contact) =>
    set((state) => ({
      contacts: [...state.contacts, contact],
    })),
  
  updateContact: (id, updates) =>
    set((state) => ({
      contacts: state.contacts.map((contact) =>
        contact.id === id ? { ...contact, ...updates } : contact
      ),
    })),
  
  removeContact: (id) =>
    set((state) => ({
      contacts: state.contacts.filter((contact) => contact.id !== id),
    })),
  
  setLoading: (isLoading) => set({ isLoading }),
  
  setError: (error) => set({ error }),
  
  getContactById: (id) => get().contacts.find((c) => c.id === id),
  
  getContactByPhone: (phone) => get().contacts.find((c) => c.phone_number === phone),
}));
