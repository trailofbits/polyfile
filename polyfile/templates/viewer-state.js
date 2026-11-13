// @ts-check
/** @typedef {{source: string, start: number, length: number}} ViewerRange */
/** @typedef {{encoded: string, regions: [number, number][]}} ViewerSource */
/**
 * @typedef {Object} ViewerNode
 * @property {number} uid
 * @property {number | null} parent
 * @property {string} source
 * @property {number} offset
 * @property {number} size
 * @property {string} name
 * @property {string} type
 * @property {string} extension
 * @property {string} analysis_status
 * @property {string} analysis_message
 * @property {string} image
 * @property {boolean} decoded
 */
/**
 * @typedef {Object} ViewerData
 * @property {string} filename
 * @property {string} mime
 * @property {Record<string, ViewerSource>} sources
 * @property {ViewerNode[]} nodes
 */
/**
 * @typedef {Object} ViewerState
 * @property {string} activeSource
 * @property {number} rowOffset
 * @property {number} visibleRows
 * @property {number} bytesPerRow
 * @property {number | null} selectedNode
 * @property {ViewerRange | null} selectedRange
 */

/** @param {string} id @returns {HTMLElement} */
function getElement(id) {
  const element = document.getElementById(id);
  if (!(element instanceof HTMLElement)) {
    throw new Error(`The viewer is missing the required element #${id}.`);
  }
  return element;
}

/** @type {ViewerData} */
const viewerData = JSON.parse(getElement('viewer-data').textContent || '{}');
/** @type {ViewerState} */
const viewerState = {
  activeSource: 'file',
  rowOffset: 0,
  visibleRows: 1,
  bytesPerRow: 16,
  selectedNode: null,
  selectedRange: null,
};
/** @type {Map<string, Uint8Array>} */
const decodedSources = new Map();
/** @type {Map<string, ViewerRange[]>} */
const highlightRanges = new Map();
const nodesById = new Map(viewerData.nodes.map((node) => [node.uid, node]));

/** @param {string} source @returns {Uint8Array} */
function getSourceBytes(source) {
  const cached = decodedSources.get(source);
  if (cached) return cached;
  const buffer = viewerData.sources[source];
  if (!buffer) throw new Error(`Unknown byte source: ${source}`);
  const binary = atob(buffer.encoded);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  decodedSources.set(source, bytes);
  return bytes;
}

/** @param {number} uid @returns {HTMLElement | null} */
function getNodeLabel(uid) {
  return document.querySelector(`.tree_label[data-uid="${uid}"]`);
}

/** @param {string} kind @param {ViewerRange[]} ranges */
function setHighlights(kind, ranges) {
  highlightRanges.set(
    kind,
    ranges.filter((range) => range.length > 0),
  );
  renderHighlights();
}

/** @param {string} kind @param {string} source @param {number} start @param {number} length */
function setHighlight(kind, source, start, length) {
  setHighlights(kind, [{ source, start, length }]);
}

/** @param {string} kind */
function clearHighlight(kind) {
  highlightRanges.delete(kind);
  renderHighlights();
}

/** @param {string} source @param {{preserveSearch?: boolean, scroll?: boolean}} [options] */
function setSource(source, options = {}) {
  if (source === viewerState.activeSource) return;
  getSourceBytes(source);
  viewerState.activeSource = source;
  viewerState.selectedNode = null;
  viewerState.selectedRange = null;
  for (const kind of highlightRanges.keys()) {
    if (kind !== 'searchresult' || options.preserveSearch === false) {
      highlightRanges.delete(kind);
    }
  }
  document.querySelectorAll('.tree_label.manually-focused').forEach((label) => {
    label.classList.remove('manually-focused');
  });
  /** @type {HTMLSelectElement} */ (getElement('source')).value = source;
  if (options.scroll !== false) viewerState.rowOffset = 0;
  updateCoverage();
  renderViewport();
  if (options.preserveSearch === false) runSearch();
}

function updateCoverage() {
  const source = viewerData.sources[viewerState.activeSource];
  if (!source) return;
  const length = getSourceBytes(viewerState.activeSource).length;
  const uncovered = source.regions.reduce((sum, region) => sum + region[1], 0);
  const coverage = document.querySelector('.coverage');
  if (!coverage) return;
  const prefix = viewerState.activeSource === 'file' ? '' : `${viewerState.activeSource}: `;
  coverage.textContent =
    prefix +
    (uncovered === 0
      ? `Every one of the ${length.toLocaleString()} bytes is described by a match.`
      : `${uncovered.toLocaleString()} of ${length.toLocaleString()} bytes ` +
        `(${((uncovered * 100) / Math.max(length, 1)).toFixed(1)}%) are undescribed.`);
}
