'use client';

import React, { useState } from 'react';
import { metaApi } from '@/services/api';
import { OAuthExchangeResponse, PhoneNumberOption } from '@/types';

interface PhoneNumberSelectorProps {
  exchangeData: OAuthExchangeResponse;
  onComplete: () => void;
  onCancel: () => void;
}

const PhoneNumberSelector: React.FC<PhoneNumberSelectorProps> = ({
  exchangeData,
  onComplete,
  onCancel,
}) => {
  const [selectedPhoneNumberId, setSelectedPhoneNumberId] = useState<string>('');
  const [manualPhoneNumberId, setManualPhoneNumberId] = useState<string>('');
  const [useManual, setUseManual] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { business_accounts, phone_numbers, access_token } = exchangeData;
  const businessAccount = business_accounts[0]; // Use first business account

  const handleSubmit = async () => {
    const phoneNumberId = useManual ? manualPhoneNumberId.trim() : selectedPhoneNumberId;

    if (!phoneNumberId) {
      setError('Please select a phone number or enter one manually');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Find the selected phone number for display
      const selectedPhone = phone_numbers.find((pn) => pn.id === phoneNumberId);
      const businessPhoneNumber = selectedPhone?.display_phone_number || selectedPhone?.verified_name;

      const response = await metaApi.completeConnection({
        business_account_id: businessAccount.id,
        phone_number_id: phoneNumberId,
        access_token: access_token,
        business_phone_number: businessPhoneNumber,
      });

      if (response.success) {
        onComplete();
      } else {
        setError(response.error || 'Failed to complete connection');
        setLoading(false);
      }
    } catch (err) {
      setError('Failed to complete connection. Please try again.');
      setLoading(false);
      console.error('Connection complete error:', err);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">Select Phone Number</h2>
        <p className="text-gray-600">
          Choose which WhatsApp phone number you want to connect from your Meta Business Account.
        </p>
        {businessAccount.name && (
          <p className="text-sm text-gray-500 mt-1">
            Business Account: <span className="font-medium">{businessAccount.name}</span>
          </p>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      {phone_numbers.length > 0 && !useManual && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <label className="block text-sm font-medium text-gray-700">
              Available Phone Numbers ({phone_numbers.length})
            </label>
          </div>
          {phone_numbers.some(
            (pn) => pn.code_verification_status && ['UNVERIFIED', 'NOT_VERIFIED'].includes(pn.code_verification_status)
          ) && (
            <div className="mb-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
              <p className="font-medium mb-1">⚠ Some phone numbers are not verified</p>
              <p className="text-xs">
                Unverified numbers may have limited functionality. You can verify them in{' '}
                <a
                  href="https://business.facebook.com/settings/whatsapp-phone-numbers"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline font-medium"
                >
                  Meta Business Manager
                </a>
                .
              </p>
            </div>
          )}
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {phone_numbers.map((phone) => (
              <label
                key={phone.id}
                className={`flex items-start p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                  selectedPhoneNumberId === phone.id
                    ? 'border-green-500 bg-green-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name="phone_number"
                  value={phone.id}
                  checked={selectedPhoneNumberId === phone.id}
                  onChange={(e) => setSelectedPhoneNumberId(e.target.value)}
                  className="mt-1 mr-3"
                />
                <div className="flex-1">
                  <div className="font-medium text-gray-900">
                    {phone.display_phone_number || phone.verified_name || 'Unknown'}
                  </div>
                  {phone.verified_name && phone.verified_name !== phone.display_phone_number && (
                    <div className="text-sm text-gray-600 mt-1">{phone.verified_name}</div>
                  )}
                  <div className="text-xs text-gray-500 mt-1">ID: {phone.id}</div>
                  <div className="flex items-center gap-2 mt-1">
                    {phone.code_verification_status && (
                      <span
                        className={`text-xs px-2 py-0.5 rounded ${
                          phone.code_verification_status === 'VERIFIED'
                            ? 'bg-green-100 text-green-700'
                            : phone.code_verification_status === 'UNVERIFIED'
                            ? 'bg-yellow-100 text-yellow-700'
                            : 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {phone.code_verification_status === 'VERIFIED' && '✓ Verified'}
                        {phone.code_verification_status === 'UNVERIFIED' && '⚠ Unverified'}
                        {phone.code_verification_status === 'NOT_VERIFIED' && '⚠ Not Verified'}
                        {!['VERIFIED', 'UNVERIFIED', 'NOT_VERIFIED'].includes(phone.code_verification_status || '') &&
                          `Status: ${phone.code_verification_status}`}
                      </span>
                    )}
                    {phone.code_verification_status &&
                      ['UNVERIFIED', 'NOT_VERIFIED'].includes(phone.code_verification_status) && (
                        <a
                          href="https://business.facebook.com/settings/whatsapp-phone-numbers"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:text-blue-800 underline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          Verify in Business Manager
                        </a>
                      )}
                  </div>
                </div>
              </label>
            ))}
          </div>
        </div>
      )}

      <div className="mb-6">
        <div className="flex items-center gap-3 mb-3">
          <input
            type="checkbox"
            id="use_manual"
            checked={useManual}
            onChange={(e) => {
              setUseManual(e.target.checked);
              if (e.target.checked) {
                setSelectedPhoneNumberId('');
              } else {
                setManualPhoneNumberId('');
              }
            }}
            className="rounded"
          />
          <label htmlFor="use_manual" className="text-sm font-medium text-gray-700 cursor-pointer">
            Enter phone number ID manually
          </label>
        </div>

        {useManual && (
          <div>
            <label htmlFor="manual_phone_id" className="block text-sm font-medium text-gray-700 mb-2">
              Phone Number ID
            </label>
            <input
              type="text"
              id="manual_phone_id"
              value={manualPhoneNumberId}
              onChange={(e) => setManualPhoneNumberId(e.target.value)}
              placeholder="Enter phone number ID from Meta Business"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              You can find this in your Meta Business Account settings.
            </p>
          </div>
        )}
      </div>

      <div className="flex gap-3">
        <button
          onClick={onCancel}
          disabled={loading}
          className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={loading || (!useManual && !selectedPhoneNumberId) || (useManual && !manualPhoneNumberId.trim())}
          className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Connecting...
            </>
          ) : (
            'Complete Connection'
          )}
        </button>
      </div>
    </div>
  );
};

export default PhoneNumberSelector;
