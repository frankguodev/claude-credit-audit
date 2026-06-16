from pathlib import Path

from cost_audit import cli, reporter, scanner
from cost_audit.estimator import estimate

INDIRECT = Path(__file__).resolve().parent / "fixtures" / "indirect-repo"


def _rules():
    return scanner.compile_rules(cli._load_yaml("billing_rules.yaml")["rules"])


def test_install_and_var_detected_low_confidence():
    sites = scanner.scan(INDIRECT, _rules())
    by_id = {s.rule_id: s for s in sites}
    assert "claude_code_install" in by_id
    assert by_id["claude_code_install"].confidence == "low"
    assert "cli_var_indirect" in by_id
    assert by_id["cli_var_indirect"].confidence == "low"


def test_low_confidence_excluded_from_total(pricing):
    sites = scanner.scan(INDIRECT, _rules())
    estimate(sites, INDIRECT, pricing, 30, 4, 10)
    costed, flagged = reporter._split_credit(sites)
    assert costed == []  # 该 fixture 只有低置信度信号
    assert len(flagged) >= 2
    txt = reporter.build_report(sites, "max5x", 100, pricing)  # 默认 en
    assert "$0 expected" in txt  # 低置信度不计入预测
    assert "verify manually" in txt


def test_var_rule_ignores_non_claude_value(tmp_path):
    wf = tmp_path / ".github" / "workflows" / "a.yml"
    wf.parent.mkdir(parents=True)
    wf.write_text("env:\n  REVIEW_CLI_BIN: amp\n", encoding="utf-8")
    sites = scanner.scan(tmp_path, _rules())
    assert all(s.rule_id != "cli_var_indirect" for s in sites)


def test_install_rule_ignores_action_package(tmp_path):
    # 不应把 claude-code-action / claude-code-base 误判成 CLI 安装信号。
    f = tmp_path / "x.sh"
    f.write_text("echo @anthropic-ai/claude-code-base\n", encoding="utf-8")
    sites = scanner.scan(tmp_path, _rules())
    assert all(s.rule_id != "claude_code_install" for s in sites)


def test_spawn_detected_low_confidence():
    sites = scanner.scan(INDIRECT, _rules())
    spawns = [s for s in sites if s.rule_id == "claude_spawn"]
    assert len(spawns) == 1  # 只命中 spawn(claudePath, ...)
    assert spawns[0].confidence == "low"
    assert spawns[0].file.endswith("spawn.ts")


def test_spawn_rule_ignores_binary_lookup_and_node(tmp_path):
    # where claude / spawn(process.execPath) 不应误报。
    f = tmp_path / "s.ts"
    f.write_text(
        "execSync('where claude')\n"
        "spawn(process.execPath, ['wrapper.js'])\n"
        "exec('which claude')\n",
        encoding="utf-8",
    )
    sites = scanner.scan(tmp_path, _rules())
    assert all(s.rule_id != "claude_spawn" for s in sites)
