/** @param {number} uid */
function selectNode(uid) {
  const node = nodesById.get(uid);
  if (!node) return;
  setSource(node.source);
  viewerState.selectedNode = uid;
  viewerState.selectedRange = { source: node.source, start: node.offset, length: node.size };
  document.querySelectorAll(".tree_label.manually-focused").forEach((label) => {
    label.classList.remove("manually-focused");
  });
  const label = getNodeLabel(uid);
  label?.classList.add("manually-focused");
  setHighlight("manually-focused", node.source, node.offset, node.size);
  scrollToByte(node.offset);
}

/** @param {number} offset */
function hoverByte(offset) {
  document.querySelectorAll(".tree_label.highlighted").forEach((label) => {
    label.classList.remove("highlighted");
  });
  setHighlight("cursor", viewerState.activeSource, offset, 1);
  for (const node of viewerData.nodes) {
    if (
      node.source === viewerState.activeSource &&
      node.offset <= offset &&
      offset < node.offset + node.size
    )
      getNodeLabel(node.uid)?.classList.add("highlighted");
  }
}

function clearHover() {
  clearHighlight("cursor");
  clearHighlight("highlighted");
  document.querySelectorAll(".tree_label.highlighted").forEach((label) => {
    label.classList.remove("highlighted");
  });
}

/** @param {number} uid */
function showDecoded(uid) {
  const node = nodesById.get(uid);
  if (!node) return;
  getElement("decoded-title").textContent = `Decoded ${node.name}`;
  getElement("decoded-text").textContent = new TextDecoder().decode(getSourceBytes(node.source));
  /** @type {HTMLDialogElement} */ (getElement("decoded-preview")).showModal();
}

function initInspection() {
  const tree = document.querySelector(".tree");
  tree?.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;
    const label = target.closest(".tree_label");
    if (!label || target.closest("[data-action]")) return;
    selectNode(Number(/** @type {HTMLElement} */ (label).dataset.uid));
  });
  tree?.addEventListener("pointerover", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;
    const label = target.closest(".tree_label");
    if (!(label instanceof HTMLElement)) return;
    const node = nodesById.get(Number(label.dataset.uid));
    if (node?.source === viewerState.activeSource) {
      setHighlight("highlighted", node.source, node.offset, node.size);
    }
  });
  tree?.addEventListener("pointerleave", clearHover);
  const editor = document.querySelector(".hexeditor");
  editor?.addEventListener("pointerover", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement) || target.dataset.cell === undefined) return;
    hoverByte(viewerState.rowOffset * viewerState.bytesPerRow + Number(target.dataset.cell));
  });
  editor?.addEventListener("pointerleave", clearHover);
}
