import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { WCAG_TAGS, blocking, saveScan, type Scan } from "../a11y/report";
import { openDemo, playRun } from "./helpers";

// Each view is scanned with axe-core on every project (desktop and mobile).
// Serious and critical violations fail; moderate and minor are only reported.
const VIEWS: Record<string, (page: Page) => Promise<void>> = {
  "main-page": async (page) => {
    await openDemo(page);
  },
  "run-detail": async (page) => {
    await openDemo(page);
    await playRun(page, 0);
  },
  "run-detail-approved": async (page) => {
    await openDemo(page);
    await playRun(page, 0);
    await page.locator("#approve").click();
    await expect(page.locator("#outcome .done")).toBeVisible();
  },
  "results-tab": async (page) => {
    await openDemo(page);
    await page.getByRole("tab", { name: "Results" }).click();
  },
  "what-didnt-work-tab": async (page) => {
    await openDemo(page);
    await page.getByRole("tab", { name: "What didn't work" }).click();
  },
};

test.use({ reducedMotion: "reduce" });

for (const [view, open] of Object.entries(VIEWS)) {
  test(`axe WCAG 2.1 AA: ${view}`, async ({ page }, testInfo) => {
    await open(page);
    const result = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    const scan: Scan = {
      project: testInfo.project.name,
      view,
      url: page.url(),
      passes: result.passes.length,
      incomplete: result.incomplete.length,
      violations: result.violations.map((v) => ({
        rule: v.id,
        impact: v.impact ?? "minor",
        help: v.help,
        helpUrl: v.helpUrl,
        wcag: v.tags.filter((t) => /^wcag\d/.test(t)),
        nodes: v.nodes.map((n) => ({ target: n.target.join(" "), html: n.html, fix: n.failureSummary ?? "" })),
      })),
    };
    saveScan(scan);
    await testInfo.attach(`axe-${view}.json`, { body: JSON.stringify(scan, null, 1), contentType: "application/json" });
    const serious = blocking(scan).map((v) => `${v.impact}: ${v.rule} on ${v.nodes.map((n) => n.target).join(", ")}`);
    expect(serious, "serious or critical WCAG violations (see e2e/a11y-report.md)").toEqual([]);
  });
}
