/** @type {ViewerRange[]} */
let baselineSearchResults = [];
let baselineSearchIndex = 0;

function runSearch() {
  const input = /** @type {HTMLInputElement} */ (getElement('search'));
  const query = input.value.toLowerCase();
  baselineSearchResults = [];
  baselineSearchIndex = 0;
  document.querySelectorAll('.tree_label.searchresult').forEach((label) => {
    label.classList.remove('searchresult');
  });
  if (query) {
    for (const node of viewerData.nodes) {
      if (node.source !== viewerState.activeSource || !node.name.toLowerCase().includes(query)) {
        continue;
      }
      baselineSearchResults.push({ source: node.source, start: node.offset, length: node.size });
      getNodeLabel(node.uid)?.classList.add('searchresult');
    }
    const bytes = getSourceBytes(viewerState.activeSource);
    let text = '';
    for (const byte of bytes) text += String.fromCharCode(byte);
    const lower = text.toLowerCase();
    for (let index = lower.indexOf(query); index >= 0; index = lower.indexOf(query, index + 1)) {
      baselineSearchResults.push({
        source: viewerState.activeSource,
        start: index,
        length: query.length,
      });
    }
  }
  baselineSearchResults.sort((left, right) => left.start - right.start);
  setHighlights('searchresult', baselineSearchResults);
  getElement('searchbuttons').hidden = baselineSearchResults.length < 2;
  getElement('searchinfo').textContent = query ? `0/${baselineSearchResults.length}` : '';
  if (baselineSearchResults.length) navigateSearch(0);
}

/** @param {number} delta */
function navigateSearch(delta) {
  if (!baselineSearchResults.length) return;
  baselineSearchIndex =
    (baselineSearchIndex + delta + baselineSearchResults.length) % baselineSearchResults.length;
  const result = baselineSearchResults[baselineSearchIndex];
  if (!result) return;
  scrollToByte(result.start);
  getElement('searchinfo').textContent =
    `${baselineSearchIndex + 1}/${baselineSearchResults.length}`;
}

function initSearch() {
  getElement('search').addEventListener('input', runSearch);
  getElement('searchup').addEventListener('click', () => navigateSearch(-1));
  getElement('searchdown').addEventListener('click', () => navigateSearch(1));
  document.addEventListener('keydown', (event) => {
    const target = event.target;
    const editing = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement;
    if (
      ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'f') ||
      (event.key === '/' && !editing)
    ) {
      event.preventDefault();
      const input = /** @type {HTMLInputElement} */ (getElement('search'));
      input.focus();
      input.select();
    } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'g') {
      event.preventDefault();
      navigateSearch(event.shiftKey ? -1 : 1);
    }
  });
}
