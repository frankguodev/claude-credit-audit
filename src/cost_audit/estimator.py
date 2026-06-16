"""模块 3：估算每个调用点的月度触发频率与成本（区间 + 模型识别）。"""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path

import yaml

DAYS_PER_MONTH = 30.42
WEEKS_PER_MONTH = 4.33


# --------------------------------------------------------------------------- #
# cron 频率
# --------------------------------------------------------------------------- #
def _expand_field(field: str, lo: int, hi: int) -> set[int]:
    """展开单个 cron 字段为命中值集合。支持 * , - / 组合。"""
    values: set[int] = set()
    for part in field.split(","):
        step = 1
        if "/" in part:
            part, step_s = part.split("/", 1)
            step = int(step_s)
        if part in ("*", ""):
            start, end = lo, hi
        elif "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a), int(b)
        else:
            start = end = int(part)
        values.update(v for v in range(start, end + 1) if (v - start) % step == 0)
    return values


def cron_runs_per_month(expr: str) -> float | None:
    """逐分钟遍历 31 天窗口，统计触发次数，归一到 30.42 天。失败返回 None。"""
    parts = expr.split()
    if len(parts) != 5:
        return None
    try:
        minutes = _expand_field(parts[0], 0, 59)
        hours = _expand_field(parts[1], 0, 23)
        doms = _expand_field(parts[2], 1, 31)
        months = _expand_field(parts[3], 1, 12)
        dows = _expand_field(parts[4], 0, 7)  # 0/7 都表示周日
    except ValueError:
        return None
    dom_restricted = parts[2] not in ("*", "")
    dow_restricted = parts[4] not in ("*", "")

    start = _dt.datetime(2026, 1, 1)
    count = 0
    cur = start
    end = start + _dt.timedelta(days=31)
    while cur < end:
        dow = (cur.weekday() + 1) % 7  # 周一=0 转成 周日=0
        dow_hit = dow in dows or (7 in dows and dow == 0)
        dom_hit = cur.day in doms
        if dom_restricted and dow_restricted:
            day_ok = dom_hit or dow_hit  # cron 语义：都受限时为「或」
        else:
            day_ok = dom_hit and dow_hit
        if cur.month in months and day_ok and cur.hour in hours and cur.minute in minutes:
            count += 1
        cur += _dt.timedelta(minutes=1)
    return count / 31 * DAYS_PER_MONTH


# --------------------------------------------------------------------------- #
# workflow 解析：触发类型 + matrix
# --------------------------------------------------------------------------- #
def _load_workflow(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, yaml.YAMLError):
        return None


def _matrix_multiplier(wf: dict) -> int:
    """估算 matrix 倍数：取各 job 中 matrix 轴长度之积的最大值。"""
    mult = 1
    jobs = wf.get("jobs", {})
    if not isinstance(jobs, dict):
        return mult
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        strat = job.get("strategy", {})
        matrix = strat.get("matrix", {}) if isinstance(strat, dict) else {}
        if not isinstance(matrix, dict):
            continue
        prod = 1
        for key, val in matrix.items():
            if key in ("include", "exclude"):
                continue
            if isinstance(val, list) and val:
                prod *= len(val)
        mult = max(mult, prod)
    return mult


def file_trigger(
    root: Path,
    rel_file: str,
    pr_per_month: float,
    manual_per_month: float,
    issues_per_month: float,
) -> tuple[str, float]:
    """估算某文件的月度触发次数。

    workflow 按 YAML 解析触发类型（cron / pull_request / push / workflow_dispatch /
    issues / issue_comment）并叠加 matrix 倍数；非 workflow 文件按手动默认。
    返回 (trigger 描述, monthly_runs)。
    """
    is_workflow = ".github/workflows" in rel_file.replace("\\", "/")
    if not is_workflow:
        return ("manual", manual_per_month)

    wf = _load_workflow(root / rel_file)
    if not isinstance(wf, dict):
        return ("manual", manual_per_month)

    on = wf.get("on", wf.get(True))  # 注意：YAML 把 `on:` 解析为布尔 True
    triggers: set[str] = set()
    crons: list[str] = []
    if isinstance(on, str):
        triggers.add(on)
    elif isinstance(on, list):
        triggers.update(str(x) for x in on)
    elif isinstance(on, dict):
        triggers.update(str(k) for k in on.keys())
        sched = on.get("schedule")
        if isinstance(sched, list):
            for item in sched:
                if isinstance(item, dict) and "cron" in item:
                    crons.append(str(item["cron"]).strip())

    runs = 0.0
    labels: list[str] = []

    cron_runs = 0.0
    for c in crons:
        rpm = cron_runs_per_month(c)
        if rpm:
            cron_runs += rpm
    if cron_runs:
        runs += cron_runs
        labels.append(f"cron({', '.join(crons)})")
    if {"pull_request", "pull_request_target"} & triggers:
        runs += pr_per_month
        labels.append("pull_request")
    if "push" in triggers:
        runs += pr_per_month
        labels.append("push")
    if {"issues", "issue_comment"} & triggers:
        runs += issues_per_month
        labels.append("issues/comment")
    if "workflow_dispatch" in triggers:
        runs += manual_per_month
        labels.append("workflow_dispatch")
    if runs == 0:
        runs = manual_per_month
        labels.append("workflow(other)")

    mult = _matrix_multiplier(wf)
    if mult > 1:
        runs *= mult
        labels.append(f"matrix ×{mult}")

    return (" + ".join(labels), runs)


# --------------------------------------------------------------------------- #
# 模型识别 + 单次成本
# --------------------------------------------------------------------------- #
_MODEL_TOKEN = re.compile(r"claude-[a-z0-9.\-]+", re.IGNORECASE)


def _family_model(token: str, pricing: dict) -> str | None:
    t = token.lower()
    fam = (
        "opus" if "opus" in t else
        "sonnet" if "sonnet" in t else
        "haiku" if "haiku" in t else
        None
    )
    if not fam:
        return None
    for key in pricing["models"]:
        if fam in key:
            return key
    return None


def detect_model(path: Path, pricing: dict) -> str | None:
    """扫文件里第一个可识别的 claude 模型 token，按 family 映射到价格行。"""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    for m in _MODEL_TOKEN.finditer(text):
        model = _family_model(m.group(0), pricing)
        if model:
            return model
    return None


def per_run_cost(pricing: dict, model: str | None = None, tier: str | None = None) -> float:
    model = model or pricing["default_model"]
    tier = tier or pricing["default_tier"]
    m = pricing["models"][model]
    t = pricing["token_tiers"][tier]
    return (
        t["input"] / 1_000_000 * m["input_per_mtok"]
        + t["output"] / 1_000_000 * m["output_per_mtok"]
    )


def estimate(
    sites,
    root: Path,
    pricing: dict,
    pr_per_month: float,
    manual_per_month: float,
    issues_per_month: float = 10.0,
    tier_override: str | None = None,
):
    """就地填充每个 credit 调用点的频率、模型与区间成本。"""
    trig_cache: dict[str, tuple[str, float]] = {}
    model_cache: dict[str, str] = {}
    for s in sites:
        if s.file not in trig_cache:
            trig_cache[s.file] = file_trigger(
                root, s.file, pr_per_month, manual_per_month, issues_per_month
            )
        if s.file not in model_cache:
            model_cache[s.file] = detect_model(root / s.file, pricing) or pricing["default_model"]

        s.trigger, s.monthly_runs = trig_cache[s.file]
        s.model = model_cache[s.file]
        if tier_override:
            s.tier = tier_override
        if s.billing == "credit":
            s.cost_low = s.monthly_runs * per_run_cost(pricing, s.model, "small")
            s.cost_expected = s.monthly_runs * per_run_cost(pricing, s.model, s.tier)
            s.cost_high = s.monthly_runs * per_run_cost(pricing, s.model, "large")
    return sites
