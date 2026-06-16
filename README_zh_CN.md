# claude-credit-audit

[English](README.md) | **中文**

> **2026-06-15 起，你的 `claude -p` 和 `claude-code-action` 会烧一个独立的 Claude Agent SDK credit 池——用完后，你的 CI 会静默停掉。** 本工具在这发生之前扫描你的仓库，告诉你会不会烧爆、第几天、以及怎么省。

一个本地 CLI（同时是 Claude/Codex skill），**事前预测**哪些 agent 调用会从订阅池转为消耗独立的 **Agent SDK credit**。竞品大多「事后追踪已花的钱」；本工具扫 CI/脚本做「事前预测」。

## 快速开始
需要 Python ≥ 3.10。

```bash
pip install claude-credit-audit
claude-credit-audit /path/to/your-repo --plan max5x
```

指向**真正在 CI 里用 Claude 的仓库**——别对本项目自己跑（测试 fixture 里有样例 `claude -p`）。`cost-audit` 是该命令的简短别名。

```bash
# 免安装直接跑
pip install pyyaml
PYTHONPATH=src python -m cost_audit.cli /path/to/your-repo --plan max5x
```

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
| `--format` | 输出格式 `text\|md` | text |
| `--output` | 写入文件而非终端（配合 `--format md`） | 终端 |
| `--calibrate` | 读取本地 `~/.claude` 用量日志，用真实历史校准 token 档位 | 关 |
| `--claude-home` | Claude 配置目录（配合 `--calibrate`） | `~/.claude` |

### 校准
`--calibrate` 解析 `~/.claude/projects/**/*.jsonl` 里每个会话的真实 token 用量（`message.usage`），用 p25/p50/p90 重算 small/medium/large 档，把「档位猜测」换成「按你历史校准」。要点：
- 缓存读取按 0.1× 折算（避免长会话里同一缓存被反复全价累加而爆炸）。
- 默认只取**非交互式**会话（`entrypoint` 非 vscode/desktop），更代表 CI/headless 规模；不足 3 个时回退到全部并标注「可能偏大」。

## 示例报告

> 终端截图就位前的文字版示例。

### ✅ 无消耗 — 不烧 credit
即使没有会烧 credit 的调用，也会检查间接信号并单列出来供你核实：

```
📊 月度 credit 预测：$0 预期（区间 $0–$0） / $100 额度（max5x）
   🟢 未发现会烧 credit 的调用

⚠️ 可能烧 credit（间接/安装信号，未计入上方预测，需人工确认）：
  scripts/install.sh:3  [CI 安装 Claude Code CLI]
    npm install -g @anthropic-ai/claude-code@latest
    原因：CI 中安装 Claude Code CLI，若以非交互方式运行（如 claude -p）会烧 credit——需确认实际是否调用
  src/spawn.ts:6  [spawn/exec claude 二进制]
    const proc = spawn(claudePath, args)
    原因：代码中 spawn/exec 一个名为 claude 的二进制（如 claude -p），属程序化非交互调用，可能烧 credit——需确认实际参数
  .github/workflows/var.yml:5  [变量间接指定 claude 为 CLI]
    REVIEW_CLI_BIN: claude
    原因：通过变量把 CLI 指定为 claude，运行时可能以非交互方式烧 credit——间接调用，需人工确认
```

### 🔴 有消耗 — 会烧 credit
```
📊 月度 credit 预测：$133 预期（区间 $15–$179） / $100 额度（max5x）
   🔴 预期情形约第 23 天烧爆额度
   ↳ 烧爆后所有自动化请求停止（除非已手动开启 overflow billing）

🔴 会烧 credit 的调用点（按预期月度消耗排序）：
  .github/workflows/matrix.yml:13  [claude -p / headless]
    模型：claude-haiku-4-5  档位：large
    触发：push + workflow_dispatch + matrix ×6 → ~204 次/月 → $61.20/月（区间 $5.10–$61.20，占 46%）
    💡 能交互完成的改用交互式 claude：省全部 $61.20/月（仍走订阅）
  .github/workflows/nightly.yml:11  [claude -p / headless]
    模型：claude-opus-4-8  档位：large
    触发：cron(0 3 * * *) → ~30 次/月 → $45.63/月（区间 $3.80–$45.63，占 34%）
    💡 降到每周触发：$45.63→$6.50/月，省 $39.14/月
    💡 改用 claude-haiku-4-5：$45.63→$9.13/月，省 $36.50/月
  … 还有 4 条（pr-check.yml、edge.sh、issue-bot.yml、agent.py）
```

_已精简：每条调用还会打印一行 `原因:` 和一条 overflow 提示；`--format md` 则输出表格。_

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

## 作为 Claude / Codex skill 使用
本仓库本身也是一个 skill：[SKILL.md](SKILL.md) 是入口。把目录放进 skills 目录（如 `~/.claude/skills/claude-credit-audit/`）即装好，然后用自然语言触发（「帮我看看这仓库会不会烧 credit」）或显式调用。skill 默认英语，请求是中文时自动切中文。

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
pytest -q
```

## 局限
- 未接真实账单 API；默认档位为估算，可用 `--calibrate`（本地历史）或 `--tier` 校准。
- 触发频率由参数提供，未自动推断。
- 规则与价格在 `src/cost_audit/data/*.yaml`，Anthropic 调整后需更新。

## 许可证
[MIT](LICENSE)
