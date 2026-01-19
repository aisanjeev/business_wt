'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { campaignApi, contactListApi, templateApi } from '@/services/api';
import { BulkMessageCampaign, CampaignStatus, ContactList, MessageTemplate } from '@/types';
import CampaignLogs from './CampaignLogs';
import TemplatePreview from './TemplateManagement/TemplatePreview';

interface BulkMessagingProps {
  onCampaignCreated?: () => void;
}

const BulkMessaging: React.FC<BulkMessagingProps> = ({ onCampaignCreated }) => {
  const [campaignName, setCampaignName] = useState('');
  const [messageContent, setMessageContent] = useState('');
  const [selectedListIds, setSelectedListIds] = useState<number[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [availableLists, setAvailableLists] = useState<ContactList[]>([]);
  const [campaigns, setCampaigns] = useState<BulkMessageCampaign[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'create' | 'list'>('create');
  const [viewLogsCampaignId, setViewLogsCampaignId] = useState<number | null>(null);
  
  // Template selection state
  const [availableTemplates, setAvailableTemplates] = useState<MessageTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [templateVariables, setTemplateVariables] = useState<Record<string, string>>({});

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

  const loadTemplates = useCallback(async () => {
    try {
      const response = await templateApi.getTemplates({
        page: 1,
        page_size: 100,
        status: 'APPROVED'
      });
      if (response.success && response.data) {
        setAvailableTemplates(response.data.items || []);
      }
    } catch (err) {
      console.error('Failed to load templates:', err);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'list') {
      loadCampaigns();
    } else {
      loadLists();
      loadTemplates();
    }
  }, [activeTab, loadLists, loadTemplates]);

  // Extract variables from template when selected
  useEffect(() => {
    if (selectedTemplateId) {
      const template = availableTemplates.find(t => t.id === selectedTemplateId);
      if (template) {
        // Extract variables from body_text
        const bodyText = template.body_text || template.content || '';
        const matches = bodyText.match(/\{\{(\d+)\}\}/g) || [];
        const varNumbers = Array.from(new Set(
          matches.map(m => m.replace(/[{}]/g, ''))
        )).sort((a, b) => parseInt(a) - parseInt(b));
        
        // Initialize template variables (preserve existing values if template hasn't changed)
        setTemplateVariables(prev => {
          const newVars: Record<string, string> = {};
          varNumbers.forEach(num => {
            newVars[num] = prev[num] || '';
          });
          return newVars;
        });
      }
    } else {
      setTemplateVariables({});
    }
  }, [selectedTemplateId, availableTemplates]);

  const loadCampaigns = async () => {
    setLoading(true);
    const response = await campaignApi.getCampaigns(1, 10);
    
    if (response.success && response.data) {
      setCampaigns(response.data.items || []);
    }
    setLoading(false);
  };

  const handleCreateCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!campaignName.trim()) {
      setError('Campaign name is required');
      return;
    }

    // If template is selected, validate variables; otherwise require message content
    if (selectedTemplateId) {
      const template = availableTemplates.find(t => t.id === selectedTemplateId);
      if (template) {
        const bodyText = template.body_text || template.content || '';
        const matches = bodyText.match(/\{\{(\d+)\}\}/g) || [];
        const varNumbers = Array.from(new Set(matches.map(m => m.replace(/[{}]/g, ''))));
        
        // Validate all variables are filled
        const missingVars = varNumbers.filter(num => !templateVariables[num] || !templateVariables[num].trim());
        if (missingVars.length > 0) {
          setError(`Please fill in all template variables: ${missingVars.map(v => `{{${v}}}`).join(', ')}`);
          return;
        }
      }
    } else if (!messageContent.trim()) {
      setError('Please provide message content or select a template');
      return;
    }

    setLoading(true);
    setError(null);

    // Validate that at least one targeting option is selected
    if (selectedListIds.length === 0 && selectedTags.length === 0) {
      setError('Please select at least one list or tag to target');
      return;
    }

    const response = await campaignApi.createCampaign({
      name: campaignName,
      message_content: messageContent || '', // Required field, but can be empty if using template
      template_id: selectedTemplateId || undefined,
      template_variables: selectedTemplateId ? templateVariables : undefined,
      list_ids: selectedListIds.length > 0 ? selectedListIds : undefined,
      tag_names: selectedTags.length > 0 ? selectedTags : undefined,
    });

    if (response.success && response.data) {
      setCampaignName('');
      setMessageContent('');
      setSelectedListIds([]);
      setSelectedTags([]);
      setSelectedTemplateId(null);
      setTemplateVariables({});
      onCampaignCreated?.();
      setActiveTab('list');
      loadCampaigns();
    } else {
      setError(response.error || 'Failed to create campaign');
    }

    setLoading(false);
  };

  const handleStartCampaign = async (campaignId: number) => {
    if (!confirm('Are you sure you want to start this campaign? Messages will be sent immediately.')) {
      return;
    }

    setLoading(true);
    const response = await campaignApi.startCampaign(campaignId);
    
    if (response.success) {
      loadCampaigns();
    } else {
      setError(response.error || 'Failed to start campaign');
    }
    setLoading(false);
  };

  const handlePublishCampaign = async (campaignId: number) => {
    if (!confirm('Publish this campaign? It will be ready to run.')) {
      return;
    }

    setLoading(true);
    const response = await campaignApi.updateCampaign(campaignId, { status: 'scheduled' });
    
    if (response.success) {
      loadCampaigns();
    } else {
      setError(response.error || 'Failed to publish campaign');
    }
    setLoading(false);
  };

  const handleStatusChange = async (campaignId: number, newStatus: 'draft' | 'scheduled' | 'sending' | 'completed' | 'failed') => {
    setLoading(true);
    const response = await campaignApi.updateCampaign(campaignId, { status: newStatus });
    
    if (response.success) {
      loadCampaigns();
    } else {
      setError(response.error || 'Failed to update campaign status');
    }
    setLoading(false);
  };

  return (
    <div className="p-6 bg-white rounded-lg shadow">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold">Bulk Messaging Campaigns</h2>
        <div className="flex gap-2 border-b">
          <button
            onClick={() => setActiveTab('create')}
            className={`px-4 py-2 font-medium text-sm transition-colors ${
              activeTab === 'create'
                ? 'border-b-2 border-green-600 text-green-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Create Campaign
          </button>
          <button
            onClick={() => setActiveTab('list')}
            className={`px-4 py-2 font-medium text-sm transition-colors ${
              activeTab === 'list'
                ? 'border-b-2 border-green-600 text-green-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            My Campaigns
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      {activeTab === 'create' ? (
        <form onSubmit={handleCreateCampaign} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Campaign Name *
            </label>
            <input
              type="text"
              value={campaignName}
              onChange={(e) => setCampaignName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
              placeholder="e.g., New Product Launch"
              required
            />
          </div>

          {/* Template Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Select Template (optional)
            </label>
            <select
              value={selectedTemplateId || ''}
              onChange={(e) => setSelectedTemplateId(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="">None - Use plain text message</option>
              {availableTemplates.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.name} ({template.category} - {template.language})
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">
              Select an approved template to use for this campaign, or leave empty to use plain text
            </p>
          </div>

          {/* Template Variables */}
          {selectedTemplateId && (() => {
            const template = availableTemplates.find(t => t.id === selectedTemplateId);
            if (!template) return null;
            
            const varNumbers = Object.keys(templateVariables).sort((a, b) => parseInt(a) - parseInt(b));
            
            return (
              <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Template Variables *
                </label>
                <div className="space-y-3">
                  {varNumbers.map((varNum) => (
                    <div key={varNum}>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        Variable {`{{${varNum}}}`}
                      </label>
                      <input
                        type="text"
                        value={templateVariables[varNum] || ''}
                        onChange={(e) => setTemplateVariables(prev => ({ ...prev, [varNum]: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 text-sm"
                        placeholder={`Enter value for {{${varNum}}}`}
                        required
                      />
                    </div>
                  ))}
                </div>
                {varNumbers.length > 0 && (
                  <div className="mt-4 border-t border-gray-200 pt-4">
                    <p className="text-xs font-medium text-gray-700 mb-2">Preview:</p>
                    <div className="bg-white border border-gray-200 rounded p-3">
                      <TemplatePreview
                        template={template}
                        sampleVariables={templateVariables}
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })()}

          {/* Message Content - Optional when template is selected */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Message Content {selectedTemplateId ? '(optional - used as fallback)' : '*'}
            </label>
            <textarea
              value={messageContent}
              onChange={(e) => setMessageContent(e.target.value)}
              rows={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
              placeholder={selectedTemplateId ? "Optional fallback message..." : "Enter your message here..."}
              required={!selectedTemplateId}
            />
            <p className="mt-1 text-xs text-gray-500">
              {messageContent.length} characters (Recommended: Under 1600 for best delivery)
            </p>
          </div>

          {/* List Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Target Lists (optional)
            </label>
            <div className="space-y-2 max-h-40 overflow-y-auto border border-gray-300 rounded-md p-2">
              {availableLists.length === 0 ? (
                <p className="text-xs text-gray-500">No lists available. Create lists from Contacts page.</p>
              ) : (
                availableLists.map((list) => (
                  <label key={list.id} className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-2 rounded">
                    <input
                      type="checkbox"
                      checked={selectedListIds.includes(list.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedListIds([...selectedListIds, list.id]);
                        } else {
                          setSelectedListIds(selectedListIds.filter(id => id !== list.id));
                        }
                      }}
                      className="rounded border-gray-300 text-green-600 focus:ring-green-500"
                    />
                    <span className="text-sm text-gray-700">{list.name}</span>
                    <span className="text-xs text-gray-500 ml-auto">({list.contacts_count || 0} contacts)</span>
                  </label>
                ))
              )}
            </div>
          </div>

          {/* Tag Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Target Tags (optional)
            </label>
            <div className="flex flex-wrap gap-2 mb-2">
              {selectedTags.map((tag, index) => (
                <span
                  key={index}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-green-100 text-green-700 text-sm rounded-full"
                >
                  {tag}
                  <button
                    type="button"
                    onClick={() => setSelectedTags(selectedTags.filter((_, i) => i !== index))}
                    className="hover:text-green-900"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Enter tag name and press Enter"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 text-sm"
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    const tagInput = e.currentTarget as HTMLInputElement;
                    const tagValue = tagInput.value.trim();
                    if (tagValue && !selectedTags.includes(tagValue)) {
                      setSelectedTags([...selectedTags, tagValue]);
                      tagInput.value = '';
                    }
                  }
                }}
              />
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Press Enter to add a tag. Messages will be sent to contacts with any of the selected tags.
            </p>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded p-3">
            <p className="text-xs text-blue-800 font-medium mb-1">Note:</p>
            <p className="text-xs text-blue-700">
              Select at least one list or tag to target contacts. If both are selected, contacts matching either criteria will be included.
            </p>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Creating...' : 'Create Campaign'}
          </button>
        </form>
      ) : viewLogsCampaignId ? (
        <CampaignLogs
          campaignId={viewLogsCampaignId}
          campaignName={campaigns.find(c => c.id === viewLogsCampaignId)?.name}
          onClose={() => setViewLogsCampaignId(null)}
        />
      ) : (
        <div className="space-y-4">
          {loading && campaigns.length === 0 ? (
            <div className="text-center py-8 text-gray-500">Loading campaigns...</div>
          ) : campaigns.length === 0 ? (
            <div className="text-center py-8 text-gray-500">No campaigns yet</div>
          ) : (
            campaigns.map((campaign) => (
              <CampaignCard
                key={campaign.id}
                campaign={campaign}
                onStart={() => handleStartCampaign(campaign.id)}
                onViewLogs={() => setViewLogsCampaignId(campaign.id)}
                onStatusChange={(newStatus) => handleStatusChange(campaign.id, newStatus)}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
};

interface CampaignCardProps {
  campaign: BulkMessageCampaign;
  onStart: () => void;
  onViewLogs: () => void;
  onStatusChange?: (newStatus: 'draft' | 'scheduled' | 'sending' | 'completed' | 'failed') => void;
}

const CampaignCard: React.FC<CampaignCardProps> = ({ campaign, onStart, onViewLogs, onStatusChange }) => {
  const [status, setStatus] = useState<CampaignStatus | null>(null);

  useEffect(() => {
    if (campaign.status === 'sending') {
      const interval = setInterval(async () => {
        const response = await campaignApi.getCampaignStatus(campaign.id);
        if (response.success && response.data) {
          setStatus(response.data);
          if (response.data.status === 'completed' || response.data.status === 'failed') {
            clearInterval(interval);
          }
        }
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [campaign.id, campaign.status]);

  const displayStatus = status || {
    id: campaign.id,
    status: campaign.status,
    total_recipients: campaign.total_recipients,
    sent_count: campaign.sent_count,
    failed_count: campaign.failed_count,
    progress_percentage: campaign.total_recipients > 0
      ? ((campaign.sent_count + campaign.failed_count) / campaign.total_recipients * 100)
      : 0,
    started_at: campaign.started_at,
    completed_at: campaign.completed_at,
  };

  const statusColors = {
    draft: 'bg-gray-100 text-gray-800',
    scheduled: 'bg-blue-100 text-blue-800',
    sending: 'bg-yellow-100 text-yellow-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  };

  return (
    <div className="p-4 border rounded-lg hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold">{campaign.name}</h3>
          <p className="text-sm text-gray-600 mt-1 line-clamp-2">{campaign.message_content}</p>
        </div>
        <span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[campaign.status as keyof typeof statusColors] || 'bg-gray-100'}`}>
          {campaign.status}
        </span>
      </div>

      {displayStatus.status === 'sending' && (
        <div className="mb-3">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-green-600 h-2 rounded-full transition-all"
              style={{ width: `${displayStatus.progress_percentage}%` }}
            ></div>
          </div>
          <p className="text-xs text-gray-600 mt-1 text-center">
            {displayStatus.progress_percentage.toFixed(1)}% - {displayStatus.sent_count} sent
          </p>
        </div>
      )}

      <div className="grid grid-cols-3 gap-4 text-sm mb-3">
        <div>
          <p className="text-gray-600">Recipients</p>
          <p className="font-semibold">{displayStatus.total_recipients}</p>
        </div>
        <div>
          <p className="text-green-600">Sent</p>
          <p className="font-semibold">{displayStatus.sent_count}</p>
        </div>
        <div>
          <p className="text-red-600">Failed</p>
          <p className="font-semibold">{displayStatus.failed_count}</p>
        </div>
      </div>

      {campaign.status === 'draft' ? (
        <div className="flex gap-2">
          <button
            onClick={() => onStatusChange?.('scheduled')}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm"
          >
            Publish
          </button>
          <button
            onClick={onStart}
            className="flex-1 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors text-sm"
          >
            Run Now
          </button>
        </div>
      ) : campaign.status === 'scheduled' ? (
        <div className="flex gap-2">
          <button
            onClick={onStart}
            className="flex-1 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors text-sm"
          >
            Run Campaign
          </button>
          <button
            onClick={() => onStatusChange?.('draft')}
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors text-sm"
          >
            Unpublish
          </button>
        </div>
      ) : (
        <button
          onClick={onViewLogs}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm"
        >
          View Logs
        </button>
      )}

      {displayStatus.started_at && (
        <p className="text-xs text-gray-500 mt-2">
          Started: {new Date(displayStatus.started_at).toLocaleString()}
        </p>
      )}
    </div>
  );
};

export default BulkMessaging;
