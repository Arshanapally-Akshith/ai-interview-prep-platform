from supabase import create_client, Client
from app.core.config import settings
import structlog

logger = structlog.get_logger(__name__)

def get_supabase_client() -> Client:
    """Returns a Supabase client instance."""
    if not settings.supabase_url or not settings.supabase_key:
        logger.warning("Supabase credentials not configured in environment.")
    
    # We might want to handle this better in a real app, maybe raising an error if missing
    return create_client(settings.supabase_url or "http://localhost", settings.supabase_key or "dummy")

# For dependency injection in FastAPI
def get_db() -> Client:
    return get_supabase_client()
