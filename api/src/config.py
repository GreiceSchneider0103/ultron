"""
config.py â€” ConfiguraÃ§Ã£o ÃšNICA do projeto Ultron.
COLOQUE EM: api/src/config.py

APAGUE: api/src/orchestrator/config.py  (o duplicado)
Todo import de config em qualquer mÃ³dulo deve usar o pacote `api.src`.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

_API_DIR = Path(__file__).resolve().parents[1]
_API_ENV_FILE = _API_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_API_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",          # ignora variÃ¡veis extras no .env sem errar
    )

    # â”€â”€ Database local (SQLite â€” desenvolvimento) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    DATABASE_URL: str = "sqlite:///./ultron.db"

    # â”€â”€ Supabase (produÃ§Ã£o) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    DEFAULT_WORKSPACE_ID: str = "00000000-0000-0000-0000-000000000000"

    # â”€â”€ Mercado Livre â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ML_ACCESS_TOKEN: str = ""
    ML_CLIENT_ID: str = ""
    ML_CLIENT_SECRET: str = ""

    # â”€â”€ Magalu â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    MAGALU_CLIENT_ID: str = ""
    MAGALU_CLIENT_SECRET: str = ""
    MAGALU_ACCESS_TOKEN: str = ""
    MAGALU_CHANNEL_ID: str = "5f62650a-0039-4d65-9b96-266d498c03bd"  # Sandbox default
    MAGALU_USE_SANDBOX: bool = True
    MAGALU_BASE_URL: str = "https://api.magalu.com"
    MAGALU_SANDBOX_BASE_URL: str = "https://api-sandbox.magalu.com"
    MAGALU_SCRAPING_DELAY_MS: int = 1500   # delay para scraping (ms)

    # â”€â”€ IA / LLM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    DEFAULT_AI_PROVIDER: str = "openai"     # openai | anthropic | gemini
    DEFAULT_AI_MODEL: str = "gpt-4o"

    # â”€â”€ Redis / Celery â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    REDIS_URL: str = "redis://localhost:6379/0"

    # â”€â”€ App â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000"
    MONITOR_SCHEDULER_ENABLED: bool = True
    MONITOR_SCHEDULER_INTERVAL_MINUTES: int = 10
    MONITOR_ALERT_DEDUPE_HOURS: int = 6
    MONITOR_MAX_LISTINGS_PER_CYCLE: int = 100

    # â”€â”€ Propriedades derivadas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    @property
    def magalu_api_url(self) -> str:
        return self.MAGALU_SANDBOX_BASE_URL if self.MAGALU_USE_SANDBOX else self.MAGALU_BASE_URL

    @property
    def MAGALU_SANDBOX(self) -> bool:
        """Compat alias for legacy code paths."""
        return self.MAGALU_USE_SANDBOX

    @property
    def ml_seller_access_token(self) -> str:
        """Compat alias for legacy connector access."""
        return self.ML_ACCESS_TOKEN

    @property
    def default_ai_provider(self) -> str:
        return self.DEFAULT_AI_PROVIDER

    @property
    def environment(self) -> str:
        return self.ENVIRONMENT

    @property
    def magalu_scraping_delay_ms(self) -> int:
        return self.MAGALU_SCRAPING_DELAY_MS

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def monitor_scheduler_should_run(self) -> bool:
        return self.MONITOR_SCHEDULER_ENABLED and self.ENVIRONMENT in {"development", "internal"}

    def ai_configured(self) -> bool:
        """True se ao menos um provider de IA estÃ¡ configurado."""
        if self.DEFAULT_AI_PROVIDER == "anthropic":
            return bool(self.ANTHROPIC_API_KEY)
        if self.DEFAULT_AI_PROVIDER == "gemini":
            return bool(self.GEMINI_API_KEY)
        return bool(self.OPENAI_API_KEY)

    def check_ai_configured(self) -> bool:
        """Compat method for legacy callers."""
        return self.ai_configured()

    def ml_configured(self) -> bool:
        return bool(self.ML_ACCESS_TOKEN or (self.ML_CLIENT_ID and self.ML_CLIENT_SECRET))

    def check_ml_configured(self) -> bool:
        """Compat method for legacy callers."""
        return self.ml_configured()

    def magalu_configured(self) -> bool:
        return bool(self.MAGALU_ACCESS_TOKEN or self.MAGALU_CLIENT_ID)


@lru_cache
def get_settings() -> Settings:
    return Settings()


# InstÃ¢ncia global para import direto
settings = get_settings()



