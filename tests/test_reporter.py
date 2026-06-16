from cost_audit import reporter, scanner
from cost_audit.estimator import estimate


def _sites(repo, rules, pricing):
    sites = scanner.scan(repo, rules)
    estimate(sites, repo, pricing, pr_per_month=30, manual_per_month=4)
    return sites


def test_risk_status_levels():
    assert reporter._risk_status(0, 0, 100, "en")[0] == "green"
    assert reporter._risk_status(150, 200, 100, "en")[0] == "red"     # 预期已烧爆
    assert reporter._risk_status(50, 200, 100, "en")[0] == "yellow"   # 仅悲观烧爆
    assert reporter._risk_status(80, 90, 100, "en")[0] == "yellow"    # 占比 >60%
    assert reporter._risk_status(10, 20, 100, "en")[0] == "green"


def test_markdown_default_english(repo, rules, pricing):
    sites = _sites(repo, rules, pricing)
    md = reporter.build_markdown(sites, "max5x", 100, pricing)  # 默认 en
    assert "# Claude Credit Audit Report" in md
    assert "| File:line |" in md
    assert "nightly.yml" in md
    assert "### Alternatives" in md


def test_markdown_chinese_when_zh(repo, rules, pricing):
    sites = _sites(repo, rules, pricing)
    md = reporter.build_markdown(sites, "max5x", 100, pricing, lang="zh")
    assert "# Claude Credit 审计报告" in md
    assert "| 文件:行 |" in md
    assert "### 替代路径" in md


def test_quantified_savings_present(repo, rules, pricing):
    sites = _sites(repo, rules, pricing)
    en = reporter.build_markdown(sites, "max5x", 100, pricing)
    zh = reporter.build_markdown(sites, "max5x", 100, pricing, lang="zh")
    assert "Drop to a weekly trigger" in en and "saves $" in en
    assert "降到每周触发" in zh and "省 $" in zh


def test_text_report_runs(repo, rules, pricing):
    sites = _sites(repo, rules, pricing)
    assert "Monthly credit forecast" in reporter.build_report(sites, "max5x", 100, pricing)
    assert "月度 credit 预测" in reporter.build_report(sites, "max5x", 100, pricing, lang="zh")


def test_footer_shows_data_asof(repo, rules, pricing):
    # 报告应标注定价数据的 as_of 日期（时效提示）。
    sites = _sites(repo, rules, pricing)
    as_of = pricing["as_of"]
    assert as_of in reporter.build_report(sites, "max5x", 100, pricing)
    assert as_of in reporter.build_markdown(sites, "max5x", 100, pricing)


def test_footer_flags_stale_data(repo, rules, pricing):
    # as_of 远早于今天时，应追加「数据过旧」提醒。
    sites = _sites(repo, rules, pricing)
    pricing = {**pricing, "as_of": "2000-01-01"}
    out = reporter.build_report(sites, "max5x", 100, pricing)
    assert "days old" in out
