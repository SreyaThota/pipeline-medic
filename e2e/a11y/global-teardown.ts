import { blocking, loadScans, writeReports } from "./report";

export default function globalTeardown(): void {
  // A run without accessibility scans (e.g. only the keyboard test) leaves the
  // previous report untouched.
  if (loadScans().length === 0) return;
  const scans = writeReports();
  const failing = scans.reduce((n, s) => n + blocking(s).length, 0);
  const total = scans.reduce((n, s) => n + s.violations.length, 0);
  console.log(`a11y: ${scans.length} scans, ${total} rule violations, ${failing} serious or critical` +
    " (e2e/a11y-report.md)");
}
