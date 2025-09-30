from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])

HTML_CONTENT = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\"/>
  <title>PDF Merger</title>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>
  <style>
    :root {
      color-scheme: light dark;
      --bg-gradient: linear-gradient(135deg, #f4f7fb 0%, #edf1ff 50%, #e6f7ff 100%);
      --card-bg: rgba(255, 255, 255, 0.92);
      --card-shadow: 0 24px 60px -30px rgba(15, 23, 42, 0.45);
      --border-soft: rgba(120, 144, 156, 0.25);
      --primary: #2563eb;
      --primary-dark: #1d4ed8;
      --accent: #3b82f6;
      --text: #0f172a;
      --muted: #475569;
      --success: #12805a;
      --error: #b91c1c;
      font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
    }

    * {
      box-sizing: border-box;
    }

    body.app {
      margin: 0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 32px 16px 48px;
      background: var(--bg-gradient);
      color: var(--text);
    }

    .container {
      width: min(880px, 100%);
    }

    .hero {
      text-align: center;
      margin-bottom: 28px;
    }

    .hero h1 {
      margin: 0;
      font-size: clamp(2rem, 2.6vw + 1.2rem, 2.75rem);
      letter-spacing: -0.02em;
    }

    .hero p {
      margin: 12px auto 0;
      max-width: 560px;
      color: var(--muted);
      font-size: 1.05rem;
    }

    .card {
      background: var(--card-bg);
      backdrop-filter: blur(10px);
      border-radius: 22px;
      padding: clamp(24px, 2vw + 16px, 40px);
      box-shadow: var(--card-shadow);
      border: 1px solid var(--border-soft);
    }

    .dropzone {
      position: relative;
      display: block;
      text-align: center;
      border: 2px dashed rgba(37, 99, 235, 0.35);
      border-radius: 18px;
      padding: 48px 24px;
      background: rgba(37, 99, 235, 0.05);
      transition: all 0.2s ease;
      cursor: pointer;
      overflow: hidden;
    }

    .dropzone:hover,
    .dropzone.is-dragover {
      border-color: rgba(37, 99, 235, 0.65);
      background: rgba(37, 99, 235, 0.12);
      box-shadow: 0 12px 30px -20px rgba(37, 99, 235, 0.75);
    }

    .dropzone input[type=file] {
      position: absolute;
      inset: 0;
      opacity: 0;
      cursor: pointer;
    }

    .dropzone-inner {
      pointer-events: none;
    }

    .drop-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 54px;
      height: 54px;
      margin-bottom: 12px;
      border-radius: 16px;
      background: white;
      color: var(--accent);
      font-size: 28px;
      box-shadow: 0 12px 40px -18px rgba(37, 99, 235, 0.55);
    }

    .dropzone strong {
      font-size: 1.15rem;
    }

    .dropzone p {
      margin: 8px 0 0;
      color: var(--muted);
    }

    .file-list {
      margin: 28px 0 14px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .file-list.empty {
      border: 1px dashed var(--border-soft);
      border-radius: 16px;
      padding: 28px;
      text-align: center;
      color: var(--muted);
      font-size: 0.95rem;
      background: rgba(148, 163, 184, 0.12);
    }

    .file-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(180px, 210px);
      gap: 16px;
      padding: 16px 18px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.88);
      border: 1px solid rgba(148, 163, 184, 0.24);
      box-shadow: 0 10px 28px -24px rgba(15, 23, 42, 0.4);
    }

    .file-meta {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 0.95rem;
      color: var(--muted);
    }

    .file-index {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      border-radius: 8px;
      background: rgba(37, 99, 235, 0.1);
      color: var(--accent);
      font-weight: 600;
    }

    .file-name {
      font-weight: 600;
      color: var(--text);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .file-size {
      font-variant-numeric: tabular-nums;
    }

    .file-actions {
      margin-top: 12px;
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .icon-btn {
      border: none;
      background: rgba(37, 99, 235, 0.12);
      color: var(--accent);
      padding: 6px 10px;
      border-radius: 10px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: transform 0.2s ease, background 0.2s ease;
    }

    .icon-btn:hover {
      background: rgba(37, 99, 235, 0.22);
      transform: translateY(-1px);
    }

    .icon-btn.danger {
      background: rgba(239, 68, 68, 0.14);
      color: #dc2626;
    }

    .icon-btn.danger:hover {
      background: rgba(239, 68, 68, 0.2);
    }

    .range-input {
      width: 100%;
      padding: 12px 14px;
      border-radius: 12px;
      border: 1px solid rgba(148, 163, 184, 0.48);
      background: rgba(248, 250, 252, 0.8);
      font-size: 0.95rem;
      transition: border 0.2s ease, box-shadow 0.2s ease;  
      color: var(--text);
    }

    .range-input:focus {
      border-color: rgba(37, 99, 235, 0.6);
      outline: none;
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.18); 
      color: var(--text);
    }

    .form-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 18px;
      margin-top: 24px;
      color: var(--text);
    }

    .form-grid label {
      display: flex;
      flex-direction: column;
      gap: 8px;
      font-weight: 600;
      color: var(--text);
    }

    .form-grid input[type=text] {
      padding: 12px 14px;
      border-radius: 12px;
      border: 1px solid rgba(148, 163, 184, 0.45);
      background: rgba(255, 255, 255, 0.9);
      font-size: 0.95rem;
      transition: border 0.2s ease, box-shadow 0.2s ease;
      color: var(--text);
    }

    .form-grid input[type=text]:focus {
      border-color: rgba(37, 99, 235, 0.6);
      outline: none;
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.18);
    }

    .actions {
      margin-top: 28px;
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
    }

    button.primary {
      border: none;
      background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
      color: white;
      padding: 12px 26px;
      border-radius: 999px;
      font-weight: 600;
      font-size: 1rem;
      cursor: pointer;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
      box-shadow: 0 12px 30px -18px rgba(37, 99, 235, 0.65);
    }

    button.primary:hover {
      transform: translateY(-1px);
      box-shadow: 0 15px 35px -15px rgba(37, 99, 235, 0.7);
    }

    button.primary:disabled {
      cursor: not-allowed;
      opacity: 0.7;
      box-shadow: none;
    }

    button.ghost {
      border: 1px solid rgba(148, 163, 184, 0.5);
      background: transparent;
      color: var(--muted);
      padding: 11px 18px;
      border-radius: 999px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s ease, color 0.2s ease, border 0.2s ease;
    }

    button.ghost:hover:not(:disabled) {
      background: rgba(148, 163, 184, 0.14);
      color: var(--text);
      border-color: rgba(148, 163, 184, 0.7);
    }

    button.ghost:disabled {
      cursor: not-allowed;
      opacity: 0.55;
    }

    .hint {
      color: var(--muted);
      font-size: 0.92rem;
    }

    .status {
      min-height: 1.2em;
      margin-top: 8px;
      font-size: 0.95rem;
      color: var(--muted);
    }

    .status.success {
      color: var(--success);
    }

    .status.error {
      color: var(--error);
    }

    .status.pending {
      color: var(--accent);
    }

    .progress {
      margin-top: 12px;
      height: 12px;
      border-radius: 999px;
      background: rgba(148, 163, 184, 0.25);
      overflow: hidden;
      position: relative;
    }

    .progress[hidden] {
      display: none;
    }

    .progress-bar {
      height: 100%;
      width: 0%;
      background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
      transition: width 0.25s ease;
    }

    .progress-bar.indeterminate {
      position: absolute;
      width: 40%;
      left: -40%;
      animation: progress-indeterminate 1.2s ease-in-out infinite;
    }

    @keyframes progress-indeterminate {
      0% {
        left: -40%;
      }
      50% {
        left: 60%;
      }
      100% {
        left: 100%;
      }
    }

    @media (max-width: 640px) {
      body.app {
        padding: 24px 12px;
      }

      .file-row {
        grid-template-columns: 1fr;
      }

      .file-actions {
        margin-top: 8px;
      }
    }
  </style>
</head>
<body class=\"app\">
  <div class=\"container\">
    <header class=\"hero\">
      <h1>PDF Merger</h1>
      <p>Combine multiple PDF files into a single document and control the order and page ranges with ease.</p>
    </header>

    <section class=\"card\">
      <label class=\"dropzone\" id=\"dropBox\">
        <input id=\"fileInput\" type=\"file\" accept=\"application/pdf\" multiple />
        <div class=\"dropzone-inner\">
          <div class=\"drop-icon\">⬆️</div>
          <strong>Drop PDF files here or click to browse</strong>
          <p>Your files will stay on this device until you choose to merge them.</p>
        </div>
      </label>

      <div id=\"files\" class=\"file-list empty\">
        <p class=\"empty-state\">No files added yet. Add PDFs above to configure their ranges.</p>
      </div>

      <div class=\"form-grid\">
        <label>
          Output filename
          <input id=\"outputName\" type=\"text\" value=\"merged.pdf\" placeholder=\"merged.pdf\" />
        </label>
        <label>
          API key
          <input id=\"apiKey\" type=\"text\" placeholder=\"Optional - only if required\" />
        </label>
      </div>

      <div class=\"actions\">
        <button id=\"mergeBtn\" class=\"primary\">Merge PDFs</button>
        <button id=\"clearBtn\" type=\"button\" class=\"ghost\" disabled>Clear files</button>
        <span class=\"hint\">Page range example: <code>1-3,5</code> (leave empty for entire file)</span>
      </div>
      <div id=\"progressWrapper\" class=\"progress\" hidden>
        <div
          id=\"progressBar\"
          class=\"progress-bar\"
          role=\"progressbar\"
          aria-valuemin=\"0\"
          aria-valuemax=\"100\"
          aria-valuenow=\"0\"
        ></div>
      </div>
      <p id=\"status\" class=\"status\" role=\"status\" aria-live=\"polite\"></p>
    </section>
  </div>

  <script>
    const fileInput = document.getElementById('fileInput');
    const dropBox = document.getElementById('dropBox');
    const filesDiv = document.getElementById('files');
    const outputName = document.getElementById('outputName');
    const mergeBtn = document.getElementById('mergeBtn');
    const apiKey = document.getElementById('apiKey');
    const clearBtn = document.getElementById('clearBtn');
    const status = document.getElementById('status');
    const progressWrapper = document.getElementById('progressWrapper');
    const progressBar = document.getElementById('progressBar');

    let files = [];
    let ranges = [];

    function buildApiUrl(path, extraParams = {}) {
      const url = new URL(path, window.location.href);
      if (apiKey.value) {
        url.searchParams.set('api_key', apiKey.value);
      }
      Object.entries(extraParams).forEach(([key, value]) => {
        if (value === undefined || value === null) return;
        url.searchParams.set(key, String(value));
      });
      return url.pathname + url.search;
    }

    function formatSize(bytes) {
      if (!Number.isFinite(bytes)) return '';
      const units = ['B', 'KB', 'MB', 'GB'];
      let size = bytes;
      let unitIndex = 0;
      while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
      }
      return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
    }

    function setStatus(message = '', type = 'info') {
      status.textContent = message;
      status.className = `status ${message ? type : ''}`.trim();
    }

    function resetProgress() {
      progressWrapper.hidden = true;
      progressBar.classList.remove('indeterminate');
      progressBar.style.width = '0%';
      progressBar.setAttribute('aria-valuenow', '0');
    }

    function startIndeterminateProgress() {
      progressWrapper.hidden = false;
      progressBar.classList.add('indeterminate');
      progressBar.style.width = '100%';
      progressBar.setAttribute('aria-valuenow', '0');
    }

    function updateProgress(percent) {
      const value = Number.isFinite(percent) ? Math.max(0, Math.min(100, percent)) : 0;
      progressWrapper.hidden = false;
      progressBar.classList.remove('indeterminate');
      progressBar.style.width = `${value}%`;
      progressBar.setAttribute('aria-valuenow', String(Math.round(value)));
    }

    function syncRangesFromInputs() {
      const inputs = filesDiv.querySelectorAll('.range-input');
      inputs.forEach((input) => {
        const idx = Number(input.dataset.idx);
        if (!Number.isNaN(idx)) {
          ranges[idx] = input.value;
        }
      });
    }

    function refreshList() {
      filesDiv.innerHTML = '';

      if (files.length === 0) {
        filesDiv.classList.add('empty');
        filesDiv.innerHTML = '<p class="empty-state">No files added yet. Add PDFs above to configure their ranges.</p>';
      } else {
        filesDiv.classList.remove('empty');
        const fragment = document.createDocumentFragment();
        files.forEach((file, index) => {
          const row = document.createElement('div');
          row.className = 'file-row';
          row.innerHTML = `
            <div>
              <div class="file-meta">
                <span class="file-index">${index + 1}</span>
                <span class="file-name" title="${file.name}">${file.name}</span>
                <span class="file-size">${formatSize(file.size)}</span>
              </div>
              <div class="file-actions">
                <button class="icon-btn" data-action="up" data-index="${index}" aria-label="Move ${file.name} up">↑</button>
                <button class="icon-btn" data-action="down" data-index="${index}" aria-label="Move ${file.name} down">↓</button>
                <button class="icon-btn danger" data-action="remove" data-index="${index}" aria-label="Remove ${file.name}">Remove</button>
              </div>
            </div>
            <div>
              <input type="text" class="range-input" placeholder="Page ranges e.g. 1-3,5" data-idx="${index}" value="${ranges[index] || ''}" />
            </div>
          `;
          fragment.appendChild(row);
        });
        filesDiv.appendChild(fragment);
      }

      clearBtn.disabled = files.length === 0;
    }

    function addFiles(newFiles) {
      if (!newFiles.length) {
        return;
      }
      const incoming = Array.from(newFiles).filter((file) => file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf'));
      if (incoming.length === 0) {
        setStatus('Only PDF files are supported.', 'error');
        return;
      }
      setStatus('');
      incoming.forEach((file) => {
        files.push(file);
        ranges.push('');
      });
      refreshList();
    }

    function moveUp(index) {
      if (index <= 0) return;
      [files[index - 1], files[index]] = [files[index], files[index - 1]];
      [ranges[index - 1], ranges[index]] = [ranges[index], ranges[index - 1]];
      refreshList();
    }

    function moveDown(index) {
      if (index >= files.length - 1) return;
      [files[index + 1], files[index]] = [files[index], files[index + 1]];
      [ranges[index + 1], ranges[index]] = [ranges[index], ranges[index + 1]];
      refreshList();
    }

    function removeFile(index) {
      files.splice(index, 1);
      ranges.splice(index, 1);
      refreshList();
    }

    async function downloadResult(jobId, outputName, headers) {
      const response = await fetch(buildApiUrl(`/merge/${jobId}/result`), {
        headers,
      });
      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || `Download failed with status ${response.status}`);
      }
      const blob = await response.blob();
      const name = outputName || 'merged.pdf';
      const anchor = document.createElement('a');
      const url = URL.createObjectURL(blob);
      anchor.href = url;
      anchor.download = name;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    }

    function trackJob(jobId, outputName, headers) {
      return new Promise((resolve, reject) => {
        let active = true;
        let eventSource;
        let pollTimer;
        let lastRevision = -1;
        let polling = false;

        const cleanup = () => {
          active = false;
          if (eventSource) {
            eventSource.close();
            eventSource = undefined;
          }
          if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = undefined;
          }
        };

        const handleError = (error) => {
          if (!active) return;
          cleanup();
          reject(error instanceof Error ? error : new Error(String(error)));
        };

        const handleSuccess = () => {
          if (!active) return;
          cleanup();
          resolve();
        };

        const handleUpdate = async (payload) => {
          if (!active || !payload) return;

          const statusText = payload.status;
          const total = Number(payload.total_pages) || 0;
          const processed = Number(payload.processed_pages) || 0;
          const percentValue = Number(payload.percent);
          if (Number.isFinite(Number(payload.revision))) {
            lastRevision = Number(payload.revision);
          }

          const currentFile = typeof payload.current_file === 'string' && payload.current_file
            ? payload.current_file
            : '';

          if (statusText === 'queued') {
            setStatus('Merge job queued…', 'pending');
            startIndeterminateProgress();
            return;
          }

          if (statusText === 'running') {
            if (total > 0) {
              const computed = Number.isFinite(percentValue)
                ? percentValue
                : (processed / total) * 100;
              updateProgress(computed);
              const label = currentFile
                ? `Merging ${currentFile}… ${processed}/${total} pages`
                : `Merging PDFs… ${processed}/${total} pages`;
              setStatus(label, 'pending');
            } else {
              startIndeterminateProgress();
              setStatus('Merging PDFs…', 'pending');
            }
            return;
          }

          if (statusText === 'completed') {
            try {
              if (total > 0) {
                updateProgress(100);
              }
              await downloadResult(jobId, payload.output_name || outputName, headers);
              setStatus('Merged successfully! Your download should begin automatically.', 'success');
              handleSuccess();
            } catch (error) {
              handleError(error);
            }
            return;
          }

          if (statusText === 'error') {
            const message = payload.error || 'Failed to merge PDFs.';
            handleError(new Error(message));
          }
        };

        const pollOnce = async () => {
          if (!active || polling) return;
          polling = true;
          try {
            const extraParams = {};
            if (lastRevision >= 0) {
              extraParams.since = String(lastRevision);
              extraParams.wait = '5';
            }
            const response = await fetch(buildApiUrl(`/merge/${jobId}`, extraParams), {
              headers,
            });
            if (!response.ok) {
              throw new Error(`Status request failed with status ${response.status}`);
            }
            const data = await response.json();
            await handleUpdate(data);
          } catch (error) {
            console.error('Polling error', error);
          } finally {
            polling = false;
          }
        };

        const startPolling = () => {
          pollOnce();
          pollTimer = window.setInterval(pollOnce, 1000);
        };

        if (typeof EventSource !== 'undefined') {
          try {
            eventSource = new EventSource(buildApiUrl(`/merge/${jobId}/events`));
            eventSource.onmessage = async (event) => {
              try {
                const data = JSON.parse(event.data || '{}');
                await handleUpdate(data);
              } catch (error) {
                console.error('Failed to parse progress update', error);
              }
            };
            eventSource.onerror = () => {
              if (!active) return;
              console.warn('SSE connection interrupted, falling back to polling.');
              eventSource?.close();
              eventSource = undefined;
              startPolling();
            };
            return;
          } catch (error) {
            console.error('Unable to establish SSE connection', error);
          }
        }

        startPolling();
      });
    }

    filesDiv.addEventListener('click', (event) => {
      const button = event.target.closest('button[data-action]');
      if (!button) return;
      const index = Number(button.dataset.index);
      if (Number.isNaN(index)) return;

      if (button.dataset.action === 'up') {
        moveUp(index);
      } else if (button.dataset.action === 'down') {
        moveDown(index);
      } else if (button.dataset.action === 'remove') {
        removeFile(index);
      }
    });

    filesDiv.addEventListener('input', (event) => {
      const input = event.target;
      if (!input.classList.contains('range-input')) return;
      const idx = Number(input.dataset.idx);
      if (!Number.isNaN(idx)) {
        ranges[idx] = input.value;
      }
    });

    fileInput.addEventListener('change', (event) => {
      addFiles(event.target.files || []);
      fileInput.value = '';
    });

    dropBox.addEventListener('dragover', (event) => {
      event.preventDefault();
      dropBox.classList.add('is-dragover');
    });

    dropBox.addEventListener('dragleave', () => {
      dropBox.classList.remove('is-dragover');
    });

    dropBox.addEventListener('drop', (event) => {
      event.preventDefault();
      dropBox.classList.remove('is-dragover');
      addFiles(event.dataTransfer.files || []);
    });

    clearBtn.addEventListener('click', () => {
      files = [];
      ranges = [];
      refreshList();
      setStatus('Cleared selected files.', 'info');
    });

    mergeBtn.addEventListener('click', async () => {
      if (files.length === 0) {
        alert('Select at least one PDF.');
        return;
      }

      syncRangesFromInputs();

      const form = new FormData();
      files.forEach((file) => form.append('files', file, file.name));
      form.append('ranges', JSON.stringify(ranges.map((value) => value || '')));
      if (outputName.value) form.append('output_name', outputName.value);

      const headers = {};
      if (apiKey.value) headers['X-API-KEY'] = apiKey.value;

      mergeBtn.disabled = true;
      mergeBtn.textContent = 'Merging…';
      setStatus('Submitting merge job…', 'pending');
      resetProgress();
      startIndeterminateProgress();

      try {
        const response = await fetch('/merge', {
          method: 'POST',
          body: form,
          headers,
        });

        if (!response.ok) {
          const message = await response.text();
          throw new Error(message || `Request failed with status ${response.status}`);
        }

        const payload = await response.json();
        if (!payload || !payload.job_id) {
          throw new Error('Unexpected response from server.');
        }

        const finalName = payload.output_name || outputName.value || 'merged.pdf';
        setStatus('Merge job queued…', 'pending');
        await trackJob(payload.job_id, finalName, headers);
      } catch (error) {
        console.error(error);
        const message = error instanceof Error ? error.message : 'Failed to merge PDFs.';
        alert(`Failed: ${message}`);
        setStatus(message, 'error');
      } finally {
        mergeBtn.disabled = false;
        mergeBtn.textContent = 'Merge PDFs';
        resetProgress();
      }
    });
  </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(content=HTML_CONTENT)
