from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Iterable, Literal, Optional, Tuple, cast

from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from anyio import to_thread
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf._page import PageObject
from PIL import Image, ImageOps, UnidentifiedImageError

try:  # pragma: no cover - optional dependency import guard
    import pikepdf  # type: ignore
except ImportError:  # pragma: no cover - optional dependency import guard
    pikepdf = None  # type: ignore[assignment]

from app.core.concurrency import get_pdf_merge_limiter
from app.utils.page_ranges import parse_page_ranges


PaperSize = Literal["A4", "Letter"]
Orientation = Literal["portrait", "landscape"]
Rotation = Literal[90, 180, 270]
FitMode = Literal["letterbox", "crop"]


@dataclass(frozen=True)
class LayoutOptions:
    paper_size: Optional[PaperSize] = None
    orientation: Optional[Orientation] = None
    rotation: Optional[Rotation] = None
    fit_mode: Optional[FitMode] = None


_PAGE_DIMENSIONS: dict[tuple[PaperSize, Orientation], Tuple[float, float]] = {
    ("A4", "portrait"): (595.2755905511812, 841.8897637795277),
    ("A4", "landscape"): (841.8897637795277, 595.2755905511812),
    ("Letter", "portrait"): (612.0, 792.0),
    ("Letter", "landscape"): (792.0, 612.0),
}

_DEFAULT_FIT_MODE: FitMode = "letterbox"


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
        content_type: str
        options: LayoutOptions

    _IMAGE_DEFAULT_OPTIONS = LayoutOptions(
        paper_size="A4",
        orientation="portrait",
        fit_mode="letterbox",
    )

    @staticmethod
    def _normalize_options(raw: Optional[dict[str, str]]) -> LayoutOptions:
        if not raw:
            return LayoutOptions()

        paper_lookup = {"a4": "A4", "letter": "Letter"}
        orientation_lookup = {"portrait": "portrait", "landscape": "landscape"}
        rotation_lookup: dict[str, Rotation] = {
            "rotate90": 90,
            "rotate180": 180,
            "rotate270": 270,
        }
        fit_lookup = {"letterbox": "letterbox", "crop": "crop"}

        def normalize(value: Optional[str], table: dict[str, str]) -> Optional[str]:
            token = str(value or "").strip().lower()
            if not token or token == "auto":
                return None
            return table.get(token)

        paper = normalize(raw.get("paper_size"), paper_lookup)
        orientation_raw = str(raw.get("orientation", "")).strip().lower()
        orientation: Optional[Orientation]
        rotation: Optional[Rotation]
        if not orientation_raw or orientation_raw == "auto":
            orientation = None
            rotation = None
        elif orientation_raw in orientation_lookup:
            orientation = cast(Optional[Orientation], orientation_lookup[orientation_raw])
            rotation = None
        else:
            orientation = None
            rotation = rotation_lookup.get(orientation_raw)
        fit_mode = normalize(raw.get("fit_mode"), fit_lookup)

        return LayoutOptions(
            paper_size=cast(Optional[PaperSize], paper),
            orientation=cast(Optional[Orientation], orientation),
            rotation=cast(Optional[Rotation], rotation),
            fit_mode=cast(Optional[FitMode], fit_mode),
        )

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
            content_type = (upload.content_type or "").lower()
            payloads.append(
                PdfMergerService._Payload(
                    filename=upload.filename or "<unnamed>",
                    data=data,
                    ranges=wanted_ranges or "",
                    content_type=content_type,
                    options=self._apply_default_layout(
                        self._normalize_options(raw_options),
                        upload.filename or "",
                        content_type,
                    ),
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
                pdf = self._load_document(payload)
            except HTTPException:
                raise
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
    def _is_supported_image_source(filename: str, content_type: str) -> bool:
        lowered_name = filename.lower()
        lowered_type = content_type.lower()
        if lowered_name.endswith((".jpg", ".jpeg", ".png")):
            return True
        image_types = {
            "image/jpeg",
            "image/pjpeg",
            "image/jpg",
            "image/png",
            "image/x-png",
        }
        if lowered_type in image_types:
            return True
        if lowered_type.startswith("image/"):
            return any(token in lowered_type for token in ("jpeg", "jpg", "png"))
        return False

    def _load_document(self, payload: _Payload) -> PdfReader:
        filename = payload.filename
        lowered_name = filename.lower()
        content_type = payload.content_type
        if lowered_name.endswith(".pdf") or content_type == "application/pdf":
            return PdfReader(io.BytesIO(payload.data))
        if self._is_supported_image_source(filename, content_type):
            pdf_bytes = self._convert_image_to_pdf(payload.data, payload.filename)
            return PdfReader(io.BytesIO(pdf_bytes))

        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {payload.filename}",
        )

    def _apply_default_layout(
        self,
        options: LayoutOptions,
        filename: str,
        content_type: str,
    ) -> LayoutOptions:
        defaults = (
            self._IMAGE_DEFAULT_OPTIONS
            if self._is_supported_image_source(filename, content_type)
            else LayoutOptions()
        )

        paper_size = cast(Optional[PaperSize], options.paper_size or defaults.paper_size)
        fit_mode = cast(Optional[FitMode], options.fit_mode or defaults.fit_mode)
        rotation = options.rotation
        orientation: Optional[Orientation]
        if options.orientation is not None or rotation is not None:
            orientation = options.orientation
        else:
            orientation = cast(Optional[Orientation], defaults.orientation)

        return LayoutOptions(
            paper_size=paper_size,
            orientation=orientation,
            rotation=rotation,
            fit_mode=fit_mode,
        )

    @staticmethod
    def _convert_image_to_pdf(data: bytes, filename: str) -> bytes:
        try:
            with Image.open(io.BytesIO(data)) as image:
                image = ImageOps.exif_transpose(image)
                prepared = PdfMergerService._prepare_image(image).copy()
                output = io.BytesIO()
                prepared.save(output, format="PDF")
        except UnidentifiedImageError as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid image file: {filename}"
            ) from exc
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process image '{filename}': {exc}",
            ) from exc

        output.seek(0)
        return output.read()

    @staticmethod
    def _prepare_image(image: Image.Image) -> Image.Image:
        if image.mode in ("RGB", "L"):
            return image.convert("RGB")

        if image.mode in ("RGBA", "LA") or (
            image.mode == "P" and "transparency" in image.info
        ):
            rgba_image = image.convert("RGBA")
            background = Image.new("RGBA", rgba_image.size, (255, 255, 255, 255))
            background.alpha_composite(rgba_image)
            return background.convert("RGB")

        return image.convert("RGB")

    @staticmethod
    def _infer_orientation(page: PageObject) -> Orientation:
        mediabox = page.mediabox
        original_width = float(mediabox.width or 0)
        original_height = float(mediabox.height or 0)
        if original_width <= 0 or original_height <= 0:
            return "portrait"
        return "landscape" if original_width >= original_height else "portrait"

    def _target_dimensions(self, paper_size: PaperSize, orientation: Orientation) -> Tuple[float, float]:
        return _PAGE_DIMENSIONS[(paper_size, orientation)]

    def _render_page(self, page: PageObject, options: LayoutOptions) -> PageObject:
        working_page = page
        rotation = options.rotation
        if rotation:
            working_page = self._apply_rotation(working_page, rotation)

        if options.paper_size is None:
            return working_page

        paper_size = cast(PaperSize, options.paper_size)
        orientation = cast(
            Orientation,
            options.orientation or self._infer_orientation(working_page),
        )
        fit_mode = cast(FitMode, options.fit_mode or _DEFAULT_FIT_MODE)
        target_width, target_height = self._target_dimensions(paper_size, orientation)
        new_page = PageObject.create_blank_page(width=target_width, height=target_height)

        applied_rotation = self._page_rotation(working_page)
        if applied_rotation:
            working_page = cast(PageObject, working_page.rotate(-applied_rotation))

        mediabox = working_page.mediabox
        original_width = float(mediabox.width or target_width)
        original_height = float(mediabox.height or target_height)

        if original_width <= 0 or original_height <= 0:
            original_width = target_width
            original_height = target_height

        if applied_rotation in (90, 270):
            content_width = original_height
            content_height = original_width
        else:
            content_width = original_width
            content_height = original_height

        if fit_mode == "crop":
            scale_factor = max(target_width / content_width, target_height / content_height)
        else:
            scale_factor = min(target_width / content_width, target_height / content_height)

        if not (scale_factor and scale_factor > 0):
            scale_factor = 1.0

        scaled_width = content_width * scale_factor
        scaled_height = content_height * scale_factor

        offset_x = (target_width - scaled_width) / 2
        offset_y = (target_height - scaled_height) / 2

        transform = (
            Transformation()
            .translate(-float(mediabox.left), -float(mediabox.bottom))
        )

        if applied_rotation:
            transform = transform.rotate(applied_rotation).translate(
                *self._rotation_translation(applied_rotation, original_width, original_height)
            )

        transform = (
            transform
            .scale(scale_factor)
            .translate(offset_x, offset_y)
        )
        new_page.merge_transformed_page(working_page, transform, expand=False)
        return new_page

    @staticmethod
    def _apply_rotation(page: PageObject, rotation: Rotation) -> PageObject:
        try:
            rotated = page.rotate(rotation)  # type: ignore[attr-defined]
            if rotated is not None:
                return cast(PageObject, rotated)
        except AttributeError:
            pass

        for method_name in ("rotate_clockwise", "rotateClockwise"):
            rotate_method = getattr(page, method_name, None)
            if callable(rotate_method):
                result = rotate_method(rotation)
                if isinstance(result, PageObject):
                    return result
                return page

        return page

    @staticmethod
    def _page_rotation(page: PageObject) -> int:
        try:
            value = int(page.get("/Rotate", 0))
        except (TypeError, ValueError):
            return 0
        value %= 360
        if value in (90, 180, 270):
            return value
        return 0

    @staticmethod
    def _rotation_translation(
        rotation: int, width: float, height: float
    ) -> Tuple[float, float]:
        if rotation == 90:
            return (height, 0.0)
        if rotation == 180:
            return (width, height)
        if rotation == 270:
            return (0.0, width)
        return (0.0, 0.0)

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
