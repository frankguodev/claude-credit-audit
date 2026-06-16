import sys
from pathlib import Path

import pytest

# 让测试无需安装即可 import cost_audit。
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cost_audit import cli  # noqa: E402

FIXTURE_REPO = Path(__file__).resolve().parent / "fixtures" / "sample-repo"


@pytest.fixture
def pricing():
    return cli._load_yaml("pricing.yaml")


@pytest.fixture
def rules():
    from cost_audit import scanner

    return scanner.compile_rules(cli._load_yaml("billing_rules.yaml")["rules"])


@pytest.fixture
def repo():
    return FIXTURE_REPO
