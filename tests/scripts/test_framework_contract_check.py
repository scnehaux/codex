from __future__ import annotations

import scripts.framework_contract_check as target


def test_framework_contract_check_passes_current_repository():
    assert target.main() == 0


def test_framework_contract_check_fails_closed(monkeypatch):
    def fail(_root):
        raise RuntimeError("synthetic contract drift")

    monkeypatch.setattr(target, "assert_framework_contract_equivalence", fail)
    assert target.main() == 1
