import asyncio
import io
import json
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.dependencies.security import ApiKeyDependency
from app.services.pdf_merger import PdfMergerService

router = APIRouter(tags=["merge"])


@dataclass
class JobState:
    job_id: str
    output_name: str
    status: str = "queued"
    total_pages: int = 0
    processed_pages: int = 0
    percent: float = 0.0
    error: Optional[str] = None
    result: Optional[bytes] = None
    listeners: set[asyncio.Queue[str]] = field(default_factory=set)

    def snapshot(self) -> Dict[str, object]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "total_pages": self.total_pages,
            "processed_pages": self.processed_pages,
            "percent": self.percent,
            "error": self.error,
            "has_result": self.result is not None,
            "output_name": self.output_name,
        }

    def register_listener(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1)
        self.listeners.add(queue)
        return queue

    def unregister_listener(self, queue: asyncio.Queue[str]) -> None:
        self.listeners.discard(queue)


jobs: Dict[str, JobState] = {}


async def _broadcast(job: JobState) -> None:
    if not job.listeners:
        return
    payload = json.dumps(job.snapshot())
    for queue in list(job.listeners):
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:  # pragma: no cover - defensive
            try:
                _ = queue.get_nowait()
            except asyncio.QueueEmpty:  # pragma: no cover - defensive
                pass
            queue.put_nowait(payload)


def _get_job(job_id: str) -> JobState:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/merge", dependencies=[ApiKeyDependency])
async def merge_pdf(
    files: List[UploadFile] = File(..., description="Upload PDF files in desired order."),
    ranges: Optional[str] = Form(
        None, description='JSON list of page ranges per file, e.g. ["1-3,5",""]'
    ),
    output_name: Optional[str] = Form("merged.pdf"),
) -> JSONResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    buffered_files: list[tuple[str, bytes]] = []
    try:
        for index, upload in enumerate(files):
            filename = upload.filename or f"upload-{index + 1}.pdf"
            if not filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail=f"Not a PDF: {filename}")

            try:
                data = await upload.read()
            except Exception as exc:  # pragma: no cover - defensive
                raise HTTPException(
                    status_code=400, detail=f"Failed to read '{filename}': {exc}"
                ) from exc

            buffered_files.append((filename, data))
    finally:
        for upload in files:
            try:
                await upload.close()
            except Exception:  # pragma: no cover - defensive
                pass

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

    finalized_name = PdfMergerService._finalize_name(output_name)
    job_id = uuid.uuid4().hex
    job = JobState(job_id=job_id, output_name=finalized_name)
    jobs[job_id] = job

    async def _run_job() -> None:
        merger = PdfMergerService()

        async def progress_callback(processed: int, total: int, _filename: str | None) -> None:
            job.total_pages = total
            job.processed_pages = processed
            job.percent = round((processed / total * 100) if total else 0.0, 2)
            await _broadcast(job)

        try:
            job.status = "running"
            await _broadcast(job)
            await merger.append_files(buffered_files, per_file_ranges, progress_callback)
            job.result = merger.to_bytes()
            job.status = "completed"
            job.processed_pages = job.total_pages
            job.percent = 100.0
            await _broadcast(job)
        except HTTPException as exc:
            job.status = "error"
            job.error = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            await _broadcast(job)
        except Exception as exc:  # pragma: no cover - defensive
            job.status = "error"
            job.error = str(exc)
            await _broadcast(job)

    asyncio.create_task(_run_job())

    return JSONResponse({"job_id": job_id, "output_name": finalized_name})


@router.get("/merge/{job_id}", dependencies=[ApiKeyDependency])
async def get_job_status(job_id: str) -> JSONResponse:
    job = _get_job(job_id)
    return JSONResponse(job.snapshot())


@router.get("/merge/{job_id}/events", dependencies=[ApiKeyDependency])
async def stream_job_status(job_id: str) -> StreamingResponse:
    job = _get_job(job_id)

    async def event_stream():
        queue = job.register_listener()
        try:
            initial_payload = json.dumps(job.snapshot())
            yield f"data: {initial_payload}\n\n"
            if job.status in {"completed", "error"}:
                return

            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
                if job.status in {"completed", "error"}:
                    return
        finally:
            job.unregister_listener(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/merge/{job_id}/result", response_class=StreamingResponse, dependencies=[ApiKeyDependency])
async def download_job_result(job_id: str) -> StreamingResponse:
    job = _get_job(job_id)
    if job.status != "completed" or job.result is None:
        raise HTTPException(status_code=404, detail="Result not ready")

    buffer = io.BytesIO(job.result)
    headers = {"Content-Disposition": f'attachment; filename="{job.output_name}"'}
    return StreamingResponse(buffer, media_type="application/pdf", headers=headers)
