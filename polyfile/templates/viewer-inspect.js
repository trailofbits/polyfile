/** @type {Set<HTMLElement>} */
const hoveredNodeLabels = new Set();
let detailsKey = '';
let copyGeneration = 0;
/** @type {HTMLElement|null} */
let copyReturnFocus = null;

/** @param {number} uid @returns {HTMLElement|null} */
function nodeChildren(uid) {
  return document.getElementById(`children${uid}`);
}

/** @param {number} uid @returns {boolean} */
function isNodeExpanded(uid) {
  const children = nodeChildren(uid);
  return children !== null && !children.hidden;
}

/** @param {number} uid @param {boolean} expanded */
function setNodeExpanded(uid, expanded) {
  const children = nodeChildren(uid);
  const toggle = document.querySelector(`[data-action="toggle-node"][data-node-uid="${uid}"]`);
  if (!children || !(toggle instanceof HTMLElement)) return;
  children.hidden = !expanded;
  toggle.setAttribute('aria-expanded', String(expanded));
  toggle.textContent = expanded ? '▾' : '▸';
  const name = nodesById.get(uid)?.name || 'node';
  toggle.setAttribute('aria-label', `${expanded ? 'Collapse' : 'Expand'} ${name}`);
}

/** Reveal a node and its ancestors without changing the selected range. @param {number} uid */
function revealNode(uid) {
  document.dispatchEvent(new CustomEvent('polyfile:reveal-node', { detail: { uid } }));
  let node = nodesById.get(uid);
  while (node) {
    const item = document.querySelector(`li[data-node-uid="${node.uid}"]`);
    if (item instanceof HTMLElement) item.hidden = false;
    if (node.parent === null) break;
    setNodeExpanded(node.parent, true);
    node = nodesById.get(node.parent);
  }
}

function clearSelectedLabels() {
  document
    .querySelectorAll('.tree_label[aria-pressed="true"], .tree_label.manually-focused')
    .forEach((label) => {
      label.classList.remove('manually-focused');
      label.setAttribute('aria-pressed', 'false');
    });
}

function showSelectedBytes() {
  if (!window.matchMedia('(max-width: 899px)').matches) return;
  selectPane('bytes');
  getElement('bytes-tab').focus();
}

/** @param {number} uid */
function selectNode(uid) {
  const node = nodesById.get(uid);
  if (!node) return;
  revealNode(uid);
  setSource(node.source);
  viewerState.selectedNode = uid;
  viewerState.selectedRange = { source: node.source, start: node.offset, length: node.size };
  clearSelectedLabels();
  const label = getNodeLabel(uid);
  label?.classList.add('manually-focused');
  label?.setAttribute('aria-pressed', 'true');
  setHighlight('manually-focused', node.source, node.offset, node.size);
  scrollToByte(node.offset);
  updateSelectionDetails();
  showSelectedBytes();
}

/** @param {number} offset @param {number} [length] */
function hoverByte(offset, length = 1) {
  clearHover();
  const bytes = getSourceBytes(viewerState.activeSource);
  if (!Number.isInteger(offset) || offset < 0 || offset >= bytes.length) return;
  const end = Math.min(bytes.length, offset + length);
  setHighlight('cursor', viewerState.activeSource, offset, end - offset);
  for (let position = offset; position < end; position += 1) {
    for (const node of nodesAtByte(viewerState.activeSource, position)) {
      const label = getNodeLabel(node.uid);
      if (!label) continue;
      label.classList.add('highlighted');
      hoveredNodeLabels.add(label);
    }
  }
}

function clearHover() {
  clearHighlight('cursor');
  clearHighlight('highlighted');
  for (const label of hoveredNodeLabels) label.classList.remove('highlighted');
  hoveredNodeLabels.clear();
}

/** @param {number} uid */
function showDecoded(uid) {
  const node = nodesById.get(uid);
  if (!node) return;
  selectNode(uid);
  selectByteView('text');
  selectPane('bytes');
}

/** @param {string} tag @param {string} text @returns {HTMLElement} */
function inspectionText(tag, text) {
  const element = document.createElement(tag);
  element.textContent = text;
  return element;
}

/** @param {HTMLDListElement} list @param {string} name @param {string} value */
function appendInspectionDetail(list, name, value) {
  list.append(inspectionText('dt', name), inspectionText('dd', value));
}

/** @param {string} label @param {() => void} action @returns {HTMLButtonElement} */
function inspectionButton(label, action) {
  const button = document.createElement('button');
  button.type = 'button';
  button.textContent = label;
  button.addEventListener('click', action);
  return button;
}

/** @param {ViewerRange} range @param {ViewerNode|undefined} node @returns {HTMLElement} */
function inspectionActions(range, node) {
  const actions = document.createElement('div');
  actions.className = 'inspection-actions';
  actions.append(
    inspectionButton('Download selection', () => {
      downloadRange(range.source, range.start, range.length, node?.type, node?.extension);
    }),
    inspectionButton('Copy offset', () => {
      void copyInspectionText(`0x${range.start.toString(16)}`);
    }),
    inspectionButton('Copy bytes as hex', () => {
      void copySelectedHex(range);
    }),
  );
  return actions;
}

function updateSelectionDetails() {
  const uid = viewerState.selectedNode;
  const node = uid === null ? undefined : nodesById.get(uid);
  const range = viewerState.selectedRange;
  const key = `${viewerState.activeSource}:${uid}:${range?.start}:${range?.length}`;
  if (key === detailsKey) return;
  detailsKey = key;
  const details = getElement('selection-details');
  if (!range || range.source !== viewerState.activeSource) {
    clearSelectedLabels();
    details.replaceChildren(
      inspectionText('p', 'Select a structure node to inspect its byte range.'),
    );
    return;
  }
  const list = document.createElement('dl');
  appendInspectionDetail(list, 'Source', range.source);
  appendInspectionDetail(list, 'Offset', `0x${range.start.toString(16)} (${range.start})`);
  appendInspectionDetail(list, 'Length', `${range.length.toLocaleString()} bytes`);
  appendInspectionDetail(list, 'MIME type', node?.type || 'application/octet-stream');
  if (node?.analysis_status) {
    appendInspectionDetail(list, 'Analysis', `${node.analysis_status}: ${node.analysis_message}`);
  }
  const status = inspectionText('p', '');
  status.id = 'inspection-status';
  status.setAttribute('role', 'status');
  details.replaceChildren(
    inspectionText('h3', node?.name || 'Byte selection'),
    list,
    inspectionActions(range, node),
    status,
  );
}

/** @param {string} message */
function inspectionStatus(message) {
  const status = document.getElementById('inspection-status');
  if (status) status.textContent = message;
}

/** @returns {HTMLDialogElement} */
function copyDialog() {
  const existing = document.getElementById('clipboard-fallback');
  if (existing instanceof HTMLDialogElement) return existing;
  const dialog = document.createElement('dialog');
  dialog.id = 'clipboard-fallback';
  dialog.className = 'copy-dialog';
  dialog.setAttribute('aria-labelledby', 'clipboard-title');
  const title = inspectionText('h2', 'Copy selected text');
  title.id = 'clipboard-title';
  const input = document.createElement('textarea');
  input.readOnly = true;
  input.spellcheck = false;
  input.setAttribute('aria-label', 'Text to copy');
  const instruction = inspectionText(
    'p',
    'Use your system copy command to copy the selected text.',
  );
  dialog.append(
    title,
    instruction,
    input,
    inspectionButton('Close', () => dialog.close()),
  );
  dialog.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') event.stopPropagation();
  });
  dialog.addEventListener('close', () => {
    if (copyReturnFocus?.isConnected) copyReturnFocus.focus();
  });
  document.body.append(dialog);
  return dialog;
}

/** @param {string} text */
function showCopyFallback(text) {
  const dialog = copyDialog();
  copyReturnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  const input = dialog.querySelector('textarea');
  if (!input) throw new Error('The copy dialog is missing its text field.');
  input.value = text;
  if (!dialog.open) dialog.showModal();
  input.focus();
  input.select();
  inspectionStatus('Clipboard access is unavailable. Copy the selected text in the dialog.');
}

/** @param {string} text */
async function copyInspectionText(text) {
  if (!navigator.clipboard) {
    showCopyFallback(text);
    return;
  }
  try {
    await navigator.clipboard.writeText(text);
    inspectionStatus('Copied to clipboard.');
  } catch {
    showCopyFallback(text);
  }
}

/** @param {Uint8Array} bytes @param {number} start @param {number} end @returns {string} */
function inspectionHexChunk(bytes, start, end) {
  const values = [];
  for (let index = start; index < end; index += 1) {
    values.push((bytes[index] ?? 0).toString(16).padStart(2, '0'));
  }
  return values.join(' ');
}

/** @param {ViewerRange} range */
async function copySelectedHex(range) {
  copyGeneration += 1;
  const generation = copyGeneration;
  const bytes = getSourceBytes(range.source);
  const end = range.start + range.length;
  if (range.start < 0 || end > bytes.length) {
    inspectionStatus('The selected range extends beyond this source. Select a valid range.');
    return;
  }
  const pieces = [];
  for (let offset = range.start; offset < end; offset += 16384) {
    pieces.push(inspectionHexChunk(bytes, offset, Math.min(end, offset + 16384)));
    inspectionStatus(`Preparing ${range.length.toLocaleString()} bytes…`);
    await new Promise((resolve) => setTimeout(resolve, 0));
    if (generation !== copyGeneration) return;
  }
  await copyInspectionText(pieces.join(' '));
}

/** @returns {HTMLInputElement} */
function gotoInput() {
  const input = getElement('goto');
  if (!(input instanceof HTMLInputElement)) throw new Error('Go to offset input is unavailable.');
  return input;
}

/** @param {string} text @returns {number} */
function parseInspectionOffset(text) {
  if (!/^(?:0x[\da-f]+|\d+)$/i.test(text.trim())) {
    throw new Error('Enter a decimal offset or a hexadecimal offset beginning with 0x.');
  }
  const offset = Number(text.trim());
  if (!Number.isSafeInteger(offset))
    throw new Error('Enter an offset within the safe integer range.');
  const length = getSourceBytes(viewerState.activeSource).length;
  if (length === 0) throw new Error('This source has no bytes to navigate.');
  if (offset >= length) {
    throw new Error(`Enter an offset from 0 to 0x${(length - 1).toString(16)} (${length - 1}).`);
  }
  return offset;
}

/** @param {SubmitEvent} event */
function submitGoto(event) {
  event.preventDefault();
  const input = gotoInput();
  try {
    const offset = parseInspectionOffset(input.value);
    input.removeAttribute('aria-invalid');
    getElement('goto-error').textContent = '';
    clearSelectedLabels();
    viewerState.selectedNode = null;
    viewerState.selectedRange = { source: viewerState.activeSource, start: offset, length: 1 };
    setHighlight('manually-focused', viewerState.activeSource, offset, 1);
    scrollToByte(offset);
    updateSelectionDetails();
    showSelectedBytes();
  } catch (error) {
    input.setAttribute('aria-invalid', 'true');
    getElement('goto-error').textContent =
      error instanceof Error ? error.message : 'Invalid offset.';
  }
}

/** @param {MouseEvent} event */
function handleInspectionClick(event) {
  const target = event.target;
  if (!(target instanceof Element)) return;
  const toggle = target.closest('[data-action="toggle-node"]');
  if (toggle instanceof HTMLElement) {
    const uid = Number(toggle.dataset['nodeUid']);
    setNodeExpanded(uid, !isNodeExpanded(uid));
    return;
  }
  const label = target.closest('.tree_label');
  if (label instanceof HTMLElement) selectNode(Number(label.dataset['uid']));
}

/** @param {PointerEvent} event */
function previewInspectionNode(event) {
  const target = event.target;
  if (!(target instanceof Element)) return;
  const label = target.closest('.tree_label');
  if (!(label instanceof HTMLElement)) return;
  const node = nodesById.get(Number(label.dataset['uid']));
  if (node?.source === viewerState.activeSource) {
    setHighlight('highlighted', node.source, node.offset, node.size);
  }
}

/** @param {PointerEvent} event */
function previewInspectionByte(event) {
  const target = event.target;
  if (!(target instanceof HTMLElement) || target.dataset['cell'] === undefined) return;
  const offset =
    target.dataset['offset'] === undefined
      ? viewerState.rowOffset * viewerState.bytesPerRow + Number(target.dataset['cell'])
      : Number(target.dataset['offset']);
  hoverByte(offset, Number(target.dataset['length'] || 1));
}

/** @param {KeyboardEvent} event */
function clearInspectionOnEscape(event) {
  if (event.key !== 'Escape' || document.querySelector('dialog[open]')) return;
  viewerState.selectedNode = null;
  viewerState.selectedRange = null;
  clearSelectedLabels();
  clearHighlight('manually-focused');
  updateSelectionDetails();
}

function initInspection() {
  const tree = /** @type {HTMLElement|null} */ (document.querySelector('.tree'));
  tree?.addEventListener('click', handleInspectionClick);
  tree?.addEventListener('pointerover', previewInspectionNode);
  tree?.addEventListener('pointerout', (event) => {
    const label = event.target instanceof Element ? event.target.closest('.tree_label') : null;
    if (label && !(event.relatedTarget instanceof Node && label.contains(event.relatedTarget))) {
      clearHover();
    }
  });
  tree?.addEventListener('pointerleave', clearHover);
  const editor = /** @type {HTMLElement|null} */ (document.querySelector('.hexeditor'));
  editor?.addEventListener('pointerover', previewInspectionByte);
  editor?.addEventListener('pointerleave', clearHover);
  getElement('goto-form').hidden = false;
  getElement('goto-form').addEventListener('submit', submitGoto);
  document.addEventListener('polyfileviewport', updateSelectionDetails);
  document.addEventListener('keydown', clearInspectionOnEscape);
  updateSelectionDetails();
}
