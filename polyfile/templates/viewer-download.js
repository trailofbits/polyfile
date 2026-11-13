/** @type {Record<string, string>} */
const downloadExtensions = {
  'application/octet-stream': 'bin',
  'application/pdf': 'pdf',
  'application/zip': 'zip',
  'application/vnd.ms-excel': 'xls',
  'application/msword': 'doc',
  'image/png': 'png',
  'image/jpeg': 'jpg',
  'text/plain': 'txt',
  'text/html': 'html',
};

/**
 * Creates a download name for a complete source or byte range.
 * @param {string} source
 * @param {number} offset
 * @param {number} length
 * @param {string} mime
 * @param {string | null | undefined} extension
 * @returns {string}
 */
function downloadName(source, offset, length, mime, extension) {
  const bytes = getSourceBytes(source);
  let name = viewerData.filename;
  if (source !== 'file') name += '-' + source.replaceAll(':', '-');
  if (offset === 0 && length === bytes.length && source === 'file') return name;
  name += '@' + offset + '-' + (offset + length - 1);
  const suffix = extension || downloadExtensions[mime];
  return suffix ? name + '.' + suffix : name;
}

/**
 * Downloads exact bytes from an embedded source without encoding a data URI.
 * @param {string} source
 * @param {number} [offset]
 * @param {number} [length]
 * @param {string | null} [mime]
 * @param {string | null} [extension]
 * @returns {void}
 */
function downloadRange(source, offset = 0, length, mime, extension) {
  const bytes = getSourceBytes(source);
  const size = length ?? bytes.length - offset;
  const type = mime || (source === 'file' ? viewerData.mime : 'application/octet-stream');
  const blob = new Blob([bytes.slice(offset, offset + size)], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = downloadName(source, offset, size, type, extension);
  anchor.hidden = true;
  document.body.append(anchor);
  try {
    anchor.click();
  } finally {
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}
