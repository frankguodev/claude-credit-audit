"""守卫测试：保证 en/zh 双语完整，未来加消息或规则漏翻会变红。"""

from cost_audit import cli
from cost_audit.i18n import LANGS, MESSAGES


def test_every_message_has_all_langs():
    for key, entry in MESSAGES.items():
        for lang in LANGS:
            assert lang in entry and entry[lang].strip(), f"消息 {key} 缺少 {lang}"


def test_every_rule_label_is_bilingual():
    rules = cli._load_yaml("billing_rules.yaml")["rules"]
    for rule in rules:
        for field in ("signal", "reason"):
            val = rule[field]
            assert isinstance(val, dict), f"规则 {rule['id']} 的 {field} 应为 {{en, zh}}"
            for lang in LANGS:
                assert val.get(lang, "").strip(), f"规则 {rule['id']} 的 {field} 缺少 {lang}"
