# Decisions needed

Open questions that CLAUDE.md does not answer and that change a design.
Each sub-task that depends on one was skipped or built in a clearly marked
local/stub form.

## 1. Which external systems should "real" tickets and notifications go to? (v0.3)

**Built tonight:** `create_ticket` and `notify` work end to end, dry-run by
default. When real actions are enabled (`ACTIONS_ENABLED=true` plus an
approved call), tickets are appended to `var/tickets.jsonl` and notifications
to `var/outbox.jsonl`. Nothing leaves the machine.

**Skipped:** an adapter for any external service, because each needs
credentials, has different permission scopes, and would publish content.

**Options:**
- **GitHub Issues** in the repo whose CI failed (via `gh` / a fine-grained
  token with `issues:write` on that repo only). Fits dogfooding best.
- **Jira** — the brief's suggestion; CLAUDE.md section 9 did not adopt it.
- **Slack / Teams / email** for `notify` (webhook URL as a secret).
- **Keep local files only** for the portfolio demo, and say so.

**Needs from you:** which backend(s), and confirmation that a token may be
used in this repo's local `.env`.
