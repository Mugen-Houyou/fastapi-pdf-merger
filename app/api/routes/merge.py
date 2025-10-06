import json
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.dependencies.security import ApiKeyDependency
from app.services.pdf_merger import PdfMergerService

router = APIRouter(tags=["merge"])


@router.post("/merge", response_class=StreamingResponse, dependencies=[ApiKeyDependency])
async def merge_pdf(
    files: List[UploadFile] = File(
        ..., description="Upload PDF, JPG, or PNG files in desired order."
    ),
    ranges: Optional[str] = Form(
        None, description='JSON list of page ranges per file, e.g. ["1-3,5",""]'
    ),
    options: Optional[str] = Form(
        None,
        description=(
            "JSON list of per-file layout options. Each object may contain "
            "'paper_size' (A4|Letter|auto), 'orientation' "
            "(portrait|landscape|rotate90|rotate180|rotate270|auto), "
            "and 'fit_mode' (letterbox|crop|auto)."
        ),
    ),
    output_name: Optional[str] = Form("merged.pdf"),
    engine: Literal["pypdf", "pikepdf"] = Form(
        "pypdf", description="PDF processing backend: 'pypdf' (default) or 'pikepdf'."
    ),
) -> StreamingResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    allowed_types = {
        "application/pdf",
        "image/jpeg",
        "image/pjpeg",
        "image/jpg",
        "image/png",
        "image/x-png",
    }
    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png"}
    for upload in files:
        filename = upload.filename or ""
        extension = Path(filename).suffix.lower()
        content_type = (upload.content_type or "").lower()
        if extension not in allowed_extensions and content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {upload.filename}",
            )

    per_file_ranges: list[str] = []
    if ranges:
        try:
            parsed = json.loads(ranges)
            if not isinstance(parsed, list):
                raise ValueError("ranges must be a JSON list of strings.")
            per_file_ranges = [value if isinstance(value, str) else "" for value in parsed]
        except Exception as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=400, detail=f"Invalid ranges JSON: {exc}") from exc

    while len(per_file_ranges) < len(files):
        per_file_ranges.append("")

    per_file_options: list[dict[str, str]] = []
    if options:
        try:
            parsed_options = json.loads(options)
            if not isinstance(parsed_options, list):
                raise ValueError("options must be a JSON list of objects.")
            for raw in parsed_options:
                if isinstance(raw, dict):
                    per_file_options.append({
                        "paper_size": str(raw.get("paper_size", "")),
                        "orientation": str(raw.get("orientation", "")),
                        "fit_mode": str(raw.get("fit_mode", "")),
                    })
                else:
                    per_file_options.append({})
        except Exception as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=400, detail=f"Invalid options JSON: {exc}") from exc

    while len(per_file_options) < len(files):
        per_file_options.append({})

    merger = PdfMergerService(engine=engine)
    await merger.append_files(files, per_file_ranges, per_file_options)
    return merger.export(output_name)
