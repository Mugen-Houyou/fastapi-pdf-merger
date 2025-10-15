from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_class=PlainTextResponse)
async def health() -> str:
    return "ok"
