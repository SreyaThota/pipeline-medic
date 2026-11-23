import { expect, test } from "@playwright/test";
import { openDemo, playRun } from "./helpers";

// Reduced motion makes the page skip its stage animation, so screenshots show
// the finished state. Latency values and audit timestamps are masked.
test.use({ reducedMotion: "reduce" });

test.describe("visual regression", () => {
  test("main page", async ({ page }) => {
    await openDemo(page);
    await expect(page).toHaveScreenshot("main.png", { fullPage: true });
  });

  test("run detail after approval", async ({ page }) => {
    await openDemo(page);
    await playRun(page, 0);
    await page.getByRole("button", { name: "Approve (dry-run)" }).click();
    await expect(page.locator("#outcome .done")).toBeVisible();
    await page.evaluate(() => window.scrollTo(0, 0));
    await expect(page).toHaveScreenshot("run-detail.png", {
      fullPage: true,
      mask: [page.locator(".ms"), page.locator(".trace"), page.locator(".audit")],
    });
  });
});
