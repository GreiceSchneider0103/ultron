import logging
from supabase import create_client, Client
from api.src.config import settings

logger = logging.getLogger(__name__)

def get_supabase() -> Client:
    """Retorna o cliente Supabase autenticado"""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("Supabase credentials not set. Persistence might fail.")
        return None
        
    return create_client(
        settings.SUPABASE_URL, 
        settings.SUPABASE_SERVICE_ROLE_KEY
    )