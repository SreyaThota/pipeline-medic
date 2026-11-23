import { expect, test, type Page } from "@playwright/test";
import { RUNS, openDemo } from "./helpers";

// Keyboard-only use: every control reachable with Tab in document order, a
// visible focus indicator on each, and approve / reject working with both
// Enter and Space. Desktop projects only (a phone has no Tab key).
test.beforeEach(({}, testInfo) => {
  test.skip(testInfo.project.name === "pixel-7", "keyboard navigation is a desktop concern");
});

interface Focused { label: string; visible: boolean; inOrder: boolean }

/** Presses Tab until focus leaves the page or returns to an element already seen. */
async function tabThrough(page: Page, max = 60): Promise<Focused[]> {
  const seen: Focused[] = [];
  await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
  for (let i = 0; i < max; i++) {
    await page.keyboard.press("Tab");
    const info = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      if (!el || el === document.body) return null;
      const w = window as unknown as { __prev?: Element };
      const prev = w.__prev;
      const inOrder = !prev || !!(prev.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING);
      w.__prev = el;
      const css = getComputedStyle(el);
      const outline = css.outlineStyle !== "none" && parseFloat(css.outlineWidth) >= 2;
      const ring = css.boxShadow !== "none";
      const name = (el.getAttribute("aria-label") ?? el.textContent ?? "").trim().replace(/\s+/g, " ").slice(0, 40);
      return { label: `${el.tagName.toLowerCase()}:${name}`, visible: outline || ring, inOrder };
    });
    if (!info || seen.some((s) => s.label === info.label)) break;
    seen.push(info);
  }
  return seen;
}

async function focusPick(page: Page, i: number, key: "Enter" | " "): Promise<void> {
  await page.locator(".pick").nth(i).focus();
  await page.keyboard.press(key);
  await expect(page.locator("#stages > .stage")).toHaveCount(6);
}

/** Tabs forward from the current focus until `selector` has focus. */
async function tabTo(page: Page, selector: string, max = 40): Promise<void> {
  for (let i = 0; i < max; i++) {
    if (await page.locator(selector).evaluate((el) => el === document.activeElement)) return;
    await page.keyboard.press("Tab");
  }
  throw new Error(`could not reach ${selector} with Tab`);
}

test.use({ reducedMotion: "reduce" });

test("every control is reachable with Tab, in order, with a visible focus style", async ({ page }) => {
  await openDemo(page);
  const order = await tabThrough(page);
  const labels = order.map((f) => f.label);
  expect(labels.slice(0, 3)).toEqual(["button:Replay", "button:Results", "button:What didn't work"]);
  for (const run of RUNS) expect(labels.some((l) => l.includes(run.repo))).toBe(true);
  expect(labels.at(-1)).toContain("LinkedIn");
  expect(order.filter((f) => !f.inOrder).map((f) => f.label), "focus jumped backwards").toEqual([]);
  expect(order.filter((f) => !f.visible).map((f) => f.label), "no visible focus style").toEqual([]);
});

test("a replayed run is reachable and its controls have visible focus", async ({ page }) => {
  await openDemo(page);
  await focusPick(page, 0, "Enter");
  const order = await tabThrough(page);
  const labels = order.map((f) => f.label);
  expect(labels).toContain("button:Approve (dry-run)");
  expect(labels).toContain("button:Reject");
  expect(order.filter((f) => !f.visible).map((f) => f.label), "no visible focus style").toEqual([]);
});

const decisions: { run: number; button: "approve" | "reject"; key: "Enter" | " " }[] = [
  { run: 0, button: "approve", key: " " },
  { run: 1, button: "reject", key: "Enter" },
  { run: 2, button: "approve", key: "Enter" },
  { run: 4, button: "reject", key: " " },
];

for (const d of decisions) {
  const keyName = d.key === " " ? "Space" : "Enter";
  test(`${d.button} works with ${keyName} (${RUNS[d.run].repo})`, async ({ page }) => {
    await openDemo(page);
    await focusPick(page, d.run, "Enter");
    await tabTo(page, `#${d.button}`);
    await page.keyboard.press(d.key);
    const outcome = page.locator("#outcome");
    await expect(outcome).toContainText(d.button === "approve" ? "Approved by" : "Rejected by");
    await expect(outcome.locator(".done")).toHaveText(
      d.button === "approve" ? "Nothing was executed: dry-run." : "Rejected: nothing was executed.",
    );
    // focus moves to the outcome, so keyboard and screen-reader users land on the result
    await expect(outcome.locator("[tabindex='-1']").first()).toBeFocused();
    await expect(page.locator("#approve")).toBeDisabled();
    await expect(page.locator("#reject")).toBeDisabled();
  });
}
