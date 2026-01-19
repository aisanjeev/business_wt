import { format, formatDistanceToNow, isToday, isYesterday, parseISO } from 'date-fns';

/**
 * Format a date string for message timestamps
 * Shows time for today, "Yesterday" for yesterday, or full date otherwise
 */
export function formatMessageTime(dateString: string): string {
  try {
    const date = parseISO(dateString);
    
    if (isToday(date)) {
      return format(date, 'h:mm a');
    }
    
    if (isYesterday(date)) {
      return `Yesterday ${format(date, 'h:mm a')}`;
    }
    
    return format(date, 'MMM d, h:mm a');
  } catch {
    return dateString;
  }
}

/**
 * Format a date for conversation list preview
 * Shows relative time for recent, or date for older
 */
export function formatConversationTime(dateString: string): string {
  try {
    const date = parseISO(dateString);
    
    if (isToday(date)) {
      return format(date, 'h:mm a');
    }
    
    if (isYesterday(date)) {
      return 'Yesterday';
    }
    
    return format(date, 'MMM d');
  } catch {
    return dateString;
  }
}

/**
 * Format relative time (e.g., "5 minutes ago")
 */
export function formatRelativeTime(dateString: string): string {
  try {
    const date = parseISO(dateString);
    return formatDistanceToNow(date, { addSuffix: true });
  } catch {
    return dateString;
  }
}

/**
 * Format phone number for display
 * Adds country code formatting if present
 */
export function formatPhoneNumber(phone: string): string {
  if (!phone) return '';
  
  // Remove all non-numeric characters except leading +
  const cleaned = phone.replace(/[^\d+]/g, '');
  
  // If starts with country code, format accordingly
  if (cleaned.startsWith('+')) {
    const digits = cleaned.substring(1);
    if (digits.length === 11 && digits.startsWith('1')) {
      // US number: +1 (xxx) xxx-xxxx
      return `+1 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
    }
    if (digits.length === 12 && digits.startsWith('91')) {
      // India number: +91 xxxxx-xxxxx
      return `+91 ${digits.slice(2, 7)}-${digits.slice(7)}`;
    }
  }
  
  // Default: return as-is with + prefix if not present
  return cleaned.startsWith('+') ? cleaned : `+${cleaned}`;
}

/**
 * Truncate text with ellipsis
 */
export function truncateText(text: string, maxLength: number = 50): string {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}

/**
 * Get initials from a name for avatar
 */
export function getInitials(name: string): string {
  if (!name) return '?';
  
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) {
    return parts[0].charAt(0).toUpperCase();
  }
  
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

/**
 * Generate a consistent color based on a string (e.g., for avatar backgrounds)
 */
export function stringToColor(str: string): string {
  if (!str) return '#6366f1'; // Default indigo
  
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  
  const colors = [
    '#ef4444', // red
    '#f97316', // orange
    '#eab308', // yellow
    '#22c55e', // green
    '#14b8a6', // teal
    '#3b82f6', // blue
    '#6366f1', // indigo
    '#8b5cf6', // violet
    '#ec4899', // pink
  ];
  
  return colors[Math.abs(hash) % colors.length];
}

/**
 * Check if a contact is considered "online" based on recent inbound message activity
 * A contact is considered online if their last inbound message was within the threshold
 * 
 * @param lastMessageAt - ISO timestamp of last message
 * @param lastMessageSenderType - "inbound" or "outbound" 
 * @param thresholdMinutes - Minutes threshold for considering someone online (default: 5)
 * @returns true if contact appears online
 */
export function isContactOnline(
  lastMessageAt: string | null | undefined,
  lastMessageSenderType: string | null | undefined,
  thresholdMinutes: number = 5
): boolean {
  // If no last message, not online
  if (!lastMessageAt) return false;
  
  // Only consider inbound messages (messages FROM the contact)
  // Outbound messages (messages TO the contact) don't indicate they're online
  if (lastMessageSenderType !== 'inbound') return false;
  
  try {
    const lastMessageDate = parseISO(lastMessageAt);
    const now = new Date();
    const diffMinutes = (now.getTime() - lastMessageDate.getTime()) / (1000 * 60);
    
    // Contact is "online" if last inbound message was within threshold
    return diffMinutes <= thresholdMinutes;
  } catch {
    return false;
  }
}