/** @template T @typedef {{start: number, end: number, value: T}} IntervalEntry */
/**
 * @template T
 * @typedef {Object} IntervalBranch
 * @property {IntervalEntry<T>} entry
 * @property {number} maxEnd
 * @property {IntervalBranch<T> | null} left
 * @property {IntervalBranch<T> | null} right
 */

/**
 * @template T
 * @param {IntervalEntry<T>[]} entries
 * @param {number} first
 * @param {number} last
 * @returns {IntervalBranch<T> | null}
 */
function buildIntervalBranch(entries, first, last) {
  if (first >= last) return null;
  const middle = Math.floor((first + last) / 2);
  const entry = entries[middle];
  if (!entry) return null;
  const left = buildIntervalBranch(entries, first, middle);
  const right = buildIntervalBranch(entries, middle + 1, last);
  return { entry, left, right, maxEnd: Math.max(entry.end, left?.maxEnd ?? 0, right?.maxEnd ?? 0) };
}

/** @template T */
class IntervalIndex {
  /** @param {IntervalEntry<T>[]} entries */
  constructor(entries) {
    const sorted = entries.filter(
      (entry) =>
        Number.isFinite(entry.start) && Number.isFinite(entry.end) && entry.end > entry.start,
    );
    sorted.sort((left, right) => left.start - right.start);
    this.root = buildIntervalBranch(sorted, 0, sorted.length);
  }

  /** @param {number} start @param {number} end @returns {T[]} */
  query(start, end) {
    /** @type {T[]} */
    const values = [];
    if (!this.root || end <= start) return values;
    const stack = [this.root];
    while (stack.length) {
      const branch = stack.pop();
      if (!branch || branch.maxEnd <= start) continue;
      if (branch.left) stack.push(branch.left);
      if (branch.entry.start < end && branch.entry.end > start) values.push(branch.entry.value);
      if (branch.right && branch.entry.start < end) stack.push(branch.right);
    }
    return values;
  }
}

/** @returns {Map<string, IntervalIndex<ViewerNode>>} */
function indexSourceNodes() {
  /** @type {Map<string, IntervalEntry<ViewerNode>[]>} */
  const sources = new Map();
  for (const node of viewerData.nodes) {
    const entries = sources.get(node.source) ?? [];
    entries.push({ start: node.offset, end: node.offset + node.size, value: node });
    sources.set(node.source, entries);
  }
  return new Map([...sources].map(([source, entries]) => [source, new IntervalIndex(entries)]));
}

/** @type {Map<number, HTMLElement>} */
const nodeLabels = new Map();
document.querySelectorAll('.tree_label[data-uid]').forEach((label) => {
  if (label instanceof HTMLElement) nodeLabels.set(Number(label.dataset['uid']), label);
});
const sourceNodeIndexes = indexSourceNodes();
/** @type {Map<string, Map<string, IntervalIndex<ViewerRange>>>} */
const highlightIndexes = new Map();
/** @type {Map<string, [number, number][]>} */
const coverageIndexes = new Map(
  Object.entries(viewerData.sources).map(([source, data]) => [
    source,
    data.regions.slice().sort((left, right) => left[0] - right[0]),
  ]),
);

/** @param {string} source @param {number} offset @returns {ViewerNode[]} */
function nodesAtByte(source, offset) {
  return sourceNodeIndexes.get(source)?.query(offset, offset + 1) ?? [];
}

/** @param {string} source @param {number} start @param {number} length @returns {boolean} */
function isRangeUndescribed(source, start, length) {
  const regions = coverageIndexes.get(source) ?? [];
  let first = 0;
  let last = regions.length;
  while (first < last) {
    const middle = Math.floor((first + last) / 2);
    const region = regions[middle];
    if (!region) return false;
    if (region[0] + region[1] <= start) first = middle + 1;
    else last = middle;
  }
  const region = regions[first];
  return Boolean(region && region[0] < start + length);
}

/** @param {string} source @param {number} offset @returns {boolean} */
function isByteUndescribed(source, offset) {
  return isRangeUndescribed(source, offset, 1);
}

/** @param {ViewerRange[]} ranges @returns {ViewerRange[]} */
function mergeHighlightRanges(ranges) {
  const sorted = ranges
    .filter(
      (range) => Number.isFinite(range.start) && Number.isFinite(range.length) && range.length > 0,
    )
    .map((range) => ({ ...range }))
    .sort((left, right) => left.source.localeCompare(right.source) || left.start - right.start);
  /** @type {ViewerRange[]} */
  const merged = [];
  for (const range of sorted) {
    const previous = merged[merged.length - 1];
    if (
      previous &&
      previous.source === range.source &&
      range.start <= previous.start + previous.length
    ) {
      previous.length = Math.max(previous.length, range.start + range.length - previous.start);
    } else merged.push(range);
  }
  return merged;
}

/** @param {ViewerRange[]} ranges @returns {Map<string, IntervalIndex<ViewerRange>>} */
function indexHighlightRanges(ranges) {
  /** @type {Map<string, IntervalEntry<ViewerRange>[]>} */
  const sources = new Map();
  for (const range of ranges) {
    const entries = sources.get(range.source) ?? [];
    entries.push({ start: range.start, end: range.start + range.length, value: range });
    sources.set(range.source, entries);
  }
  return new Map([...sources].map(([source, entries]) => [source, new IntervalIndex(entries)]));
}
