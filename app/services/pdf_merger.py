import io
from typing import Awaitable, Callable, Iterable, Optional

from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pypdf import PdfReader, PdfWriter

from app.utils.page_ranges import parse_page_ranges


class PdfMergerService:
    """Handle PDF merging logic."""

    def __init__(self) -> None:
        self.writer = PdfWriter()

    ProgressCallback = Callable[[int, int, str | None], Awaitable[None]]

    async def append_files(
        self,
        files: Iterable[UploadFile],
        ranges: list[str],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> None:
        processed_pages = 0
        prepared: list[tuple[PdfReader, list[int], str]] = []

        total_pages = 0
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
            total_pages += len(indices)
            prepared.append((pdf, indices, upload.filename))

        if progress_callback is not None:
            await progress_callback(processed_pages, total_pages, None)

        for pdf, indices, filename in prepared:
            for page_index in indices:
                self.writer.add_page(pdf.pages[page_index])
                processed_pages += 1
                if progress_callback is not None:
                    await progress_callback(processed_pages, total_pages, filename)

    def export(self, output_name: Optional[str]) -> StreamingResponse:
        buffer = io.BytesIO()
        self.writer.write(buffer)
        buffer.seek(0)

        final_name = self._finalize_name(output_name)
        headers = {"Content-Disposition": f'attachment; filename="{final_name}"'}
        return StreamingResponse(buffer, media_type="application/pdf", headers=headers)

    def to_bytes(self) -> bytes:
        buffer = io.BytesIO()
        self.writer.write(buffer)
        return buffer.getvalue()

    @staticmethod
    def _finalize_name(output_name: Optional[str]) -> str:
        final_name = output_name or "merged.pdf"
        if not final_name.lower().endswith(".pdf"):
            final_name += ".pdf"
        return final_name
