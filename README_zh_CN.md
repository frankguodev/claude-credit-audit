# claude-credit-audit

[English](README.md) | **中文**

> **2026-06-15 起，你的 `claude -p` 和 `claude-code-action` 会烧一个独立的 Claude Agent SDK credit 池——用完后，你的 CI 会静默停掉。** 本工具在这发生之前扫描你的仓库，告诉你会不会烧爆、第几天、以及怎么省。

一个本地 CLI——也可作为 [Claude Code skill](#作为-claude-code-skill-使用)（与 Codex 同款 `SKILL.md` 格式）——**事前预测**哪些 agent 调用会从订阅池转为消耗独立的 **Agent SDK credit**。它扫描 GitHub Actions workflow 与脚本里的 `claude -p`、`claude-code-action`、Agent SDK 调用。多数工具是事后统计，本工具扫 CI/脚本做**事前预测**。

## 快速开始
需要 Python ≥ 3.10。

```bash
pip install claude-credit-audit
claude-credit-audit /path/to/your-repo --plan max5x
```

指向**真正在 CI 里用 Claude 的仓库**——别对本项目自己跑（测试 fixture 里有样例 `claude -p`）。`cost-audit` 是该命令的简短别名。

需要从本地克隆运行（如开发用途），见 [开发](#开发)。

## 背景
6/15 起，`claude -p`（headless）、Claude Agent SDK、Claude Code 的 GitHub Actions（`claude-code-action`）、第三方 app 等**非交互式**调用不再算进 Claude 订阅，改走单独月度 credit（Pro ≈ $20 / Max5x ≈ $100 / Max20x ≈ $200，按 API 标准价计费）。credit 用完后自动请求**直接停止**（除非手动开 overflow），不滚存。交互式 `claude` 终端使用不受影响。

## 用法

| 参数 | 说明 | 默认 |
|---|---|---|
| `--plan` | 订阅计划 `pro\|max5x\|max20x`（决定 credit 额度） | max5x |
| `--lang` | 报告语言 `en\|zh` | en |
| `--pr-per-month` | pull_request / push 触发的 workflow 月触发次数 | 30 |
| `--issues-per-month` | issues / issue_comment 触发的 workflow 月触发次数 | 10 |
| `--manual-per-month` | workflow_dispatch 及本地脚本的月调用次数 | 4 |
| `--tier` | 强制所有调用统一 token 档 `small\|medium\|large`（覆盖规则默认） | 按规则 |
| `--format` | 输出格式 `text\|md\|json` | text |
| `--output` | 写入文件而非终端（配合 `--format md\|json`） | 终端 |
| `--fail-on-burn` | 预期消耗超过额度时以非零退出（用于 CI 门禁） | 关 |
| `--calibrate` | 读取本地 `~/.claude` 用量日志，用真实历史校准 token 档位 | 关 |
| `--claude-home` | Claude 配置目录（配合 `--calibrate`） | `~/.claude` |
| `--version` | 打印版本并退出 | — |

### 在 CI 中使用
按预测结果给流水线设门禁，并产出机器可读结果：

```bash
claude-credit-audit . --plan max5x --fail-on-burn --format json --output cost-report.json
```

`--fail-on-burn` 在**预期**消耗超过额度时以非零退出（报告仍会先打印/写出），让 workflow 在你撞上 CI 静默中断前先失败。`--format json` 字段稳定可脚本化（`forecast.expected`、`forecast.level`、`forecast.burnout_day`、每个调用的 `cost_expected`，以及 `data_as_of`/`data_stale`）。

### 校准
`--calibrate` 解析 `~/.claude/projects/**/*.jsonl` 里每个会话的真实 token 用量（`message.usage`），用 p25/p50/p90 重算 small/medium/large 档，把「档位猜测」换成「按你历史校准」。要点：
- 缓存读取按 0.1× 折算（避免长会话里同一缓存被反复全价累加而爆炸）。
- 默认只取**非交互式**会话（`entrypoint` 非 vscode/desktop），更代表 CI/headless 规模；不足 3 个时回退到全部并标注「可能偏大」。

## 示例报告
对公开仓库的真实审计，均以 `--plan pro --lang zh` 运行。

### 🔴 [browser-use/browser-use](https://github.com/browser-use/browser-use) — 32 MB，知名活跃 Python 项目
`.github/workflows/claude.yml` 里的 `claude-code-action` 步骤被命中，并给出触发类型、识别到的模型、月度成本与更省的替代方案。

![browser-use/browser-use 审计结果](https://raw.githubusercontent.com/frankguodev/claude-credit-audit/main/public/browser-use-zh.png)

### 🔴 [Shubhamsaboo/awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) — 204 MB
大仓库：关键词预过滤让扫描保持快速，其 `claude-code-action` workflow 被检测并计价。

![Shubhamsaboo/awesome-llm-apps 审计结果](https://raw.githubusercontent.com/frankguodev/claude-credit-audit/main/public/awesome-llm-apps-zh.png)

### ✅ [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) — 35 MB，Claude skills 合集
没有会烧 credit 的调用。配置文件与注释里的 `~/.claude/…` 路径引用被正确地**不计入**——无误报。

![JimLiu/baoyu-skills 审计结果](https://raw.githubusercontent.com/frankguodev/claude-credit-audit/main/public/baoyu-skills-zh.png)

## 工作原理
- **区间**：small/large 档给出乐观–悲观带，预期值按调用类型的默认档（headless → large、SDK → small 等）。
- **频率**：解析 workflow 的 cron / pull_request / push / workflow_dispatch / issues / issue_comment，并叠加 matrix 倍数（正确区分 `on.issues` 触发与 `permissions.issues` 权限）。
- **模型**：扫到 `claude-*` 模型 ID 时按 family 选对应单价，否则默认 opus。
- **置信度**：high/medium 计入成本预测；**low（间接/安装信号**，如 `npm install @anthropic-ai/claude-code`、`REVIEW_CLI_BIN: claude`、`spawn(claudePath, ['-p', …])`）单列在「需人工确认」区、**不计入预测**，避免用猜测污染头条数字。

## 常见问题（FAQ）

**我的 GitHub Action（`claude-code-action`）会烧 Agent SDK credit 吗？**
会——6/15 起它属非交互式，走 credit 池而非订阅。本工具会标出每一处 `claude-code-action`。

**`claude -p` 还算我的 Claude 订阅吗？**
不算。headless `claude -p`（及 Claude Agent SDK）已转入独立的 Agent SDK credit 池。

**Claude Agent SDK credit 用完会怎样？**
除非开了 overflow billing，否则自动化请求**直接停止**；未用完的 credit 不滚存。所以「事前预测」才有意义。

**终端里交互式 `claude` 受影响吗？**
不受影响——交互式 Claude Code / 终端使用仍走订阅。

**和用量追踪工具（如 ccusage）有何不同？**
那些报告你**已经花掉**的；本工具扫 CI/脚本**预测**你将要花的，在你跑之前。

## 作为 Claude Code skill 使用
本仓库同时是一个 **Claude Code skill**（与 Codex 使用的 `SKILL.md` 格式相同）——[SKILL.md](SKILL.md) 是入口。作为 skill，你无需自己敲任何命令；当你的请求匹配时（如「帮我审计这个仓库会不会烧 credit」），agent 会自动帮你运行内置 CLI。

> **作为 skill 使用无需 `pip install`。** skill 自带 CLI（在 `src/` 下）与启动器（Windows 用 `cost-audit.cmd`，macOS/Linux 用 `cost-audit.sh`），启动器会自己定位 Python 和 `src/`。

**前置条件**：PATH 上有 Python ≥ 3.10 且已装 PyYAML。启动器会自检，缺失时提示你 `pip install pyyaml`。

### 安装（Claude Code）
整个目录就是 skill，所以最简单的安装方式是直接把它克隆进你的 skills 目录：

```bash
# macOS / Linux
git clone https://github.com/frankguodev/claude-credit-audit ~/.claude/skills/claude-credit-audit
```
```powershell
# Windows (PowerShell)
git clone https://github.com/frankguodev/claude-credit-audit "$env:USERPROFILE\.claude\skills\claude-credit-audit"
```

这样 `SKILL.md`、`src/`、数据文件和启动器就位于 `~/.claude/skills/claude-credit-audit/`（Windows：`%USERPROFILE%\.claude\skills\claude-credit-audit\`）。多余文件（`tests/`、`README.md` 等）不影响使用。

### 使用
1. 新开一个 Claude Code 会话，让它加载新装的 skill。
2. 用自然语言提问，如「帮我审计这个仓库会不会烧 Agent SDK credit」（中英文都行——你用哪种语言问，它就用哪种语言答）。agent 会运行审计并归纳：月度预测、会烧 credit 的调用点、以及更省的替代方案。

示例——skill 在 Claude Code 对话中运行的效果：

![claude-credit-audit 作为 Claude Code skill 运行](https://raw.githubusercontent.com/frankguodev/claude-credit-audit/main/public/use-skill-zh.png)

### Codex
Codex 使用相同的 `SKILL.md` 格式；改为把本目录放进 **Codex 自己的** skills 目录（确切位置见 Codex 官方文档），然后同样用对话方式触发。

## 项目结构
| 路径 | 作用 |
|---|---|
| `src/cost_audit/scanner.py` | 扫描仓库、提取并分类调用点 |
| `src/cost_audit/estimator.py` | cron 解析 + 频率 × 成本建模 |
| `src/cost_audit/reporter.py` | 风险报告 + 量化替代建议（en/zh） |
| `src/cost_audit/calibrate.py` | 读本地用量日志校准 token 档位 |
| `src/cost_audit/i18n.py` | en/zh 消息目录 |
| `src/cost_audit/cli.py` | 命令行入口 |
| `src/cost_audit/data/billing_rules.yaml` | 计费规则（数据驱动，可更新） |
| `src/cost_audit/data/pricing.yaml` | 模型单价 + 计划额度 + token 档位 |
| `tests/` | pytest 测试 + 样例 fixture |

## 开发
```bash
pip install -e ".[dev]"
ruff check src tests
pytest -q
```
CI（GitHub Actions）在 Python 3.10–3.12 上跑 ruff + pytest。

## 局限
- 未接真实账单 API；默认档位为估算，可用 `--calibrate`（本地历史）或 `--tier` 校准。
- 触发频率由参数提供，未自动推断。
- 模型与 matrix 倍数按 workflow **job**（调用点所在 job）归因；仅定义在 workflow 顶层 `env:` 的模型会回退到默认模型。
- 规则与价格在 `src/cost_audit/data/*.yaml`；报告页脚会标注其 `as_of` 日期并对超过 90 天的数据告警——Anthropic 调整后需更新。

## 许可证
[MIT](LICENSE)


## Links
- X: [frankguodev](https://x.com/frankguodev)