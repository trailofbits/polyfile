# Test the HTML viewer

The browser tests open generated reports through `file://`, with networking disabled. Each test
fails on external requests, uncaught JavaScript errors, or console errors. Playwright and the
JavaScript check tools are development dependencies; reports contain no additional runtime assets.

Initialize the submodules, create a local environment, and install the optional browser dependencies:

```bash
git submodule update --init --recursive
uv venv --python 3.13
uv pip install -e '.[dev,viewer-test]'
uv run --no-project python -m playwright install chromium firefox webkit
PYTHONPATH=. uv run --no-project pytest -q tests/browser --browser chromium --browser firefox --browser webkit
```

Linux environments can pass `--with-deps` to `playwright install` to install system libraries.
The default test engine is Chromium. Browser tests skip if you have not installed Playwright;
existing Python tests do not require it. Failed tests save a screenshot under `test-results/`.

The Python CI matrix installs `.[dev,viewer-test]` so the project-wide type check can resolve
the browser test annotations. It runs `pytest tests --ignore=tests/browser`; the HTML viewer
workflow installs browser engines and runs `tests/browser` separately. Install the same extras
locally before running `uv run ty check --error-on-warning`.

Use `report_factory(contents, nodes=None, filename="sample.bin")` to render an independent report.
`tests.browser.helpers.match` builds match dictionaries and accepts `children`, `source`, and
additional SBuD fields. `open_report(viewer_page, report)` loads a report and waits for the byte
viewer to initialize. Each `viewer_page` has an isolated context, and the selected browser engine
is shared for the test session.

For JavaScript checks, use Node.js 24 and the exact pnpm version in `package.json`:

```bash
corepack pnpm audit --audit-level=moderate
corepack pnpm install --frozen-lockfile --ignore-scripts
corepack pnpm check:viewer
```

The project configuration disables install scripts and requires packages to be at least 24 hours
old. The checks apply to native `polyfile/templates/viewer-*.js` scripts. They use oxlint, oxfmt,
and TypeScript's strict JavaScript checks. The existing Jinja script and vendored libraries are
excluded; a report contains their rendered, inline contents. The checker reports when no native
scripts are present. Template changes also need browser tests because static checks cannot inspect
rendered Jinja output.
