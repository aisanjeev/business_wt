'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { contactImportApi, contactListApi } from '@/services/api';
import { ContactImportStatus, ContactList } from '@/types';

interface ContactImportProps {
  onImportComplete?: () => void;
}

const ContactImport: React.FC<ContactImportProps> = ({ onImportComplete }) => {
  const [file, setFile] = useState<File | null>(null);
  const [selectedListId, setSelectedListId] = useState<number | null>(null);
  const [availableLists, setAvailableLists] = useState<ContactList[]>([]);
  const [importing, setImporting] = useState(false);
  const [importStatus, setImportStatus] = useState<ContactImportStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadLists = useCallback(async () => {
    try {
      const response = await contactListApi.getLists(1, 100);
      if (response.success && response.data) {
        setAvailableLists(response.data.items);
      }
    } catch (err) {
      console.error('Failed to load lists:', err);
    }
  }, []);

  useEffect(() => {
    loadLists();
  }, [loadLists]);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) return;

    // Validate file type
    const extension = selectedFile.name.split('.').pop()?.toLowerCase();
    const allowedTypes = ['csv', 'xlsx', 'xls', 'json'];
    
    if (!extension || !allowedTypes.includes(extension)) {
      setError('Please select a CSV, Excel (.xlsx, .xls), or JSON file');
      return;
    }

    setFile(selectedFile);
    setError(null);
    setImportStatus(null);
  };

  const handleImport = async () => {
    if (!file) return;

    setImporting(true);
    setError(null);

    try {
      const response = await contactImportApi.importContacts(file, selectedListId || undefined);

      if (!response.success || !response.data) {
        setError(response.error || 'Failed to import contacts');
        setImporting(false);
        return;
      }

      const importJob = response.data;
      setImportStatus({
        id: importJob.id,
        status: importJob.status,
        total_rows: importJob.total_rows,
        successful_rows: importJob.successful_rows,
        failed_rows: importJob.failed_rows,
        progress_percentage: 0,
      });

      // Poll for status updates
      pollImportStatus(importJob.id);

    } catch (err) {
      setError('Failed to import contacts');
      setImporting(false);
    }
  };

  const pollImportStatus = async (importId: number) => {
    const maxAttempts = 300; // 5 minutes max
    let attempts = 0;

    const checkStatus = async () => {
      attempts++;
      
      const response = await contactImportApi.getImportStatus(importId);

      if (response.success && response.data) {
        const status = response.data;
        setImportStatus(status);

        if (status.status === 'completed' || status.status === 'failed') {
          setImporting(false);
          if (status.status === 'completed') {
            onImportComplete?.();
          }
          return;
        }

        // Continue polling if still processing
        if (status.status === 'processing' && attempts < maxAttempts) {
          setTimeout(checkStatus, 2000); // Check every 2 seconds
        } else {
          setImporting(false);
        }
      } else {
        setImporting(false);
        setError(response.error || 'Failed to check import status');
      }
    };

    checkStatus();
  };

  const handleReset = () => {
    setFile(null);
    setSelectedListId(null);
    setImportStatus(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="p-6 bg-white rounded-lg shadow">
      <h2 className="text-xl font-semibold mb-4">Import Contacts</h2>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      {!importStatus ? (
        <div className="space-y-4">
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-gray-400 transition-colors">
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.xls,.json"
              onChange={handleFileSelect}
              className="hidden"
              id="file-upload"
            />
            <label
              htmlFor="file-upload"
              className="cursor-pointer flex flex-col items-center"
            >
              <svg className="w-12 h-12 text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p className="text-sm text-gray-600 mb-1">
                Click to upload or drag and drop
              </p>
              <p className="text-xs text-gray-500">
                CSV, Excel (.xlsx, .xls), or JSON files
              </p>
            </label>
          </div>

          {file && (
            <div className="p-3 bg-gray-50 rounded border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-sm">{file.name}</p>
                  <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                </div>
                <button
                  onClick={handleReset}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          )}

          {/* List Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Import to List (optional)
            </label>
            <select
              value={selectedListId || ''}
              onChange={(e) => setSelectedListId(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="">No list (import as regular contacts)</option>
              {availableLists.map((list) => (
                <option key={list.id} value={list.id}>
                  {list.name} ({list.contacts_count || 0} contacts)
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">
              Select a list to automatically add imported contacts to it. You can also add contacts to lists later.
            </p>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded p-3">
            <p className="text-xs text-blue-800 font-medium mb-1">File Format Requirements:</p>
            <ul className="text-xs text-blue-700 space-y-1 list-disc list-inside">
              <li>CSV: Must include "phone" or "phone_number" column</li>
              <li>Excel: First row should contain headers</li>
              <li>JSON: Array of contact objects with phone numbers</li>
            </ul>
          </div>

          <button
            onClick={handleImport}
            disabled={!file || importing}
            className="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {importing ? 'Importing...' : 'Import Contacts'}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="p-4 bg-gray-50 rounded border">
            <div className="flex items-center justify-between mb-3">
              <span className="font-medium">Import Status: {importStatus.status}</span>
              {importStatus.status === 'processing' && (
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-green-600"></div>
              )}
            </div>

            {importStatus.status === 'processing' && (
              <div className="mb-3">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${importStatus.progress_percentage}%` }}
                  ></div>
                </div>
                <p className="text-xs text-gray-600 mt-1 text-center">
                  {importStatus.progress_percentage.toFixed(1)}% complete
                </p>
              </div>
            )}

            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-gray-600">Total Rows</p>
                <p className="font-semibold text-lg">{importStatus.total_rows}</p>
              </div>
              <div>
                <p className="text-green-600">Successful</p>
                <p className="font-semibold text-lg text-green-700">{importStatus.successful_rows}</p>
              </div>
              <div>
                <p className="text-red-600">Failed</p>
                <p className="font-semibold text-lg text-red-700">{importStatus.failed_rows}</p>
              </div>
            </div>
          </div>

          {(importStatus.status === 'completed' || importStatus.status === 'failed') && (
            <button
              onClick={handleReset}
              className="w-full px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
            >
              Import Another File
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default ContactImport;
