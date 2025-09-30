from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Iterable, Literal, Optional, cast

from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from anyio import to_thread
from pypdf import PdfReader, PdfWriter

try:  # pragma: no cover - optional dependency import guard
    import pikepdf  # type: ignore
except ImportError:  # pragma: no cover - optional dependency import guard
    pikepdf = None  # type: ignore[assignment]

from app.core.concurrency import get_pdf_merge_limiter
from app.utils.page_ranges import parse_page_ranges


class PdfMergerService:
    """Handle PDF merging logic."""

    def __init__(self, engine: Literal["pypdf", "pikepdf"] = "pypdf") -> None:
        if engine not in {"pypdf", "pikepdf"}:
            raise HTTPException(status_code=400, detail=f"Unsupported engine: {engine}")

        if engine == "pikepdf":
            if pikepdf is None:
                raise HTTPException(
                    status_code=500,
                    detail="pikepdf backend is not available on this server.",
                )
            self.engine = engine
            self.writer = pikepdf.Pdf.new()
        else:
            self.engine = "pypdf"
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
        if self.engine == "pikepdf":
            self._process_payloads_with_pikepdf(payloads)
        else:
            self._process_payloads_with_pypdf(payloads)

    def _process_payloads_with_pypdf(self, payloads: list[_Payload]) -> None:
        writer = cast(PdfWriter, self.writer)
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
                writer.add_page(pdf.pages[page_index])

    def _process_payloads_with_pikepdf(self, payloads: list[_Payload]) -> None:
        if pikepdf is None:  # pragma: no cover - defensive
            raise HTTPException(
                status_code=500,
                detail="pikepdf backend is not available on this server.",
            )

        writer = cast("pikepdf.Pdf", self.writer)

        for payload in payloads:
            try:
                with pikepdf.open(io.BytesIO(payload.data)) as pdf:
                    if pdf.is_encrypted:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Encrypted PDF not supported: {payload.filename}",
                        )

                    indices = parse_page_ranges(payload.ranges, len(pdf.pages))
                    for page_index in indices:
                        writer.pages.append(pdf.pages[page_index])
            except HTTPException:
                raise
            except Exception as exc:  # pragma: no cover - defensive
                if pikepdf is not None and isinstance(exc, pikepdf.PasswordError):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Encrypted PDF not supported: {payload.filename}",
                    ) from exc
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to read '{payload.filename}': {exc}",
                ) from exc

    def export(self, output_name: Optional[str]) -> StreamingResponse:
        buffer = io.BytesIO()
        if self.engine == "pikepdf":
            cast("pikepdf.Pdf", self.writer).save(buffer)
        else:
            cast(PdfWriter, self.writer).write(buffer)
        buffer.seek(0)

        final_name = output_name or "merged.pdf"
        if not final_name.lower().endswith(".pdf"):
            final_name += ".pdf"

        headers = {"Content-Disposition": f'attachment; filename="{final_name}"'}
        return StreamingResponse(buffer, media_type="application/pdf", headers=headers)
