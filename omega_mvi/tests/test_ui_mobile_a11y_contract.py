"""S10 static mobile/keyboard contract; not a TalkBack or device acceptance test."""
from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app


def test_turkish_page_has_explicit_main_landmark_and_safe_static_assets():
    client = TestClient(app)
    page = client.get("/")
    assert page.status_code == 200
    html = page.text
    assert '<html lang="tr">' in html
    assert 'name="viewport"' in html
    assert html.count('<main id="main-content">') == 1
    assert html.count('</main>') == 1
    assert html.index('<main id="main-content">') < html.index('id="refresh"')
    assert html.index('</main>') < html.index('<footer>')
    assert "KABUL EDİLMEDİ" in html
    assert "unsafe-inline" not in page.headers["content-security-policy"]


def test_mobile_touch_target_and_keyboard_focus_are_available_without_cdn():
    client = TestClient(app)
    response = client.get("/assets/dashboard.css")
    assert response.status_code == 200
    css = response.text
    assert "min-height:44px" in css
    assert "min-width:44px" in css
    assert "button:focus-visible" in css
    assert "outline-offset:2px" in css
    assert "@media(max-width:480px)" in css
    assert "@media(forced-colors:active)" in css
    assert "@media(prefers-reduced-motion:reduce)" in css
    js = client.get("/assets/dashboard.js").text
    assert "activeRefresh" in js and "runId!==activeRefresh" in js
    assert "innerHTML" not in js
