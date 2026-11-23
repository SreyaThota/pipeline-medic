import { readFileSync } from "node:fs";
import { expect, type Page } from "@playwright/test";

export interface Run {
  log_id: string;
  repo: string;
  workflow: string;
  run_url: string;
  label: string;
  diagnosis: { category: string | null; correct: boolean };
  risk: { level: "low" | "medium" | "high"; rationale: string };
  actions: { tool: string }[];
  approval: { required: boolean; run_status: string };
}

/** The exported runs the page replays (the same file the page fetches). */
export const RUNS: Run[] = JSON.parse(
  readFileSync(new URL("../../demo/public/runs.json", import.meta.url), "utf-8"),
).runs;

/** Collects console errors, page errors and failed same-origin requests. */
export function watchForErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(`console: ${msg.text()}`);
  });
  page.on("pageerror", (err) => errors.push(`pageerror: ${err.message}`));
  page.on("requestfailed", (req) => errors.push(`requestfailed: ${req.url()}`));
  page.on("response", (res) => {
    if (res.url().startsWith("http://127.0.0.1") && res.status() >= 400) {
      errors.push(`http ${res.status()}: ${res.url()}`);
    }
  });
  return errors;
}

/** Opens the page and waits until the run picker is filled from runs.json. */
export async function openDemo(page: Page): Promise<void> {
  await page.goto("/");
  await expect(page.locator(".pick")).toHaveCount(RUNS.length);
}

/** Picks run i and waits until all six stages have been replayed. */
export async function playRun(page: Page, i: number): Promise<void> {
  await page.locator(".pick").nth(i).click();
  await expect(page.locator("#progress i.on")).toHaveCount(6);
  await expect(page.locator("#stages > .stage")).toHaveCount(6);
}
