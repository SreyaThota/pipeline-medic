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

## 2. Is the draft risk rubric right? (v0.4, v0.5)

**Built tonight:** `agents/risk_rubric.py` defines low / medium / high:
- **high:** the project cannot build, install or ship (compile/bundle errors,
  dependency resolution, out of memory/disk, any failure in a
  release/publish/deploy workflow)
- **medium:** correctness is red (failing tests, type errors, timeouts,
  broken CI configuration)
- **low:** hygiene or transient (lint/format, docs, repo policy such as a
  missing changelog entry, network/rate-limit blips)

It drives three things at once: the prompted classifier's instructions, the
rules fallback when the model fails, and the v0.5 risk labels. It is my
draft, written from the failure categories, not something CLAUDE.md defines.

**Options:** accept as is; change the level of specific categories (e.g.
`infra_network` low → medium, `ci_config` medium → high); or add signals
beyond category (branch name, how many jobs failed, first failure vs
repeat), which would need data the logs do not carry today.

**Needs from you:** accept or edit the three level definitions. Every
risk number reported tonight is relative to this draft.

## 3. Which risk classifier should the graph use? (v0.5 finding)

**Measured tonight** (`experiments/003_lora_risk_classifier.md`, 64 held-out
logs, draft labels):

| Classifier | Accuracy | Macro-F1 | High-risk recall |
|---|---|---|---|
| Prompted llama3.2 (current graph default) | 0.500 | 0.365 | **0.00** |
| LoRA MiniLM, 3 seeds | 0.52–0.59 | 0.50–0.57 | 0.58 |
| Rubric on retrieved category (no model) | 0.609 | 0.544 | 0.67 |

The current default never predicted "high" for any of the 12 high-risk logs.

**Not changed tonight**, because every number rests on the draft rubric (#2)
and unreviewed test categories.

**Options:** keep the prompted LLM; switch to the rubric on the retrieved
category (fast, no model, but it inherits every retrieval error); use LoRA
(best macro-F1, gain over the LLM not proven); or combine them, e.g. the
rubric by default with the LLM only to explain.

**Needs from you:** a choice. Ideally after #2 and the held-out label review.
