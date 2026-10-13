"""Offline-only tests of a direct manifest SBOM; no subprocess/network."""
from pathlib import Path

import pytest

from scripts.omega_direct_sbom import ALLOWED, ManifestDenied, direct_pins, document, main


def fixture_tree(tmp_path: Path, base: str | None = None,
                 test: str | None = None, root: str = "") -> Path:
    (tmp_path / "omega_mvi").mkdir()
    (tmp_path / "requirements.txt").write_text(root, encoding="utf-8")
    (tmp_path / "omega_mvi/requirements.txt").write_text(
        base if base is not None else "fastapi==0.115.12\npsycopg[binary]==3.2.9\n",
        encoding="utf-8",
    )
    (tmp_path / "omega_mvi/requirements-test.txt").write_text(
        test if test is not None else "-r requirements.txt\npytest==8.4.1  # test runner\n",
        encoding="utf-8",
    )
    return tmp_path


def test_actual_repository_sbom_direct_only_and_deterministic():
    output = document()
    assert output == document()
    assert output["bomFormat"] == "CycloneDX"
    assert output["specVersion"] == "1.5"
    assert output["metadata"]["properties"][0]["value"] == "DIRECT_PYTHON_PINS_ONLY"
    names = [item["name"] for item in output["components"]]
    assert len(names) >= 6 and len(names) == len(set(names))
    assert all(item["purl"].startswith("pkg:pypi/") for item in output["components"])
    assert all(item["version"] for item in output["components"])
    assert {v["name"]: v["value"] for v in output["metadata"]["properties"]}[
        "omega:vulnerability-scan"] == "NOTRUN"


def test_known_nested_manifest_deduplicated(tmp_path):
    items = direct_pins(fixture_tree(tmp_path))
    assert [(x["name"], x["version"]) for x in items] == [
        ("fastapi", "0.115.12"), ("psycopg", "3.2.9"), ("pytest", "8.4.1")]
    assert items[1]["extras"] == "binary"


@pytest.mark.parametrize("content", [
    "fastapi>=1.0\n",
    "--index-url https://untrusted.invalid/simple\n",
    "-e git+https://untrusted.invalid/a\n",
    "fastapi==0.115.12; os_name == 'posix'\n",
    "-r ../outside.txt\n",
    "fastapi==0.115.12 --hash=sha256:bad\n",
    "fastapi==0.115.12\n-r /etc/passwd\n",
    "fastapi==0.115.12\n" + "B" * 257,
])
def test_disallowed_install_directive_or_unpinned_raises_only_fixed_code(tmp_path, content):
    root = fixture_tree(tmp_path, base=content)
    with pytest.raises(ManifestDenied) as exc:
        direct_pins(root)
    assert str(exc.value) in {
        "UNREVIEWED_REQUIREMENTS_FILE",
        "INVALID_REQUIREMENTS_LINE",
        "UNPINNED_OR_UNREVIEWED_DEPENDENCY",
    }
    assert "untrusted.invalid" not in str(exc.value)


def test_conflicting_pins_are_denied(tmp_path):
    root = fixture_tree(tmp_path, test="-r requirements.txt\nfastapi==1.0\n")
    with pytest.raises(ManifestDenied, match="CONFLICTING_DEPENDENCY_PINS"):
        direct_pins(root)


def test_symlink_to_private_file_is_denied(tmp_path):
    root = fixture_tree(tmp_path)
    private = tmp_path / "private-secret"
    private.write_text("dont-read-me", encoding="utf-8")
    (root / "requirements.txt").unlink()
    (root / "requirements.txt").symlink_to(private)
    with pytest.raises(ManifestDenied, match="UNSAFE_REQUIREMENTS_FILE"):
        direct_pins(root)


def test_invalid_encoding_or_oversized_denied(tmp_path):
    root = fixture_tree(tmp_path)
    file = root / "omega_mvi/requirements.txt"
    file.write_bytes(b"\xff")
    with pytest.raises(ManifestDenied, match="UNREADABLE_REQUIREMENTS_FILE"):
        direct_pins(root)
    file.write_bytes(b"z" * 16385)
    with pytest.raises(ManifestDenied, match="UNSAFE_REQUIREMENTS_FILE"):
        direct_pins(root)


def test_cli_only_digest_by_default_and_json_is_explicit(capsys):
    assert main([]) == 0
    result = capsys.readouterr().out
    assert "DIRECT_PINS_ONLY_NOT_PRODUCTION_SBOM" in result
    assert "OMEGA_DIRECT_SBOM_SHA256=" in result
    assert "fastapi" not in result
    assert main(["--json"]) == 0
    full = capsys.readouterr().out
    assert '"bomFormat":"CycloneDX"' in full
