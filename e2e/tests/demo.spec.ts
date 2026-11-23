import { expect, test } from "@playwright/test";
import { RUNS, openDemo, playRun, watchForErrors } from "./helpers";

const TABS = ["Results", "What didn't work", "Replay"];

test.describe("demo page", () => {
  test("loads with no console errors or failed requests", async ({ page }) => {
    const errors = watchForErrors(page);
    await openDemo(page);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Pipeline Medic");
    await expect(page.getByRole("tab")).toHaveCount(3);
    for (const tab of TABS) {
      await page.getByRole("tab", { name: tab }).click();
    }
    await playRun(page, 0);
    expect(errors).toEqual([]);
  });

  for (const [i, run] of RUNS.entries()) {
    test(`replays ${run.repo}: diagnosis, risk, proposal and approval`, async ({ page }) => {
      const errors = watchForErrors(page);
      await openDemo(page);
      await playRun(page, i);
      const stages = page.locator("#stages > .stage");

      // diagnosis, with the verdict against the human label
      const diagnose = stages.nth(2);
      await expect(diagnose).toContainText(run.diagnosis.category ?? "unsure");
      await expect(diagnose.locator(".verdict")).toContainText(run.diagnosis.correct ? "✓" : "✗");
      await expect(diagnose.locator(".verdict")).toContainText(run.label);

      // risk badge and rubric reason
      await expect(stages.nth(3).locator(`.badge.risk-${run.risk.level}`)).toHaveText(
        run.risk.level.toUpperCase(),
      );
      await expect(stages.nth(3)).toContainText(run.risk.rationale);

      // proposed actions
      const propose = stages.nth(4);
      if (run.actions.length === 0) {
        await expect(propose).toContainText("no action proposed");
      }
      for (const action of run.actions) {
        await expect(propose).toContainText(action.tool);
      }

      // human approval step and the dry-run notice
      const approval = stages.nth(5);
      const approve = page.locator("#approve");
      if (run.approval.required) {
        await expect(approval).toContainText("The graph is paused");
        await expect(page.getByRole("button", { name: "Approve (dry-run)" })).toBeVisible();
        await approve.click();
        await expect(page.locator("#outcome .done")).toHaveText("Nothing was executed: dry-run.");
        await expect(approve).toBeDisabled();
        await expect(approve).toHaveText("Approved");
        for (const action of run.actions) {
          await expect(page.locator("#outcome")).toContainText(`${action.tool} → dry_run`);
        }
      } else {
        await expect(approve).toHaveCount(0);
        await expect(approval).toContainText("Nothing to approve");
        await expect(approval).toContainText(run.approval.run_status);
      }
      await expect(page.locator(".trace")).toBeVisible();
      expect(errors).toEqual([]);
    });
  }

  test("results and what-didn't-work tabs render from metrics.json", async ({ page }) => {
    await openDemo(page);
    await page.getByRole("tab", { name: "Results" }).click();
    await expect(page.locator("#results")).toBeVisible();
    await expect(page.locator("#results table")).toHaveCount(3);
    await expect(page.locator("#results")).toContainText("0.413");
    await page.getByRole("tab", { name: "What didn't work" }).click();
    await expect(page.locator("#failed .card")).toHaveCount(4);
    await expect(page.locator("#failed")).toContainText("8 of 20");
  });

  test("every link points to a valid destination", async ({ page, request }) => {
    await openDemo(page);
    const hrefs = new Set<string>();
    const collect = async () => {
      const found = await page
        .locator("a[href]")
        .evaluateAll((as) => as.map((a) => (a as HTMLAnchorElement).href));
      for (const href of found) hrefs.add(href);
    };
    for (let i = 0; i < RUNS.length; i++) {
      await playRun(page, i);
      await collect();
    }
    for (const tab of ["Results", "What didn't work"]) {
      await page.getByRole("tab", { name: tab }).click();
      await collect();
    }

    // External sites are not fetched (slow and rate-limited from CI); each is
    // checked against the expected hosts and exact URLs instead.
    const origin = new URL(page.url()).origin;
    const allowedHosts = new Set(["github.com", "www.linkedin.com"]);
    for (const href of hrefs) {
      const url = new URL(href);
      if (url.origin === origin) {
        expect((await request.get(href)).status(), href).toBe(200);
        continue;
      }
      expect(url.protocol, href).toBe("https:");
      expect(allowedHosts.has(url.host), href).toBe(true);
    }
    expect(hrefs).toContain("https://github.com/SreyaThota/pipeline-medic");
    expect(hrefs).toContain("https://www.linkedin.com/in/sreyathota5");
    for (const run of RUNS) expect(hrefs).toContain(run.run_url);

    // the data files the page depends on are served
    for (const file of ["runs.json", "metrics.json"]) {
      expect((await request.get(`/${file}`)).status()).toBe(200);
    }
  });
});
