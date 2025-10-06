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
        const defaultOptions = createDefaultOptions();
        const optionsForFile = fileOptions[index] || defaultOptions;
        if (widgets.rangeLabel) widgets.rangeLabel.textContent = translate('labels.range');
        if (widgets.rangeInput) {
          widgets.rangeInput.placeholder = translate('placeholders.range');
          widgets.rangeInput.dataset.idx = String(index);
          widgets.rangeInput.value = ranges[index] || '';
        }
        if (widgets.paper?.labelEl) widgets.paper.labelEl.textContent = translate('labels.paper_size');
        if (widgets.paper?.select) {
          widgets.paper.select.dataset.idx = String(index);
          widgets.paper.select.value = optionsForFile.paper_size || defaultOptions.paper_size;
        }
        if (widgets.orientation?.labelEl) widgets.orientation.labelEl.textContent = translate('labels.orientation');
        if (widgets.orientation?.select) {
          widgets.orientation.select.dataset.idx = String(index);
          widgets.orientation.select.value = optionsForFile.orientation || defaultOptions.orientation;
        }
        if (widgets.fit?.labelEl) widgets.fit.labelEl.textContent = translate('labels.fit_mode');
        if (widgets.fit?.select) {
          widgets.fit.select.dataset.idx = String(index);
          const orientationValue = widgets.orientation?.select?.value || optionsForFile.orientation || defaultOptions.orientation;
          if (ROTATION_ORIENTATIONS.has(orientationValue)) {
            optionsForFile.fit_mode = 'auto';
            widgets.fit.select.value = 'auto';
            widgets.fit.select.disabled = true;
          } else {
            widgets.fit.select.disabled = false;
            widgets.fit.select.value = optionsForFile.fit_mode || defaultOptions.fit_mode;
          }
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

  const createDefaultOptions = () => {
    const orientation = globalOptions.orientation || 'auto';
    return {
      paper_size: globalOptions.paper_size || 'auto',
      orientation,
      fit_mode: ROTATION_ORIENTATIONS.has(orientation)
        ? 'auto'
        : (globalOptions.fit_mode || 'auto'),
    };
  };

  const isRasterImageFile = (file) => {
    if (!file) return false;
    const type = (file.type || '').toLowerCase();
    if (type && (type.includes('jpeg') || type.includes('png'))) return true;
    const name = (file.name || '').toLowerCase();
    return name.endsWith('.jpg') || name.endsWith('.jpeg') || name.endsWith('.png');
  };

  const createOptionsForFile = (file) => {
    if (isRasterImageFile(file)) {
      return {
        paper_size: 'A4',
        orientation: 'portrait',
        fit_mode: 'letterbox',
      };
    }
    return createDefaultOptions();
  };

  const syncGlobalControls = () => {
    if (globalPaper) globalPaper.value = globalOptions.paper_size || 'auto';
    if (globalOrientation) globalOrientation.value = globalOptions.orientation || 'auto';
    if (globalFit) {
      const rotation = ROTATION_ORIENTATIONS.has(globalOptions.orientation);
      if (rotation) {
        globalFit.value = 'auto';
        globalFit.disabled = true;
      } else {
        globalFit.disabled = false;
        globalFit.value = globalOptions.fit_mode || 'auto';
      }
    }
  };

  const applyGlobalChange = (key, value, { forceFitAuto = false } = {}) => {
    globalOptions = { ...globalOptions, [key]: value };
    if (forceFitAuto) {
      globalOptions.fit_mode = 'auto';
    }

    const previousOptions = fileOptions.slice();
    fileOptions = files.map((_, index) => {
      const existing = previousOptions[index]
        ? { ...previousOptions[index] }
        : createDefaultOptions();
      const next = { ...existing, [key]: value };
      if (forceFitAuto) next.fit_mode = 'auto';
      return next;
    });

    refreshList();
    syncGlobalControls();
  };

  const addFiles = (newFiles) => {
    if (!newFiles?.length) return;
    const allowedMimeTypes = new Set(['application/pdf', 'image/jpeg', 'image/pjpeg', 'image/jpg', 'image/png', 'image/x-png']);
    const allowedExtensions = ['.pdf', '.jpg', '.jpeg', '.png'];
    const incoming = Array.from(newFiles).filter((f) => {
      const type = (f.type || '').toLowerCase();
      if (allowedMimeTypes.has(type)) return true;
      const name = (f.name || '').toLowerCase();
      return allowedExtensions.some((ext) => name.endsWith(ext));
    });
    if (incoming.length === 0) { setStatus(translate('messages.pdf_only'), 'error'); return; }
    setStatus('');
    incoming.forEach(f => {
      ensureFileId(f);
      files.push(f);
      ranges.push('');
      fileOptions.push(createOptionsForFile(f));
    });
    refreshList();
    syncGlobalControls();
  };

  const removeFile = (i) => {
    files.splice(i, 1);
    ranges.splice(i, 1);
    fileOptions.splice(i, 1);
    refreshList();
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
  let touchPointerId = null;
  let touchDragHandle = null;
  let lastPointerClientY = null;

  const SCROLL_EDGE_THRESHOLD = 80;
  const MAX_SCROLL_SPEED = 28;
  let autoScrollVelocity = 0;
  let autoScrollFrame = null;

  const stopAutoScroll = () => {
    autoScrollVelocity = 0;
    lastPointerClientY = null;
    if (autoScrollFrame !== null) {
      cancelAnimationFrame(autoScrollFrame);
      autoScrollFrame = null;
    }
  };

  const stepAutoScroll = () => {
    if (autoScrollVelocity === 0) {
      autoScrollFrame = null;
      return;
    }
    const scrollElement = document.scrollingElement || document.documentElement;
    if (!scrollElement) {
      stopAutoScroll();
      return;
    }
    const maxScrollTop = scrollElement.scrollHeight - window.innerHeight;
    if ((autoScrollVelocity < 0 && scrollElement.scrollTop <= 0) ||
        (autoScrollVelocity > 0 && scrollElement.scrollTop >= maxScrollTop)) {
      stopAutoScroll();
      return;
    }
    window.scrollBy(0, autoScrollVelocity);
    if (lastPointerClientY !== null) {
      updateDropTargetFromClientY(lastPointerClientY);
    }
    autoScrollFrame = requestAnimationFrame(stepAutoScroll);
  };

  const updateAutoScroll = (clientY) => {
    if (dragIndex === null) {
      stopAutoScroll();
      return;
    }
    if (!Number.isFinite(clientY)) {
      stopAutoScroll();
      return;
    }
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
    const edge = SCROLL_EDGE_THRESHOLD;
    let velocity = 0;

    if (clientY < edge) {
      const intensity = Math.min(1, (edge - clientY) / edge);
      velocity = -Math.max(1, Math.round(intensity * MAX_SCROLL_SPEED));
    } else if (clientY > viewportHeight - edge) {
      const intensity = Math.min(1, (clientY - (viewportHeight - edge)) / edge);
      velocity = Math.max(1, Math.round(intensity * MAX_SCROLL_SPEED));
    }

    if (velocity !== 0) {
      autoScrollVelocity = velocity;
      if (autoScrollFrame === null) autoScrollFrame = requestAnimationFrame(stepAutoScroll);
    } else {
      stopAutoScroll();
    }
  };

  const updateDropIndicator = (row, after) => {
    if (dropTarget === row && dropAfter === after) return;
    filesDiv.querySelectorAll('.file-row').forEach(r => {
      if (r !== row) r.classList.remove('drag-over-top', 'drag-over-bottom');
    });
    if (row) {
      row.classList.remove('drag-over-top', 'drag-over-bottom');
      row.classList.add(after ? 'drag-over-bottom' : 'drag-over-top');
      dropTarget = row;
      dropAfter = after;
    } else {
      dropTarget = null;
      dropAfter = false;
    }
  };

  const clearDragIndicators = () => {
    filesDiv.querySelectorAll('.file-row').forEach(row => {
      row.classList.remove('dragging', 'drag-over-top', 'drag-over-bottom');
    });
    dropTarget = null;
    dropAfter = false;
  };

  const updateDropTargetFromClientY = (clientY) => {
    const rows = Array.from(filesDiv.querySelectorAll('.file-row'));
    const candidates = rows.filter(row => !row.classList.contains('dragging'));
    if (!candidates.length) {
      updateDropIndicator(null, false);
      return;
    }

    let target = null;
    let after = false;
    for (const row of candidates) {
      const rect = row.getBoundingClientRect();
      if (clientY < rect.top) {
        target = row;
        after = false;
        break;
      }
      if (clientY <= rect.bottom) {
        target = row;
        after = clientY > rect.top + rect.height / 2;
        break;
      }
    }

    if (!target) {
      target = candidates[candidates.length - 1];
      after = true;
    }

    updateDropIndicator(target, after);
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
    lastPointerClientY = Number.isFinite(e.clientY) ? e.clientY : null;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(index));
  });

  filesDiv.addEventListener('dragover', (e) => {
    if (dragIndex === null) return;
    if (!Number.isFinite(e.clientY)) return;
    lastPointerClientY = e.clientY;
    updateDropTargetFromClientY(e.clientY);
    updateAutoScroll(e.clientY);
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  });

  document.addEventListener('dragover', (e) => {
    if (dragIndex === null) return;
    if (!Number.isFinite(e.clientY)) return;
    if (filesDiv.contains(e.target)) return;
    lastPointerClientY = e.clientY;
    updateDropTargetFromClientY(e.clientY);
    updateAutoScroll(e.clientY);
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
    stopAutoScroll();
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
    stopAutoScroll();
  });

  filesDiv.addEventListener('pointerdown', (e) => {
    if (e.pointerType === 'mouse') return;
    if (touchPointerId !== null) return;
    const handle = e.target.closest('.drag-handle');
    if (!handle) return;
    const row = handle.closest('.file-row');
    if (!row) return;
    const index = Number(row.dataset.index);
    if (Number.isNaN(index)) return;

    dragIndex = index;
    row.classList.add('dragging');
    touchPointerId = e.pointerId;
    touchDragHandle = handle;
    handle.setPointerCapture?.(e.pointerId);
    if (Number.isFinite(e.clientY)) {
      lastPointerClientY = e.clientY;
      updateDropTargetFromClientY(e.clientY);
      updateAutoScroll(e.clientY);
    }
    e.preventDefault();
  });

  filesDiv.addEventListener('pointermove', (e) => {
    if (touchPointerId === null || e.pointerId !== touchPointerId) return;
    e.preventDefault();
    if (!Number.isFinite(e.clientY)) return;
    lastPointerClientY = e.clientY;
    updateDropTargetFromClientY(e.clientY);
    updateAutoScroll(e.clientY);
  });

  const handlePointerRelease = (e) => {
    if (touchPointerId === null || e.pointerId !== touchPointerId) return;
    e.preventDefault();
    let targetIndex;
    if (dropTarget) {
      targetIndex = Number(dropTarget.dataset.index);
      if (Number.isNaN(targetIndex)) targetIndex = files.length;
      if (dropAfter) targetIndex += 1;
    } else {
      targetIndex = files.length;
    }
    if (dragIndex !== null) {
      if (dragIndex < targetIndex) targetIndex -= 1;
      reorderItems(dragIndex, targetIndex);
    }
    dragIndex = null;
    clearDragIndicators();
    if (touchDragHandle) {
      touchDragHandle.releasePointerCapture?.(touchPointerId);
    }
    touchDragHandle = null;
    touchPointerId = null;
    stopAutoScroll();
  };

  filesDiv.addEventListener('pointerup', handlePointerRelease);
  filesDiv.addEventListener('pointercancel', handlePointerRelease);

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
    const target = fileOptions[i] || (fileOptions[i] = createDefaultOptions());
    target[key] = select.value;

    if (key === 'orientation') {
      const row = select.closest('.file-row');
      const fitSelect = row?.querySelector('select.option-select[data-key="fit_mode"]');
      if (ROTATION_ORIENTATIONS.has(select.value)) {
        target.fit_mode = 'auto';
        if (fitSelect) {
          fitSelect.value = 'auto';
          fitSelect.disabled = true;
        }
      } else if (fitSelect) {
        fitSelect.disabled = false;
      }
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

    const latestOptions = Array.from(document.querySelectorAll('.file-row')).map((row) => {
      const idx = Number(row.dataset.index);
      const existing = fileOptions[idx] || createDefaultOptions();
      const selects = row.querySelectorAll('.option-select');
      const next = { ...existing };
      selects.forEach((select) => {
        const key = select.dataset.key;
        if (!key) return;
        next[key] = select.value;
      });
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
      notyf.success(translate('messages.merged'));
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
