from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
from anyio import to_thread
from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.core.concurrency import get_pdf_merge_limiter
from app.utils.page_ranges import parse_page_ranges


class PdfToImagesService:
    """Convert PDF pages to images (JPG) and package them as a ZIP file."""

    def __init__(self, dpi: int = 200, quality: int = 85) -> None:
        """
        Initialize the PDF to images service.

        Args:
            dpi: Resolution for rendering PDF pages (default: 200)
            quality: JPG quality from 1-100 (default: 85)
        """
        if dpi < 72 or dpi > 600:
            raise HTTPException(status_code=400, detail="DPI must be between 72 and 600")
        if quality < 1 or quality > 100:
            raise HTTPException(status_code=400, detail="Quality must be between 1 and 100")

        self.dpi = dpi
        self.quality = quality

    async def convert_pdf_to_images(
        self,
        file: UploadFile,
        page_range: str = "",
    ) -> StreamingResponse:
        """
        Convert PDF to images and return as a ZIP file.

        Args:
            file: The uploaded PDF file
            page_range: Page range specification (e.g., "1-3,5,7-9")

        Returns:
            StreamingResponse containing a ZIP file with JPG images
        """
        # Read the uploaded file
        data = await file.read()
        if len(data) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        # Validate file type
        filename = file.filename or "document.pdf"
        if not filename.lower().endswith(".pdf") and file.content_type != "application/pdf":
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported for conversion to images"
            )

        # Process in background thread
        zip_buffer = await to_thread.run_sync(
            self._process_pdf,
            data,
            filename,
            page_range,
            limiter=get_pdf_merge_limiter(),
        )

        # Prepare output filename
        base_name = Path(filename).stem
        output_name = f"{base_name}_images.zip"

        # Return as streaming response
        headers = {"Content-Disposition": f'attachment; filename="{output_name}"'}
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers=headers,
        )

    def _process_pdf(
        self,
        data: bytes,
        filename: str,
        page_range: str,
    ) -> io.BytesIO:
        """
        Process PDF and convert pages to images.

        Args:
            data: PDF file bytes
            filename: Original filename
            page_range: Page range specification

        Returns:
            BytesIO buffer containing the ZIP file
        """
        try:
            # Open PDF document
            pdf_document = fitz.open(stream=data, filetype="pdf")
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to open PDF file '{filename}': {exc}"
            ) from exc

        try:
            # Parse page ranges
            total_pages = len(pdf_document)
            if total_pages == 0:
                raise HTTPException(status_code=400, detail="PDF has no pages")

            page_indices = parse_page_ranges(page_range, total_pages)
            if not page_indices:
                raise HTTPException(status_code=400, detail="No pages selected")

            # Create ZIP file in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                base_name = Path(filename).stem

                # Convert each page to image
                for idx, page_number in enumerate(page_indices, start=1):
                    try:
                        page = pdf_document[page_number]

                        # Render page to image
                        # Calculate zoom based on DPI (72 is the default DPI)
                        zoom = self.dpi / 72.0
                        mat = fitz.Matrix(zoom, zoom)
                        pix = page.get_pixmap(matrix=mat, alpha=False)

                        # Convert to JPG bytes
                        img_bytes = pix.tobytes("jpeg", jpg_quality=self.quality)

                        # Add to ZIP with sequential naming
                        image_name = f"{base_name}_page_{idx:04d}.jpg"
                        zip_file.writestr(image_name, img_bytes)

                    except Exception as exc:  # pragma: no cover - defensive
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to convert page {page_number + 1}: {exc}"
                        ) from exc

            zip_buffer.seek(0)
            return zip_buffer

        finally:
            pdf_document.close()
