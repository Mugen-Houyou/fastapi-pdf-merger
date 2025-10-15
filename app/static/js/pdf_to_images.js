// app/static/js/pdf_to_images.js
(() => {
  const $ = (sel) => document.querySelector(sel);

  const fileInput = $('#fileInput');
  const dropBox = $('#dropBox');
  const fileInfo = $('#fileInfo');
  const fileName = $('#fileName');
  const pageRange = $('#pageRange');
  const dpi = $('#dpi');
  const quality = $('#quality');
  const convertBtn = $('#convertBtn');
  const clearBtn = $('#clearBtn');
  const apiKey = $('#apiKey');
  const status = $('#status');

  const { apiKeyRequired, defaults, endpoints, i18n = {}, locale = 'en', limits = {} } = window.__PDF_TO_IMAGES__ || {
    apiKeyRequired: false,
    defaults: { dpi: 200, quality: 85 },
    endpoints: { convert: '/api/v1/pdf-to-images' },
    i18n: {},
    locale: 'en',
    limits: {}
  };

  let selectedFile = null;

  const translate = (key, params = {}) => {
    const parts = key.split('.');
    let value = i18n;
    for (const part of parts) {
      if (value && typeof value === 'object' && part in value) {
        value = value[part];
      } else {
        value = undefined;
        break;
      }
    }
    if (typeof value !== 'string') return key;
    return value.replace(/\{(\w+)\}/g, (_, token) => (token in params ? params[token] : `{${token}}`));
  };

  const formatSizeCompact = (bytes) => {
    if (!Number.isFinite(bytes)) return '';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes, i = 0;
    while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
    const decimals = i === 0 ? 0 : size >= 100 ? 0 : 2;
    return `${size.toFixed(decimals)}${units[i]}`;
  };

  const setStatus = (message = '', type = 'info') => {
    status.textContent = message;
    status.className = `status ${message ? type : ''}`.trim();
  };

  const updateUI = () => {
    if (selectedFile) {
      fileName.textContent = selectedFile.name;
      fileInfo.style.display = 'block';
      convertBtn.disabled = false;
    } else {
      fileInfo.style.display = 'none';
      convertBtn.disabled = true;
    }
  };

  const setFile = (file) => {
    if (!file) {
      selectedFile = null;
      updateUI();
      return;
    }

    const filename = file.name.toLowerCase();
    const contentType = (file.type || '').toLowerCase();

    if (!filename.endsWith('.pdf') && contentType !== 'application/pdf') {
      alert(translate('pdf_to_images.messages.pdf_only'));
      return;
    }

    selectedFile = file;
    updateUI();
    setStatus('');
  };

  fileInput.addEventListener('change', (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      setFile(files[0]);
    }
    fileInput.value = '';
  });

  dropBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropBox.classList.add('is-dragover');
  });

  dropBox.addEventListener('dragleave', () => {
    dropBox.classList.remove('is-dragover');
  });

  dropBox.addEventListener('drop', (e) => {
    e.preventDefault();
    dropBox.classList.remove('is-dragover');
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      setFile(files[0]);
    }
  });

  clearBtn.addEventListener('click', () => {
    if (!window.confirm(translate('pdf_to_images.messages.confirm_clear'))) return;
    selectedFile = null;
    updateUI();
    setStatus('');
  });

  convertBtn.addEventListener('click', async () => {
    if (!selectedFile) {
      alert(translate('pdf_to_images.messages.select_file'));
      return;
    }

    const form = new FormData();
    form.append('file', selectedFile, selectedFile.name);

    if (pageRange?.value) form.append('page_range', pageRange.value);
    if (dpi?.value) form.append('dpi', dpi.value);
    if (quality?.value) form.append('quality', quality.value);

    const headers = {};
    if (apiKeyRequired && apiKey?.value) headers['X-API-KEY'] = apiKey.value;

    convertBtn.disabled = true;
    const originalText = convertBtn.textContent;
    convertBtn.textContent = translate('pdf_to_images.buttons.converting');
    setStatus(translate('pdf_to_images.messages.converting'), 'pending');

    try {
      const resp = await fetch(endpoints.convert || '/api/v1/pdf-to-images', {
        method: 'POST',
        body: form,
        headers
      });

      if (!resp.ok) {
        const msg = await resp.text();
        throw new Error(msg || `Request failed with status ${resp.status}`);
      }

      let blob;
      if (resp.body && 'getReader' in resp.body) {
        const reader = resp.body.getReader();
        const chunks = [];
        let received = 0;
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          if (value) {
            chunks.push(value);
            received += value.byteLength;
            setStatus(translate('pdf_to_images.messages.converting_progress', { size: formatSizeCompact(received) }), 'pending');
          }
        }
        blob = new Blob(chunks, { type: resp.headers.get('content-type') || 'application/zip' });
      } else {
        blob = await resp.blob();
      }

      // Download the ZIP file
      const a = document.createElement('a');
      const url = URL.createObjectURL(blob);
      a.href = url;

      // Extract filename from Content-Disposition header if available
      const contentDisposition = resp.headers.get('content-disposition');
      let downloadName = 'images.zip';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+?)"?$/);
        if (filenameMatch) downloadName = filenameMatch[1];
      }

      a.download = downloadName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      setStatus(translate('pdf_to_images.messages.converted'), 'success');
      notyf.success(translate('pdf_to_images.messages.converted'));

    } catch (err) {
      console.error(err);
      const defaultError = translate('pdf_to_images.messages.convert_failed');
      const msg = err instanceof Error && err.message ? err.message : defaultError;
      alert(translate('pdf_to_images.messages.failed_prefix', { message: msg }));
      setStatus(msg, 'error');
    } finally {
      convertBtn.disabled = false;
      convertBtn.textContent = originalText;
    }
  });

  window.addEventListener('beforeunload', (event) => {
    if (!selectedFile) return;
    const message = translate('messages.leave_confirm');
    event.preventDefault();
    event.returnValue = message;
    return message;
  });

  updateUI();
})();
