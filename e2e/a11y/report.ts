// Accessibility scan results: one JSON file per (project, view) is written by
// tests/a11y.spec.ts; after the run, writeReports() merges them into
// a11y-report.json and a readable a11y-report.md.
import { mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

export const E2E_DIR = fileURLToPath(new URL("..", import.meta.url));
export const SCAN_DIR = join(E2E_DIR, ".a11y-scans");
export const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];
export const BLOCKING = new Set(["serious", "critical"]);
const IMPACT_ORDER = ["critical", "serious", "moderate", "minor"];

export interface Finding {
  rule: string;
  impact: string;
  help: string;
  helpUrl: string;
  wcag: string[];
  nodes: { target: string; html: string; fix: string }[];
}

export interface Scan {
  project: string;
  view: string;
  url: string;
  violations: Finding[];
  passes: number;
  incomplete: number;
}

export function resetScans(): void {
  rmSync(SCAN_DIR, { recursive: true, force: true });
  mkdirSync(SCAN_DIR, { recursive: true });
}

export function saveScan(scan: Scan): void {
  mkdirSync(SCAN_DIR, { recursive: true });
  writeFileSync(join(SCAN_DIR, `${scan.project}__${scan.view}.json`), JSON.stringify(scan, null, 1));
}

export function loadScans(): Scan[] {
  let files: string[] = [];
  try {
    files = readdirSync(SCAN_DIR).filter((f) => f.endsWith(".json"));
  } catch {
    return [];
  }
  return files.sort().map((f) => JSON.parse(readFileSync(join(SCAN_DIR, f), "utf-8")) as Scan);
}

export function blocking(scan: Scan): Finding[] {
  return scan.violations.filter((v) => BLOCKING.has(v.impact));
}

const cell = (s: string) => s.replace(/\|/g, "\\|").replace(/\s+/g, " ").trim();

export function toMarkdown(scans: Scan[], title = "Accessibility report (WCAG 2.1 A/AA)"): string {
  const lines = [`# ${title}`, "",
    `axe-core scan with tags ${WCAG_TAGS.map((t) => `\`${t}\``).join(", ")}.`,
    "Serious and critical violations fail the test; moderate and minor are reported only.", ""];
  lines.push("## Summary", "", "| Project | View | Critical | Serious | Moderate | Minor | Rules passed |",
    "|---|---|---|---|---|---|---|");
  for (const s of scans) {
    const count = (impact: string) => s.violations.filter((v) => v.impact === impact).length;
    lines.push(`| ${s.project} | ${s.view} | ${count("critical")} | ${count("serious")} | ${count("moderate")} | ${count("minor")} | ${s.passes} |`);
  }

  // one section per rule, listing every place it was found
  const byRule = new Map<string, { finding: Finding; where: { scan: Scan; node: Finding["nodes"][number] }[] }>();
  for (const s of scans) {
    for (const v of s.violations) {
      const entry = byRule.get(v.rule) ?? { finding: v, where: [] };
      for (const node of v.nodes) entry.where.push({ scan: s, node });
      byRule.set(v.rule, entry);
    }
  }
  lines.push("", "## Violations by rule", "");
  if (byRule.size === 0) lines.push("No violations found.");
  const rules = [...byRule.values()].sort((a, b) =>
    IMPACT_ORDER.indexOf(a.finding.impact) - IMPACT_ORDER.indexOf(b.finding.impact) || a.finding.rule.localeCompare(b.finding.rule));
  for (const { finding, where } of rules) {
    lines.push(`### \`${finding.rule}\` (${finding.impact})`, "",
      `${finding.help}. WCAG: ${finding.wcag.join(", ") || "best practice"}. Reference: ${finding.helpUrl}`, "",
      "| Project / view | Element | How to fix |", "|---|---|---|");
    const seen = new Set<string>();
    for (const { scan, node } of where) {
      const key = `${scan.view}|${node.target}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const projects = where.filter((w) => w.scan.view === scan.view && w.node.target === node.target)
        .map((w) => w.scan.project);
      lines.push(`| ${[...new Set(projects)].join(", ")} / ${scan.view} | \`${cell(node.target)}\`<br>\`${cell(node.html).slice(0, 120)}\` | ${cell(node.fix)} |`);
    }
    lines.push("");
  }
  return lines.join("\n") + "\n";
}

export function writeReports(): Scan[] {
  const scans = loadScans();
  writeFileSync(join(E2E_DIR, "a11y-report.json"), JSON.stringify({ tags: WCAG_TAGS, scans }, null, 1));
  writeFileSync(join(E2E_DIR, "a11y-report.md"), toMarkdown(scans));
  return scans;
}
