"""Synthetic-only inventory UI contracts — NOT a real owner inventory acceptance."""
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"app/static/index.html").read_text("utf-8")
CSS=(ROOT/"app/static/dashboard.css").read_text("utf-8")


class TagProbe(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags=[]
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def test_inventory_category_selector_keyboard_and_disclosure():
    page=TagProbe();page.feed(HTML)
    selects=[attrs for tag,attrs in page.tags if tag=="select"]
    assert len(selects)==1 and selects[0]["id"]=="inventory-filter"
    assert any(tag=="label" and attrs.get("for")=="inventory-filter"
               for tag,attrs in page.tags)
    assert any(tag=="p" and attrs.get("id")=="inventory-status" and
               attrs.get("aria-live")=="polite" for tag,attrs in page.tags)
    values=[attrs.get("value") for tag,attrs in page.tags if tag=="option"]
    assert values==["repository","folder","service","data_source"]
    assert "gerçek hesap veya klasörler taranmaz" in HTML
    assert "73 · Dijital envanter: KAPALI" in HTML
    assert "#inventory-filter:focus-visible" in CSS
    assert "min-height:44px" in CSS


def test_actual_browser_script_validates_fixture_in_node_vm():
    node=shutil.which("node")
    assert node, "Node is required in CI to run UI trust-boundary JS"
    script=Path(__file__).with_name("ui_demo_inventory_contract.cjs")
    cp=subprocess.run([node,"--test",str(script)],capture_output=True,text=True,
                      check=False,timeout=30)
    assert cp.returncode==0,cp.stdout+cp.stderr
