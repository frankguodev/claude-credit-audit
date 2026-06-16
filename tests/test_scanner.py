from cost_audit import scanner


def test_comment_skipped_and_deduped(repo, rules):
    sites = scanner.scan(repo, rules)
    edge = [s for s in sites if "edge.sh" in s.file]
    # edge.sh：第2行是注释掉的 claude -p，应忽略；第4行真实调用记一次。
    assert len(edge) == 1
    assert edge[0].line == 4
    assert edge[0].rule_id == "claude_headless"


def test_tier_and_confidence_carried(repo, rules):
    sites = scanner.scan(repo, rules)
    sdk = next(s for s in sites if s.rule_id == "anthropic_sdk")
    assert sdk.confidence == "medium"
    assert sdk.tier == "small"
    headless = next(s for s in sites if s.rule_id == "claude_headless")
    assert headless.tier == "large"


def test_one_site_per_line(repo, rules):
    sites = scanner.scan(repo, rules)
    seen = [(s.file, s.line) for s in sites]
    assert len(seen) == len(set(seen))


def test_is_comment():
    assert scanner._is_comment("  # claude -p x")
    assert scanner._is_comment("// claude -p")
    assert not scanner._is_comment("run: claude -p x")
