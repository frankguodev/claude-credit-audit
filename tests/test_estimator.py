from cost_audit import estimator as E


def test_cron_daily():
    # 每天一次 ≈ 30.42 次/月
    assert abs(E.cron_runs_per_month("0 3 * * *") - 30.42) < 1.0


def test_cron_half_hourly():
    # 每 30 分钟一次 = 48 次/天 ≈ 1460 次/月
    rpm = E.cron_runs_per_month("*/30 * * * *")
    assert abs(rpm - 48 * E.DAYS_PER_MONTH) < 5


def test_cron_weekly():
    # 每周一一次 ≈ 4.3 次/月
    rpm = E.cron_runs_per_month("0 0 * * 1")
    assert 3.5 < rpm < 5.0


def test_cron_invalid():
    assert E.cron_runs_per_month("not a cron") is None
    assert E.cron_runs_per_month("0 3 * *") is None


def test_family_model(pricing):
    assert E._family_model("claude-3-5-haiku-20241022", pricing) == "claude-haiku-4-5"
    assert E._family_model("claude-sonnet-4-6", pricing) == "claude-sonnet-4-6"
    assert E._family_model("claude-opus-4-8", pricing) == "claude-opus-4-8"
    assert E._family_model("gpt-4", pricing) is None


def test_detect_model(repo, pricing):
    # matrix.yml 显式写了 claude-haiku-4-5
    model = E.detect_model(repo / ".github/workflows/matrix.yml", pricing)
    assert model == "claude-haiku-4-5"


def test_per_run_cost_ordering(pricing):
    small = E.per_run_cost(pricing, "claude-opus-4-8", "small")
    large = E.per_run_cost(pricing, "claude-opus-4-8", "large")
    assert small < large


def test_issue_trigger_counted(repo):
    # issues / issue_comment 触发应计入 issues_per_month（同一文件两类只计一次）。
    label, runs = E.file_trigger(
        repo,
        ".github/workflows/issue-bot.yml",
        pr_per_month=30,
        manual_per_month=4,
        issues_per_month=10,
    )
    assert "issues/comment" in label
    assert runs == 10


def test_workflow_dispatch_only_uses_manual(repo, tmp_path):
    # 纯 workflow_dispatch 应按 manual_per_month 估，而非落到「其它触发」。
    wf = tmp_path / ".github" / "workflows" / "d.yml"
    wf.parent.mkdir(parents=True)
    wf.write_text("on:\n  workflow_dispatch:\njobs: {}\n", encoding="utf-8")
    label, runs = E.file_trigger(
        tmp_path, ".github/workflows/d.yml", 30, manual_per_month=4, issues_per_month=10
    )
    assert "workflow_dispatch" in label
    assert runs == 4


def test_matrix_multiplier():
    wf = {"jobs": {"b": {"strategy": {"matrix": {"os": ["a", "b", "c"], "node": [1, 2]}}}}}
    assert E._matrix_multiplier(wf) == 6


def test_band_ordering(repo, pricing, rules):
    from cost_audit import scanner

    sites = scanner.scan(repo, rules)
    E.estimate(sites, repo, pricing, pr_per_month=30, manual_per_month=4)
    for s in sites:
        if s.billing == "credit":
            assert s.cost_low <= s.cost_expected <= s.cost_high
