# app/api/routes/ui.py
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import settings  # 네 config.py에 Settings가 있다고 가정
from app.utils.i18n import detect_locale, get_translations

router = APIRouter(prefix="/pdf-merger", tags=["ui"])
pdf_to_images_router = APIRouter(prefix="", tags=["ui"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """
    메인 업로드/병합 UI 페이지 (Jinja 템플릿 사용)
    """
    locale = detect_locale(request)
    translations = get_translations(locale)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "locale": locale,
            "t": translations["template"],
            "client_translations": translations["client"],
            "current_year": datetime.now().year,
            # 템플릿에 내려줄 기본값/플래그
            "defaults": {
                "output_name": "merged.pdf",
                "paper_size": "auto",
                "orientation": "auto",
                "fit_mode": "auto",
                "engine": "pypdf",
            },
            "feature_flags": {
                "api_key_required": bool(settings.api_key),
            },
            "limits": {
                "total_upload_mb": settings.max_total_upload_mb,
            },
        },
    )


@pdf_to_images_router.get("/pdf-to-images", response_class=HTMLResponse)
async def pdf_to_images(request: Request) -> HTMLResponse:
    """
    PDF to Images conversion UI page
    """
    locale = detect_locale(request)
    translations = get_translations(locale)

    return templates.TemplateResponse(
        "pdf_to_images.html",
        {
            "request": request,
            "locale": locale,
            "t": translations["template"],
            "client_translations": translations["client"],
            "current_year": datetime.now().year,
            "defaults": {
                "dpi": 200,
                "quality": 85,
            },
            "feature_flags": {
                "api_key_required": bool(settings.api_key),
            },
            "limits": {
                "total_upload_mb": settings.max_total_upload_mb,
            },
        },
    )
