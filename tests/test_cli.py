import json

import pytest

from cost_audit import cli


def _sample(repo):
    return str(repo)


def _indirect(repo):
    return str(repo.parent / "indirect-repo")


def test_version_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert "cost-audit" in capsys.readouterr().out


def test_bad_dir_returns_2(capsys):
    rc = cli.main(["does-not-exist-dir"])
    assert rc == 2
    assert "not a directory" in capsys.readouterr().err


def test_text_report_runs_clean(repo, capsys):
    rc = cli.main([_sample(repo), "--plan", "max5x"])
    assert rc == 0
    assert "Monthly credit forecast" in capsys.readouterr().out


def test_json_format_parses(repo, capsys):
    rc = cli.main([_sample(repo), "--plan", "max5x", "--format", "json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["plan"] == "max5x"
    assert data["billing_change_status"] == "paused"
    assert data["data_as_of"]
    assert data["forecast"]["level"] == "red"
    assert len(data["calls"]["credit"]) >= 1


def test_fail_on_burn_returns_1_when_over(repo, capsys):
    # sample-repo 的预期消耗超过 max5x 额度 → 非零退出。
    rc = cli.main([_sample(repo), "--plan", "max5x", "--fail-on-burn", "--format", "json"])
    assert rc == 1
    assert "fail-on-burn" in capsys.readouterr().err


def test_fail_on_burn_returns_0_when_clean(repo, capsys):
    # indirect-repo 只含 low 置信度信号，不计入预测 → 退出 0。
    rc = cli.main([_indirect(repo), "--plan", "max5x", "--fail-on-burn"])
    assert rc == 0


def test_output_writes_file(repo, tmp_path, capsys):
    out = tmp_path / "report.json"
    rc = cli.main([_sample(repo), "--format", "json", "--output", str(out)])
    assert rc == 0
    assert "Wrote" in capsys.readouterr().out
    json.loads(out.read_text(encoding="utf-8"))  # 文件内容是合法 JSON
