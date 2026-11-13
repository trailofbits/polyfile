/** @typedef {'combined'|'text'|'hex'|'structure'} ViewerSearchMode */
/** @typedef {{query:string, mode:ViewerSearchMode, scope:string, matchCase:boolean}} SearchOptions */
/** @typedef {{bytes:Uint8Array, kind:string, fold:boolean}} SearchNeedle */
/** @typedef {{source:string, start:number, length:number, kinds:string[], nodes:number[]}} SearchHit */

const viewerSearch = {
  generation: 0,
  current: 0,
  lastYield: 0,
  /** @type {SearchHit[]} */
  results: [],
};

/** @returns {HTMLInputElement} */
function searchInput() {
  const input = getElement('search');
  if (!(input instanceof HTMLInputElement)) throw new Error('Search input is unavailable.');
  return input;
}

/** @returns {SearchOptions} */
function searchOptions() {
  const mode = getElement('searchmode');
  const scope = getElement('searchscope');
  const matchCase = getElement('matchcase');
  if (!(mode instanceof HTMLSelectElement) || !(scope instanceof HTMLSelectElement)) {
    throw new Error('Search mode and scope controls are unavailable.');
  }
  if (!(matchCase instanceof HTMLInputElement))
    throw new Error('Match case control is unavailable.');
  return {
    query: searchInput().value,
    mode: /** @type {ViewerSearchMode} */ (mode.value),
    scope: scope.value,
    matchCase: matchCase.checked,
  };
}

/** @param {number} value @returns {number} */
function foldSearchByte(value) {
  return value >= 65 && value <= 90 ? value + 32 : value;
}

/** @param {string} value @returns {string} */
function foldSearchText(value) {
  return value.replace(/[A-Z]/g, (letter) => letter.toLowerCase());
}

/** @param {string} query @returns {Uint8Array|null} */
function hexSearchBytes(query) {
  const compact = query.trim().replace(/^0x/i, '').replace(/\s/g, '');
  if (!compact || compact.length % 2 !== 0 || !/^[\da-f]+$/i.test(compact)) return null;
  const bytes = new Uint8Array(compact.length / 2);
  for (let index = 0; index < bytes.length; index += 1) {
    bytes[index] = Number.parseInt(compact.slice(index * 2, index * 2 + 2), 16);
  }
  return bytes;
}

/** @param {SearchOptions} options @returns {SearchNeedle[]} */
function searchNeedles(options) {
  /** @type {SearchNeedle[]} */
  const needles = [];
  if (options.mode === 'combined' || options.mode === 'text') {
    const bytes = new TextEncoder().encode(options.query);
    needles.push({ bytes, kind: 'text', fold: !options.matchCase });
  }
  if (options.mode === 'combined' || options.mode === 'hex') {
    const bytes = hexSearchBytes(options.query);
    if (bytes) needles.push({ bytes, kind: 'hex', fold: false });
    else if (options.mode === 'hex') {
      throw new Error('Enter hexadecimal byte pairs, such as 0x48 65 6c 6c 6f.');
    }
  }
  return needles;
}

/** @param {Uint8Array} bytes @returns {Int32Array} */
function searchPrefix(bytes) {
  const prefix = new Int32Array(bytes.length);
  let matched = 0;
  for (let index = 1; index < bytes.length; index += 1) {
    while (matched > 0 && bytes[index] !== bytes[matched]) matched = prefix[matched - 1] ?? 0;
    if (bytes[index] === bytes[matched]) matched += 1;
    prefix[index] = matched;
  }
  return prefix;
}

/** @param {Map<string,SearchHit>} hits @param {SearchHit} hit */
function addSearchHit(hits, hit) {
  const key = `${hit.source}:${hit.start}:${hit.length}`;
  const previous = hits.get(key);
  if (!previous) {
    hits.set(key, hit);
    return;
  }
  for (const kind of hit.kinds) if (!previous.kinds.includes(kind)) previous.kinds.push(kind);
  for (const uid of hit.nodes) if (!previous.nodes.includes(uid)) previous.nodes.push(uid);
}

/** @returns {Promise<void>} */
function yieldSearch() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

/**
 * @param {Uint8Array} bytes @param {Int32Array} prefix
 * @param {number} matched @param {number} value @returns {number}
 */
function advanceSearchMatch(bytes, prefix, matched, value) {
  while (matched > 0 && value !== bytes[matched]) matched = prefix[matched - 1] ?? 0;
  return value === bytes[matched] ? matched + 1 : matched;
}

/**
 * @param {{source:string, needle:SearchNeedle, generation:number,
 *   hits:Map<string,SearchHit>}} task
 * @returns {Promise<boolean>}
 */
async function scanSearchBytes(task) {
  const source = getSourceBytes(task.source);
  const bytes = task.needle.fold ? task.needle.bytes.map(foldSearchByte) : task.needle.bytes;
  const prefix = searchPrefix(bytes);
  let matched = 0;
  for (let index = 0; index < source.length; index += 1) {
    const value = task.needle.fold ? foldSearchByte(source[index] ?? 0) : (source[index] ?? 0);
    matched = advanceSearchMatch(bytes, prefix, matched, value);
    if (matched === bytes.length) {
      addSearchHit(task.hits, {
        source: task.source,
        start: index + 1 - matched,
        length: matched,
        kinds: [task.needle.kind],
        nodes: [],
      });
      matched = prefix[matched - 1] ?? 0;
    }
    if ((index + 1) % 16384 === 0) {
      if (!(await searchCheckpoint(task.generation, task.source, task.hits.size))) return false;
    }
  }
  return task.generation === viewerSearch.generation;
}

/** @param {number} generation @param {string} source @param {number} count */
async function searchCheckpoint(generation, source, count) {
  if (generation !== viewerSearch.generation) return false;
  if (performance.now() - viewerSearch.lastYield < 8) return true;
  getElement('searchinfo').textContent = `Searching ${source}… ${count} matches`;
  await yieldSearch();
  if (generation === viewerSearch.generation) viewerSearch.lastYield = performance.now();
  return generation === viewerSearch.generation;
}

/** @param {ViewerNode} node @param {SearchOptions} options @returns {boolean} */
function searchNodeMatches(node, options) {
  const text = [node.name, node.type, node.analysis_status, node.analysis_message].join(' ');
  if (options.matchCase) return text.includes(options.query);
  return foldSearchText(text).includes(foldSearchText(options.query));
}

/**
 * @param {SearchOptions} options @param {string[]} sources
 * @param {Map<string,SearchHit>} hits @param {number} generation
 */
async function scanSearchNodes(options, sources, hits, generation) {
  if (options.mode !== 'combined' && options.mode !== 'structure') return true;
  const included = new Set(sources);
  let index = 0;
  for (const node of viewerData.nodes) {
    if (included.has(node.source) && searchNodeMatches(node, options)) {
      addSearchHit(hits, {
        source: node.source,
        start: node.offset,
        length: node.size,
        kinds: ['structure'],
        nodes: [node.uid],
      });
    }
    index += 1;
    if (index % 512 === 0 && !(await searchCheckpoint(generation, 'structure', hits.size))) {
      return false;
    }
  }
  return generation === viewerSearch.generation;
}

/** @param {SearchOptions} options @returns {string[]} */
function searchSources(options) {
  if (options.scope === 'current') return [viewerState.activeSource];
  return ['file', ...Object.keys(viewerData.sources).filter((source) => source !== 'file')];
}

/** @param {Map<string,SearchHit>} hits @param {string[]} sources @returns {SearchHit[]} */
function orderedSearchHits(hits, sources) {
  const order = new Map(sources.map((source, index) => [source, index]));
  return [...hits.values()].sort((left, right) => {
    const sourceOrder = (order.get(left.source) ?? 0) - (order.get(right.source) ?? 0);
    return sourceOrder || left.start - right.start || left.length - right.length;
  });
}

/** @param {boolean} enabled */
function searchNavigationEnabled(enabled) {
  const buttons = getElement('searchbuttons');
  buttons.hidden = false;
  buttons.style.removeProperty('display');
  for (const id of ['searchup', 'searchdown']) {
    getElement(id).toggleAttribute('disabled', !enabled);
  }
}

/** @param {SearchHit[]} results */
function markStructureSearchResults(results) {
  /** @type {Set<number>} */
  const matches = new Set();
  for (const result of results) for (const uid of result.nodes) matches.add(uid);
  document.querySelectorAll('.tree_label[data-uid]').forEach((label) => {
    label.classList.toggle('searchresult', matches.has(Number(label.getAttribute('data-uid'))));
  });
}

/** @param {string} message */
function resetSearch(message) {
  viewerSearch.results = [];
  viewerSearch.current = 0;
  clearHighlight('searchresult');
  clearHighlight('search-current');
  markStructureSearchResults([]);
  searchNavigationEnabled(false);
  getElement('searchinfo').textContent = message;
}

/** @param {SearchOptions} options @param {number} generation */
async function executeSearch(options, generation) {
  const needles = searchNeedles(options);
  const sources = searchSources(options);
  /** @type {Map<string,SearchHit>} */
  const hits = new Map();
  for (const source of sources) {
    for (const needle of needles) {
      if (!(await scanSearchBytes({ source, needle, generation, hits }))) return;
    }
  }
  if (!(await scanSearchNodes(options, sources, hits, generation))) return;
  if (generation !== viewerSearch.generation) return;
  viewerSearch.results = orderedSearchHits(hits, sources);
  markStructureSearchResults(viewerSearch.results);
  setHighlights('searchresult', viewerSearch.results);
  searchNavigationEnabled(viewerSearch.results.length > 0);
  if (viewerSearch.results.length === 0) getElement('searchinfo').textContent = '0 results';
  else showSearchResult();
}

/** Start a cancellable search across the selected source scope. */
function runSearch() {
  viewerSearch.generation += 1;
  viewerSearch.lastYield = performance.now();
  const generation = viewerSearch.generation;
  const options = searchOptions();
  resetSearch(options.query ? 'Searching…' : '');
  if (!options.query) return;
  void executeSearch(options, generation).catch((error) => {
    if (generation !== viewerSearch.generation) return;
    resetSearch(error instanceof Error ? error.message : 'Search could not complete.');
  });
}

/** Show the current result without restarting the active query. */
function showSearchResult() {
  const result = viewerSearch.results[viewerSearch.current];
  if (!result) return;
  setSource(result.source, { preserveSearch: true, scroll: false });
  const uid = result.nodes[0];
  if (uid !== undefined) selectNode(uid, { focus: false });
  scrollToByte(result.start);
  setHighlight('search-current', result.source, result.start, result.length);
  const count = `${viewerSearch.current + 1} of ${viewerSearch.results.length}`;
  const location = `${result.source} @ 0x${result.start.toString(16)}`;
  getElement('searchinfo').textContent = `${count} · ${location} · ${result.kinds.join(', ')}`;
}

/** @param {number} delta */
function navigateSearch(delta) {
  const length = viewerSearch.results.length;
  if (length === 0) return;
  viewerSearch.current = (viewerSearch.current + delta + length) % length;
  showSearchResult();
}

/** @param {EventTarget|null} target @returns {boolean} */
function searchEditableTarget(target) {
  if (!(target instanceof HTMLElement)) return false;
  return (
    target.isContentEditable || target.closest('input,textarea,select,[contenteditable]') !== null
  );
}

/** @typedef {'focus'|'previous'|'next'|null} SearchShortcut */

/** @param {KeyboardEvent} event @returns {SearchShortcut} */
function searchCommandShortcut(event) {
  const key = event.key.toLowerCase();
  if (key === 'f') return 'focus';
  if (key === 'g') return event.shiftKey ? 'previous' : 'next';
  return null;
}

/** @param {KeyboardEvent} event @returns {SearchShortcut} */
function searchInputShortcut(event) {
  const key = event.key.toLowerCase();
  if (key === '/' && !searchEditableTarget(event.target) && !event.altKey) return 'focus';
  if (event.target === searchInput() && key === 'enter') {
    return event.shiftKey ? 'previous' : 'next';
  }
  return null;
}

/** @param {KeyboardEvent} event */
function handleSearchShortcut(event) {
  const action =
    event.ctrlKey || event.metaKey ? searchCommandShortcut(event) : searchInputShortcut(event);
  if (!action) return;
  event.preventDefault();
  if (action === 'focus') {
    searchInput().focus();
    searchInput().select();
  } else navigateSearch(action === 'previous' ? -1 : 1);
}

/** Wire search controls once after the report DOM is available. */
function initSearch() {
  const status = getElement('searchinfo');
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  searchInput().addEventListener('input', runSearch);
  for (const id of ['searchmode', 'searchscope', 'matchcase']) {
    getElement(id).addEventListener('change', runSearch);
  }
  getElement('searchup').addEventListener('click', () => navigateSearch(-1));
  getElement('searchdown').addEventListener('click', () => navigateSearch(1));
  document.addEventListener('keydown', handleSearchShortcut);
  searchNavigationEnabled(false);
}
