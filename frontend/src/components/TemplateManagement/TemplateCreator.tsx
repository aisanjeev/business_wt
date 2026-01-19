'use client';

import React, { useState, useCallback } from 'react';
import { MessageTemplate } from '@/types';
import { templateApi } from '@/services/api';
import TemplatePreview from './TemplatePreview';

interface TemplateCreatorProps {
  onSuccess?: (template: MessageTemplate) => void;
  onCancel?: () => void;
}

const TemplateCreator: React.FC<TemplateCreatorProps> = ({ onSuccess, onCancel }) => {
  const [formData, setFormData] = useState<Partial<MessageTemplate>>({
    name: '',
    category: 'utility',
    language: 'en',
    status: 'PENDING',
    header_type: null,
    header_content: '',
    body_text: '',
    footer_text: '',
    buttons: null,
    variables: {},
  });
  
  const [sampleVariables, setSampleVariables] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleInputChange = (field: keyof MessageTemplate, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setError(null);
  };

  const addVariable = useCallback(() => {
    const bodyText = formData.body_text || '';
    const matches = bodyText.match(/\{\{(\d+)\}\}/g) || [];
    const nextVar = matches.length + 1;
    const newBody = bodyText + ` {{${nextVar}}}`;
    handleInputChange('body_text', newBody);
    
    // Extract variable numbers and update sample variables
    const varNumbers = Array.from(new Set(
      (newBody.match(/\{\{(\d+)\}\}/g) || []).map(m => m.replace(/[{}]/g, ''))
    ));
    const newSampleVars: Record<string, string> = {};
    varNumbers.forEach(num => {
      newSampleVars[num] = sampleVariables[num] || `Sample ${num}`;
    });
    setSampleVariables(newSampleVars);
  }, [formData.body_text, sampleVariables]);

  const handleSubmit = async (submitToMeta: boolean = false) => {
    if (!formData.name || !formData.body_text) {
      setError('Template name and body text are required');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await templateApi.createTemplate({
        ...formData,
        name: formData.name.toLowerCase().replace(/[^a-z0-9_]/g, '_'),
      } as Partial<MessageTemplate>);

      if (response.success && response.data) {
        if (submitToMeta) {
          const submitResponse = await templateApi.submitTemplate(response.data.id);
          if (submitResponse.success && submitResponse.data) {
            onSuccess?.(submitResponse.data);
          } else {
            setError(submitResponse.error || 'Failed to submit to Meta');
          }
        } else {
          onSuccess?.(response.data);
        }
      } else {
        setError(response.error || 'Failed to create template');
      }
    } catch (err) {
      setError('An unexpected error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex gap-6 h-full">
      {/* Form Section (60%) */}
      <div className="flex-1 overflow-y-auto p-6">
        <h2 className="text-2xl font-bold mb-6">Create Template</h2>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded">
            {error}
          </div>
        )}

        <div className="space-y-6">
          {/* Category */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Category *
            </label>
            <select
              value={formData.category}
              onChange={(e) => handleInputChange('category', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            >
              <option value="marketing">Marketing</option>
              <option value="utility">Utility</option>
              <option value="authentication">Authentication</option>
            </select>
          </div>

          {/* Template Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Template Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'))}
              placeholder="template_name"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
            <p className="mt-1 text-xs text-gray-500">Lowercase letters, numbers, and underscores only</p>
          </div>

          {/* Language */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Language *
            </label>
            <select
              value={formData.language}
              onChange={(e) => handleInputChange('language', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            >
              <option value="en">English (en)</option>
              <option value="es">Spanish (es)</option>
              <option value="fr">French (fr)</option>
              <option value="de">German (de)</option>
            </select>
          </div>

          {/* Header */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Header Type
            </label>
            <select
              value={formData.header_type || ''}
              onChange={(e) => handleInputChange('header_type', e.target.value || null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            >
              <option value="">None</option>
              <option value="TEXT">Text</option>
              <option value="IMAGE">Image</option>
              <option value="VIDEO">Video</option>
              <option value="DOCUMENT">Document</option>
            </select>
            {formData.header_type === 'TEXT' && (
              <input
                type="text"
                value={formData.header_content || ''}
                onChange={(e) => handleInputChange('header_content', e.target.value)}
                placeholder="Header text (max 60 chars)"
                maxLength={60}
                className="w-full mt-2 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
              />
            )}
          </div>

          {/* Body */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Body Text *
            </label>
            <div className="flex gap-2 mb-2">
              <button
                type="button"
                onClick={addVariable}
                className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded border border-gray-300"
              >
                Add Variable
              </button>
            </div>
            <textarea
              value={formData.body_text}
              onChange={(e) => {
                handleInputChange('body_text', e.target.value);
                // Extract variables for sample data
                const matches = e.target.value.match(/\{\{(\d+)\}\}/g) || [];
                const varNumbers = Array.from(new Set(matches.map(m => m.replace(/[{}]/g, ''))));
                const newSampleVars: Record<string, string> = {};
                varNumbers.forEach(num => {
                  newSampleVars[num] = sampleVariables[num] || `Sample ${num}`;
                });
                setSampleVariables(newSampleVars);
              }}
              placeholder="Enter message body. Use {{1}}, {{2}}, etc. for variables."
              rows={6}
              maxLength={1024}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
            <p className="mt-1 text-xs text-gray-500">
              {(formData.body_text || '').length} / 1024 characters
            </p>
          </div>

          {/* Sample Variables */}
          {Object.keys(sampleVariables).length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Sample Variables (for preview)
              </label>
              <div className="space-y-2">
                {Object.entries(sampleVariables).map(([key, value]) => (
                  <div key={key} className="flex gap-2">
                    <span className="px-2 py-1 bg-gray-100 rounded text-sm">{`{{${key}}}`}</span>
                    <input
                      type="text"
                      value={value}
                      onChange={(e) => {
                        setSampleVariables(prev => ({ ...prev, [key]: e.target.value }));
                      }}
                      className="flex-1 px-3 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Footer */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Footer Text (optional)
            </label>
            <input
              type="text"
              value={formData.footer_text || ''}
              onChange={(e) => handleInputChange('footer_text', e.target.value)}
              placeholder="Footer text (max 60 chars)"
              maxLength={60}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button
              onClick={() => handleSubmit(false)}
              disabled={isSubmitting}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 disabled:opacity-50"
            >
              Save Draft
            </button>
            <button
              onClick={() => handleSubmit(true)}
              disabled={isSubmitting}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              {isSubmitting ? 'Submitting...' : 'Submit to Meta'}
            </button>
            {onCancel && (
              <button
                onClick={onCancel}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Preview Section (40%) */}
      <div className="w-2/5 border-l border-gray-200 p-6 overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4">Preview</h3>
        <TemplatePreview template={formData} sampleVariables={sampleVariables} />
      </div>
    </div>
  );
};

export default TemplateCreator;
