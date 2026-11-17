"""Acceptance CLI controls; synthetic provider, never live acceptance evidence."""
import importlib.util
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from omega import gateway

spec = importlib.util.spec_from_file_location("omega_acceptance", Path(__file__).resolve().parents[1] / "scripts/omega_provider_acceptance.py")
acceptance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acceptance)


def test_no_live_flag_never_instantiates_provider(monkeypatch, capsys):
    def forbidden():
        raise AssertionError("No provider without explicit flag")
    monkeypatch.setattr(acceptance, "RuntimeProvider", forbidden)
    assert acceptance.main([]) == 2
    evidence = json.loads(capsys.readouterr().out)
    assert evidence["status"] == "NOT_RUN" and evidence["provider_request_made"] is False


def test_synthetic_adapter_uses_returned_model_not_requested_alias(monkeypatch, capsys):
    class Fake:
        def configured(self): return True
        def candidates(self): return ("synthetic-alias",)
        def reply(self, model, message, *, probe):
            assert model == "synthetic-alias" and probe is True and message == "Yalnızca Merhaba yaz."
            return "SYNTHETIC_ONLY", "synthetic-actual-snapshot", 7
    monkeypatch.setattr(acceptance, "RuntimeProvider", Fake)
    assert acceptance.main(["--live"]) == 0
    evidence = json.loads(capsys.readouterr().out)
    assert evidence["provider_model"] == "synthetic-actual-snapshot"
    assert evidence["owner_device_acceptance"] is False and evidence["latency_ms"] == 7


def test_synthetic_provider_failure_does_not_expose_exception(monkeypatch, capsys):
    class Fake:
        def configured(self): return True
        def candidates(self): return ("synthetic-alias",)
        def reply(self, *args, **kwargs): raise RuntimeError("synthetic-private-value")
    monkeypatch.setattr(acceptance, "RuntimeProvider", Fake)
    assert acceptance.main(["--live"]) == 2
    output = capsys.readouterr().out
    assert "synthetic-private-value" not in output
    assert json.loads(output)["status"] == "DENIED"
