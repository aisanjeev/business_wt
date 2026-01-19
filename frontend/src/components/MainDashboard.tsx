'use client';

import React, { useState, useEffect } from 'react';
import { useAuthStore, useConversationStore } from '@/hooks/useAppState';
import { metaApi } from '@/services/api';
import { MetaAccountConnection } from '@/types';
import DashboardOverview from './DashboardOverview';
import WhatsAppChat from './WhatsAppChat';
import AdminDashboard from './AdminDashboard';
import ContactsList from './ContactsList';
import { MetaConnection, ContactImport, BulkMessaging, UsageDashboard } from './index';

type ActivePage = 
  | 'overview'
  | 'whatsapp'
  | 'contacts'
  | 'campaigns'
  | 'import'
  | 'usage'
  | 'settings'
  | 'admin';

interface MainDashboardProps {
  children?: React.ReactNode;
}

const MainDashboard: React.FC<MainDashboardProps> = ({ children }) => {
  const [activePage, setActivePage] = useState<ActivePage>('overview');
  const [chatExpanded, setChatExpanded] = useState(false);
  const [metaConnection, setMetaConnection] = useState<MetaAccountConnection | null>(null);
  const [connectionLoading, setConnectionLoading] = useState(true);
  const [navigateToContactId, setNavigateToContactId] = useState<number | null>(null);
  const { user, logout } = useAuthStore();
  const { selectConversation, conversations } = useConversationStore();
  const isAdmin = user?.role === 'admin' || (user as any)?.is_superuser;

  // Handle navigation to WhatsApp chat for a contact
  const handleNavigateToWhatsApp = (contactId: number) => {
    // Find conversation for this contact
    const conversation = conversations?.find(
      conv => conv.contact_id === contactId || conv.contact?.id === contactId
    );
    
    if (conversation) {
      // Select the conversation
      selectConversation(conversation.id);
      // Navigate to WhatsApp page
      setActivePage('whatsapp');
    } else {
      // Store contact ID to find/select after navigation
      setNavigateToContactId(contactId);
      // Navigate to WhatsApp page first
      setActivePage('whatsapp');
      // Conversation will be created when user sends first message
    }
  };

  // Listen for custom navigation events
  useEffect(() => {
    const handleNavigateEvent = (event: CustomEvent) => {
      const contactId = (event as any).detail?.contactId;
      if (contactId) {
        handleNavigateToWhatsApp(contactId);
      }
    };
    
    window.addEventListener('navigateToWhatsApp' as any, handleNavigateEvent);
    return () => {
      window.removeEventListener('navigateToWhatsApp' as any, handleNavigateEvent);
    };
  }, [conversations]);

  // Load Meta connection status
  useEffect(() => {
    const loadConnection = async () => {
      setConnectionLoading(true);
      const response = await metaApi.getConnection();
      if (response.success && response.data) {
        setMetaConnection(response.data);
      } else {
        setMetaConnection(null);
      }
      setConnectionLoading(false);
    };

    loadConnection();
  }, [activePage]); // Reload when page changes

  const handleLogout = () => {
    logout();
  };

  const isMetaConnected = metaConnection?.status === 'connected';

  const renderContent = () => {
    switch (activePage) {
      case 'overview':
        return <DashboardOverview onNavigate={setActivePage} />;
      case 'whatsapp':
        // Check if Meta connection exists and is connected
        if (!connectionLoading && !isMetaConnected) {
          return (
            <div className="flex-1 flex items-center justify-center bg-gray-50 p-6">
              <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
                <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <h2 className="text-2xl font-semibold text-gray-900 mb-2">Meta Account Required</h2>
                <p className="text-gray-600 mb-6">
                  Please connect your Meta Business Account to use WhatsApp chat. You'll need to complete the setup process first.
                </p>
                <button
                  onClick={() => setActivePage('settings')}
                  className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  Go to Settings
                </button>
              </div>
            </div>
          );
        }
        return <WhatsAppChat />;
      case 'contacts':
        return <ContactsList />;
      case 'campaigns':
        return <BulkMessaging onCampaignCreated={() => setActivePage('campaigns')} />;
      case 'import':
        return <ContactImport onImportComplete={() => setActivePage('contacts')} />;
      case 'usage':
        return <UsageDashboard />;
      case 'settings':
        return <MetaConnection />;
      case 'admin':
        return <AdminDashboard />;
      default:
        return <DashboardOverview onNavigate={setActivePage} />;
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Top Header */}
      <header className="bg-white shadow-sm border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold text-gray-900">WhatsApp Business Platform</h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-sm text-gray-600">
            <span className="font-medium">{user?.name || user?.email}</span>
            {isAdmin && <span className="ml-2 px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs">Admin</span>}
          </div>
          <button
            onClick={handleLogout}
            className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded transition-colors"
          >
            Logout
          </button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar Navigation */}
        <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
          <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
            {/* Dashboard */}
            <button
              onClick={() => setActivePage('overview')}
              className={`w-full text-left px-4 py-2 rounded-lg transition-colors ${
                activePage === 'overview'
                  ? 'bg-green-100 text-green-700 font-medium'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <div className="flex items-center gap-3">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                <span>Dashboard</span>
              </div>
            </button>

            {/* Chat (Expandable) */}
            <div>
              <button
                onClick={() => setChatExpanded(!chatExpanded)}
                className={`w-full text-left px-4 py-2 rounded-lg transition-colors ${
                  activePage === 'whatsapp'
                    ? 'bg-green-100 text-green-700 font-medium'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    <span>Chat</span>
                  </div>
                  <svg
                    className={`w-4 h-4 transition-transform ${chatExpanded ? 'transform rotate-90' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </button>
              {chatExpanded && (
                <div className="ml-4 mt-1 space-y-1">
                  <button
                    onClick={() => setActivePage('whatsapp')}
                    className={`w-full text-left px-4 py-2 rounded-lg transition-colors ${
                      activePage === 'whatsapp'
                        ? 'bg-green-100 text-green-700 font-medium'
                        : 'text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    WhatsApp
                  </button>
                </div>
              )}
            </div>

            {/* Contacts */}
            <button
              onClick={() => setActivePage('contacts')}
              className={`w-full text-left px-4 py-2 rounded-lg transition-colors ${
                activePage === 'contacts'
                  ? 'bg-green-100 text-green-700 font-medium'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <div className="flex items-center gap-3">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                <span>Contacts</span>
              </div>
            </button>

            {/* Campaigns */}
            <button
              onClick={() => setActivePage('campaigns')}
              className={`w-full text-left px-4 py-2 rounded-lg transition-colors ${
                activePage === 'campaigns'
                  ? 'bg-green-100 text-green-700 font-medium'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <div className="flex items-center gap-3">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z" />
                </svg>
                <span>Campaigns</span>
              </div>
            </button>

            {/* Import Contacts */}
            <button
              onClick={() => setActivePage('import')}
              className={`w-full text-left px-4 py-2 rounded-lg transition-colors ${
                activePage === 'import'
                  ? 'bg-green-100 text-green-700 font-medium'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <div className="flex items-center gap-3">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <span>Import Contacts</span>
              </div>
            </button>

            {/* Usage & Billing */}
            <button
              onClick={() => setActivePage('usage')}
              className={`w-full text-left px-4 py-2 rounded-lg transition-colors ${
                activePage === 'usage'
                  ? 'bg-green-100 text-green-700 font-medium'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <div className="flex items-center gap-3">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <span>Usage & Billing</span>
              </div>
            </button>

            {/* Settings */}
            <button
              onClick={() => setActivePage('settings')}
              className={`w-full text-left px-4 py-2 rounded-lg transition-colors ${
                activePage === 'settings'
                  ? 'bg-green-100 text-green-700 font-medium'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <div className="flex items-center gap-3">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span>Settings</span>
              </div>
            </button>

            {/* Admin (only for admins) */}
            {isAdmin && (
              <div className="pt-4 border-t border-gray-200 mt-4">
                <button
                  onClick={() => setActivePage('admin')}
                  className={`w-full text-left px-4 py-2 rounded-lg transition-colors ${
                    activePage === 'admin'
                      ? 'bg-purple-100 text-purple-700 font-medium'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                    <span>Admin</span>
                  </div>
                </button>
              </div>
            )}
          </nav>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 overflow-auto">
          {children || renderContent()}
        </main>
      </div>
    </div>
  );
};

export default MainDashboard;
