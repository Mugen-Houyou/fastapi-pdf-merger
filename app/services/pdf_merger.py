from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Iterable, Optional

from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from anyio import to_thread
from pypdf import PdfReader, PdfWriter

from app.core.concurrency import get_pdf_merge_limiter
from app.utils.page_ranges import parse_page_ranges


class PdfMergerService:
    """Handle PDF merging logic."""

    def __init__(self) -> None:
        self.writer = PdfWriter()

    @dataclass
    class _Payload:
        filename: str
        data: bytes
        ranges: str

    async def append_files(self, files: Iterable[UploadFile], ranges: list[str]) -> None:
        payloads: list[PdfMergerService._Payload] = []
        for index, upload in enumerate(files):
            data = await upload.read()
            if len(data) == 0:
                raise HTTPException(status_code=400, detail=f"Empty file: {upload.filename}")

            wanted_ranges = ranges[index] if index < len(ranges) else ""
            payloads.append(
                PdfMergerService._Payload(
                    filename=upload.filename or "<unnamed>",
                    data=data,
                    ranges=wanted_ranges or "",
                )
            )

        await to_thread.run_sync(
            self._process_payloads, payloads, limiter=get_pdf_merge_limiter()
        )

    def _process_payloads(self, payloads: list[_Payload]) -> None:
        for payload in payloads:
            try:
                pdf = PdfReader(io.BytesIO(payload.data))
            except Exception as exc:  # pragma: no cover - defensive
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to read '{payload.filename}': {exc}",
                ) from exc

            if pdf.is_encrypted:
                raise HTTPException(
                    status_code=400,
                    detail=f"Encrypted PDF not supported: {payload.filename}",
                )

            indices = parse_page_ranges(payload.ranges, len(pdf.pages))
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
