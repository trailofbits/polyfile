/**
 * @param {string} source
 * @param {number} [offset]
 * @param {number} [length]
 * @param {string} [mime]
 * @param {string} [extension]
 */
function downloadRange(source, offset = 0, length, mime, extension) {
  const bytes = getSourceBytes(source);
  const end = offset + (length ?? bytes.length - offset);
  const type = mime || (source === "file" ? viewerData.mime : "application/octet-stream");
  let filename = viewerData.filename;
  if (source !== "file") filename += "-" + source.replace(":", "-");
  if (offset !== 0 || end !== bytes.length) filename += `@${offset}-${end - 1}`;
  if (extension && !filename.endsWith("." + extension)) filename += "." + extension;
  let binary = "";
  for (const byte of bytes.subarray(offset, end)) binary += String.fromCharCode(byte);
  const legacy = /** @type {{download: (data: string, name: string, type: string) => void}} */ (
    /** @type {unknown} */ (window)
  );
  legacy.download(`data:${type};base64,${btoa(binary)}`, filename, type);
}
