from fastapi import Depends, Header, HTTPException

from app.core.config import settings


async def verify_api_key(x_api_key: str | None = Header(default=None, convert_underscores=False)) -> None:
    """Validate the optional API key header when a key is configured."""

    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


ApiKeyDependency = Depends(verify_api_key)
