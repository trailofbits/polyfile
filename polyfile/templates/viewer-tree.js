const expandableTreeNodes = new Set(
  viewerData.nodes.flatMap((node) => (node.parent === null ? [] : [node.parent])),
);
/** @type {Map<number, HTMLElement>} */
const treeRows = new Map();
document.querySelectorAll('li[data-node-uid]').forEach((row) => {
  if (row instanceof HTMLElement) treeRows.set(Number(row.dataset['nodeUid']), row);
});
const treeToolsState = {
  query: '',
  /** @type {Map<number, boolean> | null} */
  expansion: null,
};

/** @returns {HTMLInputElement} */
function treeFilterInput() {
  const input = getElement('tree-filter');
  if (!(input instanceof HTMLInputElement)) throw new Error('The structure filter is unavailable.');
  return input;
}

/** @param {number} matches */
function updateTreeFilterCount(matches) {
  const total = viewerData.nodes.length;
  const status = getElement('tree-filter-info');
  if (!treeToolsState.query) {
    status.textContent = total ? `${total} nodes` : 'No structure nodes.';
    return;
  }
  status.textContent = `${matches} of ${total} nodes ${matches === 1 ? 'matches' : 'match'}.`;
}

/** @param {boolean} expanded */
function expandTreeNodes(expanded) {
  for (const uid of expandableTreeNodes) setNodeExpanded(uid, expanded);
}

function restoreTreeFilter() {
  for (const [uid, row] of treeRows) {
    row.hidden = false;
    getNodeLabel(uid)?.classList.remove('tree-filter-match');
  }
  if (treeToolsState.expansion) {
    for (const [uid, expanded] of treeToolsState.expansion) setNodeExpanded(uid, expanded);
  }
  treeToolsState.expansion = null;
  treeToolsState.query = '';
  updateTreeFilterCount(0);
}

function clearTreeFilter() {
  treeFilterInput().value = '';
  restoreTreeFilter();
}

/** @param {ViewerNode} node @param {string} query @returns {boolean} */
function treeNodeMatches(node, query) {
  return foldSearchText([node.name, node.type, node.analysis_message].join(' ')).includes(query);
}

/** @param {number} uid @param {Set<number>} visible */
function includeTreeAncestors(uid, visible) {
  let node = nodesById.get(uid);
  while (node && !visible.has(node.uid)) {
    visible.add(node.uid);
    node = node.parent === null ? undefined : nodesById.get(node.parent);
  }
}

/** @param {Set<number>} matches @param {Set<number>} visible */
function showFilteredTree(matches, visible) {
  const expanded = new Set();
  for (const [uid, row] of treeRows) {
    row.hidden = !visible.has(uid);
    getNodeLabel(uid)?.classList.toggle('tree-filter-match', matches.has(uid));
    const parent = nodesById.get(uid)?.parent;
    if (visible.has(uid) && parent !== null && parent !== undefined) expanded.add(parent);
  }
  for (const uid of expandableTreeNodes) setNodeExpanded(uid, expanded.has(uid));
}

function filterStructureTree() {
  const query = foldSearchText(treeFilterInput().value.trim());
  if (!query) {
    restoreTreeFilter();
    return;
  }
  treeToolsState.expansion ??= new Map(
    [...expandableTreeNodes].map((uid) => [uid, isNodeExpanded(uid)]),
  );
  treeToolsState.query = query;
  const matches = new Set(
    viewerData.nodes.filter((node) => treeNodeMatches(node, query)).map((node) => node.uid),
  );
  const visible = new Set();
  for (const uid of matches) includeTreeAncestors(uid, visible);
  showFilteredTree(matches, visible);
  updateTreeFilterCount(matches.size);
}

/** @param {Event} event */
function revealFilteredTreeNode(event) {
  if (!(event instanceof CustomEvent)) return;
  const uid = /** @type {{uid: number}} */ (event.detail).uid;
  if (treeToolsState.query && treeRows.get(uid)?.hidden) clearTreeFilter();
}

/** @param {string} id @param {string} text @param {() => void} action */
function treeToolButton(id, text, action) {
  const button = document.createElement('button');
  button.id = id;
  button.type = 'button';
  button.textContent = text;
  button.disabled = expandableTreeNodes.size === 0;
  button.addEventListener('click', action);
  return button;
}

/** @returns {HTMLElement} */
function createTreeTools() {
  const tools = document.createElement('div');
  tools.className = 'tree-tools';
  tools.setAttribute('role', 'group');
  tools.setAttribute('aria-label', 'Structure tools');
  const label = document.createElement('label');
  label.className = 'tree-filter-label';
  label.textContent = 'Filter structure';
  const input = document.createElement('input');
  input.id = 'tree-filter';
  input.type = 'search';
  input.placeholder = 'Name, MIME type, or analysis message';
  input.autocomplete = 'off';
  input.spellcheck = false;
  input.setAttribute('aria-describedby', 'tree-filter-info');
  label.append(input);
  const actions = document.createElement('div');
  actions.className = 'tree-tools-actions';
  actions.append(
    treeToolButton('expand-all', 'Expand all', () => expandTreeNodes(true)),
    treeToolButton('collapse-all', 'Collapse all', () => expandTreeNodes(false)),
  );
  const status = document.createElement('span');
  status.id = 'tree-filter-info';
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  tools.append(label, actions, status);
  return tools;
}

function initTreeTools() {
  const pane = getElement('structure-pane');
  const tools = createTreeTools();
  const heading = pane.querySelector(':scope > .pane-header');
  if (heading) heading.after(tools);
  else pane.prepend(tools);
  pane.classList.add('tree-tools-enabled');
  const tree = pane.querySelector('.tree');
  if (tree instanceof HTMLElement) {
    tree.id ||= 'structure-tree';
    treeFilterInput().setAttribute('aria-controls', tree.id);
  }
  treeFilterInput().addEventListener('input', filterStructureTree);
  treeFilterInput().addEventListener('keydown', (event) => {
    if (event.key !== 'Escape' || !treeFilterInput().value) return;
    event.preventDefault();
    event.stopPropagation();
    clearTreeFilter();
  });
  document.addEventListener('polyfile:reveal-node', revealFilteredTreeNode);
  updateTreeFilterCount(0);
}

initTreeTools();
