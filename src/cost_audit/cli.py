"""入口：cost-audit <repo> --plan max5x --pr-per-month 30"""

from __future__ import annotations

import argparse
import sys
from importlib import resources
from pathlib import Path

import yaml

from . import scanner
from .estimator import estimate
from .i18n import DEFAULT_LANG, LANGS, t
from .reporter import build_markdown, build_report


def _load_yaml(name: str) -> dict:
    # 数据随包发布，用 importlib.resources 读取，wheel 安装后也可用。
    text = resources.files("cost_audit").joinpath("data", name).read_text(encoding="utf-8")
    return yaml.safe_load(text)


def _fmt_k(n: int) -> str:
    return f"{n / 1000:.0f}k" if n >= 1000 else str(n)


def _apply_calibration(pricing: dict, claude_home: str | None, lang: str) -> str:
    """就地用本地日志校准 pricing['token_tiers']，返回一行说明。"""
    from . import calibrate

    home = Path(claude_home) if claude_home else calibrate.default_claude_home()
    logs = calibrate.discover_logs(home)
    totals = calibrate.session_totals(logs)
    cal = calibrate.calibrate_tiers(totals)
    if not cal:
        return t(lang, "cli_calib_fail", home=home, n=len(totals))
    tiers, n, source = cal
    pricing["token_tiers"] = tiers
    parts = ", ".join(
        f"{name}={_fmt_k(tier['input'])}/{_fmt_k(tier['output'])}"
        for name, tier in tiers.items()
    )
    label = t(lang, "calib_label_prog" if source == "programmatic" else "calib_label_all")
    return t(lang, "cli_calib_ok", n=n, label=label, parts=parts)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="cost-audit",
        description="Forecast which agent calls will burn Agent SDK credit after the "
        "2026-06-15 billing change, with monthly risk and cheaper alternatives.",
    )
    p.add_argument("repo", nargs="?", default=".", help="repo root to scan (default: cwd)")
    p.add_argument(
        "--plan",
        default="max5x",
        choices=["pro", "max5x", "max20x"],
        help="subscription plan (sets the credit limit)",
    )
    p.add_argument(
        "--pr-per-month", type=float, default=30.0,
        help="estimated monthly runs of pull_request / push workflows (default 30)",
    )
    p.add_argument(
        "--manual-per-month", type=float, default=4.0,
        help="estimated monthly runs of workflow_dispatch / local scripts (default 4)",
    )
    p.add_argument(
        "--issues-per-month", type=float, default=10.0,
        help="estimated monthly runs of issues / issue_comment workflows (default 10)",
    )
    p.add_argument(
        "--tier", choices=["small", "medium", "large"], default=None,
        help="force one token tier for all calls (overrides per-rule default)",
    )
    p.add_argument(
        "--lang", choices=list(LANGS), default=DEFAULT_LANG,
        help="report language: en (default) or zh",
    )
    p.add_argument(
        "--format", choices=["text", "md"], default="text",
        help="output format: text (terminal, default) or md (markdown report)",
    )
    p.add_argument(
        "--output", default=None,
        help="write to a file instead of stdout (use with --format md)",
    )
    p.add_argument(
        "--calibrate", action="store_true",
        help="calibrate token tiers from local Claude Code usage logs",
    )
    p.add_argument(
        "--claude-home", default=None,
        help="Claude config dir (default ~/.claude), used with --calibrate",
    )
    args = p.parse_args(argv)

    # Windows 控制台默认 GBK，无法打印 emoji；尽量把 stdout/stderr 切到 UTF-8。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass

    root = Path(args.repo).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    pricing = _load_yaml("pricing.yaml")
    rules_raw = _load_yaml("billing_rules.yaml")["rules"]
    rules = scanner.compile_rules(rules_raw)

    if args.calibrate:
        print(_apply_calibration(pricing, args.claude_home, args.lang), file=sys.stderr)

    sites = scanner.scan(root, rules)
    estimate(
        sites,
        root,
        pricing,
        args.pr_per_month,
        args.manual_per_month,
        args.issues_per_month,
        tier_override=args.tier,
    )

    plan_credit = pricing["plans"][args.plan]["credit_usd"]
    builder = build_markdown if args.format == "md" else build_report
    report = builder(sites, args.plan, plan_credit, pricing, args.lang)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(t(args.lang, "cli_wrote", path=args.output))
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
