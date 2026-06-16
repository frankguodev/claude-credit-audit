"""多语言消息目录。默认英语（en），其次中文（zh）。"""

from __future__ import annotations

DEFAULT_LANG = "en"
LANGS = ("en", "zh")

MESSAGES: dict[str, dict[str, str]] = {
    # 头条与风险
    "headline": {
        "en": "📊 Monthly credit forecast: ${exp:.0f} expected (range ${low:.0f}–${high:.0f}) / ${credit:.0f} limit ({plan})",
        "zh": "📊 月度 credit 预测：${exp:.0f} 预期（区间 ${low:.0f}–${high:.0f}） / ${credit:.0f} 额度（{plan}）",
    },
    "risk_none": {
        "en": "No credit-burning calls found",
        "zh": "未发现会烧 credit 的调用",
    },
    "risk_burn": {
        "en": "Forecast burns through the limit around day {day:.0f}",
        "zh": "预期情形约第 {day:.0f} 天烧爆额度",
    },
    "risk_burn_note": {
        "en": "After burnout all automated requests stop (unless overflow billing is enabled)",
        "zh": "烧爆后所有自动化请求停止（除非已手动开启 overflow billing）",
    },
    "risk_pessimistic": {
        "en": "Expected stays within limit, but worst case may burn out around day {day:.0f} — leave headroom",
        "zh": "预期不烧爆，但悲观情形约第 {day:.0f} 天可能烧爆——建议预留余量",
    },
    "risk_pct": {
        "en": "Projected to use {pct:.0f}% of the limit",
        "zh": "预计用掉额度的 {pct:.0f}%",
    },
    # 区块标题
    "sec_costed": {
        "en": "🔴 Calls that will burn credit (sorted by expected monthly spend):",
        "zh": "🔴 会烧 credit 的调用点（按预期月度消耗排序）：",
    },
    "sec_flagged": {
        "en": "⚠️ May burn credit (indirect/install signals, NOT counted above, verify manually):",
        "zh": "⚠️ 可能烧 credit（间接/安装信号，未计入上方预测，需人工确认）：",
    },
    "sec_sub": {
        "en": "✅ Still on subscription (no credit):",
        "zh": "✅ 仍走订阅池（不烧 credit）：",
    },
    "none_found": {
        "en": "No agent calls found.",
        "zh": "未发现任何 agent 调用点。",
    },
    # 调用点明细
    "conf_tag": {
        "en": "  (confidence: {conf}, may be a false positive)",
        "zh": "  (置信度: {conf}, 可能误判)",
    },
    "line_model": {
        "en": "    model: {model}  tier: {tier}",
        "zh": "    模型：{model}  档位：{tier}",
    },
    "line_trigger": {
        "en": "    trigger: {trigger} → ~{runs:.0f}/mo → ${exp:.2f}/mo (range ${low:.2f}–${high:.2f}, {share:.0f}%)",
        "zh": "    触发：{trigger} → ~{runs:.0f} 次/月 → ${exp:.2f}/月（区间 ${low:.2f}–${high:.2f}，占 {share:.0f}%）",
    },
    "line_reason": {
        "en": "    reason: {reason}",
        "zh": "    原因：{reason}",
    },
    # 替代建议
    "alt_weekly": {
        "en": "Drop to a weekly trigger: ${exp:.2f}→${weekly:.2f}/mo, saves ${save:.2f}/mo",
        "zh": "降到每周触发：${exp:.2f}→${weekly:.2f}/月，省 ${save:.2f}/月",
    },
    "alt_model": {
        "en": "Switch to {hk}: ${exp:.2f}→${hk_cost:.2f}/mo, saves ${save:.2f}/mo (confirm a weaker model is acceptable)",
        "zh": "改用 {hk}：${exp:.2f}→${hk_cost:.2f}/月，省 ${save:.2f}/月（确认任务可接受较弱模型）",
    },
    "alt_interactive": {
        "en": "Run interactively instead of headless: saves all ${exp:.2f}/mo (stays on subscription)",
        "zh": "能交互完成的改用交互式 claude：省全部 ${exp:.2f}/月（仍走订阅）",
    },
    "alt_overflow": {
        "en": "Or enable overflow billing to avoid CI stalls / compare the cost of upgrading your plan",
        "zh": "或开启 overflow billing 防 CI 中断 / 比较升级计划的月度成本",
    },
    # markdown
    "md_title": {
        "en": "# Claude Credit Audit Report",
        "zh": "# Claude Credit 审计报告",
    },
    "md_headline": {
        "en": "**Monthly credit forecast: ${exp:.0f} expected (range ${low:.0f}–${high:.0f}) / ${credit:.0f} limit ({plan})**",
        "zh": "**月度 credit 预测：${exp:.0f} 预期（区间 ${low:.0f}–${high:.0f}） / ${credit:.0f} 额度（{plan}）**",
    },
    "md_sec_costed": {
        "en": "## 🔴 Calls that will burn credit",
        "zh": "## 🔴 会烧 credit 的调用点",
    },
    "md_table_head": {
        "en": "| File:line | Signal | Model/tier | Trigger | /mo | Expected $/mo | Range | Share |",
        "zh": "| 文件:行 | 信号 | 模型/档位 | 触发 | 次/月 | 预期 $/月 | 区间 | 占比 |",
    },
    "md_alts": {
        "en": "### Alternatives",
        "zh": "### 替代路径",
    },
    "md_sec_flagged": {
        "en": "## ⚠️ May burn credit (indirect/install signals, not counted, verify manually)",
        "zh": "## ⚠️ 可能烧 credit（间接/安装信号，未计入预测，需人工确认）",
    },
    "md_sec_sub": {
        "en": "## ✅ Still on subscription (no credit)",
        "zh": "## ✅ 仍走订阅池（不烧 credit）",
    },
    # CLI
    "cli_wrote": {
        "en": "Wrote {path}",
        "zh": "已写入 {path}",
    },
    "cli_calib_ok": {
        "en": "✅ Calibrated token tiers from {n} {label} local sessions (p25/p50/p90, in/out): {parts}",
        "zh": "✅ 已按 {n} 个{label}本地会话校准 token 档位（p25/p50/p90，输入/输出）：{parts}",
    },
    "cli_calib_fail": {
        "en": "⚠️ Calibration failed: too few valid sessions under {home} ({n}, need ≥3); using default tiers.",
        "zh": "⚠️ 校准失败：{home} 下有效会话不足（{n} 个，需≥3），仍用默认档位。",
    },
    "calib_label_prog": {
        "en": "programmatic (non-interactive)",
        "zh": "非交互式（程序化）",
    },
    "calib_label_all": {
        "en": "all (incl. interactive, may overestimate)",
        "zh": "全部（含交互式，可能偏大）",
    },
}


def t(lang: str, key: str, **kw) -> str:
    entry = MESSAGES[key]
    template = entry.get(lang) or entry[DEFAULT_LANG]
    return template.format(**kw) if kw else template


def loc(field, lang: str) -> str:
    """解析 {en, zh} 字段；回退到 en 再回退到任意值。"""
    if isinstance(field, str):
        return field
    return field.get(lang) or field.get(DEFAULT_LANG) or next(iter(field.values()))
