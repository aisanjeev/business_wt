'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Image from 'next/image';
import { contactListApi, contactListFolderApi, getMediaUrl } from '@/services/api';
import { ContactList, ContactListFolder, Contact } from '@/types';
import { formatPhoneNumber, getInitials, stringToColor } from '@/utils/formatters';

const ContactListManager: React.FC = () => {
  const [folders, setFolders] = useState<ContactListFolder[]>([]);
  const [lists, setLists] = useState<ContactList[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFolder, setSelectedFolder] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateFolderModal, setShowCreateFolderModal] = useState(false);
  const [showCreateListModal, setShowCreateListModal] = useState(false);
  const [editingList, setEditingList] = useState<ContactList | null>(null);
  const [editingFolder, setEditingFolder] = useState<ContactListFolder | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Set<number>>(new Set());
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [actionMenuOpen, setActionMenuOpen] = useState<number | null>(null);
  const [moveListMenuOpen, setMoveListMenuOpen] = useState<number | null>(null);
  const [selectedListForContacts, setSelectedListForContacts] = useState<ContactList | null>(null);
  const [listContacts, setListContacts] = useState<Contact[]>([]);
  const [loadingContacts, setLoadingContacts] = useState(false);

  // Close action menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (actionMenuOpen !== null) {
        setActionMenuOpen(null);
      }
    };
    if (actionMenuOpen !== null) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [actionMenuOpen]);

  const loadFolders = useCallback(async () => {
    try {
      const response = await contactListFolderApi.getFolders();
      if (response.success && response.data) {
        setFolders(response.data);
      }
    } catch (err) {
      console.error('Failed to load folders:', err);
    }
  }, []);

  const loadLists = useCallback(async (folderId?: number, search?: string) => {
    try {
      const response = await contactListApi.getLists(1, 100, folderId);
      if (response.success && response.data) {
        let filteredLists = response.data.items;
        
        // Apply search filter
        if (search) {
          const searchLower = search.toLowerCase();
          filteredLists = filteredLists.filter(list => 
            list.name.toLowerCase().includes(searchLower) || 
            list.id.toString().includes(search)
          );
        }
        
        // Sort by creation date
        filteredLists.sort((a, b) => {
          const dateA = new Date(a.created_at).getTime();
          const dateB = new Date(b.created_at).getTime();
          return sortOrder === 'desc' ? dateB - dateA : dateA - dateB;
        });
        
        setLists(filteredLists);
      }
    } catch (err) {
      console.error('Failed to load lists:', err);
    }
  }, [sortOrder]);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        await Promise.all([loadFolders(), loadLists(selectedFolder || undefined, searchQuery)]);
      } catch (err) {
        setError('Failed to load lists and folders');
        console.error('Error loading data:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [loadFolders, loadLists, selectedFolder, searchQuery, sortOrder]);

  // Calculate total lists count (all lists, not filtered)
  const totalListsCount = lists.length;

  // Build folder tree structure
  const buildFolderTree = (folders: ContactListFolder[]): Array<ContactListFolder & { children?: ContactListFolder[]; lists?: ContactList[] }> => {
    const folderMap = new Map<number, ContactListFolder & { children?: ContactListFolder[]; lists?: ContactList[] }>();
    const rootFolders: Array<ContactListFolder & { children?: ContactListFolder[]; lists?: ContactList[] }> = [];

    // First pass: create map
    folders.forEach(folder => {
      folderMap.set(folder.id, { ...folder, children: [], lists: [] });
    });

    // Second pass: build tree
    folders.forEach(folder => {
      const folderNode = folderMap.get(folder.id)!;
      if (folder.parent_folder_id) {
        const parent = folderMap.get(folder.parent_folder_id);
        if (parent) {
          if (!parent.children) parent.children = [];
          parent.children.push(folderNode);
        }
      } else {
        rootFolders.push(folderNode);
      }
    });

    return rootFolders;
  };

  const folderTree = buildFolderTree(folders);

  // Get lists without folders (only when showing all folders)
  const listsWithoutFolders = selectedFolder === null 
    ? lists.filter(list => !list.folder_id)
    : [];

  // Toggle folder expansion
  const toggleFolder = (folderId: number) => {
    setExpandedFolders(prev => {
      const newSet = new Set(prev);
      if (newSet.has(folderId)) {
        newSet.delete(folderId);
      } else {
        newSet.add(folderId);
      }
      return newSet;
    });
  };

  const handleCreateFolder = async (name: string, description?: string, parentFolderId?: number) => {
    try {
      const response = await contactListFolderApi.createFolder({ name, description, parent_folder_id: parentFolderId });
      if (response.success) {
        await loadFolders();
        setShowCreateFolderModal(false);
      }
    } catch (err) {
      console.error('Failed to create folder:', err);
    }
  };

  const handleCreateList = async (name: string, description?: string, folderId?: number, color?: string) => {
    try {
      const response = await contactListApi.createList({ name, description, folder_id: folderId, color });
      if (response.success) {
        await loadLists(selectedFolder || undefined, searchQuery);
        setShowCreateListModal(false);
      }
    } catch (err) {
      console.error('Failed to create list:', err);
    }
  };

  const handleDeleteList = async (listId: number) => {
    if (!confirm('Are you sure you want to delete this list? This will not delete the contacts.')) return;
    
    try {
      const response = await contactListApi.deleteList(listId);
      if (response.success) {
        await loadLists(selectedFolder || undefined, searchQuery);
        setActionMenuOpen(null);
      }
    } catch (err) {
      console.error('Failed to delete list:', err);
    }
  };

  const handleDeleteFolder = async (folderId: number) => {
    if (!confirm('Are you sure you want to delete this folder? Lists in this folder will be moved to root.')) return;
    
    try {
      const response = await contactListFolderApi.deleteFolder(folderId);
      if (response.success) {
        await loadFolders();
        await loadLists(selectedFolder || undefined, searchQuery);
      }
    } catch (err) {
      console.error('Failed to delete folder:', err);
    }
  };

  const handleMoveList = async (listId: number, targetFolderId: number | null) => {
    try {
      const response = await contactListApi.moveList(listId, targetFolderId);
      if (response.success) {
        await loadLists(selectedFolder || undefined, searchQuery);
        setActionMenuOpen(null);
      }
    } catch (err) {
      console.error('Failed to move list:', err);
    }
  };

  const handleViewListContacts = async (list: ContactList) => {
    setSelectedListForContacts(list);
    setLoadingContacts(true);
    try {
      const response = await contactListApi.getListContacts(list.id, 1, 100);
      if (response.success && response.data) {
        setListContacts(response.data.items);
      } else {
        setListContacts([]);
      }
    } catch (err) {
      console.error('Failed to load list contacts:', err);
      setListContacts([]);
    } finally {
      setLoadingContacts(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Filter lists based on selected folder and paginate
  const filteredLists = selectedFolder
    ? lists.filter(list => list.folder_id === selectedFolder)
    : lists;
  
  // Pagination
  const pageSize = 20;
  const startIndex = (page - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedLists = filteredLists.slice(startIndex, endIndex);
  const totalFilteredPages = Math.ceil(filteredLists.length / pageSize);

  if (loading && lists.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center text-red-600">
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex bg-gray-50 h-full">
      {/* Left Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col h-full">
        {/* Folder Dropdown Header */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <button
              onClick={() => setSelectedFolder(null)}
              className={`flex items-center justify-between w-full text-left px-3 py-2 rounded-lg transition-colors ${
                selectedFolder === null
                  ? 'bg-purple-50 text-purple-700 font-medium'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <span>All folders ({totalListsCount} lists)</span>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
        </div>

        {/* Folder Tree */}
        <div className="flex-1 overflow-y-auto p-2">
          {folderTree.map((folder) => {
            const isExpanded = expandedFolders.has(folder.id);
            const isSelected = selectedFolder === folder.id;
            const folderListsCount = lists.filter(l => l.folder_id === folder.id).length;

            return (
              <div key={folder.id} className="mb-1">
                <div
                  className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-purple-50 text-purple-700 font-medium'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                  onClick={() => {
                    setSelectedFolder(folder.id);
                    setPage(1);
                    if (folder.children && folder.children.length > 0) {
                      toggleFolder(folder.id);
                    }
                  }}
                >
                  <span className="flex-1 truncate">{folder.name} ({folderListsCount} lists)</span>
                  {folder.children && folder.children.length > 0 && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleFolder(folder.id);
                      }}
                      className="ml-2 p-1"
                    >
                      <svg
                        className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  )}
                </div>
                {isExpanded && folder.children && folder.children.length > 0 && (
                  <div className="ml-4 mt-1">
                    {folder.children.map((child) => {
                      const childListsCount = lists.filter(l => l.folder_id === child.id).length;
                      const isChildSelected = selectedFolder === child.id;
                      return (
                        <div
                          key={child.id}
                          className={`px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                            isChildSelected
                              ? 'bg-purple-50 text-purple-700 font-medium'
                              : 'text-gray-600 hover:bg-gray-50'
                          }`}
                          onClick={() => {
                            setSelectedFolder(child.id);
                            setPage(1);
                          }}
                        >
                          {child.name} ({childListsCount} lists)
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}

          {/* Lists without folders */}
          {listsWithoutFolders.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase mb-2">
                Lists without folders
              </div>
                  {listsWithoutFolders.map((list) => (
                <div
                  key={list.id}
                  className="px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-lg cursor-pointer truncate"
                  onClick={() => handleViewListContacts(list)}
                >
                  {list.name}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Create Folder Button */}
        <div className="p-4 border-t border-gray-200">
          <button
            onClick={() => setShowCreateFolderModal(true)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm font-medium"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Create a new folder
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Show Contacts View if a list is selected, otherwise show Lists Table */}
        {selectedListForContacts ? (
          <ListContactsView
            list={selectedListForContacts}
            contacts={listContacts}
            loading={loadingContacts}
            onBack={() => {
              setSelectedListForContacts(null);
              setListContacts([]);
            }}
          />
        ) : (
          <>
            {/* Header */}
            <div className="bg-white border-b border-gray-200 p-6">
              <div className="mb-4">
                <h1 className="text-2xl font-bold text-gray-900 mb-2">Lists</h1>
                <p className="text-sm text-gray-600 mb-3">
                  This is where you organize your lists. Create, modify, and manage custom lists for targeted interactions, and keep them in folders for easy navigation.
                </p>
                <div className="flex items-center gap-4 text-sm">
                  <a href="#" className="text-blue-600 hover:text-blue-700 flex items-center gap-1">
                    Get started with Lists and Folders
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                  <a href="#" className="text-blue-600 hover:text-blue-700 flex items-center gap-1">
                    Lists vs Segments
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                </div>
              </div>

              <div className="flex items-center justify-between">
                {/* Search Bar */}
                <div className="flex-1 max-w-md">
                  <div className="relative">
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => {
                        setSearchQuery(e.target.value);
                        setPage(1);
                      }}
                      placeholder="Search a list name or ID"
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

                {/* Create List Button */}
                <button
                  onClick={() => setShowCreateListModal(true)}
                  className="ml-4 flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 font-medium"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Create a list
                </button>
              </div>
            </div>

            {/* Table */}
            <div className="flex-1 overflow-y-auto bg-white">
          {paginatedLists.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p>No lists found. Create your first list to get started.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Folder
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Contacts
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      <button
                        onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
                        className="flex items-center gap-1 hover:text-gray-700"
                      >
                        Creation date
                        <svg
                          className={`w-4 h-4 transition-transform ${sortOrder === 'desc' ? '' : 'rotate-180'}`}
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                        </svg>
                      </button>
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {paginatedLists.map((list) => {
                    const folder = folders.find(f => f.id === list.folder_id);
                    return (
                      <tr 
                        key={list.id} 
                        className="hover:bg-gray-50 cursor-pointer"
                        onClick={() => handleViewListContacts(list)}
                      >
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          #{list.id}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {folder ? folder.name : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {list.contacts_count || 0} {list.contacts_count === 1 ? 'contact' : 'contacts'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDate(list.created_at)}
                        </td>
                        <td 
                          className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium relative"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setActionMenuOpen(actionMenuOpen === list.id ? null : list.id);
                            }}
                            className="text-gray-400 hover:text-gray-600"
                          >
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                              <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                            </svg>
                          </button>
                          {actionMenuOpen === list.id && (
                            <div 
                              className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg z-10 border border-gray-200"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <div className="py-1">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setEditingList(list);
                                    setActionMenuOpen(null);
                                  }}
                                  className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                                >
                                  Edit
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setMoveListMenuOpen(list.id);
                                    setActionMenuOpen(null);
                                  }}
                                  className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                                >
                                  Move to folder
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDeleteList(list.id);
                                  }}
                                  className="block w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-100"
                                >
                                  Delete
                                </button>
                              </div>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Move List Menu */}
        {moveListMenuOpen !== null && (
          <div 
            className="fixed inset-0 z-40"
            onClick={() => setMoveListMenuOpen(null)}
          >
            <div 
              className="absolute right-4 top-1/2 transform -translate-y-1/2 w-64 bg-white rounded-md shadow-lg z-50 border border-gray-200"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-4 border-b border-gray-200">
                <h3 className="text-sm font-medium text-gray-900">Move to folder</h3>
              </div>
              <div className="py-2 max-h-64 overflow-y-auto">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    const list = lists.find(l => l.id === moveListMenuOpen);
                    if (list) {
                      handleMoveList(list.id, null);
                    }
                    setMoveListMenuOpen(null);
                  }}
                  className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  Root (no folder)
                </button>
                {folders.map((folder) => (
                  <button
                    key={folder.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      const list = lists.find(l => l.id === moveListMenuOpen);
                      if (list) {
                        handleMoveList(list.id, folder.id);
                      }
                      setMoveListMenuOpen(null);
                    }}
                    className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    {folder.name}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Pagination */}
        {totalFilteredPages > 1 && (
          <div className="bg-white border-t border-gray-200 p-4 flex items-center justify-between">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <span className="text-sm text-gray-600">
              Page {page} of {totalFilteredPages}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalFilteredPages, p + 1))}
              disabled={page === totalFilteredPages}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        )}
        </>
        )}
      </div>

      {/* Create Folder Modal */}
      {showCreateFolderModal && (
        <CreateFolderModal
          folders={folders}
          onClose={() => setShowCreateFolderModal(false)}
          onCreate={handleCreateFolder}
        />
      )}

      {/* Create List Modal */}
      {showCreateListModal && (
        <CreateListModal
          folders={folders}
          onClose={() => setShowCreateListModal(false)}
          onCreate={handleCreateList}
        />
      )}

      {/* Edit List Modal */}
      {editingList && (
        <EditListModal
          list={editingList}
          folders={folders}
          onClose={() => setEditingList(null)}
          onUpdate={async (updates) => {
            try {
              await contactListApi.updateList(editingList.id, updates);
              await loadLists(selectedFolder || undefined, searchQuery);
              setEditingList(null);
            } catch (err) {
              console.error('Failed to update list:', err);
            }
          }}
        />
      )}

    </div>
  );
};

// Create Folder Modal Component
interface CreateFolderModalProps {
  folders: ContactListFolder[];
  onClose: () => void;
  onCreate: (name: string, description?: string, parentFolderId?: number) => void;
}

const CreateFolderModal: React.FC<CreateFolderModalProps> = ({ folders, onClose, onCreate }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [parentFolderId, setParentFolderId] = useState<number | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onCreate(name.trim(), description.trim() || undefined, parentFolderId || undefined);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Create Folder</h2>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Folder Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description (optional)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              rows={3}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Parent Folder (optional)</label>
            <select
              value={parentFolderId || ''}
              onChange={(e) => setParentFolderId(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="">None (root)</option>
              {folders.map((folder) => (
                <option key={folder.id} value={folder.id}>
                  {folder.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-2 justify-end pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              Create Folder
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Create List Modal Component
interface CreateListModalProps {
  folders: ContactListFolder[];
  onClose: () => void;
  onCreate: (name: string, description?: string, folderId?: number, color?: string) => void;
}

const CreateListModal: React.FC<CreateListModalProps> = ({ folders, onClose, onCreate }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [folderId, setFolderId] = useState<number | null>(null);
  const [color, setColor] = useState('#10b981');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onCreate(name.trim(), description.trim() || undefined, folderId || undefined, color);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Create List</h2>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">List Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description (optional)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              rows={3}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Folder (optional)</label>
            <select
              value={folderId || ''}
              onChange={(e) => setFolderId(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="">None (root)</option>
              {folders.map((folder) => (
                <option key={folder.id} value={folder.id}>
                  {folder.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Color (optional)</label>
            <div className="flex gap-2 items-center">
              <input
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="w-16 h-10 border border-gray-300 rounded cursor-pointer"
              />
              <input
                type="text"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                pattern="^#[0-9A-Fa-f]{6}$"
              />
            </div>
          </div>
          <div className="flex gap-2 justify-end pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              Create List
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Edit List Modal Component
interface EditListModalProps {
  list: ContactList;
  folders: ContactListFolder[];
  onClose: () => void;
  onUpdate: (updates: Partial<ContactList>) => void;
}

const EditListModal: React.FC<EditListModalProps> = ({ list, folders, onClose, onUpdate }) => {
  const [name, setName] = useState(list.name);
  const [description, setDescription] = useState(list.description || '');
  const [folderId, setFolderId] = useState<number | null>(list.folder_id || null);
  const [color, setColor] = useState(list.color || '#10b981');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onUpdate({
      name: name.trim(),
      description: description.trim() || undefined,
      folder_id: folderId || undefined,
      color: color || undefined,
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Edit List</h2>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">List Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description (optional)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
              rows={3}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Folder (optional)</label>
            <select
              value={folderId || ''}
              onChange={(e) => setFolderId(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="">None (root)</option>
              {folders.map((folder) => (
                <option key={folder.id} value={folder.id}>
                  {folder.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Color (optional)</label>
            <div className="flex gap-2 items-center">
              <input
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="w-16 h-10 border border-gray-300 rounded cursor-pointer"
              />
              <input
                type="text"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                pattern="^#[0-9A-Fa-f]{6}$"
              />
            </div>
          </div>
          <div className="flex gap-2 justify-end pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              Update List
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// List Contacts View Component (replaces modal - shows in main content area)
interface ListContactsViewProps {
  list: ContactList;
  contacts: Contact[];
  loading: boolean;
  onBack: () => void;
}

const ListContactsView: React.FC<ListContactsViewProps> = ({ list, contacts, loading, onBack }) => {
  const [allLists, setAllLists] = useState<ContactList[]>([]);

  // Load all lists to display list names in badges
  useEffect(() => {
    const loadLists = async () => {
      try {
        const response = await contactListApi.getLists(1, 100);
        if (response.success && response.data) {
          setAllLists(response.data.items);
        }
      } catch (err) {
        console.error('Failed to load lists:', err);
      }
    };
    loadLists();
  }, []);

  const getListName = (listId: number): string => {
    const foundList = allLists.find(l => l.id === listId);
    return foundList ? foundList.name : `List #${listId}`;
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
  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-gray-50">
      {/* Header with Back Button */}
      <div className="bg-white border-b border-gray-200 p-6">
        <div className="flex items-center gap-4 mb-4">
          <button
            onClick={onBack}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Lists
          </button>
        </div>
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Contacts in "{list.name}"</h2>
          <p className="text-sm text-gray-500 mt-1">
            {contacts.length} {contacts.length === 1 ? 'contact' : 'contacts'}
          </p>
        </div>
      </div>

      {/* Contacts List */}
      <div className="flex-1 overflow-y-auto bg-white p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500" />
            </div>
          ) : contacts.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p>No contacts in this list.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {contacts.map((contact) => (
                <div
                  key={contact.id}
                  className="p-4 hover:bg-gray-50 transition-colors"
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
    </div>
  );
};

export default ContactListManager;
