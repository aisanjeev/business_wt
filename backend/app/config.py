"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server Configuration
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    host: str = "0.0.0.0"
    port: int = 8000

    # Database Configuration
    database_type: Literal["sqlite", "mysql"] = "sqlite"
    database_url: str = "sqlite+aiosqlite:///./whatsapp_chat.db"

    # Database Pool Settings (for MySQL)
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 3600
    db_echo: bool = False

    # Meta WhatsApp API
    whatsapp_phone_number_id: str = ""
    whatsapp_business_account_id: str = ""
    whatsapp_api_token: str = ""
    webhook_verify_token: str = ""
    whatsapp_api_version: str = "v18.0"
    
    # Meta OAuth (for customer account connections)
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_oauth_redirect_uri: str = ""
    
    # Encryption
    encryption_key: str = "change_this_in_production_32_chars"  # Must be 32 bytes for AES-256
    
    # Meta Cost Calculation (per message type)
    meta_cost_per_text_message: float = 0.005  # $0.005 per text message (example)
    meta_cost_per_template_message: float = 0.005  # $0.005 per template message
    meta_cost_per_media_message: float = 0.010  # $0.010 per media message (example)

    # JWT Authentication
    jwt_secret: str = "change_this_in_production"
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 86400  # 24 hours in seconds

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8000"
    
    # Azure Blob Storage
    azure_storage_connection_string: str = ""
    azure_storage_container_name: str = "techpath-ai-saas"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list) -> str:
        """Parse CORS origins from string or list."""
        if isinstance(v, list):
            return ",".join(v)
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        return self.database_type == "sqlite"

    @property
    def is_mysql(self) -> bool:
        """Check if using MySQL database."""
        return self.database_type == "mysql"

    @property
    def whatsapp_api_base_url(self) -> str:
        """Get the WhatsApp API base URL."""
        return f"https://graph.facebook.com/{self.whatsapp_api_version}"

    @property
    def whatsapp_messages_url(self) -> str:
        """Get the WhatsApp messages API URL."""
        return f"{self.whatsapp_api_base_url}/{self.whatsapp_phone_number_id}/messages"

    def get_database_url(self, async_mode: bool = True) -> str:
        """Get the appropriate database URL based on database type and mode.
        
        Args:
            async_mode: If True, returns async-compatible URL.
                       For SQLite: sqlite+aiosqlite
                       For MySQL: mysql+aiomysql (async) or mysql+pymysql (sync)
        
        Returns:
            Database URL string.
        """
        url = self.database_url
        
        if self.is_sqlite:
            if async_mode and "aiosqlite" not in url:
                url = url.replace("sqlite://", "sqlite+aiosqlite://")
            elif not async_mode and "aiosqlite" in url:
                url = url.replace("sqlite+aiosqlite://", "sqlite://")
        elif self.is_mysql:
            # Handle MySQL async/sync driver conversion
            if async_mode:
                # Convert to aiomysql for async mode
                if "pymysql" in url:
                    url = url.replace("mysql+pymysql", "mysql+aiomysql")
                elif "mysql://" in url and "aiomysql" not in url:
                    url = url.replace("mysql://", "mysql+aiomysql://")
            else:
                # Convert to pymysql for sync mode
                if "aiomysql" in url:
                    url = url.replace("mysql+aiomysql", "mysql+pymysql")
        
        return url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
