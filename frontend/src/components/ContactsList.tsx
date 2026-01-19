'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Image from 'next/image';
import { contactApi, contactListApi, getMediaUrl } from '@/services/api';
import { Contact, PaginatedResponse, ContactList } from '@/types';
import { formatPhoneNumber, getInitials, stringToColor } from '@/utils/formatters';
import ContactInfo from './ContactInfo';
import ContactListManager from './ContactListManager';

type SourceFilter = 'all' | 'imported' | 'chat' | 'manual';
type ViewMode = 'contacts' | 'lists';

interface ContactsListProps {
  onContactSelect?: (contact: Contact) => void;
}

const ContactsList: React.FC<ContactsListProps> = ({ onContactSelect }) => {
  const [viewMode, setViewMode] = useState<ViewMode>('contacts');
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [lists, setLists] = useState<ContactList[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null);
  const [showContactInfo, setShowContactInfo] = useState(false);

  // Load lists to display list names in badges
  useEffect(() => {
    const loadLists = async () => {
      try {
        const response = await contactListApi.getLists(1, 100);
        if (response.success && response.data) {
          setLists(response.data.items);
        }
      } catch (err) {
        console.error('Failed to load lists:', err);
      }
    };
    loadLists();
  }, []);

  const getListName = (listId: number): string => {
    const list = lists.find(l => l.id === listId);
    return list ? list.name : `List #${listId}`;
  };

  const loadContacts = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await contactApi.getContacts(
        page,
        50,
        searchQuery || undefined,
        sourceFilter
      );

      if (response.success && response.data) {
        setContacts(response.data.items);
        setTotalPages(response.data.total_pages);
      } else {
        setError(response.error || 'Failed to load contacts');
      }
    } catch (err) {
      setError('Failed to load contacts');
      console.error('Error loading contacts:', err);
    } finally {
      setLoading(false);
    }
  }, [page, searchQuery, sourceFilter]);

  useEffect(() => {
    loadContacts();
  }, [loadContacts]);

  const handleContactClick = async (contact: Contact) => {
    setSelectedContact(contact);
    setShowContactInfo(true);
    if (onContactSelect) {
      onContactSelect(contact);
    }
  };

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setPage(1); // Reset to first page on search
  };

  const getSourceBadgeColor = (source?: string) => {
    switch (source) {
      case 'imported':
        return 'bg-blue-100 text-blue-700';
      case 'chat':
        return 'bg-green-100 text-green-700';
      case 'manual':
        return 'bg-gray-100 text-gray-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const getSourceLabel = (source?: string) => {
    switch (source) {
      case 'imported':
        return 'Imported';
      case 'chat':
        return 'Chat Contact';
      case 'manual':
        return 'Manually Added';
      default:
        return 'Unknown';
    }
  };

  const sourceTabs: { id: SourceFilter; label: string; count?: number }[] = [
    { id: 'all', label: 'All' },
    { id: 'imported', label: 'Imported' },
    { id: 'chat', label: 'Chat Contacts' },
    { id: 'manual', label: 'Manually Added' },
  ];

  return (
    <div className="flex-1 flex flex-col bg-gray-50 h-full">
      {/* Header with Tabs */}
      <div className="bg-white border-b border-gray-200">
        <div className="p-4">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Contacts</h1>
          
          {/* Tab Navigation */}
          <div className="flex gap-2 border-b border-gray-200 -mb-px">
            <button
              onClick={() => setViewMode('contacts')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                viewMode === 'contacts'
                  ? 'border-green-500 text-green-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Contacts
            </button>
            <button
              onClick={() => setViewMode('lists')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                viewMode === 'lists'
                  ? 'border-green-500 text-green-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Lists
            </button>
          </div>
        </div>
      </div>

      {/* Content based on view mode */}
      {viewMode === 'lists' ? (
        <ContactListManager />
      ) : (
        <>
          {/* Contacts View Header */}
          <div className="bg-white border-b border-gray-200 p-4">
        
        {/* Search */}
        <div className="mb-4">
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={handleSearch}
              placeholder="Search contacts by name, phone, or email..."
              className="w-full px-4 py-2 pl-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
            <svg
              className="absolute left-3 top-2.5 w-5 h-5 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>

        {/* Category Tabs */}
        <div className="flex gap-2">
          {sourceTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setSourceFilter(tab.id);
                setPage(1);
              }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                sourceFilter === tab.id
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Contacts List */}
      <div className="flex-1 overflow-y-auto">
        {loading && contacts.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500" />
          </div>
        ) : error ? (
          <div className="p-8 text-center">
            <p className="text-red-500 mb-4">{error}</p>
            <button
              onClick={loadContacts}
              className="text-green-600 hover:text-green-700 font-medium"
            >
              Try again
            </button>
          </div>
        ) : contacts.length === 0 ? (
          <div className="p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <h3 className="text-gray-900 font-medium mb-1">No contacts found</h3>
            <p className="text-gray-500 text-sm">
              {searchQuery
                ? 'No contacts match your search'
                : sourceFilter !== 'all'
                ? `No ${getSourceLabel(sourceFilter).toLowerCase()} contacts`
                : 'Import contacts or start a conversation to add contacts'}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {contacts.map((contact) => (
              <div
                key={contact.id}
                onClick={() => handleContactClick(contact)}
                className="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
              >
                <div className="flex items-center gap-4">
                  {/* Avatar */}
                  <div className="relative flex-shrink-0">
                    <div
                      className="w-12 h-12 rounded-full flex items-center justify-center text-white font-medium"
                      style={{ backgroundColor: stringToColor(contact.name || contact.phone_number) }}
                    >
                      {contact.avatar_url ? (
                        <Image
                          src={getMediaUrl(contact.avatar_url)}
                          alt={contact.name || contact.phone_number}
                          width={48}
                          height={48}
                          className="w-12 h-12 rounded-full object-cover"
                          unoptimized
                          onError={(e) => {
                            // Fallback to initials if image fails to load
                            const target = e.target as HTMLImageElement;
                            target.style.display = 'none';
                            const parent = target.parentElement;
                            if (parent) {
                              const initials = getInitials(contact.name || contact.phone_number);
                              if (!parent.textContent || parent.textContent.trim() === '') {
                                parent.textContent = initials;
                              }
                            }
                          }}
                        />
                      ) : (
                        getInitials(contact.name || contact.phone_number)
                      )}
                    </div>
                  </div>

                  {/* Contact Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <h3 className="font-medium text-gray-900 truncate">
                        {contact.name || contact.phone_number}
                      </h3>
                      {contact.source && (
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${getSourceBadgeColor(contact.source)}`}
                        >
                          {getSourceLabel(contact.source)}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-sm text-gray-500 mb-1">
                      <span>{formatPhoneNumber(contact.phone_number)}</span>
                      {contact.email && (
                        <span className="truncate">{contact.email}</span>
                      )}
                    </div>
                    {/* Tags and Lists */}
                    {(contact.tags && contact.tags.length > 0) || (contact.list_ids && contact.list_ids.length > 0) ? (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {contact.tags && contact.tags.map((tag, index) => (
                          <span
                            key={`tag-${index}`}
                            className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded-full"
                          >
                            #{tag}
                          </span>
                        ))}
                        {contact.list_ids && contact.list_ids.map((listId) => (
                          <span
                            key={`list-${listId}`}
                            className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded-full"
                            title={getListName(listId)}
                          >
                            {getListName(listId)}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </div>

                  {/* Status indicator */}
                  <div className="flex-shrink-0">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        contact.status === 'active' ? 'bg-green-500' : 'bg-gray-300'
                      }`}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="bg-white border-t border-gray-200 p-4 flex items-center justify-between">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}

          {/* Contact Info Panel */}
          {showContactInfo && selectedContact && (
            <ContactInfo
              conversation={null}
              contact={selectedContact}
              isOpen={showContactInfo}
              onClose={() => {
                setShowContactInfo(false);
                setSelectedContact(null);
              }}
              onNavigateToWhatsApp={(contactId) => {
                // Navigate to WhatsApp chat and select this contact's conversation
                setShowContactInfo(false);
                if (typeof window !== 'undefined') {
                  window.dispatchEvent(new CustomEvent('navigateToWhatsApp', { detail: { contactId } }));
                }
              }}
            />
          )}
        </>
      )}
    </div>
  );
};

export default ContactsList;
