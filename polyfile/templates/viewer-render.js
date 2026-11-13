/** @type {number} */
let byteHeight = 16;
/** @type {HTMLElement[]} */
let hexCells = [];
/** @type {HTMLElement[]} */
let asciiCells = [];
/** @type {HTMLElement[]} */
let readableCells = [];

/** @param {number} byte @returns {string} */
function displayByte(byte) {
  if (byte < 32) return String.fromCharCode(0x2400 + byte);
  if (byte === 127) return '\u2421';
  return String.fromCharCode(byte);
}

/** @param {string} className @returns {HTMLSpanElement} */
function createSpan(className) {
  const span = document.createElement('span');
  span.className = className;
  return span;
}

function rebuildRows() {
  const hex = getElement('hexdump');
  const ascii = getElement('ascii');
  hex.replaceChildren();
  ascii.replaceChildren();
  hexCells = [];
  asciiCells = [];
  for (let row = 0; row < viewerState.visibleRows; row += 1) {
    const hexRow = document.createElement('div');
    const asciiRow = document.createElement('div');
    hexRow.className = asciiRow.className = 'byteline';
    const address = createSpan('byterow');
    address.dataset['row'] = String(row);
    address.title = 'Double-click to jump to an address';
    hexRow.append(address);
    for (let column = 0; column < viewerState.bytesPerRow; column += 1) {
      const cell = row * viewerState.bytesPerRow + column;
      const hexCell = createSpan('byte');
      const asciiCell = createSpan('byte');
      hexCell.id = `byte${cell}`;
      asciiCell.id = `ascii${cell}`;
      hexCell.dataset['cell'] = asciiCell.dataset['cell'] = String(cell);
      hexRow.append(hexCell);
      asciiRow.append(asciiCell);
      hexCells.push(hexCell);
      asciiCells.push(asciiCell);
    }
    hex.append(hexRow);
    ascii.append(asciiRow);
  }
}

/** @param {number} offset @returns {boolean} */
function byteUndescribed(offset) {
  const source = viewerData.sources[viewerState.activeSource];
  return Boolean(
    source?.regions.some(([start, length]) => offset >= start && offset < start + length),
  );
}

function renderReadable() {
  const start = viewerState.rowOffset * viewerState.bytesPerRow;
  const bytes = getSourceBytes(viewerState.activeSource);
  const end = Math.min(bytes.length, start + hexCells.length);
  const fragment = document.createDocumentFragment();
  readableCells = [];
  for (let offset = start; offset < end; offset += 1) {
    const span = createSpan('readable-byte');
    span.dataset['cell'] = String(offset - start);
    span.classList.toggle('undescribed', byteUndescribed(offset));
    span.textContent = displayByte(bytes[offset] ?? 0);
    fragment.append(span);
    readableCells.push(span);
    if (bytes[offset] === 10) fragment.append(document.createElement('br'));
  }
  getElement('readablebytes').replaceChildren(fragment);
}

function renderViewport() {
  const bytes = getSourceBytes(viewerState.activeSource);
  const rowCount = Math.max(1, Math.ceil(bytes.length / viewerState.bytesPerRow));
  const maxRow = Math.max(0, rowCount - viewerState.visibleRows);
  viewerState.rowOffset = Math.max(0, Math.min(viewerState.rowOffset, maxRow));
  if (hexCells.length !== viewerState.visibleRows * viewerState.bytesPerRow) rebuildRows();
  const start = viewerState.rowOffset * viewerState.bytesPerRow;
  for (let index = 0; index < hexCells.length; index += 1) {
    const byte = bytes[start + index];
    const hex = hexCells[index];
    const ascii = asciiCells[index];
    if (!hex || !ascii) continue;
    hex.textContent = byte === undefined ? '' : byte.toString(16).padStart(2, '0');
    ascii.textContent = byte === undefined ? '' : displayByte(byte);
    const uncovered = byte !== undefined && byteUndescribed(start + index);
    hex.classList.toggle('undescribed', uncovered);
    ascii.classList.toggle('undescribed', uncovered);
  }
  document.querySelectorAll('#hexdump .byterow').forEach((label, row) => {
    label.textContent =
      ((viewerState.rowOffset + row) * viewerState.bytesPerRow)
        .toString(16)
        .padStart(Math.max(1, bytes.length.toString(16).length), '0') + ': ';
  });
  getElement('scrollheightproxy').style.height = `${byteHeight * (rowCount + 2)}px`;
  getElement('scrollcontainer').scrollTop = byteHeight * viewerState.rowOffset;
  renderReadable();
  renderHighlights();
}

function renderHighlights() {
  const cells = [...hexCells, ...asciiCells, ...readableCells];
  const kinds = ['highlighted', 'manually-focused', 'cursor', 'searchresult', 'search-current'];
  for (const cell of cells) cell.classList.remove(...kinds);
  const start = viewerState.rowOffset * viewerState.bytesPerRow;
  for (const [kind, ranges] of highlightRanges) {
    for (const range of ranges) {
      if (range.source !== viewerState.activeSource) continue;
      const first = Math.max(0, range.start - start);
      const last = Math.min(hexCells.length, range.start + range.length - start);
      for (let index = first; index < last; index += 1) {
        hexCells[index]?.classList.add(kind);
        asciiCells[index]?.classList.add(kind);
        readableCells[index]?.classList.add(kind);
      }
    }
  }
}

/** @param {number} offset */
function scrollToByte(offset) {
  if (!Number.isFinite(offset)) return;
  viewerState.rowOffset = Math.floor(Math.max(0, offset) / viewerState.bytesPerRow);
  renderViewport();
}

function resizeViewport() {
  const probe = document.querySelector('.hexeditor .byte');
  if (probe instanceof HTMLElement) byteHeight = Math.max(1, probe.getBoundingClientRect().height);
  const height = getElement('scrollcontainer').clientHeight;
  viewerState.visibleRows = Math.max(1, Math.floor(height / byteHeight) - 2);
  renderViewport();
}
