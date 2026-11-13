#!/usr/bin/env bash
set -euo pipefail

viewer_scripts=()
for script in polyfile/templates/viewer-*.js; do
  if [[ -f "$script" ]]; then
    viewer_scripts+=("$script")
  fi
done

if [[ ${#viewer_scripts[@]} -eq 0 ]]; then
  printf '%s\n' 'No native viewer scripts to check; the current viewer uses a Jinja template.'
  exit 0
fi

viewer_directory=$(mktemp -d "${TMPDIR:-/tmp}/polyfile-viewer.XXXXXX")
cleanup() {
  rm -f "${viewer_directory}/viewer.js"
  rmdir "$viewer_directory"
}
trap cleanup EXIT
cat "${viewer_scripts[@]}" >"${viewer_directory}/viewer.js"
pnpm exec oxlint --config .oxlintrc.json --deny-warnings "${viewer_directory}/viewer.js"
pnpm exec oxfmt --check "${viewer_scripts[@]}"
pnpm exec tsc --project tsconfig.viewer.json
