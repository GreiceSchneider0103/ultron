import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./ultron.db"
    
    # Supabase
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    DEFAULT_WORKSPACE_ID: str = "00000000-0000-0000-0000-000000000000"
    
    # Mercado Livre
    ML_ACCESS_TOKEN: str = ""
    
    # Magalu (Sandbox / Operacional)
    MAGALU_CLIENT_ID: str = ""
    MAGALU_CLIENT_SECRET: str = ""
    MAGALU_ACCESS_TOKEN: str = ""
    MAGALU_CHANNEL_ID: str = "5f62650a-0039-4d65-9b96-266d498c03bd" # Sandbox Default
    MAGALU_USE_SANDBOX: bool = True
    MAGALU_BASE_URL: str = "https://api.magalu.com"
    MAGALU_SANDBOX_BASE_URL: str = "https://api-sandbox.magalu.com"
    
    # System
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()