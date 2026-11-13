/** @param {number} row */
function jumpFromRow(row) {
  const current = (viewerState.rowOffset + row) * viewerState.bytesPerRow;
  const address = window.prompt(
    'To what address would you like to jump? (hexadecimal)',
    current.toString(16),
  );
  if (address === null || !/^(?:0x)?[0-9a-f]+$/i.test(address.trim())) return;
  scrollToByte(Number.parseInt(address.trim().replace(/^0x/i, ''), 16));
}

/** @param {MouseEvent} event */
function handleViewerAction(event) {
  const target = event.target;
  if (!(target instanceof Element)) return;
  const action = target.closest('[data-action]');
  if (!(action instanceof HTMLElement)) return;
  const node = nodesById.get(Number(action.dataset['uid']));
  switch (action.dataset['action']) {
    case 'download-file':
      downloadRange(viewerState.activeSource);
      break;
    case 'download':
      if (node) downloadRange(node.source, node.offset, node.size, node.type, node.extension);
      break;
    case 'decode':
      if (node) showDecoded(node.uid);
      break;
    case 'close-preview':
      /** @type {HTMLDialogElement} */ (getElement('decoded-preview')).close();
      break;
    default:
      return;
  }
  event.preventDefault();
  event.stopPropagation();
}

function initImages() {
  for (const node of viewerData.nodes) {
    if (!/^data:image\/(?:png|jpeg|gif|bmp|webp);base64,/.test(node.image)) continue;
    const holder = document.querySelector(`[data-image-uid="${node.uid}"]`);
    if (!holder) continue;
    const image = document.createElement('img');
    image.src = node.image;
    image.alt = node.name;
    image.style.maxWidth = '8em';
    holder.append(image);
  }
}

/** @param {"bytes" | "structure"} pane @param {boolean} [focus] */
function selectPane(pane, focus = false) {
  getElement('workspace').dataset['activePane'] = pane;
  const narrow = window.matchMedia('(max-width: 899px)').matches;
  for (const name of ['structure', 'bytes']) {
    const tab = getElement(`${name}-tab`);
    const selected = name === pane;
    tab.setAttribute('aria-selected', String(selected));
    tab.tabIndex = selected ? 0 : -1;
    const panel = getElement(`${name}-pane`);
    panel.setAttribute('role', narrow ? 'tabpanel' : 'region');
    panel.setAttribute('aria-labelledby', `${name}-${narrow ? 'tab' : 'title'}`);
  }
  if (focus) getElement(`${pane}-tab`).focus();
  resizeViewport();
}

/** @param {"bytes" | "text"} mode */
function selectByteView(mode) {
  getElement('scrollcapture').hidden = mode !== 'bytes';
  getElement('text-pane').hidden = mode !== 'text';
  getElement('byte-pane').dataset['display'] = mode;
  getElement('byte-view').setAttribute('aria-pressed', String(mode === 'bytes'));
  getElement('text-view').setAttribute('aria-pressed', String(mode === 'text'));
  resizeViewport();
}

function updateViewportStatus() {
  const bytes = getSourceBytes(viewerState.activeSource);
  const start = viewerState.rowOffset * viewerState.bytesPerRow;
  const end = Math.min(bytes.length, start + viewerState.visibleRows * viewerState.bytesPerRow);
  getElement('active-source').textContent = viewerState.activeSource;
  getElement('active-source').title = viewerState.activeSource;
  getElement('byte-position').textContent =
    bytes.length === 0
      ? 'Empty source'
      : `0x${start.toString(16)}–0x${Math.max(start, end - 1).toString(16)} / ` +
        `${bytes.length.toLocaleString()} bytes`;
}

/** @param {number} percentage */
function setStructureWidth(percentage) {
  const workspace = getElement('workspace');
  const minimum = Math.max(20, (240 / Math.max(1, workspace.clientWidth)) * 100);
  const maximum = Math.max(minimum, Math.min(60, 100 - (320 / workspace.clientWidth) * 100));
  const value = Math.max(minimum, Math.min(maximum, percentage));
  workspace.style.setProperty('--structure-width', `${value}%`);
  const separator = getElement('pane-separator');
  separator.setAttribute('aria-valuemin', String(Math.round(minimum)));
  separator.setAttribute('aria-valuemax', String(Math.round(maximum)));
  separator.setAttribute('aria-valuenow', String(Math.round(value)));
  resizeViewport();
}

function initSeparator() {
  const separator = getElement('pane-separator');
  separator.addEventListener('keydown', (event) => {
    const value = Number(separator.getAttribute('aria-valuenow'));
    const keys = { ArrowLeft: value - 2, ArrowRight: value + 2, Home: 20, End: 60 };
    if (!(event.key in keys)) return;
    event.preventDefault();
    setStructureWidth(keys[/** @type {keyof typeof keys} */ (event.key)]);
  });
  separator.addEventListener('pointerdown', (event) => {
    if (event.button !== 0) return;
    event.preventDefault();
    separator.setPointerCapture(event.pointerId);
    separator.focus();
  });
  separator.addEventListener('pointermove', (event) => {
    if (!separator.hasPointerCapture(event.pointerId)) return;
    const bounds = getElement('workspace').getBoundingClientRect();
    setStructureWidth(((event.clientX - bounds.left) / bounds.width) * 100);
  });
  separator.addEventListener('pointerup', (event) => {
    if (separator.hasPointerCapture(event.pointerId))
      separator.releasePointerCapture(event.pointerId);
  });
}

function initLayout() {
  getElement('theme').addEventListener('change', (event) => {
    document.documentElement.dataset['theme'] = /** @type {HTMLSelectElement} */ (
      event.target
    ).value;
  });
  for (const pane of /** @type {const} */ (['structure', 'bytes'])) {
    getElement(`${pane}-tab`).addEventListener('click', () => selectPane(pane));
    getElement(`${pane}-tab`).addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const next =
        event.key === 'Home'
          ? 'structure'
          : event.key === 'End'
            ? 'bytes'
            : pane === 'bytes'
              ? 'structure'
              : 'bytes';
      selectPane(next, true);
    });
  }
  getElement('byte-view').addEventListener('click', () => selectByteView('bytes'));
  getElement('text-view').addEventListener('click', () => selectByteView('text'));
  window.matchMedia('(max-width: 899px)').addEventListener('change', () => {
    const pane =
      getElement('workspace').dataset['activePane'] === 'structure' ? 'structure' : 'bytes';
    selectPane(pane);
  });
  document.addEventListener('polyfileviewport', updateViewportStatus);
  new ResizeObserver(resizeViewport).observe(getElement('byte-pane'));
  initSeparator();
  selectPane('bytes');
  updateViewportStatus();
}

let wheelRemainder = 0;

/** @param {WheelEvent} event */
function handleByteWheel(event) {
  const target = event.target;
  if (!(target instanceof Element) || target.closest('#scrollcontainer')) return;
  if (event.ctrlKey || event.shiftKey || Math.abs(event.deltaX) > Math.abs(event.deltaY)) return;
  if (event.deltaY === 0) return;
  event.preventDefault();
  const scale =
    event.deltaMode === 1
      ? byteHeight
      : event.deltaMode === 2
        ? getElement('byte-pane').clientHeight
        : 1;
  wheelRemainder += event.deltaY * scale;
  const rows = Math.trunc(wheelRemainder / byteHeight);
  wheelRemainder -= rows * byteHeight;
  if (rows !== 0) scrollToByte((viewerState.rowOffset + rows) * viewerState.bytesPerRow);
}

function initShell() {
  document.addEventListener('click', handleViewerAction);
  getElement('source').addEventListener('change', (event) => {
    const select = /** @type {HTMLSelectElement} */ (event.target);
    setSource(select.value, { preserveSearch: false });
  });
  const scroll = getElement('scrollcontainer');
  scroll.addEventListener('scroll', () => {
    if (!scroll.clientHeight || !scroll.getClientRects().length) return;
    const row = Math.floor(scroll.scrollTop / byteHeight);
    if (row !== viewerState.rowOffset) {
      viewerState.rowOffset = row;
      renderViewport();
    }
  });
  getElement('byte-pane').addEventListener('wheel', handleByteWheel, { passive: false });
  getElement('hexdump').addEventListener('dblclick', (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const row = target.closest('.byterow');
    if (row instanceof HTMLElement) jumpFromRow(Number(row.dataset['row']));
  });
  window.addEventListener('resize', resizeViewport);
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    viewerState.selectedNode = null;
    viewerState.selectedRange = null;
    clearHighlight('manually-focused');
    document.querySelectorAll('.tree_label.manually-focused').forEach((label) => {
      label.classList.remove('manually-focused');
    });
  });
}

initImages();
initShell();
initLayout();
initInspection();
initSearch();
resizeViewport();
getElement('loading').remove();
document.documentElement.dataset['viewerReady'] = 'true';
