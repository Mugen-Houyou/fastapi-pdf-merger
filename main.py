import io
import os
import re
from typing import List, Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Header, Request
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel
from pypdf import PdfReader, PdfWriter

# ===== 설정 =====
API_KEY = os.getenv("PDF_MERGER_API_KEY")  # 있으면 X-API-KEY 헤더로 검사
MAX_TOTAL_UPLOAD_MB = int(os.getenv("PDF_MERGER_MAX_MB", "200"))  # 총 업로드 제한(대략용)

app = FastAPI(title="Internal PDF Merger", version="1.0.0")


# ===== 간단 업로드 용량 제한(대략) =====
@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    if request.method == "POST" and request.url.path == "/merge":
        # Content-Length 헤더가 있으면 대략 체크
        cl = request.headers.get("content-length")
        if cl and cl.isdigit():
            size_mb = int(cl) / (1024 * 1024)
            if size_mb > MAX_TOTAL_UPLOAD_MB:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Payload too large (> {MAX_TOTAL_UPLOAD_MB} MB)."},
                )
    return await call_next(request)


# ===== 간단 인증(옵션) =====
def check_api_key(x_api_key: Optional[str]):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ===== 유틸: "1-3,5,7-9" 같은 범위를 0-index 페이지 인덱스 리스트로 변환 =====
_range_token = re.compile(r"^\s*(\d+)\s*(-\s*(\d+)\s*)?$")

def parse_page_ranges(range_str: str, total_pages: int) -> List[int]:
    """
    1-based 입력을 0-based 인덱스로 변환. 범위를 벗어나면 400 반환.
    예) "1-3,5" -> [0,1,2,4]
    """
    indices: List[int] = []
    if not range_str.strip():
        return list(range(total_pages))  # 전체 페이지
    parts = range_str.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = _range_token.match(part)
        if not m:
            raise HTTPException(status_code=400, detail=f"Invalid range token: '{part}'")
        start = int(m.group(1))
        end = m.group(3)
        if end is None:
            end_num = start
        else:
            end_num = int(end)
        if start < 1 or end_num < 1 or start > total_pages or end_num > total_pages:
            raise HTTPException(status_code=400, detail=f"Range out of bounds: '{part}' (doc has {total_pages} pages)")
        if start <= end_num:
            rng = range(start - 1, end_num)  # inclusive
        else:
            # 역순도 허용 (예: 10-7)
            rng = range(start - 1, end_num - 2, -1)
        indices.extend(list(rng))
    return indices


# ===== 간단 홈 UI =====
@app.get("/", response_class=HTMLResponse)
def index():
    html = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>PDF Merger</title>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; }
    .box { border: 2px dashed #999; padding: 24px; border-radius: 8px; text-align: center; }
    .row { display: flex; gap: 8px; align-items: center; margin: 8px 0; }
    .file-row { display: grid; grid-template-columns: 1fr 220px; gap: 8px; margin-bottom: 6px; }
    input[type=text] { width: 100%; padding: 8px; }
    button { padding: 10px 16px; cursor: pointer; }
    .hint { color: #555; font-size: 0.9rem; }
  </style>
</head>
<body>
  <h1>PDF Merger</h1>
  <div class="box" id="dropBox">
    <p><strong>Drag & drop</strong> or select PDF files (order matters).</p>
    <input id="fileInput" type="file" accept="application/pdf" multiple />
  </div>

  <h3>Files & Page Ranges</h3>
  <div id="files"></div>
  <div class="row">
    <label for="outputName">Output filename:</label>
    <input id="outputName" type="text" value="merged.pdf" />
  </div>
  <div class="row">
    <label for="apiKey">X-API-KEY (if required):</label>
    <input id="apiKey" type="text" placeholder="optional"/>
  </div>
  <div class="row">
    <button id="mergeBtn">Merge PDFs</button>
    <span class="hint">Page ranges example: <code>1-3,5</code> (leave empty for all)</span>
  </div>

  <script>
    const fileInput = document.getElementById('fileInput');
    const dropBox = document.getElementById('dropBox');
    const filesDiv = document.getElementById('files');
    const outputName = document.getElementById('outputName');
    const mergeBtn = document.getElementById('mergeBtn');
    const apiKey = document.getElementById('apiKey');

    let files = [];

    function refreshList() {
      filesDiv.innerHTML = '';
      files.forEach((f, i) => {
        const row = document.createElement('div');
        row.className = 'file-row';
        row.innerHTML = `
          <div>
            <strong>${i+1}.</strong> ${f.name}
            <button onclick="moveUp(${i})">↑</button>
            <button onclick="moveDown(${i})">↓</button>
            <button onclick="removeFile(${i})">✕</button>
          </div>
          <input type="text" placeholder="page ranges e.g. 1-3,5" data-idx="${i}" class="rangeInput"/>
        `;
        filesDiv.appendChild(row);
      });
    }

    function moveUp(i) { if (i>0){ [files[i-1],files[i]]=[files[i],files[i-1]]; refreshList(); } }
    function moveDown(i){ if (i<files.length-1){ [files[i+1],files[i]]=[files[i],files[i+1]]; refreshList(); } }
    function removeFile(i){ files.splice(i,1); refreshList(); }

    fileInput.addEventListener('change', (e) => {
      files = [...files, ...e.target.files];
      refreshList();
    });

    dropBox.addEventListener('dragover', (e)=>{ e.preventDefault(); dropBox.style.background='#f8f8f8'; });
    dropBox.addEventListener('dragleave', (e)=>{ dropBox.style.background=''; });
    dropBox.addEventListener('drop', (e)=>{
      e.preventDefault();
      dropBox.style.background='';
      files = [...files, ...e.dataTransfer.files];
      refreshList();
    });

    mergeBtn.addEventListener('click', async ()=>{
      if (files.length === 0) { alert('Select at least one PDF.'); return; }
      const form = new FormData();
      files.forEach((f, i) => form.append('files', f, f.name));
      // collect ranges in order
      const ranges = Array.from(document.querySelectorAll('.rangeInput'))
        .map(inp => inp.value || '');
      form.append('ranges', JSON.stringify(ranges));
      if (outputName.value) form.append('output_name', outputName.value);

      const headers = {};
      if (apiKey.value) headers['X-API-KEY'] = apiKey.value;

      const resp = await fetch('/merge', { method: 'POST', body: form, headers });
      if (!resp.ok) {
        const msg = await resp.text();
        alert(`Failed: ${resp.status} ${msg}`);
        return;
      }
      const blob = await resp.blob();
      const a = document.createElement('a');
      const url = URL.createObjectURL(blob);
      a.href = url;
      a.download = outputName.value || 'merged.pdf';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    });
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.get("/health", response_class=PlainTextResponse)
def health():
    return "ok"


class MergeResponse(BaseModel):
    filename: str
    size_bytes: int


@app.post("/merge", response_class=StreamingResponse)
async def merge_pdf(
    files: List[UploadFile] = File(..., description="Upload PDF files in desired order."),
    ranges: Optional[str] = Form(None, description='JSON list of page ranges per file, e.g. ["1-3,5",""]'),
    output_name: Optional[str] = Form("merged.pdf"),
    x_api_key: Optional[str] = Header(None, convert_underscores=False),
):
    check_api_key(x_api_key)

    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    # 간단 타입 검사
    for f in files:
        if not f.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"Not a PDF: {f.filename}")

    # ranges 파싱
    per_file_ranges: List[Optional[str]] = []
    if ranges:
        import json
        try:
            parsed = json.loads(ranges)
            if not isinstance(parsed, list):
                raise ValueError("ranges must be a JSON list of strings.")
            per_file_ranges = [r if isinstance(r, str) else "" for r in parsed]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid ranges JSON: {e}")
    # 파일 수에 못 미치면 나머지 빈 문자열로
    while len(per_file_ranges) < len(files):
        per_file_ranges.append("")

    writer = PdfWriter()

    # 메모리 혹은 임시파일로 처리
    try:
        for i, up in enumerate(files):
            # 업로드 스트림을 메모리로 복사
            data = await up.read()
            if len(data) == 0:
                raise HTTPException(status_code=400, detail=f"Empty file: {up.filename}")

            try:
                pdf = PdfReader(io.BytesIO(data))
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to read '{up.filename}': {e}")

            if pdf.is_encrypted:
                # pypdf는 대부분 암호 없이 열 수 없으므로 예외 처리
                raise HTTPException(status_code=400, detail=f"Encrypted PDF not supported: {up.filename}")

            # 페이지 선택
            want = per_file_ranges[i] if i < len(per_file_ranges) else ""
            if want is None:
                want = ""
            indices = parse_page_ranges(want, total_pages=len(pdf.pages))
            for idx in indices:
                writer.add_page(pdf.pages[idx])

        # 출력
        out_buf = io.BytesIO()
        writer.write(out_buf)
        out_buf.seek(0)

        final_name = output_name or "merged.pdf"
        if not final_name.lower().endswith(".pdf"):
            final_name += ".pdf"

        headers = {
            "Content-Disposition": f'attachment; filename="{final_name}"'
        }
        return StreamingResponse(out_buf, media_type="application/pdf", headers=headers)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Merge failed: {e}")
