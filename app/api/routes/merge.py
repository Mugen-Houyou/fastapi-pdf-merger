import asyncio
import io
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
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
    current_file: Optional[str] = None
    revision: int = 0
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def _bump_revision(self) -> None:
        self.revision += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def mark_running(self) -> None:
        self.status = "running"
        self.error = None
        self._bump_revision()

    def mark_completed(self, result: bytes) -> None:
        self.result = result
        self.status = "completed"
        if self.total_pages and self.processed_pages < self.total_pages:
            self.processed_pages = self.total_pages
        if self.total_pages:
            self.percent = 100.0
        self.current_file = None
        self.error = None
        self._bump_revision()

    def mark_error(self, message: str) -> None:
        self.status = "error"
        self.error = message
        self.current_file = None
        self._bump_revision()

    def update_progress(
        self, processed: int, total: int, current_file: Optional[str]
    ) -> None:
        self.total_pages = total
        self.processed_pages = processed
        if current_file is not None:
            self.current_file = current_file
        elif processed >= total:
            self.current_file = None
        self.percent = round((processed / total * 100) if total else 0.0, 2)
        self._bump_revision()

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
            "current_file": self.current_file,
            "revision": self.revision,
            "updated_at": self.updated_at,
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

        async def progress_callback(
            processed: int, total: int, filename: str | None
        ) -> None:
            job.update_progress(processed, total, filename)
            await _broadcast(job)

        try:
            job.mark_running()
            await _broadcast(job)
            await merger.append_files(buffered_files, per_file_ranges, progress_callback)
            result_bytes = merger.to_bytes()
            job.mark_completed(result_bytes)
            await _broadcast(job)
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            job.mark_error(detail)
            await _broadcast(job)
        except Exception as exc:  # pragma: no cover - defensive
            job.mark_error(str(exc))
            await _broadcast(job)

    asyncio.create_task(_run_job())

    return JSONResponse({"job_id": job_id, "output_name": finalized_name})


@router.get("/merge/{job_id}", dependencies=[ApiKeyDependency])
async def get_job_status(
    job_id: str,
    since: Optional[int] = Query(default=None, ge=0),
    wait: float = Query(default=0.0, ge=0.0, le=30.0),
) -> JSONResponse:
    job = _get_job(job_id)

    should_wait = (
        since is not None
        and job.revision <= since
        and wait > 0
        and job.status not in {"completed", "error"}
    )

    if should_wait:
        queue = job.register_listener()
        try:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=wait)
            except asyncio.TimeoutError:
                return JSONResponse(job.snapshot())
        finally:
            job.unregister_listener(queue)

        try:
            payload = json.loads(data)
        except json.JSONDecodeError:  # pragma: no cover - defensive
            payload = job.snapshot()
        return JSONResponse(payload)

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
