import json
import logging
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

ATTRIBUTES_JS = """els => els.filter(e => e.getBoundingClientRect().width > 0).map(e => ({
 tag:e.tagName, attributes:Object.fromEntries([...e.attributes].map(a=>[a.name,a.value])),
 text:(e.innerText||'').slice(0,500), html:e.outerHTML.slice(0,2000)
})).slice(0,200)"""


def snapshot(page, folder: Path, label: str):
    folder.mkdir(parents=True, exist_ok=True)
    prefix = folder / f"{datetime.now():%Y%m%d-%H%M%S-%f}-{label}"
    try:
        page.screenshot(path=str(prefix.with_suffix(".png")), full_page=True, timeout=15000)
        prefix.with_suffix(".html").write_text(page.content(), encoding="utf-8")
        attrs = page.locator('[role="button"], button, [aria-label], [contenteditable="true"]').evaluate_all(ATTRIBUTES_JS)
        prefix.with_suffix(".json").write_text(json.dumps(attrs, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("UI diagnostics saved: %s", prefix)
        log.debug("Visible controls: %s", json.dumps(attrs, ensure_ascii=False))
    except Exception:
        log.exception("Could not save complete UI diagnostics")
