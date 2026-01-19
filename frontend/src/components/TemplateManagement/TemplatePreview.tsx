'use client';

import React, { useEffect, useState } from 'react';
import Image from 'next/image';
import { MessageTemplate } from '@/types';
import { getMediaUrl } from '@/services/api';

interface TemplatePreviewProps {
  template: Partial<MessageTemplate>;
  sampleVariables?: Record<string, string>;
}

const TemplatePreview: React.FC<TemplatePreviewProps> = ({
  template,
  sampleVariables = {},
}) => {
  const [previewBody, setPreviewBody] = useState<string>('');

  useEffect(() => {
    // Replace variables in body text
    let body = template.body_text || template.content || '';
    
    // Use provided sample variables or template's default variables
    const vars = Object.keys(sampleVariables).length > 0 
      ? sampleVariables 
      : template.variables || {};
    
    // Replace variables {{1}}, {{2}}, etc.
    Object.entries(vars).forEach(([key, value]) => {
      body = body.replace(new RegExp(`\\{\\{${key}\\}\\}`, 'g'), String(value));
    });
    
    setPreviewBody(body);
  }, [template.body_text, template.content, template.variables, sampleVariables]);

  const headerType = template.header_type;
  const headerContent = template.header_content;
  const footerText = template.footer_text;
  const buttons = template.buttons;

  return (
    <div className="flex flex-col items-center p-6 bg-gray-50 rounded-lg">
      <div className="w-full max-w-sm bg-white rounded-lg shadow-lg overflow-hidden">
        {/* WhatsApp-style header */}
        <div className="bg-green-600 text-white px-4 py-3 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
              <path d="M17.472 14.382c-.297-.149-1.758-1.123-2.03-1.258-.272-.134-.47-.2-.669.2-.197.4-.767 1.258-.94 1.517-.173.258-.347.3-.644.15-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.058-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.19 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.98 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z" />
            </svg>
          </div>
          <div>
            <div className="font-semibold">Template Preview</div>
            <div className="text-xs opacity-90">WhatsApp</div>
          </div>
        </div>

        {/* Message content */}
        <div className="p-4 space-y-3">
          {/* Header */}
          {headerType && headerContent && (
            <div className="border-b border-gray-200 pb-3">
              {headerType === 'TEXT' && (
                <div className="text-lg font-semibold text-gray-900">{headerContent}</div>
              )}
              {headerType === 'IMAGE' && (
                <div className="relative w-full h-48 rounded-lg overflow-hidden bg-gray-100">
                  <Image
                    src={getMediaUrl(headerContent)}
                    alt="Header"
                    fill
                    className="object-cover"
                    unoptimized
                  />
                </div>
              )}
              {headerType === 'VIDEO' && (
                <div className="relative w-full h-48 rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center">
                  <svg className="w-16 h-16 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                </div>
              )}
              {headerType === 'DOCUMENT' && (
                <div className="flex items-center gap-2 p-3 bg-gray-100 rounded-lg">
                  <svg className="w-8 h-8 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="text-sm text-gray-700">Document</span>
                </div>
              )}
            </div>
          )}

          {/* Body */}
          {previewBody && (
            <div className="text-gray-800 whitespace-pre-wrap break-words">
              {previewBody}
            </div>
          )}

          {/* Footer */}
          {footerText && (
            <div className="text-xs text-gray-500 pt-2 border-t border-gray-100">
              {footerText}
            </div>
          )}

          {/* Buttons */}
          {buttons?.buttons && buttons.buttons.length > 0 && (
            <div className="space-y-2 pt-3 border-t border-gray-100">
              {buttons.buttons.map((button: any, index: number) => (
                <button
                  key={index}
                  className="w-full px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
                  disabled
                >
                  {button.text || button.title || `Button ${index + 1}`}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TemplatePreview;
