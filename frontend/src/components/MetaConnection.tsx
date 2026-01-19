'use client';

import React, { useState, useEffect } from 'react';
import { metaApi } from '@/services/api';
import { MetaAccountConnection } from '@/types';

interface MetaConnectionProps {
  onConnectionChange?: (connected: boolean) => void;
}

const MetaConnection: React.FC<MetaConnectionProps> = ({ onConnectionChange }) => {
  const [connection, setConnection] = useState<MetaAccountConnection | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    loadConnection();
  }, []);

  const loadConnection = async () => {
    setLoading(true);
    setError(null);
    const response = await metaApi.getConnection();
    
    if (response.success && response.data) {
      setConnection(response.data);
      onConnectionChange?.(response.data.status === 'connected');
    } else {
      // No connection is not an error
      if (response.error && !response.error.includes('404')) {
        setError(response.error);
      }
    }
    setLoading(false);
  };

  const handleConnect = async () => {
    setConnecting(true);
    setError(null);

    try {
      // Get OAuth URL
      const urlResponse = await metaApi.getOAuthUrl();
      
      if (!urlResponse.success || !urlResponse.data) {
        setError(urlResponse.error || 'Failed to get OAuth URL');
        setConnecting(false);
        return;
      }

      // Redirect to OAuth URL - Meta will redirect back to /meta-oauth/callback
      const { auth_url } = urlResponse.data;
      window.location.href = auth_url;

      // Note: This will redirect the user away from the current page
      // After OAuth, Meta redirects to /meta-oauth/callback which handles the rest

    } catch (err) {
      setError('Failed to initiate connection');
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect your Meta account?')) {
      return;
    }

    setLoading(true);
    setError(null);

    const response = await metaApi.disconnect();
    
    if (response.success) {
      setConnection(null);
      onConnectionChange?.(false);
    } else {
      setError(response.error || 'Failed to disconnect');
    }

    setLoading(false);
  };

  if (loading && !connection) {
    return (
      <div className="p-6 bg-white rounded-lg shadow">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-10 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-white rounded-lg shadow">
      <h2 className="text-xl font-semibold mb-4">Meta Account Connection</h2>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      {connection ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-green-50 border border-green-200 rounded">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <div>
                <p className="font-medium text-green-900">Connected</p>
                <p className="text-sm text-green-700">
                  {connection.business_phone_number || connection.phone_number_id}
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-gray-600">Business Account ID</p>
              <p className="font-mono text-xs mt-1">{connection.meta_business_account_id}</p>
            </div>
            <div>
              <p className="text-gray-600">Phone Number ID</p>
              <p className="font-mono text-xs mt-1">{connection.phone_number_id}</p>
            </div>
            <div>
              <p className="text-gray-600">Status</p>
              <p className="mt-1 capitalize">{connection.status.replace('_', ' ')}</p>
            </div>
            <div>
              <p className="text-gray-600">Verification</p>
              <p className="mt-1 capitalize">{connection.business_verification_status}</p>
            </div>
          </div>

          <button
            onClick={handleDisconnect}
            disabled={loading}
            className="w-full px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Disconnecting...' : 'Disconnect Meta Account'}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="p-4 bg-yellow-50 border border-yellow-200 rounded">
            <p className="text-sm text-yellow-800">
              Connect your Meta Business Account to start sending WhatsApp messages.
              You'll be redirected to Meta's OAuth page to authorize access.
            </p>
          </div>

          <button
            onClick={handleConnect}
            disabled={connecting}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {connecting ? (
              <>
                <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Connecting...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                </svg>
                Connect Meta Account
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};

export default MetaConnection;
