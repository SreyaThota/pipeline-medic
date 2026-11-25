# Accessibility after fixes (demo page, 2026-11-25)

The same checks as [a11y-before.md](a11y-before.md), after the fixes in commit
`8a3afa8`. The axe scan below is the report from CI (GitHub Actions run
45204901764, image `mcr.microsoft.com/playwright:v1.65.0-noble`); CI uploads a
fresh one as the `a11y-report` artifact on every run.

## What changed

| Before | Fix | WCAG |
|---|---|---|
| Log line numbers at 3.35:1 (2.7:1 on highlighted evidence lines) | New colour `#8b949e`: 6.29:1 and 5.06:1 | 1.4.3 Contrast (Minimum) |
| High-risk badge text at 4.15:1 | New colour `#ff7b72`: 5.14:1 | 1.4.3 Contrast (Minimum) |
| Only the browser's 1px default focus ring | A 3px `#ffd33d` outline on every control (12–13:1 against the page) | 2.4.7 Focus Visible |
| No way to reject a proposal | A Reject button beside Approve, in a labelled group; its outcome is a real rejected run exported by `demo/build_demo_data.py` | 3.3.4 / usability |
| Focus lost after a decision | Focus moves to the recorded outcome | 2.4.3 Focus Order |
| Decorative progress bar read by screen readers | `aria-hidden="true"` | 1.3.1 Info and Relationships |

## Keyboard test (tests/keyboard.spec.ts)

All 6 tests pass on Desktop Chrome and Desktop Firefox: every control is
reached with Tab in document order with a visible focus style, and approve
and reject each work with Enter and with Space and move focus to the result.

---

## axe-core scan (WCAG 2.1 A/AA)

axe-core scan with tags `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`.
Serious and critical violations fail the test; moderate and minor are reported only.

### Summary

| Project | View | Critical | Serious | Moderate | Minor | Rules passed |
|---|---|---|---|---|---|---|
| desktop-chrome | main-page | 0 | 0 | 0 | 0 | 22 |
| desktop-chrome | results-tab | 0 | 0 | 0 | 0 | 25 |
| desktop-chrome | run-detail-approved | 0 | 0 | 0 | 0 | 25 |
| desktop-chrome | run-detail | 0 | 0 | 0 | 0 | 25 |
| desktop-chrome | what-didnt-work-tab | 0 | 0 | 0 | 0 | 22 |
| desktop-firefox | main-page | 0 | 0 | 0 | 0 | 22 |
| desktop-firefox | results-tab | 0 | 0 | 0 | 0 | 25 |
| desktop-firefox | run-detail-approved | 0 | 0 | 0 | 0 | 25 |
| desktop-firefox | run-detail | 0 | 0 | 0 | 0 | 25 |
| desktop-firefox | what-didnt-work-tab | 0 | 0 | 0 | 0 | 22 |
| pixel-7 | main-page | 0 | 0 | 0 | 0 | 22 |
| pixel-7 | results-tab | 0 | 0 | 0 | 0 | 25 |
| pixel-7 | run-detail-approved | 0 | 0 | 0 | 0 | 25 |
| pixel-7 | run-detail | 0 | 0 | 0 | 0 | 25 |
| pixel-7 | what-didnt-work-tab | 0 | 0 | 0 | 0 | 22 |

### Violations by rule

No violations found.
