from __future__ import annotations

import yaml

from tests.support.repository import REPOSITORY_ROOT


def test_repository_declares_canonical_lf_text_policy():
    attributes = (REPOSITORY_ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert "* text=auto eol=lf" in attributes
    assert "*.png binary" in attributes
    assert "*.pdf binary" in attributes


def test_genesis_bootstrap_allows_gitattributes():
    manifest = yaml.safe_load(
        (REPOSITORY_ROOT / "governance" / "bootstrap-manifest.yaml").read_text(
            encoding="utf-8"
        )
    )

    allowed = manifest["genesis_contract"]["allowed_paths"]
    assert ".gitattributes" in allowed
