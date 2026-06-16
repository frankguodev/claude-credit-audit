"""模块 4：生成风险报告（区间）+ 量化替代路径建议。支持 en / zh。"""

from __future__ import annotations

import datetime as _dt
import json
import sys

from .estimator import WEEKS_PER_MONTH, per_run_cost
from .i18n import DEFAULT_LANG, loc, t

DAYS_PER_MONTH = 30.42
STALE_AFTER_DAYS = 90

_USE_COLOR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return text if not _USE_COLOR else f"\033[{code}m{text}\033[0m"


def _red(x):
    return _c("31", x)


def _green(x):
    return _c("32", x)


def _yellow(x):
    return _c("33", x)


def _bold(x):
    return _c("1", x)


_LEVEL_EMOJI = {"red": "🔴", "yellow": "🟡", "green": "🟢"}
_LEVEL_COLOR = {"red": _red, "yellow": _yellow, "green": _green}


def _footer_lines(pricing: dict, lang: str) -> list[str]:
    """数据时效页脚：始终标注 as_of 日期；过旧时追加提醒。"""
    as_of = pricing.get("as_of")
    if not as_of:
        return []
    lines = [t(lang, "footer_asof", date=as_of)]
    try:
        age = (_dt.date.today() - _dt.date.fromisoformat(str(as_of))).days
    except ValueError:
        age = 0
    if age > STALE_AFTER_DAYS:
        lines.append(t(lang, "footer_stale", days=age))
    return lines


def _haiku_key(pricing: dict) -> str | None:
    for key in pricing["models"]:
        if "haiku" in key:
            return key
    return None


def _totals(credit_sites):
    return (
        sum(s.cost_low for s in credit_sites),
        sum(s.cost_expected for s in credit_sites),
        sum(s.cost_high for s in credit_sites),
    )


def _split_credit(sites):
    """把 credit 调用点分为「已计入成本」（high/medium）与「需人工确认」（low）。"""
    costed, flagged = [], []
    for s in sites:
        if s.billing != "credit":
            continue
        (flagged if s.confidence == "low" else costed).append(s)
    return costed, flagged


def _risk_status(exp: float, high: float, credit: float, lang: str) -> tuple[str, list[str]]:
    """返回 (level, 已本地化消息行)。文本/markdown 渲染器共用。"""
    if exp <= 0:
        return ("green", [t(lang, "risk_none")])
    if exp > credit:
        day = credit / exp * DAYS_PER_MONTH
        return ("red", [t(lang, "risk_burn", day=day), t(lang, "risk_burn_note")])
    if high > credit:
        day = credit / high * DAYS_PER_MONTH
        return ("yellow", [t(lang, "risk_pessimistic", day=day)])
    pct = exp / credit * 100
    return ("yellow" if pct > 60 else "green", [t(lang, "risk_pct", pct=pct)])


def _risk_lines(exp: float, high: float, credit: float, lang: str) -> list[str]:
    level, msgs = _risk_status(exp, high, credit, lang)
    color, emoji = _LEVEL_COLOR[level], _LEVEL_EMOJI[level]
    out = [color(f"   {emoji} {msgs[0]}")]
    out.extend(color(f"   ↳ {m}") for m in msgs[1:])
    return out


def _alternatives(s, pricing: dict, lang: str) -> list[str]:
    tips: list[str] = []
    unit = per_run_cost(pricing, s.model, s.tier)

    if "cron" in s.trigger and s.monthly_runs > WEEKS_PER_MONTH:
        weekly = WEEKS_PER_MONTH * unit
        save = s.cost_expected - weekly
        if save > 0:
            tips.append(t(lang, "alt_weekly", exp=s.cost_expected, weekly=weekly, save=save))

    hk = _haiku_key(pricing)
    if hk and s.model != hk:
        hk_cost = s.monthly_runs * per_run_cost(pricing, hk, s.tier)
        save = s.cost_expected - hk_cost
        if save > 0:
            tips.append(t(lang, "alt_model", hk=hk, exp=s.cost_expected, hk_cost=hk_cost, save=save))

    sig_en = loc(s.signal, "en")
    if "headless" in sig_en or "claude -p" in sig_en:
        tips.append(t(lang, "alt_interactive", exp=s.cost_expected))

    tips.append(t(lang, "alt_overflow"))
    return tips


def build_report(sites, plan: str, plan_credit: float, pricing: dict, lang: str = DEFAULT_LANG) -> str:
    costed, flagged = _split_credit(sites)
    sub_sites = [s for s in sites if s.billing == "subscription"]
    low, exp, high = _totals(costed)

    lines: list[str] = [
        _bold(t(lang, "headline", exp=exp, low=low, high=high, credit=plan_credit, plan=plan))
    ]
    lines.extend(_risk_lines(exp, high, plan_credit, lang))
    lines.append("")

    if costed:
        lines.append(_red(t(lang, "sec_costed")))
        for s in sorted(costed, key=lambda x: x.cost_expected, reverse=True):
            share = (s.cost_expected / exp * 100) if exp else 0
            conf = "" if s.confidence == "high" else _yellow(t(lang, "conf_tag", conf=s.confidence))
            lines.append(f"  {s.file}:{s.line}  [{loc(s.signal, lang)}]{conf}")
            lines.append(f"    {s.snippet}")
            lines.append(t(lang, "line_model", model=s.model, tier=s.tier))
            lines.append(
                t(lang, "line_trigger", trigger=s.trigger, runs=s.monthly_runs,
                  exp=s.cost_expected, low=s.cost_low, high=s.cost_high, share=share)
            )
            lines.append(t(lang, "line_reason", reason=loc(s.reason, lang)))
            for tip in _alternatives(s, pricing, lang):
                lines.append(_yellow(f"    💡 {tip}"))
            lines.append("")

    if flagged:
        lines.append(_yellow(t(lang, "sec_flagged")))
        for s in flagged:
            lines.append(f"  {s.file}:{s.line}  [{loc(s.signal, lang)}]")
            lines.append(f"    {s.snippet}")
            lines.append(t(lang, "line_reason", reason=loc(s.reason, lang)))
        lines.append("")

    if sub_sites:
        lines.append(_green(t(lang, "sec_sub")))
        for s in sub_sites:
            lines.append(f"  {s.file}:{s.line}  [{loc(s.signal, lang)}]")
        lines.append("")

    if not costed and not flagged and not sub_sites:
        lines.append(t(lang, "none_found"))

    footer = _footer_lines(pricing, lang)
    if footer:
        lines.append("")
        lines.extend(footer)

    return "\n".join(lines)


def build_markdown(sites, plan: str, plan_credit: float, pricing: dict, lang: str = DEFAULT_LANG) -> str:
    """生成 markdown 报告（无 ANSI，适合写文件 / PR 评论）。"""
    costed_all, flagged = _split_credit(sites)
    costed = sorted(costed_all, key=lambda x: x.cost_expected, reverse=True)
    sub_sites = [s for s in sites if s.billing == "subscription"]
    low, exp, high = _totals(costed)
    level, msgs = _risk_status(exp, high, plan_credit, lang)

    out: list[str] = [t(lang, "md_title"), ""]
    out.append(t(lang, "md_headline", exp=exp, low=low, high=high, credit=plan_credit, plan=plan))
    out.append("")
    out.append(f"{_LEVEL_EMOJI[level]} " + "; ".join(msgs))
    out.append("")

    if costed:
        out.append(t(lang, "md_sec_costed"))
        out.append("")
        out.append(t(lang, "md_table_head"))
        out.append("|---|---|---|---|---|---|---|---|")
        for s in costed:
            share = (s.cost_expected / exp * 100) if exp else 0
            flag = " ⚠️" if s.confidence != "high" else ""
            out.append(
                f"| `{s.file}:{s.line}`{flag} | {loc(s.signal, lang)} | {s.model}/{s.tier} | "
                f"{s.trigger} | {s.monthly_runs:.0f} | ${s.cost_expected:.2f} | "
                f"${s.cost_low:.2f}–${s.cost_high:.2f} | {share:.0f}% |"
            )
        out.append("")
        out.append(t(lang, "md_alts"))
        out.append("")
        for s in costed:
            out.append(f"- **`{s.file}:{s.line}`**")
            for tip in _alternatives(s, pricing, lang):
                out.append(f"  - {tip}")
        out.append("")

    if flagged:
        out.append(t(lang, "md_sec_flagged"))
        out.append("")
        for s in flagged:
            out.append(f"- `{s.file}:{s.line}` — {loc(s.signal, lang)}: {loc(s.reason, lang)}")
        out.append("")

    if sub_sites:
        out.append(t(lang, "md_sec_sub"))
        out.append("")
        for s in sub_sites:
            out.append(f"- `{s.file}:{s.line}` — {loc(s.signal, lang)}")
        out.append("")

    if not costed and not flagged and not sub_sites:
        out.append(t(lang, "none_found"))

    footer = _footer_lines(pricing, lang)
    if footer:
        out.append("---")
        out.append("")
        out.extend(footer)

    return "\n".join(out)


def forecast_summary(sites, plan_credit: float, lang: str = DEFAULT_LANG) -> dict:
    """预测汇总：仅含已计入成本（high/medium）的 credit 调用。供 JSON 与退出码判定共用。"""
    costed, _ = _split_credit(sites)
    low, exp, high = _totals(costed)
    level, _ = _risk_status(exp, high, plan_credit, lang)
    burnout_day = credit_burnout_day(exp, plan_credit)
    return {"expected": exp, "low": low, "high": high, "level": level, "burnout_day": burnout_day}


def credit_burnout_day(expected: float, plan_credit: float) -> float | None:
    """预期消耗超额时，返回约第几天烧爆；否则 None。"""
    if expected > plan_credit and expected > 0:
        return plan_credit / expected * DAYS_PER_MONTH
    return None


def build_json(sites, plan: str, plan_credit: float, pricing: dict, lang: str = DEFAULT_LANG) -> str:
    """机器可读的 JSON 报告，便于 CI / dashboard 消费。"""
    costed_all, flagged = _split_credit(sites)
    costed = sorted(costed_all, key=lambda x: x.cost_expected, reverse=True)
    sub_sites = [s for s in sites if s.billing == "subscription"]
    summ = forecast_summary(sites, plan_credit, lang)

    def site_obj(s, with_cost: bool):
        o = {
            "file": s.file,
            "line": s.line,
            "signal": loc(s.signal, lang),
            "reason": loc(s.reason, lang),
            "billing": s.billing,
            "confidence": s.confidence,
            "model": s.model,
            "tier": s.tier,
            "trigger": s.trigger,
            "monthly_runs": round(s.monthly_runs, 2),
        }
        if with_cost:
            o["cost_expected"] = round(s.cost_expected, 2)
            o["cost_low"] = round(s.cost_low, 2)
            o["cost_high"] = round(s.cost_high, 2)
        return o

    as_of = pricing.get("as_of")
    stale = False
    if as_of:
        try:
            stale = (_dt.date.today() - _dt.date.fromisoformat(str(as_of))).days > STALE_AFTER_DAYS
        except ValueError:
            stale = False

    data = {
        "plan": plan,
        "credit_limit_usd": plan_credit,
        "data_as_of": as_of,
        "data_stale": stale,
        "forecast": {
            "expected": round(summ["expected"], 2),
            "low": round(summ["low"], 2),
            "high": round(summ["high"], 2),
            "level": summ["level"],
            "burnout_day": (round(summ["burnout_day"], 1) if summ["burnout_day"] else None),
        },
        "calls": {
            "credit": [site_obj(s, True) for s in costed],
            "flagged": [site_obj(s, False) for s in flagged],
            "subscription": [site_obj(s, False) for s in sub_sites],
        },
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
