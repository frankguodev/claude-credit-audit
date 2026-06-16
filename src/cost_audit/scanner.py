"""模块 1：扫描仓库，提取 agent 调用点。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# 只扫描这些扩展名 + 无扩展名的脚本，避免读二进制和依赖目录。
SCAN_SUFFIXES = {".yml", ".yaml", ".sh", ".bash", ".py", ".js", ".ts", ".mjs", ".cjs"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}

# 整行注释前缀：命中的调用若被注释掉，不应计费。
_COMMENT_PREFIXES = ("#", "//", "*", "<!--")

# 预过滤关键词：所有规则的 pattern 都必含 "claude" 或 "anthropic"（由 test 守卫），
# 故不含这两个子串的文件不可能命中任何规则，直接跳过逐行正则——大仓库显著提速。
SCAN_KEYWORDS = ("claude", "anthropic")


@dataclass
class CallSite:
    file: str
    line: int
    snippet: str
    rule_id: str
    signal: dict  # {en, zh}
    billing: str  # "credit" | "subscription"
    reason: dict  # {en, zh}
    confidence: str = "high"  # high | medium | low
    tier: str = "medium"  # small | medium | large（来自规则，可被 --tier 覆盖）
    # 由 estimator 填充
    model: str = ""
    trigger: str = "manual"
    monthly_runs: float = 0.0
    cost_low: float = 0.0       # small 档（乐观）
    cost_expected: float = 0.0  # 该调用点指定档（预期）
    cost_high: float = 0.0      # large 档（悲观）


@dataclass
class CompiledRule:
    id: str
    signal: dict
    billing: str
    reason: dict
    confidence: str = "high"
    tier: str = "medium"
    regexes: list[re.Pattern] = field(default_factory=list)


def compile_rules(rules: list[dict]) -> list[CompiledRule]:
    compiled = []
    for r in rules:
        compiled.append(
            CompiledRule(
                id=r["id"],
                signal=r["signal"],
                billing=r["billing"],
                reason=r["reason"],
                confidence=r.get("confidence", "high"),
                tier=r.get("tier", "medium"),
                regexes=[re.compile(p) for p in r["patterns"]],
            )
        )
    return compiled


def _iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SCAN_SUFFIXES:
            yield path


def _is_comment(line: str) -> bool:
    return line.lstrip().startswith(_COMMENT_PREFIXES)


def scan(root: Path, rules: list[CompiledRule]) -> list[CallSite]:
    """返回去重后的调用点。

    去重策略：整行注释跳过；同一行命中多条规则时只记第一条（按规则顺序，
    避免一行物理调用被重复计费）。
    """
    sites: list[CallSite] = []
    for path in _iter_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        # 预过滤：无关键词的文件不可能命中任何规则，跳过逐行正则。
        low = text.lower()
        if not any(kw in low for kw in SCAN_KEYWORDS):
            continue
        rel = str(path.relative_to(root))
        for lineno, raw in enumerate(text.splitlines(), start=1):
            if _is_comment(raw):
                continue
            for rule in rules:
                if any(rx.search(raw) for rx in rule.regexes):
                    sites.append(
                        CallSite(
                            file=rel,
                            line=lineno,
                            snippet=raw.strip()[:120],
                            rule_id=rule.id,
                            signal=rule.signal,
                            billing=rule.billing,
                            reason=rule.reason,
                            confidence=rule.confidence,
                            tier=rule.tier,
                        )
                    )
                    break  # 一行只记一条，按规则优先级取第一条
    return sites
