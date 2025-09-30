import io
from typing import Iterable, Optional

from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pypdf import PdfReader, PdfWriter

from app.utils.page_ranges import parse_page_ranges


class PdfMergerService:
    """Handle PDF merging logic."""

    def __init__(self) -> None:
        self.writer = PdfWriter()

    async def append_files(self, files: Iterable[UploadFile], ranges: list[str]) -> None:
        for index, upload in enumerate(files):
            data = await upload.read()
            if len(data) == 0:
                raise HTTPException(status_code=400, detail=f"Empty file: {upload.filename}")

            try:
                pdf = PdfReader(io.BytesIO(data))
            except Exception as exc:  # pragma: no cover - defensive
                raise HTTPException(
                    status_code=400, detail=f"Failed to read '{upload.filename}': {exc}"
                ) from exc

            if pdf.is_encrypted:
                raise HTTPException(
                    status_code=400,
                    detail=f"Encrypted PDF not supported: {upload.filename}",
                )

            wanted_ranges = ranges[index] if index < len(ranges) else ""
            indices = parse_page_ranges(wanted_ranges or "", len(pdf.pages))
            for page_index in indices:
                self.writer.add_page(pdf.pages[page_index])

    def export(self, output_name: Optional[str]) -> StreamingResponse:
        buffer = io.BytesIO()
        self.writer.write(buffer)
        buffer.seek(0)

        final_name = output_name or "merged.pdf"
        if not final_name.lower().endswith(".pdf"):
            final_name += ".pdf"

        headers = {"Content-Disposition": f'attachment; filename="{final_name}"'}
        return StreamingResponse(buffer, media_type="application/pdf", headers=headers)
