# claude-credit-audit

**English** | [中文](README_zh_CN.md)

> **After 2026-06-15, your `claude -p` and `claude-code-action` runs burn a separate Claude Agent SDK credit pool — and when it runs out, your CI silently stops.** This tool scans your repo *before* that happens and tells you whether you'll run out, when, and how to cut the cost.

A local CLI (and Claude / Codex skill) that **forecasts** which agent calls move from your Claude subscription to burning separate **Agent SDK credit**. Most tools track spend *after the fact* — this one scans your CI and scripts to **predict** it.

## Quickstart
Requires Python ≥ 3.10.

```bash
pip install claude-credit-audit
claude-credit-audit /path/to/your-repo --plan max5x
```

Point it at a **real repo that uses Claude in CI** — not at this repo itself (its test fixtures contain sample `claude -p` calls). `cost-audit` works as a short alias for the command.

```bash
# run without installing
pip install pyyaml
PYTHONPATH=src python -m cost_audit.cli /path/to/your-repo --plan max5x
```

## Background
From 2026-06-15, **non-interactive** calls — `claude -p` (headless), the Claude Agent SDK, Claude Code GitHub Actions (`claude-code-action`), and third-party apps — no longer draw from your Claude subscription. They consume a separate monthly credit pool (Pro ≈ $20 / Max5x ≈ $100 / Max20x ≈ $200, billed at standard API rates). When the credit runs out, automated requests **stop entirely** (unless you enable overflow billing); credits don't roll over. Interactive `claude` in the terminal is unaffected.

## Usage

| Flag | Meaning | Default |
|---|---|---|
| `--plan` | subscription plan `pro\|max5x\|max20x` (sets the credit limit) | max5x |
| `--lang` | report language `en\|zh` | en |
| `--pr-per-month` | monthly runs of pull_request / push workflows | 30 |
| `--issues-per-month` | monthly runs of issues / issue_comment workflows | 10 |
| `--manual-per-month` | monthly runs of workflow_dispatch / local scripts | 4 |
| `--tier` | force one token tier `small\|medium\|large` (overrides per-rule default) | per-rule |
| `--format` | output format `text\|md` | text |
| `--output` | write to a file instead of stdout (use with `--format md`) | stdout |
| `--calibrate` | calibrate token tiers from local `~/.claude` usage history | off |
| `--claude-home` | Claude config dir (with `--calibrate`) | `~/.claude` |

### Calibration
`--calibrate` parses real per-session token usage from `~/.claude/projects/**/*.jsonl` (`message.usage`) and recomputes the small/medium/large tiers from the p25/p50/p90 of your actual history — turning a tier *guess* into a calibration. Notes:
- Cache reads are weighted 0.1× (otherwise the same cached context, re-read every turn, inflates a long session by orders of magnitude).
- By default it uses only **non-interactive** sessions (whose `entrypoint` isn't vscode/desktop), which better represent CI/headless size; if there are fewer than 3 it falls back to all sessions and labels the result "may overestimate".

## Example reports

> Placeholder text reports until terminal screenshots are added.

### ✅ Clean — nothing burns credit
Even a repo with no credit-burning calls is checked for indirect signals, listed separately so you can verify them:

```
📊 Monthly credit forecast: $0 expected (range $0–$0) / $100 limit (max5x)
   🟢 No credit-burning calls found

⚠️ May burn credit (indirect/install signals, NOT counted above, verify manually):
  scripts/install.sh:3  [CI installs Claude Code CLI]
    npm install -g @anthropic-ai/claude-code@latest
    reason: CI installs the Claude Code CLI; if run non-interactively (e.g. claude -p) it burns credit — confirm whether it is actually called
  src/spawn.ts:6  [spawn/exec a claude binary]
    const proc = spawn(claudePath, args)
    reason: Code spawns/execs a binary named claude (e.g. claude -p), a programmatic non-interactive call that may burn credit — confirm the actual args
  .github/workflows/var.yml:5  [variable indirectly set to claude CLI]
    REVIEW_CLI_BIN: claude
    reason: A variable points the CLI at claude; at runtime it may run non-interactively and burn credit — indirect call, verify manually
```

### 🔴 Will burn credit
```
📊 Monthly credit forecast: $133 expected (range $15–$179) / $100 limit (max5x)
   🔴 Forecast burns through the limit around day 23
   ↳ After burnout all automated requests stop (unless overflow billing is enabled)

🔴 Calls that will burn credit (sorted by expected monthly spend):
  .github/workflows/matrix.yml:13  [claude -p / headless]
    model: claude-haiku-4-5  tier: large
    trigger: push + workflow_dispatch + matrix ×6 → ~204/mo → $61.20/mo (range $5.10–$61.20, 46%)
    💡 Run interactively instead of headless: saves all $61.20/mo (stays on subscription)
  .github/workflows/nightly.yml:11  [claude -p / headless]
    model: claude-opus-4-8  tier: large
    trigger: cron(0 3 * * *) → ~30/mo → $45.63/mo (range $3.80–$45.63, 34%)
    💡 Drop to a weekly trigger: $45.63→$6.50/mo, saves $39.14/mo
    💡 Switch to claude-haiku-4-5: $45.63→$9.13/mo, saves $36.50/mo
  … and 4 more calls (pr-check.yml, edge.sh, issue-bot.yml, agent.py)
```

_Abbreviated: each call also prints a `reason:` line and an overflow-billing tip; `--format md` produces a table instead._

## How it works
- **Range** — small/large tiers give an optimistic–pessimistic band; the expected value uses each call type's default tier (headless → large, SDK → small, …).
- **Frequency** — parses workflow triggers (cron / pull_request / push / workflow_dispatch / issues / issue_comment) and multiplies by the matrix size, correctly distinguishing an `on.issues` trigger from a `permissions.issues` grant.
- **Model** — when a `claude-*` model id is present it prices by family, otherwise defaults to Opus.
- **Confidence** — high/medium signals are counted in the forecast; **low** ones (indirect/install signals such as `npm install @anthropic-ai/claude-code`, `REVIEW_CLI_BIN: claude`, `spawn(claudePath, ['-p', …])`) are listed separately under "verify manually" and are **not** counted, so guesses don't pollute the headline number.

## FAQ

**Does my GitHub Action (`claude-code-action`) burn Agent SDK credit?**
Yes — from 2026-06-15 it runs non-interactively and draws from the credit pool, not your subscription. This tool flags every `claude-code-action` step.

**Does `claude -p` still count toward my Claude subscription?**
No. Headless `claude -p` (and the Claude Agent SDK) moved to the separate Agent SDK credit pool.

**What happens when the Claude Agent SDK credit runs out?**
Automated requests stop entirely unless you've enabled overflow billing; unused credit doesn't roll over. That's why a forecast matters.

**Is interactive `claude` in the terminal affected?**
No — interactive Claude Code / terminal use stays on your subscription.

**How is this different from usage trackers (e.g. ccusage)?**
Those report what you already spent. This scans your CI/scripts to **predict** what you'll spend before you run it.

## Use as a Claude / Codex skill
This repo is also a skill: [SKILL.md](SKILL.md) is the entry point. Install it by placing the folder under your skills directory (e.g. `~/.claude/skills/claude-credit-audit/`), then trigger it conversationally ("audit whether this repo will burn credit") or explicitly. The skill defaults to English and switches to Chinese when your request is Chinese.

## Project layout
| Path | Purpose |
|---|---|
| `src/cost_audit/scanner.py` | scan the repo, extract & classify call sites |
| `src/cost_audit/estimator.py` | cron parsing + frequency × cost modeling |
| `src/cost_audit/reporter.py` | risk report + quantified alternatives (en/zh) |
| `src/cost_audit/calibrate.py` | calibrate token tiers from local usage logs |
| `src/cost_audit/i18n.py` | en/zh message catalog |
| `src/cost_audit/cli.py` | command-line entry point |
| `src/cost_audit/data/billing_rules.yaml` | billing rules (data-driven, updatable) |
| `src/cost_audit/data/pricing.yaml` | model prices + plan limits + token tiers |
| `tests/` | pytest suite + sample fixtures |

## Development
```bash
pip install -e ".[dev]"
pytest -q
```

## Limitations
- No real billing API; tiers are estimates — calibrate with `--calibrate` (local history) or `--tier`.
- Trigger frequencies come from flags, not auto-inferred.
- Rules and prices live in `src/cost_audit/data/*.yaml`; update them when Anthropic changes pricing.

## License
[MIT](LICENSE)
