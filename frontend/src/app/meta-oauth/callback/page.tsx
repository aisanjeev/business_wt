'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { metaApi } from '@/services/api';
import PhoneNumberSelector from '@/components/PhoneNumberSelector';
import { OAuthExchangeResponse } from '@/types';

export default function MetaOAuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exchangeData, setExchangeData] = useState<OAuthExchangeResponse | null>(null);

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');

    if (!code) {
      setError('No authorization code received from Meta. Please try again.');
      setLoading(false);
      return;
    }

    // Exchange code for token and get phone numbers
    const exchangeCode = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await metaApi.exchangeCode(code);

        if (!response.success || !response.data) {
          setError(response.error || 'Failed to exchange authorization code');
          setLoading(false);
          return;
        }

        setExchangeData(response.data);
        setLoading(false);
      } catch (err) {
        setError('Failed to exchange authorization code. Please try again.');
        setLoading(false);
        console.error('OAuth exchange error:', err);
      }
    };

    exchangeCode();
  }, [searchParams]);

  const handleConnectionComplete = () => {
    // Redirect to settings page after successful connection
    router.push('/?page=settings');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500 mx-auto mb-4" />
          <p className="text-gray-600">Processing authorization...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900">Authorization Failed</h2>
          </div>
          <p className="text-gray-700 mb-6">{error}</p>
          <button
            onClick={() => router.push('/?page=settings')}
            className="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
          >
            Go to Settings
          </button>
        </div>
      </div>
    );
  }

  if (exchangeData) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="max-w-2xl w-full">
          <PhoneNumberSelector
            exchangeData={exchangeData}
            onComplete={handleConnectionComplete}
            onCancel={() => router.push('/?page=settings')}
          />
        </div>
      </div>
    );
  }

  return null;
}
