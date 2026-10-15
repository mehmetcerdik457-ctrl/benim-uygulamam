"""No-network negative tests: a local tag is insufficient without digest and size."""
import json
import sys

import pytest

from scripts import omega_loopback_model_benchmark as bench


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.data = json.dumps(payload).encode()

    def read(self, size):
        return self.data[:size]


def _stub_catalogue(monkeypatch, entry):
    calls = []

    class Connection:
        def __init__(self, host, port, timeout):
            assert host == "127.0.0.1"
            assert port == 11434

        def request(self, method, path, headers):
            calls.append((method, path))

        def getresponse(self):
            return FakeResponse({"models": [entry]})

        def close(self):
            pass

    monkeypatch.setattr(bench.http.client, "HTTPConnection", Connection)
    return calls


@pytest.mark.parametrize("bad", [
    {"name": "verified:1b", "size": 1234},
    {"name": "verified:1b", "digest": "not-a-digest", "size": 1234},
    {"name": "verified:1b", "digest": "sha256:" + "a" * 64},
    {"name": "verified:1b", "digest": "sha256:" + "a" * 64, "size": 0},
    {"name": "verified:1b", "digest": "sha256:" + "a" * 64, "size": True},
    {"name": "verified:1b", "digest": "sha256:" + "a" * 63, "size": 1234},
])
def test_unverified_metadata_never_admitted(monkeypatch, bad):
    calls = _stub_catalogue(monkeypatch, bad)
    with pytest.raises(RuntimeError, match="local_model_identity_unverified"):
        bench.installed_model_metadata("verified:1b", 11434)
    assert calls == [("GET", "/api/tags")]


def test_cli_returns_nonzero_without_generation_for_missing_digest(monkeypatch, capsys):
    calls = _stub_catalogue(monkeypatch, {"name": "verified:1b", "size": 1234})
    monkeypatch.setattr(sys, "argv", ["benchmark", "--model", "verified:1b"])
    assert bench.main() == 2
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "NOT_MEASURED"
    assert output["production_accepted"] is False
    assert calls == [("GET", "/api/tags")]


def test_valid_existing_digest_and_size_still_accepted(monkeypatch):
    digest = "sha256:" + "a" * 64
    calls = _stub_catalogue(monkeypatch, {"name": "verified:1b", "digest": digest, "size": 1234})
    assert bench.installed_model_metadata("verified:1b", 11434) == {
        "digest": digest, "size_bytes": 1234
    }
    assert calls == [("GET", "/api/tags")]
