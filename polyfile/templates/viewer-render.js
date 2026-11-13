/** @type {number} */
let byteHeight = 24;
/** @type {HTMLElement[]} */
let hexCells = [];
/** @type {HTMLElement[]} */
let asciiCells = [];
/** @type {{element: HTMLElement, start: number, end: number}[]} */
let readableRanges = [];
let renderedColumns = 0;
/** @type {string[]} */
let paintedHighlightKinds = [];
const utf8Decoder = new TextDecoder('utf-8', { ignoreBOM: true });

/** @param {number} byte @returns {string} */
function displayByte(byte) {
  if (byte < 32) return String.fromCharCode(0x2400 + byte);
  if (byte === 127) return '\u2421';
  return byte < 127 ? String.fromCharCode(byte) : '\u00b7';
}

/** @param {string} className @returns {HTMLSpanElement} */
function createSpan(className) {
  const span = document.createElement('span');
  span.className = className;
  return span;
}

/** @param {number} row @returns {[HTMLElement, HTMLElement]} */
function createByteRow(row) {
  const hexRow = document.createElement('div');
  const asciiRow = document.createElement('div');
  hexRow.className = asciiRow.className = 'byteline';
  const address = createSpan('byterow');
  address.dataset['row'] = String(row);
  address.title = 'Double-click to jump to an address';
  hexRow.append(address);
  for (let column = 0; column < viewerState.bytesPerRow; column += 1) {
    const cell = row * viewerState.bytesPerRow + column;
    const hex = createSpan('byte');
    const ascii = createSpan('byte');
    hex.id = `byte${cell}`;
    ascii.id = `ascii${cell}`;
    hex.dataset['cell'] = ascii.dataset['cell'] = String(cell);
    hexRow.append(hex);
    asciiRow.append(ascii);
    hexCells.push(hex);
    asciiCells.push(ascii);
  }
  return [hexRow, asciiRow];
}

function rebuildRows() {
  const hex = document.createDocumentFragment();
  const ascii = document.createDocumentFragment();
  hexCells = [];
  asciiCells = [];
  for (let row = 0; row < viewerState.visibleRows; row += 1) {
    const [hexRow, asciiRow] = createByteRow(row);
    hex.append(hexRow);
    ascii.append(asciiRow);
  }
  getElement('hexdump').replaceChildren(hex);
  getElement('ascii').replaceChildren(ascii);
  renderedColumns = viewerState.bytesPerRow;
}

/** @param {number} lead @returns {number} */
function utf8ExpectedLength(lead) {
  if (lead >= 0xc2 && lead <= 0xdf) return 2;
  if (lead >= 0xe0 && lead <= 0xef) return 3;
  if (lead >= 0xf0 && lead <= 0xf4) return 4;
  return 1;
}

/** @type {Map<number, [number, number]>} */
const utf8FirstBounds = new Map([
  [0xe0, [0xa0, 0xbf]],
  [0xed, [0x80, 0x9f]],
  [0xf0, [0x90, 0xbf]],
  [0xf4, [0x80, 0x8f]],
]);

/** @param {number} lead @param {number | undefined} byte @param {number} index */
function validUtf8Continuation(lead, byte, index) {
  if (byte === undefined || byte < 0x80 || byte > 0xbf) return false;
  if (index !== 1) return true;
  const bounds = utf8FirstBounds.get(lead);
  return byte >= (bounds?.[0] ?? 0x80) && byte <= (bounds?.[1] ?? 0xbf);
}

/** @param {Uint8Array} bytes @param {number} offset @returns {number} */
function utf8UnitLength(bytes, offset) {
  const lead = bytes[offset] ?? 0;
  const expected = utf8ExpectedLength(lead);
  let length = 1;
  for (let index = 1; index < expected; index += 1) {
    if (!validUtf8Continuation(lead, bytes[offset + index], index)) break;
    length += 1;
  }
  return length;
}

/** @param {Uint8Array} bytes @param {number} start @returns {number} */
function utf8WindowStart(bytes, start) {
  let offset = Math.max(0, start - 3);
  while (offset < start) {
    const next = offset + utf8UnitLength(bytes, offset);
    if (next > start) return offset;
    offset = next;
  }
  return start;
}

/** @param {Uint8Array} bytes @param {number} offset @param {number} length */
function readableCharacter(bytes, offset, length) {
  const byte = bytes[offset] ?? 0;
  if (byte < 128 && byte !== 10 && byte !== 9) return displayByte(byte);
  return utf8Decoder.decode(bytes.subarray(offset, offset + length));
}

function renderReadable() {
  const start = viewerState.rowOffset * viewerState.bytesPerRow;
  const bytes = getSourceBytes(viewerState.activeSource);
  const end = Math.min(bytes.length, start + hexCells.length);
  const fragment = document.createDocumentFragment();
  readableRanges = [];
  for (let offset = utf8WindowStart(bytes, start); offset < end;) {
    const length = utf8UnitLength(bytes, offset);
    const span = createSpan('readable-byte');
    span.dataset['cell'] = String(offset - start);
    span.dataset['offset'] = String(offset);
    span.dataset['length'] = String(length);
    span.classList.toggle('undescribed', isByteUndescribed(viewerState.activeSource, offset));
    span.textContent = readableCharacter(bytes, offset, length);
    fragment.append(span);
    readableRanges.push({ element: span, start: offset, end: offset + length });
    offset += length;
  }
  getElement('readablebytes').replaceChildren(fragment);
}

/** @param {Uint8Array} bytes @param {number} start */
function renderByteCells(bytes, start) {
  for (let index = 0; index < hexCells.length; index += 1) {
    const byte = bytes[start + index];
    const hex = hexCells[index];
    const ascii = asciiCells[index];
    if (!hex || !ascii) continue;
    hex.textContent = byte === undefined ? '' : byte.toString(16).padStart(2, '0');
    ascii.textContent = byte === undefined ? '' : displayByte(byte);
    const uncovered =
      byte !== undefined && isByteUndescribed(viewerState.activeSource, start + index);
    hex.classList.toggle('undescribed', uncovered);
    ascii.classList.toggle('undescribed', uncovered);
  }
}

function renderViewport() {
  const bytes = getSourceBytes(viewerState.activeSource);
  const rowCount = Math.max(1, Math.ceil(bytes.length / viewerState.bytesPerRow));
  const maxRow = Math.max(0, rowCount - viewerState.visibleRows);
  viewerState.rowOffset = Math.max(0, Math.min(Math.floor(viewerState.rowOffset), maxRow));
  if (
    renderedColumns !== viewerState.bytesPerRow ||
    hexCells.length !== viewerState.visibleRows * viewerState.bytesPerRow
  )
    rebuildRows();
  const start = viewerState.rowOffset * viewerState.bytesPerRow;
  renderByteCells(bytes, start);
  const digits = Math.max(1, Math.max(bytes.length - 1, 0).toString(16).length);
  document.querySelectorAll('#hexdump .byterow').forEach((label, row) => {
    const offset = (viewerState.rowOffset + row) * viewerState.bytesPerRow;
    label.textContent = offset.toString(16).padStart(digits, '0') + ': ';
  });
  getElement('scrollheightproxy').style.height = `${byteHeight * (rowCount + 1)}px`;
  const scroll = getElement('scrollcontainer');
  const top = byteHeight * viewerState.rowOffset;
  if (Math.abs(scroll.scrollTop - top) >= 1) scroll.scrollTop = top;
  renderReadable();
  renderHighlights();
  document.dispatchEvent(new Event('polyfileviewport'));
}

/** @param {number} offset @returns {number} */
function firstReadableAt(offset) {
  let first = 0;
  let last = readableRanges.length;
  while (first < last) {
    const middle = Math.floor((first + last) / 2);
    if ((readableRanges[middle]?.end ?? 0) <= offset) first = middle + 1;
    else last = middle;
  }
  return first;
}

/** @param {string} kind @param {ViewerRange} range @param {number} start */
function paintHighlight(kind, range, start) {
  const first = Math.max(0, Math.floor(range.start - start));
  const last = Math.min(hexCells.length, range.start + range.length - start);
  for (let index = first; index < last; index += 1) {
    if (!hexCells[index]?.textContent) continue;
    hexCells[index]?.classList.add(kind);
    asciiCells[index]?.classList.add(kind);
  }
  for (let index = firstReadableAt(range.start); index < readableRanges.length; index += 1) {
    const readable = readableRanges[index];
    if (!readable || readable.start >= range.start + range.length) break;
    readable.element.classList.add(kind);
  }
}

function renderHighlights() {
  const kinds = [...new Set([...paintedHighlightKinds, ...highlightIndexes.keys()])];
  const cells = [...hexCells, ...asciiCells, ...readableRanges.map((range) => range.element)];
  for (const cell of cells) cell.classList.remove(...kinds);
  paintedHighlightKinds = [...highlightIndexes.keys()];
  const start = viewerState.rowOffset * viewerState.bytesPerRow;
  for (const [kind, sources] of highlightIndexes) {
    const ranges =
      sources.get(viewerState.activeSource)?.query(start, start + hexCells.length) ?? [];
    for (const range of ranges) paintHighlight(kind, range, start);
  }
}

/** @param {number} offset */
function scrollToByte(offset) {
  if (!Number.isFinite(offset)) return;
  viewerState.rowOffset = Math.floor(Math.max(0, offset) / viewerState.bytesPerRow);
  renderViewport();
}

/** @param {Element | null} element @param {number} fallback @returns {number} */
function measuredWidth(element, fallback) {
  return element?.getBoundingClientRect().width || fallback;
}

/** @returns {number} */
function fittedColumns() {
  const pane = document.getElementById('byte-pane');
  const width =
    pane?.clientWidth ??
    document.documentElement.clientWidth - measuredWidth(document.querySelector('.tree'), 0) - 80;
  const style = getComputedStyle(pane ?? getElement('scrollcapture'));
  const padding = Number.parseFloat(style.paddingLeft) + Number.parseFloat(style.paddingRight);
  const chrome =
    measuredWidth(getElement('scrollcontainer'), 20) +
    (Number.parseFloat(style.columnGap) || 0) +
    padding;
  const hex = measuredWidth(document.querySelector('#hexdump .byte'), 30);
  const ascii = measuredWidth(document.querySelector('#ascii .byte'), 10);
  const gutter = Math.max(measuredWidth(document.querySelector('#hexdump .byterow'), 0), 64);
  return width >= 16 * (hex + ascii) + gutter + chrome ? 16 : 8;
}

function resizeViewport() {
  const start = viewerState.rowOffset * viewerState.bytesPerRow;
  if (!hexCells.length) rebuildRows();
  viewerState.bytesPerRow = fittedColumns();
  const pane = document.getElementById('byte-pane');
  pane?.style.setProperty('--byte-columns', String(viewerState.bytesPerRow));
  const row = document.querySelector('#hexdump .byteline');
  byteHeight = Math.max(1, row?.getBoundingClientRect().height || byteHeight);
  const height = getElement('scrollcontainer').clientHeight;
  viewerState.visibleRows = Math.max(1, Math.floor(height / byteHeight));
  viewerState.rowOffset = Math.floor(start / viewerState.bytesPerRow);
  renderViewport();
}
