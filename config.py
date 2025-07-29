"""
Configuration Management for AI PostgreSQL Chatbot

This module handles all configuration settings using Pydantic for validation
and environment variables for security.
"""

import os
from typing import Optional, List
from pathlib import Path
from pydantic import BaseSettings, validator, Field
from pydantic.types import SecretStr


class Settings(BaseSettings):
    """
    Application settings with automatic environment variable loading.
    
    All settings can be overridden via environment variables with the prefix
    'CHATBOT_' (e.g., CHATBOT_DB_HOST=localhost).
    """
    
    # Database Configuration
    db_host: str = Field(default="localhost", description="PostgreSQL host")
    db_port: int = Field(default=5432, description="PostgreSQL port")
    db_name: str = Field(..., description="PostgreSQL database name")
    db_user: str = Field(..., description="PostgreSQL username")
    db_password: SecretStr = Field(..., description="PostgreSQL password")
    db_schema: Optional[str] = Field(default="public", description="Default schema")
    
    # Connection Pool Settings
    db_pool_size: int = Field(default=10, ge=1, le=50, description="Connection pool size")
    db_pool_overflow: int = Field(default=20, ge=0, le=100, description="Connection pool overflow")
    db_pool_timeout: int = Field(default=30, ge=1, le=300, description="Connection timeout in seconds")
    
    # AI/LLM Configuration
    openai_api_key: Optional[SecretStr] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-3.5-turbo", description="OpenAI model to use")
    openai_temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="LLM temperature")
    openai_max_tokens: int = Field(default=1000, ge=1, le=4000, description="Max tokens for response")
    
    # Alternative LLM Support
    huggingface_api_key: Optional[SecretStr] = Field(default=None, description="HuggingFace API key")
    use_local_llm: bool = Field(default=False, description="Use local LLM instead of API")
    local_llm_model: str = Field(default="microsoft/DialoGPT-medium", description="Local LLM model")
    
    # Application Settings
    app_name: str = Field(default="AI PostgreSQL Chatbot", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Security Settings
    max_query_length: int = Field(default=10000, ge=1, le=50000, description="Maximum query length")
    allowed_schemas: List[str] = Field(default=["public"], description="Allowed database schemas")
    blocked_keywords: List[str] = Field(
        default=["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE"],
        description="SQL keywords to block for safety"
    )
    enable_query_validation: bool = Field(default=True, description="Enable SQL query validation")
    
    # Web Interface Settings
    web_host: str = Field(default="localhost", description="Web interface host")
    web_port: int = Field(default=8501, ge=1, le=65535, description="Web interface port")
    web_title: str = Field(default="AI PostgreSQL Chatbot", description="Web interface title")
    
    # Cache Settings
    enable_cache: bool = Field(default=True, description="Enable query result caching")
    cache_ttl: int = Field(default=300, ge=0, le=3600, description="Cache TTL in seconds")
    cache_max_size: int = Field(default=100, ge=1, le=1000, description="Maximum cache entries")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=60, ge=1, le=1000, description="Requests per minute")
    rate_limit_window: int = Field(default=60, ge=1, le=3600, description="Rate limit window in seconds")
    
    # Query Optimization
    query_timeout: int = Field(default=30, ge=1, le=300, description="Query timeout in seconds")
    max_result_rows: int = Field(default=1000, ge=1, le=10000, description="Maximum result rows")
    enable_explain: bool = Field(default=False, description="Enable EXPLAIN for queries")
    
    @validator('db_password', pre=True)
    def validate_db_password(cls, v):
        """Ensure database password is provided."""
        if not v:
            raise ValueError("Database password is required")
        return v
    
    @validator('openai_api_key', 'huggingface_api_key', pre=True)
    def validate_api_keys(cls, v):
        """Convert empty strings to None for API keys."""
        if v == "":
            return None
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @validator('blocked_keywords', pre=True)
    def validate_blocked_keywords(cls, v):
        """Ensure blocked keywords are uppercase."""
        if isinstance(v, list):
            return [keyword.upper() for keyword in v]
        return v
    
    @validator('allowed_schemas', pre=True)
    def validate_allowed_schemas(cls, v):
        """Ensure at least one schema is allowed."""
        if isinstance(v, list) and len(v) == 0:
            raise ValueError("At least one schema must be allowed")
        return v
    
    def get_database_url(self, async_driver: bool = False) -> str:
        """
        Generate database connection URL.
        
        Args:
            async_driver: If True, use asyncpg driver, else use psycopg2
            
        Returns:
            Database connection URL
        """
        driver = "postgresql+asyncpg" if async_driver else "postgresql+psycopg2"
        password = self.db_password.get_secret_value()
        
        return (
            f"{driver}://{self.db_user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    
    def get_openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key as string."""
        if self.openai_api_key:
            return self.openai_api_key.get_secret_value()
        return None
    
    def get_huggingface_api_key(self) -> Optional[str]:
        """Get HuggingFace API key as string."""
        if self.huggingface_api_key:
            return self.huggingface_api_key.get_secret_value()
        return None
    
    def is_query_allowed(self, query: str) -> tuple[bool, str]:
        """
        Check if a query is allowed based on security settings.
        
        Args:
            query: SQL query to validate
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        if not self.enable_query_validation:
            return True, "Validation disabled"
        
        # Check query length
        if len(query) > self.max_query_length:
            return False, f"Query too long (max {self.max_query_length} characters)"
        
        # Check for blocked keywords
        query_upper = query.upper()
        for keyword in self.blocked_keywords:
            if keyword in query_upper:
                return False, f"Blocked keyword detected: {keyword}"
        
        return True, "Query allowed"
    
    def get_connection_params(self) -> dict:
        """Get database connection parameters as dictionary."""
        return {
            "host": self.db_host,
            "port": self.db_port,
            "database": self.db_name,
            "user": self.db_user,
            "password": self.db_password.get_secret_value(),
        }
    
    class Config:
        """Pydantic configuration."""
        env_prefix = "CHATBOT_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        validate_assignment = True


def load_settings(config_file: Optional[str] = None) -> Settings:
    """
    Load application settings with optional config file override.
    
    Args:
        config_file: Path to custom .env file
        
    Returns:
        Configured Settings instance
    """
    if config_file and Path(config_file).exists():
        os.environ["CONFIG_FILE"] = config_file
    
    try:
        settings = Settings()
        
        # Validate essential configuration
        if not settings.get_openai_api_key() and not settings.use_local_llm:
            raise ValueError(
                "Either OpenAI API key must be provided or local LLM must be enabled"
            )
        
        return settings
        
except Exception as e:
        raise RuntimeError(f"Failed to load configuration: {e}")


def create_sample_env_file(file_path: str = ".env.sample") -> None:
    """
    Create a sample .env file with all configuration options.
    
    Args:
        file_path: Path to create the sample file
    """
    sample_content = """# AI PostgreSQL Chatbot Configuration
# Copy this file to .env and fill in your values

# Database Configuration (Required)
CHATBOT_DB_HOST=localhost
CHATBOT_DB_PORT=5432
CHATBOT_DB_NAME=your_database_name
CHATBOT_DB_USER=your_username
CHATBOT_DB_PASSWORD=your_password
CHATBOT_DB_SCHEMA=public

# Database Connection Pool
CHATBOT_DB_POOL_SIZE=10
CHATBOT_DB_POOL_OVERFLOW=20
CHATBOT_DB_POOL_TIMEOUT=30

# AI/LLM Configuration
CHATBOT_OPENAI_API_KEY=your_openai_api_key_here
CHATBOT_OPENAI_MODEL=gpt-3.5-turbo
CHATBOT_OPENAI_TEMPERATURE=0.1
CHATBOT_OPENAI_MAX_TOKENS=1000

# Alternative LLM (Optional)
CHATBOT_HUGGINGFACE_API_KEY=your_huggingface_key
CHATBOT_USE_LOCAL_LLM=false
CHATBOT_LOCAL_LLM_MODEL=microsoft/DialoGPT-medium

# Application Settings
CHATBOT_APP_NAME=AI PostgreSQL Chatbot
CHATBOT_DEBUG_MODE=false
CHATBOT_LOG_LEVEL=INFO

# Security Settings
CHATBOT_MAX_QUERY_LENGTH=10000
CHATBOT_ALLOWED_SCHEMAS=["public"]
CHATBOT_ENABLE_QUERY_VALIDATION=true

# Web Interface
CHATBOT_WEB_HOST=localhost
CHATBOT_WEB_PORT=8501
CHATBOT_WEB_TITLE=AI PostgreSQL Chatbot

# Performance Settings
CHATBOT_ENABLE_CACHE=true
CHATBOT_CACHE_TTL=300
CHATBOT_QUERY_TIMEOUT=30
CHATBOT_MAX_RESULT_ROWS=1000

# Rate Limiting
CHATBOT_RATE_LIMIT_REQUESTS=60
CHATBOT_RATE_LIMIT_WINDOW=60
"""
    
    with open(file_path, "w") as f:
        f.write(sample_content)
    
    print(f"Sample configuration file created: {file_path}")
    print("Copy this file to .env and update with your values.")


if __name__ == "__main__":
    # Create sample .env file when run directly
    create_sample_env_file()
    
    # Test configuration loading
    try:
        settings = load_settings()
        print("✅ Configuration loaded successfully!")
        print(f"Database: {settings.db_host}:{settings.db_port}/{settings.db_name}")
        print(f"OpenAI Model: {settings.openai_model}")
        print(f"Debug Mode: {settings.debug_mode}")
except Exception as e:
        print(f"❌ Configuration error: {e}")
        print("💡 Make sure to create a .env file with your settings.")
