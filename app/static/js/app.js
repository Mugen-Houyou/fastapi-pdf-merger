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
  const globalPaper = $('#globalPaper');
  const globalOrientation = $('#globalOrientation');
  const globalFit = $('#globalFit');

  const { apiKeyRequired, defaults, endpoints, i18n = {}, locale = 'en', limits = {} } = window.__PDFMERGER__ || {
    apiKeyRequired: false,
    defaults: { output_name: 'merged.pdf', paper_size: 'auto', orientation: 'auto', fit_mode: 'auto' },
    endpoints: { merge: '/merge' },
    i18n: {},
    locale: 'en',
    limits: {}
  };

  const ROTATION_ORIENTATIONS = new Set(['rotate90', 'rotate180', 'rotate270']);
  const FALLBACK_DEFAULTS = {
    paper_size: 'A4',
    orientation: 'portrait',
    fit_mode: 'letterbox',
  };

  let globalOptions = {
    paper_size: defaults.paper_size || 'auto',
    orientation: defaults.orientation || 'auto',
    fit_mode: defaults.fit_mode || 'auto',
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

  let files = [];
  let ranges = [];
  let fileOptions = [];
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
    const hasImages = hasImageUploads();
    const allowAuto = !hasImages;
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

      const side = document.createElement('div');
      side.className = 'file-side';

      const rangeField = document.createElement('label');
      rangeField.className = 'file-field';
      const rangeLabel = document.createElement('span');
      rangeLabel.className = 'field-label';
      const rangeInput = document.createElement('input');
      rangeInput.type = 'text';
      rangeInput.className = 'range-input';
      rangeInput.autocomplete = 'off';
      rangeField.appendChild(rangeLabel);
      rangeField.appendChild(rangeInput);

      const optionsWrapper = document.createElement('div');
      optionsWrapper.className = 'file-options';

      const makeSelect = (key, options) => {
        const wrapper = document.createElement('label');
        wrapper.className = 'file-field';
        const title = document.createElement('span');
        title.className = 'field-label';
        const select = document.createElement('select');
        select.className = 'option-select';
        select.dataset.key = key;
        options.forEach(({ value, label }) => {
          const opt = document.createElement('option');
          opt.value = value;
          opt.textContent = label;
          select.appendChild(opt);
        });
        // wrapper.appendChild(title);
        wrapper.appendChild(select);
        optionsWrapper.appendChild(wrapper);
        return { wrapper, select, labelEl: title };
      };

      const selects = {
        rangeLabel,
        rangeInput,
        paper: makeSelect('paper_size', [
          { value: 'auto', label: translate('options.paper_size.auto') },
          { value: 'A4', label: translate('options.paper_size.A4') },
          { value: 'Letter', label: translate('options.paper_size.Letter') },
        ]),
        orientation: makeSelect('orientation', [
          { value: 'auto', label: translate('options.orientation.auto') },
          { value: 'portrait', label: translate('options.orientation.portrait') },
          { value: 'landscape', label: translate('options.orientation.landscape') },
          { value: 'rotate90', label: translate('options.orientation.rotate90') },
          { value: 'rotate180', label: translate('options.orientation.rotate180') },
          { value: 'rotate270', label: translate('options.orientation.rotate270') },
        ]),
        fit: makeSelect('fit_mode', [
          { value: 'auto', label: translate('options.fit_mode.auto') },
          { value: 'letterbox', label: translate('options.fit_mode.letterbox') },
          { value: 'crop', label: translate('options.fit_mode.crop') },
        ]),
      };

      side.appendChild(rangeField);
      actions.appendChild(optionsWrapper);

      row.appendChild(main);
      row.appendChild(side);

      row.__structureReady = true;
      row.__widgets = selects;
      return row;
    };

    const updateRow = (row, file, index) => {
      const defaultOptions = createDefaultOptions(hasImages);
      const currentOptions = fileOptions[index]
        ? { ...defaultOptions, ...fileOptions[index] }
        : { ...defaultOptions };

      if (!allowAuto) {
        currentOptions.paper_size = sanitizeValue('paper_size', currentOptions.paper_size, allowAuto);
        currentOptions.orientation = sanitizeValue('orientation', currentOptions.orientation, allowAuto);
        currentOptions.fit_mode = sanitizeValue('fit_mode', currentOptions.fit_mode, allowAuto);
      }

      const rotationSelected = ROTATION_ORIENTATIONS.has(currentOptions.orientation);
      if (rotationSelected) {
        currentOptions.fit_mode = allowAuto ? 'auto' : defaultOptions.fit_mode;
      }

      fileOptions[index] = currentOptions;

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
        removeBtn.style.marginRight = '1em';
      }

      const widgets = row.__widgets;
      if (widgets) {
        if (widgets.rangeLabel) widgets.rangeLabel.textContent = translate('labels.range');
        if (widgets.rangeInput) {
          widgets.rangeInput.placeholder = translate('placeholders.range');
          widgets.rangeInput.dataset.idx = String(index);
          widgets.rangeInput.value = ranges[index] || '';
        }
        if (widgets.paper?.labelEl) widgets.paper.labelEl.textContent = translate('labels.paper_size');
        if (widgets.paper?.select) {
          widgets.paper.select.dataset.idx = String(index);
          widgets.paper.select.value = currentOptions.paper_size;
          updateAutoOptionAvailability(
            widgets.paper.select,
            allowAuto,
            currentOptions.paper_size || defaultOptions.paper_size,
          );
        }
        if (widgets.orientation?.labelEl) widgets.orientation.labelEl.textContent = translate('labels.orientation');
        if (widgets.orientation?.select) {
          widgets.orientation.select.dataset.idx = String(index);
          widgets.orientation.select.value = currentOptions.orientation;
          updateAutoOptionAvailability(
            widgets.orientation.select,
            allowAuto,
            currentOptions.orientation || defaultOptions.orientation,
          );
        }
        if (widgets.fit?.labelEl) widgets.fit.labelEl.textContent = translate('labels.fit_mode');
        if (widgets.fit?.select) {
          widgets.fit.select.dataset.idx = String(index);
          const orientationValue = widgets.orientation?.select?.value || currentOptions.orientation;
          const isRotation = ROTATION_ORIENTATIONS.has(orientationValue);
          if (isRotation) {
            widgets.fit.select.disabled = true;
          } else {
            widgets.fit.select.disabled = false;
          }
          widgets.fit.select.value = currentOptions.fit_mode;
          updateAutoOptionAvailability(
            widgets.fit.select,
            !isRotation && allowAuto,
            currentOptions.fit_mode || defaultOptions.fit_mode,
          );
        }
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

  const createDefaultOptions = (hasImages = hasImageUploads()) => {
    const allowAuto = !hasImages;
    const basePaper = globalOptions.paper_size || 'auto';
    const baseOrientation = globalOptions.orientation || 'auto';
    const baseFit = globalOptions.fit_mode || 'auto';
    const paperSize = sanitizeValue('paper_size', basePaper, allowAuto);
    const orientation = sanitizeValue('orientation', baseOrientation, allowAuto);
    const rotationSelected = ROTATION_ORIENTATIONS.has(orientation);
    let fitMode;
    if (rotationSelected) {
      fitMode = allowAuto ? 'auto' : FALLBACK_DEFAULTS.fit_mode;
    } else {
      fitMode = sanitizeValue('fit_mode', baseFit, allowAuto);
    }
    return {
      paper_size: paperSize,
      orientation,
      fit_mode: fitMode,
    };
  };

  const syncGlobalControls = () => {
    const hasImages = hasImageUploads();
    const allowAuto = !hasImages;
    if (globalPaper) {
      const value = sanitizeValue('paper_size', globalOptions.paper_size || 'auto', allowAuto);
      globalPaper.value = value;
      updateAutoOptionAvailability(globalPaper, allowAuto, value);
    }
    if (globalOrientation) {
      const value = sanitizeValue('orientation', globalOptions.orientation || 'auto', allowAuto);
      globalOrientation.value = value;
      updateAutoOptionAvailability(globalOrientation, allowAuto, value);
    }
    if (globalFit) {
      const orientationValue = globalOrientation ? globalOrientation.value : globalOptions.orientation || 'auto';
      const rotation = ROTATION_ORIENTATIONS.has(orientationValue);
      if (rotation) {
        const rotationValue = sanitizeValue('fit_mode', 'auto', allowAuto);
        globalFit.value = rotationValue;
        globalFit.disabled = true;
        updateAutoOptionAvailability(globalFit, false, rotationValue);
      } else {
        const value = sanitizeValue('fit_mode', globalOptions.fit_mode || 'auto', allowAuto);
        globalFit.disabled = false;
        globalFit.value = value;
        updateAutoOptionAvailability(globalFit, allowAuto, value);
      }
    }
  };

  const applyGlobalChange = (key, value, { forceFitAuto = false } = {}) => {
    const hasImages = hasImageUploads();
    const allowAuto = !hasImages;
    const sanitizedValue = sanitizeValue(key, value, allowAuto);
    globalOptions = { ...globalOptions, [key]: sanitizedValue };
    if (forceFitAuto) {
      globalOptions.fit_mode = sanitizeValue('fit_mode', 'auto', allowAuto);
    }

    const previousOptions = fileOptions.slice();
    fileOptions = files.map((_, index) => {
      const existing = previousOptions[index]
        ? { ...previousOptions[index] }
        : {};
      const defaults = createDefaultOptions(hasImages);
      const next = { ...defaults, ...existing, [key]: sanitizedValue };
      if (!allowAuto) {
        next.paper_size = sanitizeValue('paper_size', next.paper_size, allowAuto);
        next.orientation = sanitizeValue('orientation', next.orientation, allowAuto);
        next.fit_mode = sanitizeValue('fit_mode', next.fit_mode, allowAuto);
      }
      if (forceFitAuto) {
        next.fit_mode = sanitizeValue('fit_mode', 'auto', allowAuto);
      } else if (!allowAuto && (!next.fit_mode || next.fit_mode === 'auto')) {
        next.fit_mode = defaults.fit_mode;
      }
      return next;
    });

    refreshList();
    syncGlobalControls();
  };

  const isJpegFile = (file) => {
    if (!file) return false;
    const type = (file.type || '').toLowerCase();
    if (type === 'image/jpeg') return true;
    const name = (file.name || '').toLowerCase();
    return name.endsWith('.jpg') || name.endsWith('.jpeg');
  };

  const isSupportedFile = (file) => {
    if (!file) return false;
    const type = (file.type || '').toLowerCase();
    if (type === 'application/pdf' || type === 'image/jpeg') return true;
    const name = (file.name || '').toLowerCase();
    return name.endsWith('.pdf') || name.endsWith('.jpg') || name.endsWith('.jpeg');
  };

  const hasImageUploads = () => files.some((file) => isJpegFile(file));

  const sanitizeValue = (key, value, allowAuto) => {
    if (allowAuto) return value;
    if (value === 'auto' || !value) return FALLBACK_DEFAULTS[key];
    return value;
  };

  const updateAutoOptionAvailability = (select, allowAuto, fallbackValue) => {
    if (!select) return;
    const autoOption = select.querySelector('option[value="auto"]');
    if (autoOption) autoOption.disabled = !allowAuto;
    if (!allowAuto && select.value === 'auto') {
      select.value = fallbackValue;
    }
  };

  const addFiles = (newFiles) => {
    if (!newFiles?.length) return;
    const incoming = Array.from(newFiles).filter(isSupportedFile);
    if (incoming.length === 0) { setStatus(translate('messages.pdf_only'), 'error'); return; }
    setStatus('');
    incoming.forEach(f => {
      ensureFileId(f);
      files.push(f);
      ranges.push('');
      const defaults = createDefaultOptions(hasImageUploads());
      fileOptions.push({ ...defaults });
    });
    refreshList();
    syncGlobalControls();
  };

  const removeFile = (i) => {
    files.splice(i, 1);
    ranges.splice(i, 1);
    fileOptions.splice(i, 1);
    refreshList();
    syncGlobalControls();
  };

  filesDiv.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-action]');
    if (!btn) return;
    const i = Number(btn.dataset.index);
    if (Number.isNaN(i)) return;
    if (btn.dataset.action === 'remove') {
      if (!window.confirm(translate('messages.confirm_remove'))) return;
      removeFile(i);
    }
  });

  const reorderItems = (from, to) => {
    if (from === to) return;
    if (from < 0 || from >= files.length) return;
    if (to < 0) to = 0;
    if (to > files.length) to = files.length;
    const [movedFile] = files.splice(from, 1);
    const [movedRange] = ranges.splice(from, 1);
    const [movedOptions] = fileOptions.splice(from, 1);
    files.splice(to, 0, movedFile);
    ranges.splice(to, 0, movedRange);
    fileOptions.splice(to, 0, movedOptions);
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

  filesDiv.addEventListener('change', (e) => {
    const select = e.target;
    if (!select.classList.contains('option-select')) return;
    const i = Number(select.dataset.idx);
    const key = select.dataset.key;
    if (Number.isNaN(i) || !key) return;
    const hasImages = hasImageUploads();
    const allowAuto = !hasImages;
    const target = fileOptions[i] || (fileOptions[i] = createDefaultOptions(hasImages));
    target[key] = allowAuto ? select.value : sanitizeValue(key, select.value, allowAuto);

    if (key === 'orientation') {
      const row = select.closest('.file-row');
      const fitSelect = row?.querySelector('select.option-select[data-key="fit_mode"]');
      if (ROTATION_ORIENTATIONS.has(select.value)) {
        target.fit_mode = sanitizeValue('fit_mode', 'auto', allowAuto);
        if (fitSelect) {
          fitSelect.value = target.fit_mode;
          fitSelect.disabled = true;
          updateAutoOptionAvailability(fitSelect, false, target.fit_mode);
        }
      } else if (fitSelect) {
        fitSelect.disabled = false;
        updateAutoOptionAvailability(
          fitSelect,
          allowAuto,
          sanitizeValue('fit_mode', fitSelect.value, allowAuto),
        );
      }
    } else if (!allowAuto) {
      target.paper_size = sanitizeValue('paper_size', target.paper_size, allowAuto);
      target.orientation = sanitizeValue('orientation', target.orientation, allowAuto);
      target.fit_mode = sanitizeValue('fit_mode', target.fit_mode, allowAuto);
    }
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
      fileOptions.reverse();
      refreshList();
      setStatus(translate('messages.reordered'), 'info');
    });
  }

  clearBtn.addEventListener('click', () => {
    if (files.length === 0) return;
    if (!window.confirm(translate('messages.confirm_clear'))) return;
    files = [];
    ranges = [];
    fileOptions = [];
    refreshList();
    setStatus(translate('messages.cleared'), 'info');
    syncGlobalControls();
  });

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

    const hasImages = hasImageUploads();
    const allowAuto = !hasImages;
    const latestOptions = Array.from(document.querySelectorAll('.file-row')).map((row) => {
      const idx = Number(row.dataset.index);
      const existing = fileOptions[idx] || createDefaultOptions(hasImages);
      const selects = row.querySelectorAll('.option-select');
      const next = { ...existing };
      selects.forEach((select) => {
        const key = select.dataset.key;
        if (!key) return;
        next[key] = select.value;
      });
      if (!allowAuto) {
        next.paper_size = sanitizeValue('paper_size', next.paper_size, allowAuto);
        next.orientation = sanitizeValue('orientation', next.orientation, allowAuto);
        next.fit_mode = sanitizeValue('fit_mode', next.fit_mode, allowAuto);
      }
      return next;
    });

    fileOptions = latestOptions;
    form.append('options', JSON.stringify(latestOptions));

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

  if (globalPaper) {
    globalPaper.addEventListener('change', () => {
      const value = globalPaper.value || 'auto';
      applyGlobalChange('paper_size', value);
    });
  }

  if (globalOrientation) {
    globalOrientation.addEventListener('change', () => {
      const value = globalOrientation.value || 'auto';
      const isRotation = ROTATION_ORIENTATIONS.has(value);
      applyGlobalChange('orientation', value, { forceFitAuto: isRotation });
    });
  }

  if (globalFit) {
    globalFit.addEventListener('change', () => {
      if (ROTATION_ORIENTATIONS.has(globalOptions.orientation)) {
        syncGlobalControls();
        return;
      }
      const value = globalFit.value || 'auto';
      applyGlobalChange('fit_mode', value);
    });
  }

  syncGlobalControls();
})();
