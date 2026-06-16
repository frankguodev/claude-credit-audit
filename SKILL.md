---
name: claude-credit-audit
description: Audit a code repository for Anthropic Claude Agent SDK credit cost under Anthropic's announced 2026-06-15 Agent SDK billing change (currently paused) — which agent calls would move from the subscription pool to burning Agent SDK credit, the monthly cost risk (with a burn-out-day forecast), and cheaper alternatives. Use when the user asks whether a repo will burn credit, about Agent SDK / Claude Code CI cost, whether `claude -p` or GitHub Actions still count as subscription, or wants to audit Claude calls in CI / scripts / workflows. 中文触发：审计这个仓库会不会烧 credit、Agent SDK 成本、claude -p 和 GitHub Actions 还算订阅吗、Claude Code CI 月度花费、credit 会不会用爆。
---

# Claude Credit Audit

Reads a repo's CI config, scripts, and the user's subscription plan to **forecast, ahead of time**, which agent calls would burn Agent SDK credit *if/when* Anthropic's announced 2026-06-15 billing change takes effect, whether the monthly credit limit would run out (and when), and how to cut cost. Unlike after-the-fact usage trackers, it scans workflows/scripts to predict.

> **Status (2026-06-16): the billing change is paused** ([Anthropic note](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan) — "for now, nothing has changed"). When presenting results, make clear this is a forecast of what would happen if/when the change resumes, not current billing.

## Locale
Default to **English** (`--lang en`). Use **Chinese** (`--lang zh`) when the user's request is primarily Chinese, the target audience is Chinese, or the user asks for a Chinese report. Present your spoken summary in the same language you pass to `--lang`.

## When to trigger
The user wants the credit cost of a repo's Claude/agent calls after the 6/15 change, or wants to audit `claude -p`, `claude-code-action`, Agent SDK, or Anthropic SDK calls in CI / workflows / scripts.

## How to run (you execute it — do not make the user type commands)
This skill bundles a Python CLI. **Prerequisite:** Python ≥ 3.10 with PyYAML on PATH; the wrappers check and tell the user to `pip install pyyaml` if it's missing. Run the wrapper from **this skill's directory** (it locates the interpreter and `src` itself):

```
# Windows
cost-audit.cmd <repo-path> --plan <pro|max5x|max20x> --lang <en|zh> --format md --output <tmpdir>/cost-report.md
# macOS / Linux
sh cost-audit.sh <repo-path> --plan <pro|max5x|max20x> --lang <en|zh> --format md --output <tmpdir>/cost-report.md
```

- If a wrapper is unavailable, equivalent: `PYTHONPATH=<skill-dir>/src python -m cost_audit.cli <repo> --plan <plan> --lang <lang> ...`
- After it runs, read the generated markdown and present it (below). Do not just paste the raw file.
- Ask the user for `--plan` (their plan sets the credit limit). If they use Claude Code heavily and want a more accurate token estimate, add `--calibrate` (calibrates tiers from local `~/.claude` history).

### Useful flags
- `--plan pro|max5x|max20x` — credit limit $20/$100/$200.
- `--lang en|zh` — report language (default en).
- `--pr-per-month N` / `--issues-per-month N` / `--manual-per-month N` — monthly trigger estimates (default 30/10/4).
- `--tier small|medium|large` — force one token tier (overrides per-rule default).
- `--calibrate` — calibrate tiers from local real usage.
- `--format md|json --output FILE` — write markdown (to present) or JSON (machine-readable); omit to print text to terminal.
- `--fail-on-burn` — exit non-zero when the expected forecast exceeds the credit limit (for CI gating; not needed for an interactive audit).

## How to present results
Summarize into sections — do not dump the raw report:
1. **Headline**: monthly credit forecast (expected + optimistic–pessimistic range) vs the limit, and whether/when it burns out.
2. **Calls that will burn credit**: sorted by spend; for each give file:line, trigger type & frequency, detected model, and the **quantified savings** of each alternative.
3. **Verify manually (low confidence)**: indirect/install signals (installing the Claude Code CLI, `spawn(claudePath)`, a variable pointing the CLI at claude) — **not counted in the forecast**; ask the user to confirm.
4. Also list the calls that stay on subscription (no credit).

Help the user decide what's worth changing vs. ignorable; prioritize high-frequency/high-cost items (lower cron frequency / switch to a cheaper model / run interactively / enable overflow / compare a plan upgrade).

## Limitations (state them honestly)
- Token usage is tier-estimated, not real billing; calibrate with `--calibrate` or `--tier`.
- Trigger frequencies come from flags, not auto-inferred.
- Rules and prices live in `src/cost_audit/data/*.yaml`; update them when Anthropic changes pricing.
- Literal-regex scanning: highly indirect calls in app code may only appear as low-confidence signals that need manual confirmation.
