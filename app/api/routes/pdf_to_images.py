# app/api/routes/pdf_to_images.py
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.dependencies.security import ApiKeyDependency
from app.services.pdf_to_images import PdfToImagesService

router = APIRouter(prefix="/pdf-merger", tags=["pdf-to-images"])


@router.post(
    "/pdf-to-images",
    response_class=StreamingResponse,
    dependencies=[ApiKeyDependency]
)
async def convert_pdf_to_images(
    file: UploadFile = File(..., description="Upload a single PDF file to convert to images"),
    page_range: Optional[str] = Form(
        "",
        description='Page range specification (e.g., "1-3,5,7-9"). Leave empty for all pages.'
    ),
    dpi: Optional[int] = Form(
        200,
        description="Resolution for rendering PDF pages (72-600). Higher values produce better quality but larger files.",
        ge=72,
        le=600
    ),
    quality: Optional[int] = Form(
        85,
        description="JPG quality from 1-100. Higher values produce better quality but larger files.",
        ge=1,
        le=100
    ),
) -> StreamingResponse:
    """
    Convert PDF pages to JPG images and return as a ZIP file.

    - **file**: The PDF file to convert
    - **page_range**: Pages to convert (e.g., "1-3,5" means pages 1,2,3,5). Empty = all pages
    - **dpi**: Image resolution (default: 200)
    - **quality**: JPG quality 1-100 (default: 85)

    Returns a ZIP file containing the converted images.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    # Validate file type
    filename = file.filename.lower()
    content_type = (file.content_type or "").lower()

    if not filename.endswith(".pdf") and content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported. Please upload a PDF file."
        )

    # Create service and process
    service = PdfToImagesService(dpi=dpi or 200, quality=quality or 85)
    return await service.convert_pdf_to_images(file, page_range or "")
