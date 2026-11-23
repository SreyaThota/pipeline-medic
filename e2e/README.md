# e2e: browser tests for the demo page

Playwright (TypeScript) tests for the static demo page in `demo/public`,
kept separate from the Python project. `serve.mjs` serves that folder on
`http://127.0.0.1:4173` through Playwright's `webServer`; the tests never
touch the live site.

| Spec | What it checks |
|---|---|
| `tests/demo.spec.ts` | Page loads with no console errors or failed requests; each replayed run shows its diagnosis, risk, proposed action and approval step (dry-run notice included); Results and "What didn't work" tabs; every link points to an expected destination |
| `tests/visual.spec.ts` | Screenshot regression of the main page and one run detail view |

Projects: Desktop Chrome, Desktop Firefox and Pixel 7.

## Run

```bash
cd e2e
npm ci
npx playwright install chromium firefox
npx playwright test --ignore-snapshots   # functional tests on Windows/macOS
```

## Screenshot baselines

Baselines live in `tests/__screenshots__/<project>/`. They are rendered in the
Linux image `mcr.microsoft.com/playwright:v1.65.0-noble`, the same one CI
uses, because fonts and anti-aliasing differ between operating systems. To
regenerate them:

- **In CI:** Actions → E2E → Run workflow, tick `update_snapshots`, then
  download the `screenshot-baselines` artifact into `tests/__screenshots__/`.
- **With Docker:** `npm run test:docker:update`.

Timestamps and latency values are masked, and the page is captured with
reduced motion so its stage animation does not affect the image.
