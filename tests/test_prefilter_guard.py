"""守卫测试：保证 scanner 的子串预过滤永远安全。

scanner.scan 会跳过不含 SCAN_KEYWORDS 的文件。这只有在「每条规则的每个
pattern 都必含某个关键词」时才不会漏报。下面的测试把这条不变量钉死——
未来若加一条不含 claude/anthropic 的规则，这里会变红。
"""

from cost_audit import cli, scanner


def test_every_pattern_contains_a_keyword():
    rules = cli._load_yaml("billing_rules.yaml")["rules"]
    for rule in rules:
        for pat in rule["patterns"]:
            low = pat.lower()
            assert any(kw in low for kw in scanner.SCAN_KEYWORDS), (
                f"规则 {rule['id']} 的 pattern 不含预过滤关键词 "
                f"{scanner.SCAN_KEYWORDS}，会被 scan 的预过滤漏掉：{pat}"
            )


def test_prefilter_skips_irrelevant_file(tmp_path):
    # 不含关键词的文件即使有 spawn/exec 也不应被逐行扫描。
    f = tmp_path / "x.py"
    f.write_text("import os\nos.spawnl(os.P_WAIT, '/bin/ls')\nexec('print(1)')\n", encoding="utf-8")
    rules = scanner.compile_rules(cli._load_yaml("billing_rules.yaml")["rules"])
    assert scanner.scan(tmp_path, rules) == []
