"""Usage calculator service for tracking API costs."""

from typing import Optional

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class UsageCalculator:
    """Service for calculating API usage costs."""
    
    def __init__(self):
        """Initialize usage calculator."""
        self.cost_per_text = settings.meta_cost_per_text_message
        self.cost_per_template = settings.meta_cost_per_template_message
        self.cost_per_media = settings.meta_cost_per_media_message
    
    def calculate_cost(self, message_type: str) -> float:
        """Calculate cost for a message type.
        
        Args:
            message_type: Message type (text, template, image, document, audio, video).
        
        Returns:
            Estimated cost in USD.
        """
        # Map message types to cost categories
        if message_type in ("text", "location", "contacts"):
            return self.cost_per_text
        elif message_type == "template":
            return self.cost_per_template
        elif message_type in ("image", "document", "audio", "video", "sticker"):
            return self.cost_per_media
        else:
            # Default to text message cost for unknown types
            logger.warning(f"Unknown message type '{message_type}', using text message cost")
            return self.cost_per_text
    
    def format_cost(self, cost: float) -> str:
        """Format cost as string with precision.
        
        Args:
            cost: Cost in USD.
        
        Returns:
            Formatted cost string.
        """
        return f"{cost:.6f}"


# Singleton instance
usage_calculator = UsageCalculator()
