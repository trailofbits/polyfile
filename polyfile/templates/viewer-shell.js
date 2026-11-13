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

function initShell() {
  document.addEventListener('click', handleViewerAction);
  getElement('source').addEventListener('change', (event) => {
    const select = /** @type {HTMLSelectElement} */ (event.target);
    setSource(select.value, { preserveSearch: false });
  });
  const scroll = getElement('scrollcontainer');
  scroll.addEventListener('scroll', () => {
    const row = Math.floor(scroll.scrollTop / byteHeight);
    if (row !== viewerState.rowOffset) {
      viewerState.rowOffset = row;
      renderViewport();
    }
  });
  getElement('scrollcapture').addEventListener(
    'wheel',
    (event) => {
      if (event.deltaY === 0) return;
      event.preventDefault();
      const rows =
        Math.sign(event.deltaY) * Math.max(1, Math.round(Math.abs(event.deltaY) / byteHeight));
      scrollToByte((viewerState.rowOffset + rows) * viewerState.bytesPerRow);
    },
    { passive: false },
  );
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
initInspection();
initSearch();
resizeViewport();
getElement('loading').remove();
document.documentElement.dataset['viewerReady'] = 'true';
