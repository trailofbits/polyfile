/** @typedef {ViewerRange & {node: ViewerNode, container: ViewerNode | null}} ImageAnchor */
/** @typedef {{anchors: ImageAnchor[], top: number}} ImageGroup */
/**
 * @typedef {Object} ImageCard
 * @property {HTMLElement} element
 * @property {HTMLElement} marker
 * @property {HTMLButtonElement} open
 * @property {HTMLElement} caption
 * @property {HTMLElement} count
 * @property {HTMLButtonElement} previous
 * @property {HTMLButtonElement} next
 * @property {ImageAnchor} anchor
 * @property {ImageGroup} group
 */
const imageGutterWidth = 240;
const imageCardHeight = 224;
/** @type {Map<number, ImageCard>} */
const imageCards = new Map();
/** @type {Map<string, number>} */
const imageChoices = new Map();
/** @type {HTMLElement | null} */
let imageReturnFocus = null;
/** @type {ImageAnchor | null} */
let dialogImageAnchor = null;

/** @param {ViewerNode} node @returns {boolean} */
function hasPreviewImage(node) {
  return /^data:image\/(?:png|jpeg|gif|bmp|webp);base64,[A-Za-z0-9+/]+={0,2}$/.test(node.image);
}

/** @param {ViewerNode} node @param {ViewerNode} location @returns {ImageAnchor | null} */
function imageAnchorAt(node, location) {
  const source = viewerData.sources[location.source];
  if (!source || !Number.isSafeInteger(location.offset) || !Number.isSafeInteger(location.size))
    return null;
  const padding = source.encoded.endsWith('==') ? 2 : Number(source.encoded.endsWith('='));
  const length = Math.floor((source.encoded.length * 3) / 4) - padding;
  const start = Math.max(0, location.offset);
  const end = Math.min(length, location.offset + location.size);
  if (location.size <= 0 || end <= start) return null;
  return {
    node,
    source: location.source,
    start,
    length: end - start,
    container: location.uid === node.uid ? null : location,
  };
}

/** @param {ViewerNode} node @returns {ViewerNode[]} */
function imageLocations(node) {
  const locations = new Map([[node.source, node]]);
  let location = node;
  while (location.parent !== null) {
    const parent = nodesById.get(location.parent);
    if (!parent) break;
    if (parent.size > 0 && !locations.has(parent.source)) locations.set(parent.source, parent);
    location = parent;
  }
  return [...locations.values()];
}

/** @returns {Map<string, IntervalIndex<ImageAnchor>>} */
function indexImageAnchors() {
  /** @type {Map<string, IntervalEntry<ImageAnchor>[]>} */
  const sources = new Map();
  const images = viewerData.nodes.filter(
    (node) => hasPreviewImage(node) && Object.hasOwn(viewerData.sources, node.source),
  );
  for (const node of images) {
    for (const location of imageLocations(node)) {
      const anchor = imageAnchorAt(node, location);
      if (!anchor) continue;
      const entries = sources.get(anchor.source) ?? [];
      entries.push({ start: anchor.start, end: anchor.start + anchor.length, value: anchor });
      sources.set(anchor.source, entries);
    }
  }
  return new Map([...sources].map(([source, entries]) => [source, new IntervalIndex(entries)]));
}

const imageAnchorIndexes = indexImageAnchors();

function layoutImagePreviews() {
  const pane = getElement('byte-pane');
  const rail = getElement('image-previews');
  rail.hidden =
    getElement('scrollcapture').hidden || !imageAnchorIndexes.has(viewerState.activeSource);
  if (rail.hidden) {
    pane.dataset['images'] = 'none';
    return;
  }
  const hex = measuredWidth(document.querySelector('#hexdump .byte'), 30);
  const ascii = measuredWidth(document.querySelector('#ascii .byte'), 10);
  const address = Math.max(measuredWidth(document.querySelector('#hexdump .byterow'), 0), 64);
  const gap = Number.parseFloat(getComputedStyle(pane).columnGap) || 0;
  const fits = availableByteWidth(false) >= 8 * (hex + ascii) + address + imageGutterWidth + gap;
  pane.dataset['images'] = fits ? 'gutter' : 'strip';
  pane.style.setProperty(
    '--image-strip-height',
    `${Math.min(160, Math.floor(pane.clientHeight / 3))}px`,
  );
}

/** @param {ViewerNode} node @returns {HTMLElement} */
function imageContent(node) {
  const holder = document.createElement('span');
  holder.className = 'image-content';
  const image = document.createElement('img');
  image.alt = node.name;
  const failure = document.createElement('span');
  failure.textContent = 'Image preview unavailable';
  failure.hidden = true;
  image.addEventListener('error', () => {
    image.hidden = true;
    failure.hidden = false;
  });
  image.src = node.image;
  holder.append(image, failure);
  return holder;
}

/** @param {string} text @param {() => void} action @returns {HTMLButtonElement} */
function imageButton(text, action) {
  const button = document.createElement('button');
  button.type = 'button';
  button.textContent = text;
  button.addEventListener('click', action);
  return button;
}

/** @param {ImageAnchor} anchor @returns {string} */
function imageLocationLabel(anchor) {
  const location = `${anchor.source} @ 0x${anchor.start.toString(16)} · ${anchor.length} bytes`;
  return anchor.container ? `From ${anchor.node.source} · container ${location}` : location;
}

/** @param {ImageAnchor} anchor */
function highlightImageAnchor(anchor) {
  clearHover();
  setHighlight('highlighted', anchor.source, anchor.start, anchor.length);
  const label = getNodeLabel(anchor.node.uid);
  if (label) {
    label.classList.add('highlighted');
    hoveredNodeLabels.add(label);
  }
}

/** @param {ImageAnchor} anchor @returns {ImageCard} */
function createImageCard(anchor) {
  const element = document.createElement('article');
  element.className = 'image-card';
  const marker = document.createElement('div');
  marker.className = 'image-range-marker';
  marker.setAttribute('aria-hidden', 'true');
  const open = imageButton('', () => openImageDialog(card.anchor, open));
  open.className = 'image-open';
  const caption = document.createElement('p');
  caption.className = 'image-caption';
  const count = document.createElement('span');
  count.setAttribute('aria-live', 'polite');
  const previous = imageButton('‹', () => cycleImageCard(card, -1));
  previous.setAttribute('aria-label', 'Previous image in group');
  const next = imageButton('›', () => cycleImageCard(card, 1));
  next.setAttribute('aria-label', 'Next image in group');
  const controls = document.createElement('div');
  controls.className = 'image-controls';
  controls.append(previous, count, next);
  element.append(open, caption, controls);
  const card = {
    element,
    marker,
    open,
    caption,
    count,
    previous,
    next,
    anchor,
    group: { anchors: [anchor], top: 0 },
  };
  element.addEventListener('pointerenter', () => highlightImageAnchor(card.anchor));
  element.addEventListener('focusin', () => highlightImageAnchor(card.anchor));
  element.addEventListener('pointerleave', () => {
    if (!element.contains(document.activeElement)) clearHover();
  });
  element.addEventListener('focusout', (event) => {
    if (!(event.relatedTarget instanceof Node && element.contains(event.relatedTarget)))
      clearHover();
  });
  updateImageCard(card, anchor);
  return card;
}

/** @param {ImageCard} card @param {ImageAnchor} anchor */
function updateImageCard(card, anchor) {
  card.anchor = anchor;
  if (card.open.dataset['imageUid'] !== String(anchor.node.uid)) {
    card.open.replaceChildren(imageContent(anchor.node));
    card.open.dataset['imageUid'] = String(anchor.node.uid);
  }
  card.open.setAttribute('aria-label', `Enlarge ${anchor.node.name}`);
  const name = document.createElement('strong');
  name.textContent = anchor.node.name;
  const location = document.createElement('span');
  location.textContent = imageLocationLabel(anchor);
  card.caption.replaceChildren(name, location);
  card.caption.title = `${anchor.node.name}\n${location.textContent}`;
  const index = card.group.anchors.indexOf(anchor);
  const count = `Image ${index + 1} of ${card.group.anchors.length}`;
  if (card.count.textContent !== count) card.count.textContent = count;
  card.previous.disabled = card.next.disabled = card.group.anchors.length < 2;
  const focused = document.activeElement;
  if ((focused === card.previous || focused === card.next) && card.previous.disabled)
    card.open.focus();
  updateImageMarker(card);
}

/** @param {ImageCard} card */
function updateImageMarker(card) {
  const row = viewerState.rowOffset;
  const columns = viewerState.bytesPerRow;
  const height = getElement('scrollcontainer').clientHeight;
  const top = Math.max(0, (Math.floor(card.anchor.start / columns) - row) * byteHeight);
  const end = Math.ceil((card.anchor.start + card.anchor.length) / columns);
  card.marker.style.top = `${top}px`;
  card.marker.style.height = `${Math.max(2, Math.min(height, (end - row) * byteHeight) - top)}px`;
}

/** @param {ImageCard} card @param {number} direction */
function cycleImageCard(card, direction) {
  const anchors = card.group.anchors;
  const index = anchors.indexOf(card.anchor);
  const anchor = anchors[(index + direction + anchors.length) % anchors.length];
  if (!anchor) return;
  imageChoices.set(`${viewerState.activeSource}:${anchors[0]?.node.uid}`, anchor.node.uid);
  updateImageCard(card, anchor);
  highlightImageAnchor(anchor);
}

/** @returns {ImageGroup[]} */
function visibleImageGroups() {
  const start = viewerState.rowOffset * viewerState.bytesPerRow;
  const end = start + viewerState.visibleRows * viewerState.bytesPerRow;
  const anchors = imageAnchorIndexes.get(viewerState.activeSource)?.query(start, end) ?? [];
  anchors.sort((left, right) => left.start - right.start || left.node.uid - right.node.uid);
  const height = getElement('scrollcontainer').clientHeight;
  const cardHeight = Math.min(imageCardHeight, height);
  getElement('image-previews').style.setProperty('--image-card-height', `${cardHeight}px`);
  /** @type {ImageGroup[]} */
  const groups = [];
  for (const anchor of anchors) {
    const row = Math.floor(anchor.start / viewerState.bytesPerRow) - viewerState.rowOffset;
    const top = Math.max(0, Math.min(row * byteHeight, height - cardHeight));
    const previous = groups.at(-1);
    if (previous && top < previous.top + cardHeight + 12) previous.anchors.push(anchor);
    else groups.push({ anchors: [anchor], top });
  }
  return groups;
}

/** @param {ImageGroup} group @returns {ImageAnchor | undefined} */
function chosenImageAnchor(group) {
  const first = group.anchors[0];
  const uid = imageChoices.get(`${viewerState.activeSource}:${first?.node.uid}`);
  const previous = [...imageCards.values()].find((card) =>
    group.anchors.some((anchor) => anchor.node.uid === card.anchor.node.uid),
  );
  return (
    group.anchors.find((anchor) => anchor.node.uid === uid) ??
    group.anchors.find((anchor) => anchor.node.uid === previous?.anchor.node.uid) ??
    first
  );
}

/** @param {number} key @param {ImageAnchor} anchor @returns {ImageCard} */
function imageCardFor(key, anchor) {
  const existing = imageCards.get(key);
  if (existing) return existing;
  for (const [previousKey, card] of imageCards) {
    if (card.anchor.node.uid !== anchor.node.uid) continue;
    imageCards.delete(previousKey);
    return card;
  }
  return createImageCard(anchor);
}

function renderImagePreviews() {
  const rail = getElement('image-previews');
  if (rail.hidden) return;
  const retained = new Set();
  for (const group of visibleImageGroups()) {
    const first = group.anchors[0];
    const anchor = chosenImageAnchor(group);
    if (!first || !anchor) continue;
    const key = first.node.uid;
    const card = imageCardFor(key, anchor);
    card.group = group;
    card.element.style.top = `${group.top}px`;
    updateImageCard(card, anchor);
    if (!card.element.isConnected) rail.append(card.marker, card.element);
    imageCards.set(key, card);
    retained.add(key);
  }
  removeImageCards(retained);
}

/** @param {Set<number>} retained */
function removeImageCards(retained) {
  for (const [key, card] of imageCards) {
    if (retained.has(key)) continue;
    const focused = card.element.contains(document.activeElement);
    card.marker.remove();
    card.element.remove();
    imageCards.delete(key);
    if (focused) getElement('scrollcontainer').focus({ preventScroll: true });
  }
}

/** @returns {HTMLDialogElement} */
function createImageDialog() {
  const dialog = document.createElement('dialog');
  dialog.id = 'image-dialog';
  dialog.className = 'image-dialog';
  dialog.setAttribute('aria-labelledby', 'image-dialog-title');
  const title = document.createElement('h2');
  title.id = 'image-dialog-title';
  const contents = document.createElement('div');
  contents.id = 'image-dialog-content';
  const details = document.createElement('p');
  details.id = 'image-dialog-details';
  details.className = 'image-details';
  const actions = document.createElement('div');
  actions.className = 'image-dialog-actions';
  const reveal = imageButton('Reveal structure', () => {
    const uid = dialogImageAnchor?.node.uid;
    imageReturnFocus = null;
    dialog.close();
    if (uid === undefined) return;
    selectNode(uid, { focus: false });
    selectPane('structure');
    getNodeLabel(uid)?.focus();
  });
  const close = imageButton('Close', () => dialog.close());
  close.autofocus = true;
  actions.append(reveal, close);
  dialog.append(title, contents, details, actions);
  dialog.addEventListener('keydown', cycleImageDialogFocus);
  dialog.addEventListener('close', () => {
    contents.replaceChildren();
    dialogImageAnchor = null;
    if (!imageReturnFocus) return;
    const target = imageReturnFocus?.isConnected ? imageReturnFocus : getElement('scrollcontainer');
    target.focus({ preventScroll: true });
  });
  document.body.append(dialog);
  return dialog;
}

/** @param {KeyboardEvent} event */
function cycleImageDialogFocus(event) {
  if (event.key !== 'Tab' || !(event.currentTarget instanceof HTMLDialogElement)) return;
  const buttons = [...event.currentTarget.querySelectorAll('button')];
  const index = buttons.findIndex((button) => button === document.activeElement);
  const next = (index + (event.shiftKey ? -1 : 1) + buttons.length) % buttons.length;
  buttons[next]?.focus();
  event.preventDefault();
}

/** @param {ImageAnchor} anchor @param {HTMLElement} trigger */
function openImageDialog(anchor, trigger) {
  let dialog = document.getElementById('image-dialog');
  if (!(dialog instanceof HTMLDialogElement)) dialog = createImageDialog();
  if (!(dialog instanceof HTMLDialogElement)) return;
  imageReturnFocus = trigger;
  dialogImageAnchor = anchor;
  getElement('image-dialog-title').textContent = anchor.node.name;
  const own = `${anchor.node.source} @ 0x${anchor.node.offset.toString(16)} · ${anchor.node.size} bytes`;
  getElement('image-dialog-details').textContent = anchor.container
    ? `${own}. Shown within ${imageLocationLabel(anchor)}.`
    : own;
  getElement('image-dialog-content').replaceChildren(imageContent(anchor.node));
  clearHover();
  dialog.showModal();
}

function initImages() {
  for (const node of viewerData.nodes.filter(hasPreviewImage)) {
    const holder = document.querySelector(`[data-image-uid="${node.uid}"]`);
    holder?.append(imageContent(node));
  }
  document.addEventListener('polyfileviewport', renderImagePreviews);
}
