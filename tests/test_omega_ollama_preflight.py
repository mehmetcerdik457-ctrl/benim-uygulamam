"""No socket creation: fake in-process HTTP response only."""
import json
import sys
import pytest
from scripts import omega_loopback_model_benchmark as bench


class Response:
    def __init__(self, *, body, status=200):
        self.status = status
        self.body = body

    def read(self, n):
        return self.body[:n]


class Connection:
    def __init__(self, host, port, timeout, *, body, requests):
        assert host == "127.0.0.1"
        self.response = Response(body=body)
        self.requests = requests

    def request(self, method, path, headers):
        self.requests.append((method, path))

    def getresponse(self):
        return self.response

    def close(self):
        pass


def mock_conn(monkeypatch, payload):
    calls = []
    def factory(host, port, timeout):
        return Connection(host, port, timeout, body=json.dumps(payload).encode(), requests=calls)
    monkeypatch.setattr(bench.http.client, "HTTPConnection", factory)
    return calls


def test_existing_exact_model_and_digest(monkeypatch):
    digest = "sha256:" + "a"*64
    calls = mock_conn(monkeypatch, {"models":[{"name":"safe:1b", "digest":digest, "size":1234}]})
    assert bench.installed_model_metadata("safe:1b", 11434) == {"digest":digest,"size_bytes":1234}
    assert calls == [("GET", "/api/tags")]


def test_missing_tag_refused_before_generation(monkeypatch, capsys):
    calls = mock_conn(monkeypatch, {"models":[{"name":"other:1b"}]})
    monkeypatch.setattr(sys, "argv", ["benchmark", "--model", "missing:1b"])
    assert bench.main() == 2
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "NOT_MEASURED" and not output["production_accepted"]
    assert calls == [("GET", "/api/tags")]


@pytest.mark.parametrize("bad", [{}, {"models":{}}, {"models":["safe:1b"]}, {"models":[]}])
def test_untrusted_or_empty_catalogue_fails_closed(monkeypatch, bad):
    mock_conn(monkeypatch, bad)
    with pytest.raises(RuntimeError):
        bench.installed_model_metadata("safe:1b", 11434)
