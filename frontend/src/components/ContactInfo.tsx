'use client';

import React, { useState, useEffect } from 'react';
import Image from 'next/image';
import { Contact, Conversation, ContactList } from '@/types';
import { formatPhoneNumber, formatRelativeTime, getInitials, stringToColor } from '@/utils/formatters';
import { getMediaUrl, contactApi, contactListApi } from '@/services/api';

interface ContactInfoProps {
  conversation: Conversation | null;
  contact?: Contact;
  isOpen: boolean;
  onClose: () => void;
  onNavigateToWhatsApp?: (contactId: number) => void;
}

const ContactInfo: React.FC<ContactInfoProps> = ({
  conversation,
  contact,
  isOpen,
  onClose,
  onNavigateToWhatsApp,
}) => {
  const [allLists, setAllLists] = useState<ContactList[]>([]);
  const [contactLists, setContactLists] = useState<ContactList[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [newTag, setNewTag] = useState('');
  const [selectedListId, setSelectedListId] = useState<number | null>(null);

  useEffect(() => {
    if (isOpen && contact) {
      loadLists();
      setTags(contact.tags || []);
    }
  }, [isOpen, contact]);

  const loadLists = async () => {
    try {
      setLoading(true);
      const listsResponse = await contactListApi.getLists(1, 100);
      if (listsResponse.success && listsResponse.data) {
        setAllLists(listsResponse.data.items);
        
        // Get lists for this contact
        if (contact?.list_ids) {
          const contactListItems = listsResponse.data.items.filter(list => 
            contact.list_ids?.includes(list.id)
          );
          setContactLists(contactListItems);
        }
      }
    } catch (error) {
      console.error('Failed to load lists:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddTag = async () => {
    if (!newTag.trim() || !contact) return;
    
    const updatedTags = [...tags, newTag.trim()];
    setTags(updatedTags);
    setNewTag('');
    
    try {
      await contactApi.updateContactTags(contact.id, updatedTags);
    } catch (error) {
      console.error('Failed to update tags:', error);
      setTags(tags); // Revert on error
    }
  };

  const handleRemoveTag = async (tagToRemove: string) => {
    if (!contact) return;
    
    const updatedTags = tags.filter(t => t !== tagToRemove);
    setTags(updatedTags);
    
    try {
      await contactApi.updateContactTags(contact.id, updatedTags);
    } catch (error) {
      console.error('Failed to update tags:', error);
      setTags(tags); // Revert on error
    }
  };

  const handleAddToList = async () => {
    if (!selectedListId || !contact) return;
    
    try {
      await contactListApi.addContactToList(selectedListId, contact.id);
      await loadLists(); // Refresh lists
      setSelectedListId(null);
    } catch (error) {
      console.error('Failed to add contact to list:', error);
    }
  };

  const handleRemoveFromList = async (listId: number) => {
    if (!contact) return;
    
    try {
      await contactListApi.removeContactFromList(listId, contact.id);
      await loadLists(); // Refresh lists
    } catch (error) {
      console.error('Failed to remove contact from list:', error);
    }
  };

  const handleWhatsAppClick = () => {
    if (contact && onNavigateToWhatsApp) {
      onNavigateToWhatsApp(contact.id);
      onClose();
    }
  };

  if (!isOpen) return null;

  const contactName = contact?.name || 'Unknown Contact';
  const contactPhone = contact?.phone_number || '';

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Modal */}
      <div
        className={`fixed inset-0 z-50 flex items-center justify-center p-4 transition-opacity ${
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
      >
        <div
          className="bg-white rounded-lg shadow-xl w-full max-w-md max-h-[90vh] flex flex-col transform transition-transform"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="h-14 px-4 flex items-center justify-between border-b border-gray-200 rounded-t-lg">
            <h2 className="font-semibold text-gray-900">Contact Info</h2>
            <div className="flex items-center gap-2">
              {/* WhatsApp Icon */}
              {contact && onNavigateToWhatsApp && (
                <button
                  onClick={handleWhatsAppClick}
                  className="p-2 hover:bg-green-50 rounded-full transition-colors"
                  title="Open in WhatsApp Chat"
                >
                  <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                  </svg>
                </button>
              )}
              <button
                onClick={onClose}
                className="p-1 hover:bg-gray-100 rounded-full transition-colors"
              >
                <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto">
                {/* Profile section */}
            <div className="p-6 text-center border-b border-gray-100">
          <div
            className="w-24 h-24 rounded-full flex items-center justify-center text-white text-3xl font-bold mx-auto mb-4 relative"
            style={{ backgroundColor: stringToColor(contactName) }}
          >
            {contact?.avatar_url ? (
              <Image
                src={getMediaUrl(contact.avatar_url)}
                alt={contactName}
                width={96}
                height={96}
                className="w-24 h-24 rounded-full object-cover"
                unoptimized
                onError={(e) => {
                  // Fallback to initials if image fails to load
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                  const parent = target.parentElement;
                  if (parent) {
                    const initials = getInitials(contactName);
                    if (!parent.textContent || parent.textContent.trim() === '') {
                      parent.textContent = initials;
                    }
                  }
                }}
              />
            ) : (
              getInitials(contactName)
            )}
          </div>
          <h3 className="text-xl font-semibold text-gray-900">{contactName}</h3>
          <p className="text-gray-500">{formatPhoneNumber(contactPhone)}</p>
          {contact?.source && (
            <span
              className={`inline-block mt-2 px-3 py-1 rounded-full text-xs font-medium ${
                contact.source === 'imported'
                  ? 'bg-blue-100 text-blue-700'
                  : contact.source === 'chat'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-700'
              }`}
            >
              {contact.source === 'imported'
                ? 'Imported Contact'
                : contact.source === 'chat'
                ? 'Chat Contact'
                : 'Manually Added'}
            </span>
            )}
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

          {/* Source/Category */}
          {contact?.source && (
            <div className="flex items-center gap-3 py-3 border-b border-gray-100">
              <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                </svg>
              </div>
              <div>
                <p className="text-sm text-gray-500">Category</p>
                <p className="font-medium text-gray-900 capitalize">
                  {contact.source === 'imported'
                    ? 'Imported'
                    : contact.source === 'chat'
                    ? 'Chat Contact'
                    : 'Manually Added'}
                </p>
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
          {conversation && (
            <div className="p-4 border-t border-gray-100">
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Conversation Info
              </h4>

              {/* Tags */}
              {conversation.tags && Object.keys(conversation.tags).length > 0 && (
                <div className="mb-4">
                  <p className="text-sm text-gray-500 mb-2">Tags</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(conversation.tags).map(([key, value], index) => (
                      <span
                        key={index}
                        className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full"
                      >
                        {typeof value === 'string' ? value : key}
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
          )}

          {/* Tags Section */}
          <div className="p-4 border-t border-gray-100">
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Tags
            </h4>
            
            {/* Tags Display */}
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3">
                {tags.map((tag, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full"
                  >
                    {tag}
                    <button
                      onClick={() => handleRemoveTag(tag)}
                      className="hover:text-green-900"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
            
            {/* Add Tag Input */}
            <div className="flex gap-2">
              <input
                type="text"
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleAddTag();
                  }
                }}
                placeholder="Add tag..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              />
              <button
                onClick={handleAddTag}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium"
              >
                Add
              </button>
            </div>
          </div>

          {/* Lists Section */}
          <div className="p-4 border-t border-gray-100">
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Lists
            </h4>
            
            {/* Contact's Lists */}
            {contactLists.length > 0 && (
              <div className="mb-3 space-y-2">
                {contactLists.map((list) => (
                  <div
                    key={list.id}
                    className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg"
                  >
                    <span className="text-sm font-medium text-gray-900">{list.name}</span>
                    <button
                      onClick={() => handleRemoveFromList(list.id)}
                      className="text-red-600 hover:text-red-800 text-sm"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
            
            {/* Add to List */}
            <div className="flex gap-2">
              <select
                value={selectedListId || ''}
                onChange={(e) => setSelectedListId(e.target.value ? parseInt(e.target.value) : null)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              >
                <option value="">Select a list...</option>
                {allLists
                  .filter(list => !contactLists.find(cl => cl.id === list.id))
                  .map((list) => (
                    <option key={list.id} value={list.id}>
                      {list.name}
                    </option>
                  ))}
              </select>
              <button
                onClick={handleAddToList}
                disabled={!selectedListId}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-sm font-medium"
              >
                Add
              </button>
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
      </div>
    </>
  );
};

export default ContactInfo;
