"""S10 fail-closed unavailable feature disclosure and bilingual UI contract."""
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import shutil


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/dashboard.css").read_text(encoding="utf-8")


class Probe(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.attrs = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attrs.append(dict(attrs))


def test_disabled_feature_disclosures_are_not_fake_interactive_forms():
    probe = Probe()
    probe.feed(HTML)
    for marker in ["inventoryLabel", "searchLabel", "secretsLabel", "prLabel", "authLabel"]:
        assert f'data-i18n="{marker}"' in HTML
    assert HTML.count('class="feature-list"') == 1
    assert "gizli değerler gösterilmez" in HTML
    assert "KABUL EDİLMEDİ" in HTML
    assert probe.tags.count("form") == 0
    assert probe.tags.count("input") == 0
    assert probe.tags.count("a") == 0
    assert probe.tags.count("main") == 1
    assert probe.tags.count("footer") == 1
    assert any(x.get("aria-pressed") == "false" for x in probe.attrs)
    assert any(x.get("data-i18n-aria-label") == "preferencesLabel" for x in probe.attrs)


def test_light_theme_and_long_citations_are_visible_without_inline_scripts():
    assert ':root[data-theme="light"]' in CSS
    assert '#sources{overflow-wrap:anywhere;word-break:break-word}' in CSS
    assert "button:focus-visible" in CSS
    assert "@media(forced-colors:active)" in CSS
    assert "@media(prefers-reduced-motion:reduce)" in CSS
    assert "<script>" not in HTML
    assert 'src="/assets/dashboard.js"' in HTML


def test_real_javascript_locale_and_privacy_contract():
    node = shutil.which("node")
    assert node, "Node.js required; never skip runtime locale tests in CI"
    result = subprocess.run(
        [node, "--test", str(Path(__file__).with_name("ui_dashboard_preferences.cjs"))],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=20, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
