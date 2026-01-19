'use client';

import React, { useState, useEffect } from 'react';
import { campaignApi } from '@/services/api';

interface CampaignLog {
  id: number;
  campaign_id: number;
  contact_id: number;
  message_id?: number;
  phone_number: string;
  contact_name?: string;
  status: 'pending' | 'sent' | 'delivered' | 'read' | 'failed';
  sent_at?: string;
  delivered_at?: string;
  read_at?: string;
  failed_at?: string;
  error_message?: string;
  cost?: string;
  created_at: string;
}

interface CampaignLogsProps {
  campaignId: number;
  campaignName?: string;
  onClose?: () => void;
}

const CampaignLogs: React.FC<CampaignLogsProps> = ({ campaignId, campaignName, onClose }) => {
  const [logs, setLogs] = useState<CampaignLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pageSize] = useState(50);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadLogs();
  }, [campaignId, page, statusFilter, search]);

  const loadLogs = async () => {
    setLoading(true);
    setError(null);

    const response = await campaignApi.getCampaignLogs(
      campaignId,
      page,
      pageSize,
      statusFilter || undefined,
      search || undefined
    );

    if (response.success && response.data) {
      setLogs(response.data.items || []);
      setTotal(response.data.total || 0);
    } else {
      setError(response.error || 'Failed to load logs');
    }

    setLoading(false);
  };

  const handleExport = async (format: 'csv' | 'json' = 'csv') => {
    try {
      const blob = await campaignApi.exportCampaignLogs(campaignId, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `campaign_${campaignId}_logs.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError('Failed to export logs');
    }
  };

  const statusColors = {
    pending: 'bg-gray-100 text-gray-800',
    sent: 'bg-blue-100 text-blue-800',
    delivered: 'bg-green-100 text-green-800',
    read: 'bg-purple-100 text-purple-800',
    failed: 'bg-red-100 text-red-800',
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="p-6 bg-white rounded-lg shadow">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold">Campaign Recipient Logs</h2>
          {campaignName && <p className="text-sm text-gray-600 mt-1">{campaignName}</p>}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleExport('csv')}
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors text-sm"
          >
            Export CSV
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors text-sm"
            >
              Close
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex gap-4">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search by phone or name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
        >
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="sent">Sent</option>
          <option value="delivered">Delivered</option>
          <option value="read">Read</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {/* Logs Table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Recipient</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Phone</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Sent At</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Delivered At</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Read At</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Cost</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Error</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                  Loading logs...
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                  No logs found
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">
                    {log.contact_name || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">{log.phone_number}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      statusColors[log.status] || statusColors.pending
                    }`}>
                      {log.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">{formatDate(log.sent_at)}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{formatDate(log.delivered_at)}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{formatDate(log.read_at)}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{log.cost || '-'}</td>
                  <td className="px-4 py-3 text-sm text-red-600 max-w-xs truncate" title={log.error_message || ''}>
                    {log.error_message || '-'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > pageSize && (
        <div className="mt-4 flex items-center justify-between">
          <div className="text-sm text-gray-600">
            Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} logs
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={page * pageSize >= total}
              className="px-3 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CampaignLogs;
