from pathlib import Path

from cost_audit import calibrate

LOGS = Path(__file__).resolve().parent / "fixtures" / "logs"


def _paths():
    return sorted(LOGS.glob("*.jsonl"))


def test_session_total_sums_within_session():
    # sess_c：两条 assistant，输入合计 200000、输出 20000，过滤掉非 assistant 行。
    t = calibrate._session_total(LOGS / "sess_c.jsonl")
    assert t == (200000, 20000, None)


def test_session_total_combines_input_fields():
    # sess_a：8000 + 2000(cache_creation) + 0.1×0 = 10000 输入。
    assert calibrate._session_total(LOGS / "sess_a.jsonl") == (10000, 1000, None)


def test_cache_read_weighted(tmp_path):
    # cache_read 按 0.1 折算：1000 + 0 + 0.1×50000 = 6000。
    f = tmp_path / "s.jsonl"
    f.write_text(
        '{"type":"assistant","message":{"usage":{"input_tokens":1000,'
        '"cache_creation_input_tokens":0,"cache_read_input_tokens":50000,'
        '"output_tokens":200}}}\n',
        encoding="utf-8",
    )
    assert calibrate._session_total(f) == (6000, 200, None)


def test_entrypoint_detected(tmp_path):
    f = tmp_path / "s.jsonl"
    f.write_text(
        '{"type":"user","entrypoint":"sdk-ts"}\n'
        '{"type":"assistant","entrypoint":"sdk-ts","message":{"usage":'
        '{"input_tokens":1000,"output_tokens":100}}}\n',
        encoding="utf-8",
    )
    assert calibrate._session_total(f) == (1000, 100, "sdk-ts")


def test_session_totals_collects_all():
    totals = calibrate.session_totals(_paths())
    assert sorted(totals) == [
        (10000, 1000, None),
        (50000, 5000, None),
        (200000, 20000, None),
    ]


def test_calibrate_tiers_percentiles():
    totals = calibrate.session_totals(_paths())
    cal = calibrate.calibrate_tiers(totals)
    assert cal is not None
    tiers, n, source = cal
    assert n == 3
    # 中位数 = 第二大的会话。
    assert tiers["medium"]["input"] == 50000
    assert tiers["medium"]["output"] == 5000
    assert tiers["small"]["input"] < tiers["medium"]["input"] < tiers["large"]["input"]


def test_programmatic_filter_excludes_interactive():
    # 三个程序化会话 + 一个巨大的交互式会话；校准应排除交互式。
    totals = [
        (10000, 1000, "sdk-ts"),
        (50000, 5000, None),
        (200000, 20000, "sdk-ts"),
        (99_000_000, 9_000_000, "claude-vscode"),  # 交互式，须被排除
    ]
    tiers, n, source = calibrate.calibrate_tiers(totals)
    assert source == "programmatic"
    assert n == 3
    assert tiers["large"]["input"] < 1_000_000  # 巨大交互式会话未污染档位


def test_calibrate_falls_back_to_all_when_too_few_programmatic():
    totals = [
        (10000, 1000, "claude-vscode"),
        (50000, 5000, "claude-desktop"),
        (200000, 20000, "claude-vscode"),
    ]
    tiers, n, source = calibrate.calibrate_tiers(totals)
    assert source == "all"
    assert n == 3


def test_calibrate_insufficient_sessions():
    assert calibrate.calibrate_tiers([(1, 1, None)], min_sessions=3) is None


def test_discover_logs_missing_home(tmp_path):
    assert calibrate.discover_logs(tmp_path) == []
