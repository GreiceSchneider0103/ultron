import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./ultron.db"
    
    # Mercado Livre
    ML_ACCESS_TOKEN: str = ""
    
    # Magalu (Sandbox / Operacional)
    MAGALU_CLIENT_ID: str = ""
    MAGALU_CLIENT_SECRET: str = ""
    MAGALU_ACCESS_TOKEN: str = ""
    MAGALU_CHANNEL_ID: str = "5f62650a-0039-4d65-9b96-266d498c03bd" # Sandbox Default
    MAGALU_SANDBOX: bool = True
    
    # System
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()