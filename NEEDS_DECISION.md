# Decisions needed

None open. The three questions left by the overnight build were resolved on
2026-10-23 in [`docs/decisions/004-resolve-open-decisions.md`](docs/decisions/004-resolve-open-decisions.md):

| # | Question | Resolution |
|---|---|---|
| 1 | Where do real tickets and notifications go? | Local files only (`var/`), dry-run by default |
| 2 | Is the draft risk rubric right? | Kept as rubric v1, unchanged; the final labels surfaced no problem |
| 3 | Which risk classifier does the graph use? | The rule-based rubric on the retrieved category: best accuracy (0.609) and high-risk recall (0.67) on the final labels |
