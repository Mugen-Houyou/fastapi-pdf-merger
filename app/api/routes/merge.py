import json
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.dependencies.security import ApiKeyDependency
from app.services.pdf_merger import PdfMergerService

router = APIRouter(tags=["merge"])


@router.post("/merge", response_class=StreamingResponse, dependencies=[ApiKeyDependency])
async def merge_pdf(
    files: List[UploadFile] = File(..., description="Upload PDF files in desired order."),
    ranges: Optional[str] = Form(
        None, description='JSON list of page ranges per file, e.g. ["1-3,5",""]'
    ),
    output_name: Optional[str] = Form("merged.pdf"),
) -> StreamingResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    for upload in files:
        if not upload.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"Not a PDF: {upload.filename}")

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

    merger = PdfMergerService()
    await merger.append_files(files, per_file_ranges)
    return merger.export(output_name)
