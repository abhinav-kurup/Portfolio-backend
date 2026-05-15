from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_admin_key(api_key: str = Security(api_key_header)):
    """
    Dependency to validate the admin API key from the X-API-Key header.
    """
    if api_key == settings.ADMIN_API_KEY:
        return api_key
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials. Please provide a valid X-API-Key header."
    )
