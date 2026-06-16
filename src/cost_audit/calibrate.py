"""V2：读取本地 Claude Code 用量日志，用真实历史校准 token 档位。

日志结构（实测自 ~/.claude/projects/<proj>/<session>.jsonl）：
每行一个 JSON 事件；`type == "assistant"` 的行带 `message.usage`，含
`input_tokens / cache_creation_input_tokens / cache_read_input_tokens / output_tokens`。
事件还带 `entrypoint`（如 sdk-ts / claude-vscode / claude-desktop），用于区分
程序化（会烧 credit）与交互式（不烧）。一个 jsonl 文件 ≈ 一个会话（一次 agent 运行）。

输入量口径：`input_tokens + cache_creation + CACHE_READ_WEIGHT × cache_read`。
缓存读取在长会话里会被每个 turn 反复计入，且实际按约 0.1x 计费，全价累加会把
同一段缓存上下文重复计数几十上百倍——因此按 0.1 权重折算，与真实计费对齐。

校准默认只取**非交互式**会话：6/15 计费变更针对的正是这类调用，且其规模比交互式
会话更能代表 CI / headless 的实际用量。
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

# 缓存读取的计费权重（API 上 cache read ≈ 0.1× 输入价）。
CACHE_READ_WEIGHT = 0.1

# 交互式入口（不烧 credit）。其余入口（sdk-*、headless、cli、未知）视为程序化。
INTERACTIVE_ENTRYPOINTS = {"claude-vscode", "claude-desktop", "claude-code", "claude"}


def default_claude_home() -> Path:
    return Path.home() / ".claude"


def discover_logs(claude_home: Path) -> list[Path]:
    proj = claude_home / "projects"
    if not proj.is_dir():
        return []
    return sorted(proj.rglob("*.jsonl"))


def _session_total(path: Path) -> tuple[int, int, str | None] | None:
    """返回 (输入 token 总和, 输出 token 总和, 会话主入口)；无 usage 返回 None。"""
    inp = out = 0.0
    found = False
    entrypoints: Counter = Counter()
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        ep = obj.get("entrypoint")
        if ep:
            entrypoints[ep] += 1
        if obj.get("type") != "assistant":
            continue
        usage = (obj.get("message") or {}).get("usage") or {}
        if not usage:
            continue
        inp += (
            (usage.get("input_tokens") or 0)
            + (usage.get("cache_creation_input_tokens") or 0)
            + CACHE_READ_WEIGHT * (usage.get("cache_read_input_tokens") or 0)
        )
        out += usage.get("output_tokens") or 0
        found = True
    if not found:
        return None
    entry = entrypoints.most_common(1)[0][0] if entrypoints else None
    return (int(round(inp)), int(out), entry)


def session_totals(paths) -> list[tuple[int, int, str | None]]:
    res = []
    for p in paths:
        t = _session_total(Path(p))
        if t and (t[0] > 0 or t[1] > 0):
            res.append(t)
    return res


def _is_interactive(entry: str | None) -> bool:
    return entry in INTERACTIVE_ENTRYPOINTS


def _percentile(sorted_vals: list[int], q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = q * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def calibrate_tiers(totals, min_sessions: int = 3, programmatic_only: bool = True):
    """从会话总量分布导出 token 档位。

    small=p25、medium=p50、large=p90。默认只取非交互式会话；不足时回退到全部。
    会话不足 min_sessions 返回 None。返回 (tiers_dict, n, source)，
    source ∈ {"programmatic", "all"}。
    """
    pool = totals
    source = "all"
    if programmatic_only:
        prog = [t for t in totals if not _is_interactive(t[2])]
        if len(prog) >= min_sessions:
            pool, source = prog, "programmatic"
        # 否则回退到全部（source 保持 "all"）

    if len(pool) < min_sessions:
        return None

    ins = sorted(t[0] for t in pool)
    outs = sorted(t[1] for t in pool)

    def tier(q: float) -> dict:
        return {
            "input": int(round(_percentile(ins, q))),
            "output": int(round(_percentile(outs, q))),
        }

    tiers = {"small": tier(0.25), "medium": tier(0.5), "large": tier(0.9)}
    return tiers, len(pool), source
