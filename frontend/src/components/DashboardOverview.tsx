'use client';

import React, { useEffect, useState } from 'react';
import { conversationApi, metaApi, usageApi } from '@/services/api';
import { MetaAccountConnection } from '@/types';

interface DashboardOverviewProps {
  onNavigate: (page: string) => void;
}

const DashboardOverview: React.FC<DashboardOverviewProps> = ({ onNavigate }) => {
  const [stats, setStats] = useState({
    totalMessages: 0,
    activeConversations: 0,
    campaigns: 0,
    storageUsed: 0,
    storageFormatted: '0 B',
  });
  const [connectionStatus, setConnectionStatus] = useState<MetaAccountConnection | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadOverview();
  }, []);

  const loadOverview = async () => {
    setLoading(true);
    try {
      // Load conversations count
      const convResponse = await conversationApi.getConversations();
      if (convResponse.success && convResponse.data) {
        const conversations = Array.isArray(convResponse.data) ? convResponse.data : [];
        setStats(prev => ({
          ...prev,
          activeConversations: conversations.length,
        }));
      }

      // Load Meta connection status
      const connResponse = await metaApi.getConnection();
      if (connResponse.success && connResponse.data) {
        setConnectionStatus(connResponse.data);
      }

      // Load storage usage
      const storageResponse = await usageApi.getStorage();
      if (storageResponse.success && storageResponse.data) {
        setStats(prev => ({
          ...prev,
          storageUsed: storageResponse.data!.storage_used_bytes,
          storageFormatted: storageResponse.data!.storage_formatted,
        }));
      }
    } catch (error) {
      console.error('Failed to load overview:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Dashboard Overview</h2>
      </div>

      {/* Connection Status */}
      {connectionStatus && (
        <div className={`p-4 rounded-lg border ${
          connectionStatus.status === 'connected'
            ? 'bg-green-50 border-green-200'
            : 'bg-yellow-50 border-yellow-200'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${
                connectionStatus.status === 'connected' ? 'bg-green-500' : 'bg-yellow-500'
              }`}></div>
              <div>
                <p className="font-medium text-gray-900">
                  Meta Account: {connectionStatus.status === 'connected' ? 'Connected' : 'Not Connected'}
                </p>
                {connectionStatus.business_phone_number && (
                  <p className="text-sm text-gray-600">{connectionStatus.business_phone_number}</p>
                )}
              </div>
            </div>
            {connectionStatus.status !== 'connected' && (
              <button
                onClick={() => onNavigate('settings')}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
              >
                Connect Now
              </button>
            )}
          </div>
        </div>
      )}

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">Active Conversations</h3>
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <p className="text-3xl font-bold text-gray-900">{stats.activeConversations}</p>
          <button
            onClick={() => onNavigate('whatsapp')}
            className="text-sm text-green-600 hover:text-green-700 mt-2"
          >
            View Messages →
          </button>
        </div>

        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">Campaigns</h3>
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z" />
            </svg>
          </div>
          <p className="text-3xl font-bold text-gray-900">{stats.campaigns}</p>
          <button
            onClick={() => onNavigate('campaigns')}
            className="text-sm text-green-600 hover:text-green-700 mt-2"
          >
            View Campaigns →
          </button>
        </div>

        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">Total Messages</h3>
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <p className="text-3xl font-bold text-gray-900">{stats.totalMessages}</p>
          <button
            onClick={() => onNavigate('usage')}
            className="text-sm text-green-600 hover:text-green-700 mt-2"
          >
            View Usage →
          </button>
        </div>

        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">Storage Used</h3>
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
            </svg>
          </div>
          <p className="text-3xl font-bold text-blue-600">{stats.storageFormatted}</p>
          <p className="text-xs text-gray-500 mt-1">Media files stored</p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
        <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            onClick={() => onNavigate('import')}
            className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-green-500 hover:bg-green-50 transition-colors text-left"
          >
            <svg className="w-8 h-8 text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <h4 className="font-medium text-gray-900">Import Contacts</h4>
            <p className="text-sm text-gray-600 mt-1">Upload CSV or Excel file</p>
          </button>

          <button
            onClick={() => onNavigate('campaigns')}
            className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-green-500 hover:bg-green-50 transition-colors text-left"
          >
            <svg className="w-8 h-8 text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <h4 className="font-medium text-gray-900">Create Campaign</h4>
            <p className="text-sm text-gray-600 mt-1">Send bulk messages</p>
          </button>

          <button
            onClick={() => onNavigate('settings')}
            className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-green-500 hover:bg-green-50 transition-colors text-left"
          >
            <svg className="w-8 h-8 text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <h4 className="font-medium text-gray-900">Settings</h4>
            <p className="text-sm text-gray-600 mt-1">Manage connections</p>
          </button>
        </div>
      </div>
    </div>
  );
};

export default DashboardOverview;
