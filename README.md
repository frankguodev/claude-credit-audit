# claude-credit-audit

**English** | [中文](README_zh_CN.md)

> **Anthropic announced a billing change (effective 2026-06-15) that moves `claude -p` and `claude-code-action` to a separate Agent SDK credit pool — then [*paused* it on 2026-06-15](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan), so for now nothing has changed.** This tool forecasts what it *would* cost you if/when the change takes effect — so you're ready, not surprised.

A local CLI — or a [Claude Code skill](#use-as-a-claude-code-skill-or-codex) — that **forecasts** which agent calls *would* move from your Claude subscription to burning separate **Agent SDK credit**. It scans GitHub Actions workflows and scripts for `claude -p`, `claude-code-action`, and Agent SDK calls. Most tools track spend *after the fact* — this one scans your CI and scripts to **predict** it.

## Quickstart
Requires Python ≥ 3.10.

```bash
pip install claude-credit-audit
claude-credit-audit /path/to/your-repo --plan max5x
```

Point it at a **real repo that uses Claude in CI** — not at this repo itself (its test fixtures contain sample `claude -p` calls). `cost-audit` works as a short alias for the command.

To run from a local clone (e.g. for development), see [Development](#development).

## Background
Anthropic announced that, from 2026-06-15, **non-interactive** calls — `claude -p` (headless), the Claude Agent SDK, the Claude Code GitHub Actions integration (`claude-code-action`), and third-party apps — would no longer draw from your Claude subscription, consuming a separate monthly credit pool instead (Pro $20 / Max5x $100 / Max20x $200, billed at standard API rates; when it runs out, automated requests **stop** unless you enable usage credits, and unused credit doesn't roll over). Interactive `claude` in the terminal/IDE is unaffected.

> **Status (2026-06-16): the change is [paused](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan).** Anthropic's note reads *"for now, nothing has changed"* — `claude -p` and `claude-code-action` still use your subscription today. This tool forecasts the impact *if/when* the change resumes, so you can plan ahead.

## Usage

| Flag | Meaning | Default |
|---|---|---|
| `--plan` | subscription plan `pro\|max5x\|max20x` (sets the credit limit) | max5x |
| `--lang` | report language `en\|zh` | en |
| `--pr-per-month` | monthly runs of pull_request / push workflows | 30 |
| `--issues-per-month` | monthly runs of issues / issue_comment workflows | 10 |
| `--manual-per-month` | monthly runs of workflow_dispatch / local scripts | 4 |
| `--tier` | force one token tier `small\|medium\|large` (overrides per-rule default) | per-rule |
| `--format` | output format `text\|md\|json` | text |
| `--output` | write to a file instead of stdout (use with `--format md\|json`) | stdout |
| `--fail-on-burn` | exit non-zero when the expected forecast exceeds the credit limit (for CI gating) | off |
| `--calibrate` | calibrate token tiers from local `~/.claude` usage history | off |
| `--claude-home` | Claude config dir (with `--calibrate`) | `~/.claude` |
| `--version` | print version and exit | — |

### Use in CI
Gate a pipeline on the forecast and emit a machine-readable artifact:

```bash
claude-credit-audit . --plan max5x --fail-on-burn --format json --output cost-report.json
```

`--fail-on-burn` exits non-zero when the **expected** forecast exceeds your credit limit (the report is still printed/written first), so a workflow step fails before you hit a silent CI stall. `--format json` is stable for scripting (`forecast.expected`, `forecast.level`, `forecast.burnout_day`, per-call `cost_expected`, plus `data_as_of`/`data_stale`).

### Calibration
`--calibrate` parses real per-session token usage from `~/.claude/projects/**/*.jsonl` (`message.usage`) and recomputes the small/medium/large tiers from the p25/p50/p90 of your actual history — turning a tier *guess* into a calibration. Notes:
- Cache reads are weighted 0.1× (otherwise the same cached context, re-read every turn, inflates a long session by orders of magnitude).
- By default it uses only **non-interactive** sessions (whose `entrypoint` isn't vscode/desktop), which better represent CI/headless size; if there are fewer than 3 it falls back to all sessions and labels the result "may overestimate".

## Example reports
Real audits of public repositories, run with `--plan max5x`.

### 🔴 [browser-use/browser-use](https://github.com/browser-use/browser-use) — 32 MB, active Python project
A `claude-code-action` step in `.github/workflows/claude.yml` is flagged with its trigger, detected model, monthly cost, and cheaper alternatives.

![Audit of browser-use/browser-use](https://raw.githubusercontent.com/frankguodev/claude-credit-audit/main/public/browser-use-en.png)

### 🔴 [Shubhamsaboo/awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) — 204 MB
A large repository: the keyword pre-filter keeps the scan fast, and its `claude-code-action` workflow is detected and priced.

![Audit of Shubhamsaboo/awesome-llm-apps](https://raw.githubusercontent.com/frankguodev/claude-credit-audit/main/public/awesome-llm-apps-en.png)

### ✅ [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) — 35 MB, Claude skills collection
No credit-burning calls. References to `~/.claude/…` in config files and comments are correctly **not** flagged — no false positives.

![Audit of JimLiu/baoyu-skills](https://raw.githubusercontent.com/frankguodev/claude-credit-audit/main/public/baoyu-skills-en.png)

## How it works
- **Range** — small/large tiers give an optimistic–pessimistic band; the expected value uses each call type's default tier (headless → large, SDK → small, …).
- **Frequency** — parses workflow triggers (cron / pull_request / push / workflow_dispatch / issues / issue_comment) and multiplies by the matrix size, correctly distinguishing an `on.issues` trigger from a `permissions.issues` grant.
- **Model** — when a `claude-*` model id is present it prices by family, otherwise defaults to Opus.
- **Confidence** — high/medium signals are counted in the forecast; **low** ones (indirect/install signals such as `npm install @anthropic-ai/claude-code`, `REVIEW_CLI_BIN: claude`, `spawn(claudePath, ['-p', …])`) are listed separately under "verify manually" and are **not** counted, so guesses don't pollute the headline number.

## FAQ

**Is this billing change in effect right now?**
No. Anthropic [paused it on 2026-06-15](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan) — *"for now, nothing has changed."* `claude -p` and `claude-code-action` still use your subscription today. The answers below describe what happens **if/when the change resumes**, which is what this tool forecasts.

**Would my GitHub Action (`claude-code-action`) burn Agent SDK credit?**
Yes, once the change takes effect — it runs non-interactively and would draw from the credit pool, not your subscription. This tool flags every `claude-code-action` step.

**Would `claude -p` still count toward my Claude subscription?**
No. Once in effect, headless `claude -p` (and the Claude Agent SDK) move to the separate Agent SDK credit pool.

**What happens when the Claude Agent SDK credit runs out?**
Automated requests stop entirely unless you've enabled usage credits (overflow billing); unused credit doesn't roll over. That's why a forecast matters.

**Is interactive `claude` in the terminal affected?**
No — interactive Claude Code / terminal use stays on your subscription.

**How is this different from usage trackers (e.g. ccusage)?**
Those report what you already spent. This scans your CI/scripts to **predict** what you'll spend before you run it.

## Use as a Claude Code skill (or Codex)
This repo doubles as a **Claude Code skill** (the same `SKILL.md` format Codex uses) — [SKILL.md](SKILL.md) is the entry point. As a skill you don't run any commands yourself; the agent runs the bundled CLI for you when your request matches (e.g. *"audit whether this repo will burn credit"*).

> **No `pip install` needed for skill use.** The skill is self-contained: it bundles the CLI under `src/` and a launcher (`cost-audit.cmd` on Windows, `cost-audit.sh` on macOS/Linux) that locates Python and `src/` itself.

**Prerequisite:** Python ≥ 3.10 with PyYAML on PATH. The launcher checks for PyYAML and tells you to `pip install pyyaml` if it's missing.

### Install (Claude Code)
The whole folder *is* the skill, so the simplest install is to clone it straight into your skills directory:

```bash
# macOS / Linux
git clone https://github.com/frankguodev/claude-credit-audit ~/.claude/skills/claude-credit-audit
```
```powershell
# Windows (PowerShell)
git clone https://github.com/frankguodev/claude-credit-audit "$env:USERPROFILE\.claude\skills\claude-credit-audit"
```

That puts `SKILL.md`, `src/`, the data files, and the launchers under `~/.claude/skills/claude-credit-audit/` (Windows: `%USERPROFILE%\.claude\skills\claude-credit-audit\`). The extra files (`tests/`, `README.md`, …) are harmless.

### Use it
1. Start a new Claude Code session so it picks up the newly added skill.
2. Ask it in plain language, e.g. *"audit whether this repo will burn Agent SDK credit"* (Chinese works too — the skill replies in the language you ask in). The agent will run the audit and summarize the forecast, the calls that burn credit, and cheaper alternatives.

Example — the skill running inside a Claude Code chat:

![claude-credit-audit running as a Claude Code skill](https://raw.githubusercontent.com/frankguodev/claude-credit-audit/main/public/use-skill-en.png)

### Codex
Codex uses the same `SKILL.md` format; place this folder in **Codex's** skills directory instead (see Codex's own docs for its exact location), then trigger it the same conversational way.

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
ruff check src tests
pytest -q
```
CI (GitHub Actions) runs ruff + pytest on Python 3.10–3.12.

## Limitations
- No real billing API; tiers are estimates — calibrate with `--calibrate` (local history) or `--tier`.
- Trigger frequencies come from flags, not auto-inferred.
- Model and matrix size are attributed per workflow **job** (the job containing the call); a model set only at the workflow's top-level `env:` falls back to the default model.
- Rules and prices live in `src/cost_audit/data/*.yaml`; the report footer stamps their `as_of` date and flags data older than 90 days — update them when Anthropic changes pricing.

## License
[MIT](LICENSE)

## Links
- X: [frankguodev](https://x.com/frankguodev)