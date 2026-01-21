"""Phone number normalization utilities."""

import re
from typing import Optional


def normalize_phone_number(phone_number: str) -> str:
    """Normalize phone number to a standard format.
    
    Rules:
    - Remove all spaces, dashes, and parentheses
    - If number starts with 0, remove it
    - If number is 10 digits and starts with 6-9, assume it's Indian and add +91
    - If number already has country code (starts with +), keep it as is
    - Otherwise, assume it's Indian and add +91
    
    Examples:
        "8299708052" -> "+918299708052"
        "+1554545464" -> "+1554545464"
        "08299708052" -> "+918299708052"
        "+918299708052" -> "+918299708052"
        "82997-08052" -> "+918299708052"
    
    Args:
        phone_number: Raw phone number string.
    
    Returns:
        Normalized phone number with country code.
    """
    if not phone_number:
        return phone_number
    
    # Remove all spaces, dashes, parentheses, and other non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone_number.strip())
    
    # If already has country code (starts with +), return as is
    if cleaned.startswith('+'):
        return cleaned
    
    # Remove leading 0 if present (common in Indian numbers)
    if cleaned.startswith('0'):
        cleaned = cleaned[1:]
    
    # If it's 10 digits and starts with 6-9, it's likely an Indian mobile number
    if len(cleaned) == 10 and cleaned[0] in '6789':
        return f"+91{cleaned}"
    
    # If it's 11 digits and starts with 91, it's already Indian with country code
    if len(cleaned) == 11 and cleaned.startswith('91'):
        return f"+{cleaned}"
    
    # If it's 12 digits and starts with 91, it's already Indian with country code
    if len(cleaned) == 12 and cleaned.startswith('91'):
        return f"+{cleaned}"
    
    # For other cases, assume it's Indian if it's 10 digits
    if len(cleaned) == 10:
        return f"+91{cleaned}"
    
    # If it's already longer, assume it has country code and add +
    if len(cleaned) > 10:
        return f"+{cleaned}"
    
    # Default: assume Indian number
    return f"+91{cleaned}"


def get_phone_number_variants(phone_number: str) -> list[str]:
    """Get all possible variants of a phone number for searching.
    
    This helps find contacts even if they were stored in different formats.
    
    Args:
        phone_number: Normalized phone number.
    
    Returns:
        List of possible phone number variants.
    """
    normalized = normalize_phone_number(phone_number)
    variants = [normalized]
    
    # If it's an Indian number (+91...), add variants without country code
    if normalized.startswith('+91'):
        number_without_code = normalized[3:]  # Remove +91
        variants.append(number_without_code)
        variants.append(f"0{number_without_code}")  # With leading 0
        variants.append(f"91{number_without_code}")  # Without +
    
    return variants
