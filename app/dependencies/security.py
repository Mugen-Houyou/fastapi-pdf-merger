from fastapi import Depends, Header, HTTPException, Query

from app.core.config import settings


async def verify_api_key(
    x_api_key: str | None = Header(default=None, convert_underscores=False),
    api_key: str | None = Query(default=None),
) -> None:
    """Validate the optional API key header when a key is configured."""

    provided = x_api_key or api_key
    if settings.api_key and provided != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


ApiKeyDependency = Depends(verify_api_key)
