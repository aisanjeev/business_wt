'use client';

import React from 'react';
import Image from 'next/image';
import { Contact, Conversation } from '@/types';
import { formatPhoneNumber, formatRelativeTime, getInitials, stringToColor } from '@/utils/formatters';

interface ContactInfoProps {
  conversation: Conversation;
  contact?: Contact;
  isOpen: boolean;
  onClose: () => void;
}

const ContactInfo: React.FC<ContactInfoProps> = ({
  conversation,
  contact,
  isOpen,
  onClose,
}) => {
  if (!isOpen) return null;

  const contactName = contact?.name || 'Unknown Contact';
  const contactPhone = contact?.phone_number || '';

  return (
    <div className="w-80 bg-white border-l border-gray-200 flex flex-col h-full">
      {/* Header */}
      <div className="h-14 px-4 flex items-center justify-between border-b border-gray-200">
        <h2 className="font-semibold text-gray-900">Contact Info</h2>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 rounded-full transition-colors"
        >
          <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Profile section */}
        <div className="p-6 text-center border-b border-gray-100">
          <div
            className="w-24 h-24 rounded-full flex items-center justify-center text-white text-3xl font-bold mx-auto mb-4"
            style={{ backgroundColor: stringToColor(contactName) }}
          >
            {contact?.avatar_url ? (
              <Image
                src={contact.avatar_url}
                alt={contactName}
                width={96}
                height={96}
                className="w-24 h-24 rounded-full object-cover"
                unoptimized
              />
            ) : (
              getInitials(contactName)
            )}
          </div>
          <h3 className="text-xl font-semibold text-gray-900">{contactName}</h3>
          <p className="text-gray-500">{formatPhoneNumber(contactPhone)}</p>
        </div>

        {/* Details section */}
        <div className="p-4">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Contact Details
          </h4>
          
          {/* Phone */}
          <div className="flex items-center gap-3 py-3 border-b border-gray-100">
            <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
              <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
              </svg>
            </div>
            <div>
              <p className="text-sm text-gray-500">Phone</p>
              <p className="font-medium text-gray-900">{formatPhoneNumber(contactPhone)}</p>
            </div>
          </div>

          {/* Email */}
          {contact?.email && (
            <div className="flex items-center gap-3 py-3 border-b border-gray-100">
              <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <div>
                <p className="text-sm text-gray-500">Email</p>
                <p className="font-medium text-gray-900">{contact.email}</p>
              </div>
            </div>
          )}

          {/* Status */}
          <div className="flex items-center gap-3 py-3 border-b border-gray-100">
            <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
              <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <p className="text-sm text-gray-500">Status</p>
              <p className="font-medium text-gray-900 capitalize">{contact?.status || 'Unknown'}</p>
            </div>
          </div>

          {/* Created at */}
          {contact?.created_at && (
            <div className="flex items-center gap-3 py-3 border-b border-gray-100">
              <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <div>
                <p className="text-sm text-gray-500">Contact since</p>
                <p className="font-medium text-gray-900">{formatRelativeTime(contact.created_at)}</p>
              </div>
            </div>
          )}
        </div>

        {/* Conversation Info */}
        <div className="p-4">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Conversation Info
          </h4>

          {/* Tags */}
          {conversation.tags && conversation.tags.length > 0 && (
            <div className="mb-4">
              <p className="text-sm text-gray-500 mb-2">Tags</p>
              <div className="flex flex-wrap gap-2">
                {conversation.tags.map((tag, index) => (
                  <span
                    key={index}
                    className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Conversation ID */}
          <div className="flex items-center gap-3 py-3 border-b border-gray-100">
            <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
              <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
              </svg>
            </div>
            <div>
              <p className="text-sm text-gray-500">Conversation ID</p>
              <p className="font-medium text-gray-900">#{conversation.id}</p>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="p-4 space-y-2">
          <button className="w-full py-2 px-4 text-left text-gray-700 hover:bg-gray-100 rounded-lg transition-colors flex items-center gap-3">
            <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
            </svg>
            <span>Archive conversation</span>
          </button>
          
          <button className="w-full py-2 px-4 text-left text-red-600 hover:bg-red-50 rounded-lg transition-colors flex items-center gap-3">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
            <span>Block contact</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ContactInfo;
