'use client';

import React, { useState, useEffect } from 'react';
import { MessageTemplate } from '@/types';
import { templateApi } from '@/services/api';

interface TemplateListProps {
  onSelectTemplate?: (template: MessageTemplate) => void;
  onCreateNew?: () => void;
}

const TemplateList: React.FC<TemplateListProps> = ({ onSelectTemplate, onCreateNew }) => {
  const [templates, setTemplates] = useState<MessageTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    category: '',
    status: '',
    language: '',
    search: '',
  });
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 0,
  });

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const response = await templateApi.getTemplates({
        page: pagination.page,
        page_size: pagination.page_size,
        ...filters,
      });
      if (response.success && response.data) {
        setTemplates(response.data.items || []);
        if (response.data) {
          setPagination(prev => ({
            ...prev,
            total: response.data!.total || 0,
            total_pages: Math.ceil((response.data!.total || 0) / (response.data!.page_size || 20)),
          }));
        }
      }
    } catch (error) {
      console.error('Failed to load templates:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTemplates();
  }, [pagination.page, filters]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'APPROVED': return 'bg-green-100 text-green-700';
      case 'PENDING': return 'bg-yellow-100 text-yellow-700';
      case 'REJECTED': return 'bg-red-100 text-red-700';
      case 'DISABLED': return 'bg-gray-100 text-gray-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this template?')) return;
    const response = await templateApi.deleteTemplate(id);
    if (response.success) {
      loadTemplates();
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncMessage(null);
    try {
      const response = await templateApi.syncTemplates();
      if (response.success && response.data) {
        const { created, updated, errors, message } = response.data;
        if (errors && errors.length > 0) {
          setSyncMessage(`Synced: ${created} created, ${updated} updated. Errors: ${errors.join(', ')}`);
        } else {
          setSyncMessage(`Successfully synced: ${created} new templates, ${updated} updated`);
        }
        // Reload templates after sync
        await loadTemplates();
      } else {
        setSyncMessage(response.error || 'Failed to sync templates');
      }
    } catch (error) {
      setSyncMessage('An error occurred while syncing templates');
      console.error('Sync error:', error);
    } finally {
      setSyncing(false);
      // Clear message after 5 seconds
      setTimeout(() => setSyncMessage(null), 5000);
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Templates</h2>
        <div className="flex gap-3">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {syncing ? (
              <>
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Syncing...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Sync from Meta
              </>
            )}
          </button>
          <button
            onClick={onCreateNew}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            Create Template
          </button>
        </div>
      </div>

      {/* Sync Message */}
      {syncMessage && (
        <div className={`mb-4 p-3 rounded-lg ${
          syncMessage.includes('Error') || syncMessage.includes('Failed')
            ? 'bg-red-50 border border-red-200 text-red-700'
            : 'bg-green-50 border border-green-200 text-green-700'
        }`}>
          {syncMessage}
        </div>
      )}

      {/* Filters */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <input
          type="text"
          placeholder="Search templates..."
          value={filters.search}
          onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value, page: 1 }))}
          className="px-3 py-2 border border-gray-300 rounded-lg"
        />
        <select
          value={filters.category}
          onChange={(e) => setFilters(prev => ({ ...prev, category: e.target.value, page: 1 }))}
          className="px-3 py-2 border border-gray-300 rounded-lg"
        >
          <option value="">All Categories</option>
          <option value="marketing">Marketing</option>
          <option value="utility">Utility</option>
          <option value="authentication">Authentication</option>
        </select>
        <select
          value={filters.status}
          onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value, page: 1 }))}
          className="px-3 py-2 border border-gray-300 rounded-lg"
        >
          <option value="">All Statuses</option>
          <option value="PENDING">Pending</option>
          <option value="APPROVED">Approved</option>
          <option value="REJECTED">Rejected</option>
          <option value="DISABLED">Disabled</option>
        </select>
        <select
          value={filters.language}
          onChange={(e) => setFilters(prev => ({ ...prev, language: e.target.value, page: 1 }))}
          className="px-3 py-2 border border-gray-300 rounded-lg"
        >
          <option value="">All Languages</option>
          <option value="en">English</option>
          <option value="es">Spanish</option>
          <option value="fr">French</option>
        </select>
      </div>

      {/* Templates Table */}
      {loading ? (
        <div className="text-center py-12">Loading...</div>
      ) : templates.length === 0 ? (
        <div className="text-center py-12 text-gray-500">No templates found</div>
      ) : (
        <>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Language</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {templates.map((template) => (
                  <tr key={template.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="font-medium text-gray-900">{template.name}</div>
                      <div className="text-sm text-gray-500 truncate max-w-xs">
                        {template.body_text || template.content}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 capitalize">
                      {template.category}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {template.language}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(template.status)}`}>
                        {template.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button
                        onClick={() => onSelectTemplate?.(template)}
                        className="text-green-600 hover:text-green-900 mr-4"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(template.id)}
                        className="text-red-600 hover:text-red-900"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {pagination.total_pages > 1 && (
            <div className="mt-4 flex justify-center gap-2">
              <button
                onClick={() => setPagination(prev => ({ ...prev, page: prev.page - 1 }))}
                disabled={pagination.page === 1}
                className="px-3 py-1 border rounded disabled:opacity-50"
              >
                Previous
              </button>
              <span className="px-3 py-1">
                Page {pagination.page} of {pagination.total_pages}
              </span>
              <button
                onClick={() => setPagination(prev => ({ ...prev, page: prev.page + 1 }))}
                disabled={pagination.page >= pagination.total_pages}
                className="px-3 py-1 border rounded disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default TemplateList;
