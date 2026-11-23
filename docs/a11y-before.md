# Accessibility before fixes (demo page, 2026-11-23)

The first scan of `demo/public/index.html`, before any accessibility fix.
Produced by `cd e2e && npx playwright test tests/a11y.spec.ts tests/keyboard.spec.ts`
(axe-core 4.14 through `@axe-core/playwright`, Chromium, Firefox and Pixel 7).

## Keyboard test (tests/keyboard.spec.ts, Desktop Chrome)

axe cannot test keyboard use, so these come from the keyboard test run on the
same unchanged page:

| Problem | WCAG | Evidence |
|---|---|---|
| No focus style of its own: all 10 controls on the start screen relied on the browser's 1px default ring, which is hard to see on the dark background | 2.4.7 Focus Visible | `every control is reachable with Tab...` failed: all 10 controls listed under "no visible focus style" |
| No way to reject: the approval step offered only "Approve (dry-run)" | 3.3.4 (error prevention: a reversible choice) / usability | `a replayed run is reachable...` failed: no `button:Reject` among the focusable controls |
| Focus lost after approving: the button disabled itself and focus fell back to the page body, so keyboard and screen-reader users did not land on the result | 2.4.3 Focus Order | `approve works with Space/Enter` failed: no focused element in the outcome |

Tab order itself was already logical: tabs, the five runs, then the footer
links, never jumping backwards.

---

## axe-core scan (WCAG 2.1 A/AA)

axe-core scan with tags `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`.
Serious and critical violations fail the test; moderate and minor are reported only.

### Summary

| Project | View | Critical | Serious | Moderate | Minor | Rules passed |
|---|---|---|---|---|---|---|
| desktop-chrome | main-page | 0 | 0 | 0 | 0 | 21 |
| desktop-chrome | results-tab | 0 | 0 | 0 | 0 | 24 |
| desktop-chrome | run-detail-approved | 0 | 1 | 0 | 0 | 24 |
| desktop-chrome | run-detail | 0 | 1 | 0 | 0 | 24 |
| desktop-chrome | what-didnt-work-tab | 0 | 0 | 0 | 0 | 21 |
| desktop-firefox | main-page | 0 | 0 | 0 | 0 | 21 |
| desktop-firefox | results-tab | 0 | 0 | 0 | 0 | 24 |
| desktop-firefox | run-detail-approved | 0 | 1 | 0 | 0 | 24 |
| desktop-firefox | run-detail | 0 | 1 | 0 | 0 | 24 |
| desktop-firefox | what-didnt-work-tab | 0 | 0 | 0 | 0 | 21 |
| pixel-7 | main-page | 0 | 0 | 0 | 0 | 21 |
| pixel-7 | results-tab | 0 | 0 | 0 | 0 | 24 |
| pixel-7 | run-detail-approved | 0 | 1 | 0 | 0 | 24 |
| pixel-7 | run-detail | 0 | 1 | 0 | 0 | 24 |
| pixel-7 | what-didnt-work-tab | 0 | 0 | 0 | 0 | 21 |

### Violations by rule

#### `color-contrast` (serious)

Elements must meet minimum color contrast ratio thresholds. WCAG: wcag2aa, wcag143. Reference: https://dequeuniversity.com/rules/axe/4.14/color-contrast?application=playwright

| Project / view | Element | How to fix |
|---|---|---|
| desktop-chrome, desktop-firefox, pixel-7 / run-detail-approved | `div:nth-child(1) > .n`<br>`<span class="n">327</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail-approved | `div:nth-child(2) > .n`<br>`<span class="n">328</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail-approved | `.ev:nth-child(3) > .n`<br>`<span class="n">329</span>` | Fix any of the following: Element has insufficient color contrast of 2.7 (foreground color: #5c6773, background color: #0d2826, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail-approved | `div:nth-child(4) > .n`<br>`<span class="n">330</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail-approved | `div:nth-child(5) > .n`<br>`<span class="n">331</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail-approved | `div:nth-child(7) > .n`<br>`<span class="n">345</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail-approved | `div:nth-child(8) > .n`<br>`<span class="n">346</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail-approved | `.ev:nth-child(9) > .n`<br>`<span class="n">347</span>` | Fix any of the following: Element has insufficient color contrast of 2.7 (foreground color: #5c6773, background color: #0d2826, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail-approved | `div:nth-child(10) > .n`<br>`<span class="n">348</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail-approved | `div:nth-child(11) > .n`<br>`<span class="n">349</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail-approved | `div:nth-child(13) > .n`<br>`<span class="n">364</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail-approved | `div:nth-child(14) > .n`<br>`<span class="n">365</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail-approved | `.ev:nth-child(15) > .n`<br>`<span class="n">366</span>` | Fix any of the following: Element has insufficient color contrast of 2.7 (foreground color: #5c6773, background color: #0d2826, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail-approved | `.ev:nth-child(16) > .n`<br>`<span class="n">367</span>` | Fix any of the following: Element has insufficient color contrast of 2.7 (foreground color: #5c6773, background color: #0d2826, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail-approved | `div:nth-child(17) > .n`<br>`<span class="n">368</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail-approved | `div:nth-child(18) > .n`<br>`<span class="n">369</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail-approved | `.risk-high`<br>`<span class="badge risk-high" style="font-size:16px">HIGH</span>` | Fix any of the following: Element has insufficient color contrast of 4.15 (foreground color: #f85149, background color: #3f2529, font size: 12.0pt (16px), font weight: bold). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail | `div:nth-child(1) > .n`<br>`<span class="n">327</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail | `div:nth-child(2) > .n`<br>`<span class="n">328</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail | `.ev:nth-child(3) > .n`<br>`<span class="n">329</span>` | Fix any of the following: Element has insufficient color contrast of 2.7 (foreground color: #5c6773, background color: #0d2826, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail | `div:nth-child(4) > .n`<br>`<span class="n">330</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail | `div:nth-child(5) > .n`<br>`<span class="n">331</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail | `div:nth-child(7) > .n`<br>`<span class="n">345</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail | `div:nth-child(8) > .n`<br>`<span class="n">346</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail | `.ev:nth-child(9) > .n`<br>`<span class="n">347</span>` | Fix any of the following: Element has insufficient color contrast of 2.7 (foreground color: #5c6773, background color: #0d2826, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail | `div:nth-child(10) > .n`<br>`<span class="n">348</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail | `div:nth-child(11) > .n`<br>`<span class="n">349</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail | `div:nth-child(13) > .n`<br>`<span class="n">364</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail | `div:nth-child(14) > .n`<br>`<span class="n">365</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail | `.ev:nth-child(15) > .n`<br>`<span class="n">366</span>` | Fix any of the following: Element has insufficient color contrast of 2.7 (foreground color: #5c6773, background color: #0d2826, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail | `.ev:nth-child(16) > .n`<br>`<span class="n">367</span>` | Fix any of the following: Element has insufficient color contrast of 2.7 (foreground color: #5c6773, background color: #0d2826, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail | `div:nth-child(17) > .n`<br>`<span class="n">368</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail | `div:nth-child(18) > .n`<br>`<span class="n">369</span>` | Fix any of the following: Element has insufficient color contrast of 3.35 (foreground color: #5c6773, background color: #0a0e13, font size: 9.4pt (12.5px), font weight: normal). Expected contrast ratio of 4.5:1 |
| desktop-chrome, desktop-firefox, pixel-7 / run-detail | `.risk-high`<br>`<span class="badge risk-high" style="font-size:16px">HIGH</span>` | Fix any of the following: Element has insufficient color contrast of 4.15 (foreground color: #f85149, background color: #3f2529, font size: 12.0pt (16px), font weight: bold). Expected contrast ratio of 4.5:1 |

