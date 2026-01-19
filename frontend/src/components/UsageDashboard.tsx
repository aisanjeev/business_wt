'use client';

import React, { useState, useEffect } from 'react';
import { usageApi } from '@/services/api';
import { UsageStats, UsageCost } from '@/types';

const UsageDashboard: React.FC = () => {
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [costs, setCosts] = useState<UsageCost | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<'7d' | '30d' | '90d'>('30d');

  useEffect(() => {
    loadUsageData();
  }, [period]);

  const loadUsageData = async () => {
    setLoading(true);
    setError(null);

    const endDate = new Date();
    const startDate = new Date();
    
    switch (period) {
      case '7d':
        startDate.setDate(endDate.getDate() - 7);
        break;
      case '30d':
        startDate.setDate(endDate.getDate() - 30);
        break;
      case '90d':
        startDate.setDate(endDate.getDate() - 90);
        break;
    }

    const periodStart = startDate.toISOString();
    const periodEnd = endDate.toISOString();

    const [statsResponse, costsResponse] = await Promise.all([
      usageApi.getStats(periodStart, periodEnd),
      usageApi.getCosts(periodStart, periodEnd),
    ]);

    if (statsResponse.success && statsResponse.data) {
      setStats(statsResponse.data);
    }

    if (costsResponse.success && costsResponse.data) {
      setCosts(costsResponse.data);
    }

    if (!statsResponse.success || !costsResponse.success) {
      setError(statsResponse.error || costsResponse.error || 'Failed to load usage data');
    }

    setLoading(false);
  };

  const handleExport = async (format: 'csv' | 'json' = 'csv') => {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - (period === '7d' ? 7 : period === '30d' ? 30 : 90));

    try {
      const blob = await usageApi.exportUsage(format, startDate.toISOString(), endDate.toISOString());
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `usage_export_${period}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError('Failed to export usage data');
    }
  };

  if (loading && !stats) {
    return (
      <div className="p-6 bg-white rounded-lg shadow">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="h-32 bg-gray-200 rounded mb-4"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-white rounded-lg shadow">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold">Usage & Costs</h2>
        <div className="flex gap-2">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value as '7d' | '30d' | '90d')}
            className="px-3 py-1 border border-gray-300 rounded text-sm"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
          </select>
          <button
            onClick={() => handleExport('csv')}
            className="px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700 transition-colors"
          >
            Export CSV
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      {stats && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm text-blue-600 mb-1">Total Messages</p>
              <p className="text-2xl font-bold text-blue-900">{stats.total_messages.toLocaleString()}</p>
            </div>
            <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
              <p className="text-sm text-purple-600 mb-1">API Calls</p>
              <p className="text-2xl font-bold text-purple-900">{stats.total_api_calls.toLocaleString()}</p>
            </div>
            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
              <p className="text-sm text-green-600 mb-1">Total Cost</p>
              <p className="text-2xl font-bold text-green-900">
                ${costs?.total_cost.toFixed(2) || '0.00'}
              </p>
            </div>
          </div>

          {/* Message Type Breakdown */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Messages by Type</h3>
            <div className="space-y-2">
              {Object.entries(stats.breakdown_by_type || {}).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                  <span className="capitalize font-medium">{type}</span>
                  <div className="flex items-center gap-4">
                    <span className="text-gray-600">{count.toLocaleString()}</span>
                    <div className="w-32 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-green-600 h-2 rounded-full"
                        style={{
                          width: `${(count / stats.total_messages) * 100}%`,
                        }}
                      ></div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Cost Breakdown */}
          {costs && Object.keys(costs.cost_breakdown || {}).length > 0 && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Cost Breakdown</h3>
              <div className="space-y-2">
                {Object.entries(costs.cost_breakdown).map(([type, cost]) => (
                  <div key={type} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <span className="capitalize font-medium">{type}</span>
                    <div className="flex items-center gap-4">
                      <span className="text-gray-600">${cost.toFixed(4)}</span>
                      <div className="w-32 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-green-600 h-2 rounded-full"
                          style={{
                            width: `${(cost / costs.total_cost) * 100}%`,
                          }}
                        ></div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Period Info */}
          <div className="text-xs text-gray-500 pt-4 border-t">
            Period: {new Date(stats.period_start).toLocaleDateString()} - {new Date(stats.period_end).toLocaleDateString()}
          </div>
        </div>
      )}
    </div>
  );
};

export default UsageDashboard;
