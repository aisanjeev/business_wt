"""Contact import service for bulk contact import from files."""

import csv
import json
from typing import Any, Dict, List, Optional, Tuple
from io import BytesIO

import httpx
from openpyxl import load_workbook

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ContactImportError(Exception):
    """Custom exception for contact import errors."""
    
    def __init__(self, message: str, row_number: Optional[int] = None):
        self.message = message
        self.row_number = row_number
        super().__init__(self.message)


class ContactImporter:
    """Service for importing contacts from files."""
    
    def __init__(self):
        """Initialize contact importer."""
        pass
    
    async def parse_csv(self, file_content: bytes) -> List[Dict[str, Any]]:
        """Parse CSV file content.
        
        Args:
            file_content: CSV file content as bytes.
        
        Returns:
            List of contact dictionaries.
        
        Raises:
            ContactImportError: If parsing fails.
        """
        try:
            content_str = file_content.decode('utf-8-sig')  # Handle BOM
            csv_reader = csv.DictReader(content_str.splitlines())
            
            contacts = []
            for row in csv_reader:
                contacts.append(row)
            
            logger.info(f"Parsed {len(contacts)} contacts from CSV")
            return contacts
            
        except Exception as e:
            logger.error(f"CSV parsing error: {e}")
            raise ContactImportError(f"Failed to parse CSV: {str(e)}")
    
    async def parse_excel(self, file_content: bytes) -> List[Dict[str, Any]]:
        """Parse Excel file content.
        
        Args:
            file_content: Excel file content as bytes.
        
        Returns:
            List of contact dictionaries.
        
        Raises:
            ContactImportError: If parsing fails.
        """
        try:
            workbook = load_workbook(filename=BytesIO(file_content), data_only=True)
            worksheet = workbook.active
            
            # Get headers from first row
            headers = []
            for cell in worksheet[1]:
                headers.append(str(cell.value).strip() if cell.value else "")
            
            # Parse rows
            contacts = []
            for row in worksheet.iter_rows(min_row=2, values_only=False):
                contact = {}
                for idx, cell in enumerate(row):
                    if idx < len(headers) and headers[idx]:
                        contact[headers[idx]] = str(cell.value).strip() if cell.value else ""
                if contact:
                    contacts.append(contact)
            
            logger.info(f"Parsed {len(contacts)} contacts from Excel")
            return contacts
            
        except Exception as e:
            logger.error(f"Excel parsing error: {e}")
            raise ContactImportError(f"Failed to parse Excel: {str(e)}")
    
    async def parse_json(self, file_content: bytes) -> List[Dict[str, Any]]:
        """Parse JSON file content.
        
        Args:
            file_content: JSON file content as bytes.
        
        Returns:
            List of contact dictionaries.
        
        Raises:
            ContactImportError: If parsing fails.
        """
        try:
            content_str = file_content.decode('utf-8')
            data = json.loads(content_str)
            
            # Handle both array and object formats
            if isinstance(data, list):
                contacts = data
            elif isinstance(data, dict) and "contacts" in data:
                contacts = data["contacts"]
            else:
                contacts = [data]
            
            logger.info(f"Parsed {len(contacts)} contacts from JSON")
            return contacts
            
        except Exception as e:
            logger.error(f"JSON parsing error: {e}")
            raise ContactImportError(f"Failed to parse JSON: {str(e)}")
    
    def normalize_phone_number(self, phone: str) -> Optional[str]:
        """Normalize phone number format.
        
        Args:
            phone: Raw phone number string.
        
        Returns:
            Normalized phone number or None if invalid.
        """
        if not phone:
            return None
        
        # Remove common separators
        phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        # Remove leading + if present
        if phone.startswith("+"):
            phone = phone[1:]
        
        # Remove country code prefix (simplified - adjust as needed)
        # This is a basic normalization - you may need more sophisticated logic
        
        # Validate: should be 10-15 digits
        if not phone.isdigit() or len(phone) < 10 or len(phone) > 15:
            return None
        
        return phone
    
    def validate_contact(self, contact: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate a contact record.
        
        Args:
            contact: Contact dictionary.
        
        Returns:
            Tuple of (is_valid, error_message).
        """
        # Try to find phone number in various field names
        phone = None
        for field in ["phone", "phone_number", "mobile", "mobile_number", "tel", "number"]:
            if field in contact:
                phone = contact[field]
                break
        
        # Also try uppercase variants
        if not phone:
            for field in ["Phone", "PhoneNumber", "Mobile", "MobileNumber", "Tel", "Number"]:
                if field in contact:
                    phone = contact[field]
                    break
        
        if not phone:
            return False, "Phone number not found in contact record"
        
        normalized_phone = self.normalize_phone_number(str(phone))
        if not normalized_phone:
            return False, f"Invalid phone number format: {phone}"
        
        return True, None
    
    def extract_contact_data(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize contact data from import record.
        
        Args:
            contact: Contact dictionary from file.
        
        Returns:
            Normalized contact data dictionary.
        """
        # Try to find name in various field names
        name = None
        for field in ["name", "full_name", "contact_name", "customer_name"]:
            if field in contact and contact[field]:
                name = str(contact[field]).strip()
                break
        
        # Try uppercase variants
        if not name:
            for field in ["Name", "FullName", "ContactName", "CustomerName"]:
                if field in contact and contact[field]:
                    name = str(contact[field]).strip()
                    break
        
        # Extract phone number
        phone = None
        for field in ["phone", "phone_number", "mobile", "mobile_number", "tel", "number"]:
            if field in contact:
                phone = self.normalize_phone_number(str(contact[field]))
                if phone:
                    break
        
        # Try uppercase variants
        if not phone:
            for field in ["Phone", "PhoneNumber", "Mobile", "MobileNumber", "Tel", "Number"]:
                if field in contact:
                    phone = self.normalize_phone_number(str(contact[field]))
                    if phone:
                        break
        
        # Extract email
        email = None
        for field in ["email", "email_address", "e_mail"]:
            if field in contact and contact[field]:
                email = str(contact[field]).strip()
                break
        
        return {
            "phone_number": phone,
            "name": name,
            "email": email if email else None,
        }


# Singleton instance
contact_importer = ContactImporter()
