from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Iterable, Literal, Optional, Tuple, cast

from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from anyio import to_thread
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf._page import PageObject

try:  # pragma: no cover - optional dependency import guard
    import pikepdf  # type: ignore
except ImportError:  # pragma: no cover - optional dependency import guard
    pikepdf = None  # type: ignore[assignment]

from app.core.concurrency import get_pdf_merge_limiter
from app.utils.page_ranges import parse_page_ranges


PaperSize = Literal["A4", "Letter"]
Orientation = Literal["portrait", "landscape"]
FitMode = Literal["letterbox", "crop"]


@dataclass(frozen=True)
class LayoutOptions:
    paper_size: PaperSize = "A4"
    orientation: Orientation = "portrait"
    fit_mode: FitMode = "letterbox"


_PAGE_DIMENSIONS: dict[tuple[PaperSize, Orientation], Tuple[float, float]] = {
    ("A4", "portrait"): (595.2755905511812, 841.8897637795277),
    ("A4", "landscape"): (841.8897637795277, 595.2755905511812),
    ("Letter", "portrait"): (612.0, 792.0),
    ("Letter", "landscape"): (792.0, 612.0),
}

_DEFAULT_LAYOUT = LayoutOptions()


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
        self._pages: list[PageObject] = []

    @dataclass
    class _Payload:
        filename: str
        data: bytes
        ranges: str
        options: LayoutOptions

    @staticmethod
    def _normalize_options(raw: Optional[dict[str, str]]) -> LayoutOptions:
        if not raw:
            return LayoutOptions()

        paper_lookup = {"a4": "A4", "letter": "Letter"}
        orientation_lookup = {"portrait": "portrait", "landscape": "landscape"}
        fit_lookup = {"letterbox": "letterbox", "crop": "crop"}

        paper = paper_lookup.get(str(raw.get("paper_size", "")).strip().lower(), _DEFAULT_LAYOUT.paper_size)
        orientation = orientation_lookup.get(
            str(raw.get("orientation", "")).strip().lower(), _DEFAULT_LAYOUT.orientation
        )
        fit_mode = fit_lookup.get(str(raw.get("fit_mode", "")).strip().lower(), _DEFAULT_LAYOUT.fit_mode)

        return LayoutOptions(paper_size=cast(PaperSize, paper), orientation=cast(Orientation, orientation), fit_mode=cast(FitMode, fit_mode))

    async def append_files(
        self,
        files: Iterable[UploadFile],
        ranges: list[str],
        options: Optional[list[dict[str, str]]] = None,
    ) -> None:
        payloads: list[PdfMergerService._Payload] = []
        options = options or []
        for index, upload in enumerate(files):
            data = await upload.read()
            if len(data) == 0:
                raise HTTPException(status_code=400, detail=f"Empty file: {upload.filename}")

            wanted_ranges = ranges[index] if index < len(ranges) else ""
            raw_options = options[index] if index < len(options) else None
            payloads.append(
                PdfMergerService._Payload(
                    filename=upload.filename or "<unnamed>",
                    data=data,
                    ranges=wanted_ranges or "",
                    options=self._normalize_options(raw_options),
                )
            )

        prepared_pages = await to_thread.run_sync(
            self._process_payloads, payloads, limiter=get_pdf_merge_limiter()
        )
        self._pages.extend(prepared_pages)

    def _process_payloads(self, payloads: list[_Payload]) -> list[PageObject]:
        pages: list[PageObject] = []
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
                page = cast(PageObject, pdf.pages[page_index])
                pages.append(self._render_page(page, payload.options))
        return pages

    @staticmethod
    def _target_dimensions(options: LayoutOptions) -> Tuple[float, float]:
        return _PAGE_DIMENSIONS[(options.paper_size, options.orientation)]

    def _render_page(self, page: PageObject, options: LayoutOptions) -> PageObject:
        target_width, target_height = self._target_dimensions(options)
        new_page = PageObject.create_blank_page(width=target_width, height=target_height)

        mediabox = page.mediabox
        original_width = float(mediabox.width or target_width)
        original_height = float(mediabox.height or target_height)

        if original_width <= 0 or original_height <= 0:
            original_width = target_width
            original_height = target_height

        if options.fit_mode == "crop":
            scale_factor = max(target_width / original_width, target_height / original_height)
        else:
            scale_factor = min(target_width / original_width, target_height / original_height)

        if not (scale_factor and scale_factor > 0):
            scale_factor = 1.0

        scaled_width = original_width * scale_factor
        scaled_height = original_height * scale_factor

        offset_x = (target_width - scaled_width) / 2
        offset_y = (target_height - scaled_height) / 2

        transform = (
            Transformation()
            .translate(-float(mediabox.left), -float(mediabox.bottom))
            .scale(scale_factor)
            .translate(offset_x, offset_y)
        )
        new_page.merge_transformed_page(page, transform, expand=False)
        return new_page

    def export(self, output_name: Optional[str]) -> StreamingResponse:
        writer = PdfWriter()
        for page in self._pages:
            writer.add_page(page)

        buffer = io.BytesIO()
        writer.write(buffer)
        buffer.seek(0)

        if self.engine == "pikepdf" and pikepdf is not None:
            with pikepdf.open(buffer) as pdf:
                buffer = io.BytesIO()
                pdf.save(buffer)
            buffer.seek(0)

        final_name = output_name or "merged.pdf"
        if not final_name.lower().endswith(".pdf"):
            final_name += ".pdf"

        headers = {"Content-Disposition": f'attachment; filename="{final_name}"'}
        return StreamingResponse(buffer, media_type="application/pdf", headers=headers)
