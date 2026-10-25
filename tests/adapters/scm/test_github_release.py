from __future__ import annotations

import io
from types import SimpleNamespace

import pytest

from engine.adapters.scm import github_release as target


@pytest.mark.parametrize(
    "raw",
    [b"{}", b"[]", b"bad", b" " * 1_000_001],
    ids=["object", "array", "malformed", "oversize"],
)
def test_provider_transport_is_read_only_and_bounded(monkeypatch, raw):
    requests = []

    def open_request(request, timeout):
        requests.append((request, timeout))
        return io.BytesIO(raw)

    monkeypatch.setattr(
        target, "build_opener", lambda *args: SimpleNamespace(open=open_request)
    )
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-read-token")
    if raw == b"{}":
        assert target.read_github("/repos/scnehaux/codex/pulls/1") == {}
    else:
        with pytest.raises((ValueError, target.ReleaseError)):
            target.read_github("/repos/scnehaux/codex/pulls/1")
    request, timeout = requests[0]
    assert request.get_method() == "GET"
    assert request.full_url == "https://api.github.com/repos/scnehaux/codex/pulls/1"
    assert timeout == 30


def test_provider_transport_requires_no_secret_and_refuses_redirects(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    def open_request(request, timeout):
        assert request.get_header("Authorization") is None
        return io.BytesIO(b"{}")

    monkeypatch.setattr(
        target, "build_opener", lambda *args: SimpleNamespace(open=open_request)
    )
    assert target.read_github("/repos/scnehaux/codex/pulls/1") == {}
    with pytest.raises(target.ReleaseError, match="redirect refused"):
        target._NoRedirect().redirect_request(
            None, None, 302, "Moved", {}, "https://other.invalid"
        )
