// app/static/js/app.js
(() => {
  const $ = (sel) => document.querySelector(sel);

  const fileInput = $('#fileInput');
  const dropBox = $('#dropBox');
  const filesDiv = $('#files');
  const outputName = $('#outputName');
  const engine = $('#engine');
  const mergeBtn = $('#mergeBtn');
  const apiKey = $('#apiKey');
  const clearBtn = $('#clearBtn');
  const reverseBtn = $('#reverseBtn');
  const status = $('#status');

  const paperSize = $('#paperSize');
  const orientation = $('#orientation');
  const fitMode = $('#fitMode');

  const { apiKeyRequired, defaults, endpoints, i18n = {}, locale = 'en', limits = {} } = window.__PDFMERGER__ || {
    apiKeyRequired: false,
    defaults: { output_name: 'merged.pdf', paper_size: 'A4', orientation: 'portrait', fit_mode: 'letterbox' },
    endpoints: { merge: '/merge' },
    i18n: {},
    locale: 'en',
    limits: {}
  };

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

  // defaults 적용 (SSR에서 이미 넣어주지만, JS 초기화 보강)
  if (outputName && defaults.output_name) outputName.value = defaults.output_name;
  if (engine && defaults.engine) engine.value = defaults.engine;
  if (paperSize && defaults.paper_size) paperSize.value = defaults.paper_size;
  if (orientation && defaults.orientation) orientation.value = defaults.orientation;
  if (fitMode && defaults.fit_mode) fitMode.value = defaults.fit_mode;

  let files = [];
  let ranges = [];
  let fileIdCounter = 0;

  const ensureFileId = (file) => {
    if (!file.__pdfMergerId) {
      file.__pdfMergerId = `file-${fileIdCounter++}`;
    }
    return file.__pdfMergerId;
  };

  const formatSize = (bytes) => {
    if (!Number.isFinite(bytes)) return '';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes, i = 0;
    while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
    return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
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

  const refreshList = () => {
    const previousPositions = new Map();
    const existingRows = new Map();

    filesDiv.querySelectorAll('.file-row').forEach((row) => {
      const id = row.dataset.fileId;
      if (!id) return;
      existingRows.set(id, row);
      previousPositions.set(id, row.getBoundingClientRect());
    });

    filesDiv.innerHTML = '';

    if (files.length === 0) {
      filesDiv.classList.add('empty');
      filesDiv.innerHTML = `<p class="empty-state">${translate('messages.empty')}</p>`;
      if (clearBtn) clearBtn.disabled = true;
      if (reverseBtn) reverseBtn.disabled = true;
      return;
    }

    filesDiv.classList.remove('empty');

    const ensureRowStructure = (row) => {
      if (row.__structureReady) return row;
      row.className = 'file-row';
      const main = document.createElement('div');
      main.className = 'file-main';

      const handle = document.createElement('button');
      handle.type = 'button';
      handle.className = 'drag-handle';
      handle.draggable = true;
      handle.innerHTML = '<span aria-hidden="true">⋮⋮</span>';

      const body = document.createElement('div');
      body.className = 'file-body';

      const meta = document.createElement('div');
      meta.className = 'file-meta';

      const indexEl = document.createElement('span');
      indexEl.className = 'file-index';

      const nameEl = document.createElement('span');
      nameEl.className = 'file-name';

      const sizeEl = document.createElement('span');
      sizeEl.className = 'file-size';

      meta.appendChild(indexEl);
      meta.appendChild(nameEl);
      meta.appendChild(sizeEl);

      const actions = document.createElement('div');
      actions.className = 'file-actions';

      const removeBtn = document.createElement('button');
      removeBtn.className = 'icon-btn danger';
      removeBtn.type = 'button';
      removeBtn.dataset.action = 'remove';
      actions.appendChild(removeBtn);

      body.appendChild(meta);
      body.appendChild(actions);

      main.appendChild(handle);
      main.appendChild(body);

      const rangeWrapper = document.createElement('div');
      const rangeInput = document.createElement('input');
      rangeInput.type = 'text';
      rangeInput.className = 'range-input';
      rangeInput.autocomplete = 'off';
      rangeWrapper.appendChild(rangeInput);

      row.appendChild(main);
      row.appendChild(rangeWrapper);

      row.__structureReady = true;
      return row;
    };

    const updateRow = (row, file, index) => {
      ensureRowStructure(row);
      const id = ensureFileId(file);
      row.dataset.fileId = id;
      row.dataset.index = String(index);
      row.classList.remove('dragging', 'drag-over-top', 'drag-over-bottom');

      const handle = row.querySelector('.drag-handle');
      if (handle) {
        handle.dataset.index = String(index);
        handle.setAttribute('aria-label', translate('aria.drag_handle', { name: file.name }));
      }

      const indexEl = row.querySelector('.file-index');
      if (indexEl) indexEl.textContent = String(index + 1);

      const nameEl = row.querySelector('.file-name');
      if (nameEl) {
        nameEl.textContent = file.name;
        nameEl.title = file.name;
      }

      const sizeEl = row.querySelector('.file-size');
      if (sizeEl) sizeEl.textContent = formatSize(file.size);

      const removeBtn = row.querySelector('button[data-action="remove"]');
      if (removeBtn) {
        removeBtn.dataset.index = String(index);
        removeBtn.setAttribute('aria-label', translate('aria.remove', { name: file.name }));
        removeBtn.textContent = translate('buttons.remove');
      }

      const rangeInput = row.querySelector('.range-input');
      if (rangeInput) {
        rangeInput.placeholder = translate('placeholders.range');
        rangeInput.dataset.idx = String(index);
        rangeInput.value = ranges[index] || '';
      }

      return row;
    };

    const frag = document.createDocumentFragment();
    files.forEach((file, index) => {
      const id = ensureFileId(file);
      const row = updateRow(existingRows.get(id) || document.createElement('div'), file, index);
      frag.appendChild(row);
      existingRows.delete(id);
    });

    filesDiv.appendChild(frag);

    if (clearBtn) clearBtn.disabled = false;
    if (reverseBtn) reverseBtn.disabled = files.length <= 1;

    filesDiv.querySelectorAll('.file-row').forEach((row) => {
      const id = row.dataset.fileId;
      if (!id) return;
      const previous = previousPositions.get(id);
      if (!previous) return;
      const current = row.getBoundingClientRect();
      const deltaX = previous.left - current.left;
      const deltaY = previous.top - current.top;
      if (Math.abs(deltaX) < 0.5 && Math.abs(deltaY) < 0.5) return;

      row.classList.add('is-animating');
      row.style.transition = 'none';
      row.style.transform = `translate(${deltaX}px, ${deltaY}px)`;
      requestAnimationFrame(() => {
        row.style.transition = '';
        row.style.transform = '';
      });

      const handleTransitionEnd = (event) => {
        if (event.propertyName === 'transform') {
          row.classList.remove('is-animating');
          row.style.transition = '';
          row.style.transform = '';
          row.removeEventListener('transitionend', handleTransitionEnd);
        }
      };

      row.addEventListener('transitionend', handleTransitionEnd);
    });
  };

  const addFiles = (newFiles) => {
    if (!newFiles?.length) return;
    const incoming = Array.from(newFiles).filter(f => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf'));
    if (incoming.length === 0) { setStatus(translate('messages.pdf_only'), 'error'); return; }
    setStatus('');
    incoming.forEach(f => {
      ensureFileId(f);
      files.push(f);
      ranges.push('');
    });
    refreshList();
  };

  const removeFile = (i) => { files.splice(i,1); ranges.splice(i,1); refreshList(); };

  filesDiv.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-action]');
    if (!btn) return;
    const i = Number(btn.dataset.index);
    if (Number.isNaN(i)) return;
    if (btn.dataset.action === 'remove') removeFile(i);
  });

  const reorderItems = (from, to) => {
    if (from === to) return;
    if (from < 0 || from >= files.length) return;
    if (to < 0) to = 0;
    if (to > files.length) to = files.length;
    const [movedFile] = files.splice(from, 1);
    const [movedRange] = ranges.splice(from, 1);
    files.splice(to, 0, movedFile);
    ranges.splice(to, 0, movedRange);
    refreshList();
  };

  let dragIndex = null;
  let dropTarget = null;
  let dropAfter = false;

  const clearDragIndicators = () => {
    filesDiv.querySelectorAll('.file-row').forEach(row => {
      row.classList.remove('dragging', 'drag-over-top', 'drag-over-bottom');
    });
    dropTarget = null;
    dropAfter = false;
  };

  filesDiv.addEventListener('dragstart', (e) => {
    const handle = e.target.closest('.drag-handle');
    if (!handle) {
      e.preventDefault();
      return;
    }
    const row = handle.closest('.file-row');
    if (!row) {
      e.preventDefault();
      return;
    }
    const index = Number(row.dataset.index);
    if (Number.isNaN(index)) {
      e.preventDefault();
      return;
    }
    dragIndex = index;
    row.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(index));
  });

  filesDiv.addEventListener('dragover', (e) => {
    if (dragIndex === null) return;
    const row = e.target.closest('.file-row');
    if (!row) {
      clearDragIndicators();
      e.preventDefault();
      return;
    }
    e.preventDefault();
    const rect = row.getBoundingClientRect();
    const after = e.clientY > rect.top + rect.height / 2;
    if (dropTarget !== row || dropAfter !== after) {
      clearDragIndicators();
      row.classList.add(after ? 'drag-over-bottom' : 'drag-over-top');
      dropTarget = row;
      dropAfter = after;
    }
    e.dataTransfer.dropEffect = 'move';
  });

  filesDiv.addEventListener('dragleave', (e) => {
    const row = e.target.closest('.file-row');
    if (!row) return;
    row.classList.remove('drag-over-top', 'drag-over-bottom');
    if (row === dropTarget) {
      dropTarget = null;
      dropAfter = false;
    }
  });

  filesDiv.addEventListener('drop', (e) => {
    if (dragIndex === null) return;
    e.preventDefault();
    let targetIndex;
    if (dropTarget) {
      targetIndex = Number(dropTarget.dataset.index);
      if (Number.isNaN(targetIndex)) {
        clearDragIndicators();
        dragIndex = null;
        return;
      }
      if (dropAfter) targetIndex += 1;
    } else {
      targetIndex = files.length;
    }
    if (dragIndex < targetIndex) targetIndex -= 1;
    reorderItems(dragIndex, targetIndex);
    dragIndex = null;
    clearDragIndicators();
  });

  filesDiv.addEventListener('dragend', () => {
    dragIndex = null;
    clearDragIndicators();
  });

  filesDiv.addEventListener('input', (e) => {
    const input = e.target;
    if (!input.classList.contains('range-input')) return;
    const i = Number(input.dataset.idx);
    if (!Number.isNaN(i)) ranges[i] = input.value;
  });

  fileInput.addEventListener('change', (e) => { addFiles(e.target.files || []); fileInput.value = ''; });

  dropBox.addEventListener('dragover', (e) => { e.preventDefault(); dropBox.classList.add('is-dragover'); });
  dropBox.addEventListener('dragleave', () => { dropBox.classList.remove('is-dragover'); });
  dropBox.addEventListener('drop', (e) => { e.preventDefault(); dropBox.classList.remove('is-dragover'); addFiles(e.dataTransfer.files || []); });

  if (reverseBtn) {
    reverseBtn.addEventListener('click', () => {
      if (files.length <= 1) return;
      files.reverse();
      ranges.reverse();
      refreshList();
      setStatus(translate('messages.reordered'), 'info');
    });
  }

  clearBtn.addEventListener('click', () => { files = []; ranges = []; refreshList(); setStatus(translate('messages.cleared'), 'info'); });

  mergeBtn.addEventListener('click', async () => {
    if (files.length === 0) { alert(translate('messages.select_one')); return; }

    // collect ranges
    document.querySelectorAll('.range-input').forEach(inp => {
      const i = Number(inp.dataset.idx);
      if (!Number.isNaN(i)) ranges[i] = inp.value || '';
    });

    const form = new FormData();
    files.forEach(f => form.append('files', f, f.name));
    form.append('ranges', JSON.stringify(ranges.map(v => v || '')));
    if (outputName?.value) form.append('output_name', outputName.value);
    if (engine?.value) form.append('engine', engine.value);

    // 추가 옵션 (A4/Letter, orientation, fit_mode)
    if (paperSize?.value) form.append('paper_size', paperSize.value);
    if (orientation?.value) form.append('orientation', orientation.value);
    if (fitMode?.value) form.append('fit_mode', fitMode.value);

    const headers = {};
    if (apiKeyRequired && apiKey?.value) headers['X-API-KEY'] = apiKey.value;

    mergeBtn.disabled = true;
    mergeBtn.textContent = translate('buttons.merging');
    setStatus(translate('messages.merging'), 'pending');

    try {
      const resp = await fetch(endpoints.merge || '/merge', { method: 'POST', body: form, headers });
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
            setStatus(translate('messages.merging_progress', { size: formatSizeCompact(received) }), 'pending');
          }
        }
        blob = new Blob(chunks, { type: resp.headers.get('content-type') || 'application/pdf' });
      } else {
        blob = await resp.blob();
      }

      const a = document.createElement('a');
      const url = URL.createObjectURL(blob);
      a.href = url;
      a.download = (outputName?.value || 'merged.pdf');
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setStatus(translate('messages.merged'), 'success');
    } catch (err) {
      console.error(err);
      const defaultError = translate('messages.merge_failed');
      const msg = err instanceof Error && err.message ? err.message : defaultError;
      alert(translate('messages.failed_prefix', { message: msg }));
      setStatus(msg, 'error');
    } finally {
      mergeBtn.disabled = false;
      mergeBtn.textContent = translate('buttons.merge');
    }
  });
})();
