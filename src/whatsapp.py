import hashlib
import json
import logging
import re
from dataclasses import dataclass
from .diagnostics import ATTRIBUTES_JS, snapshot
from .files import is_arw, safe_filename
from .selectors import selectors

log = logging.getLogger(__name__)


@dataclass
class Attachment:
    key: str
    name: str
    message_id: str


class WhatsApp:
    def __init__(self, page, config, debug_dir, headless=False):
        self.page, self.config, self.debug_dir = page, config, debug_dir
        self.headless = headless
        self.s = selectors(config.selectors)

    @property
    def main(self):
        return self.page.locator(self.s["main"])

    def open(self):
        self.page.goto("https://web.whatsapp.com/", wait_until="domcontentloaded", timeout=90000)
        log.info("Waiting for WhatsApp. If prompted, scan the QR code or complete login manually in the browser.")
        if self.headless:
            log.info("Headless mode needs a previously authenticated tool profile. Use a visible run if login times out.")
        self.page.locator(self.s["sidebar"]).wait_for(state="visible", timeout=self.config.login_timeout_seconds * 1000)
        self.select_chat()

    def select_chat(self):
        sidebar = self.page.locator(self.s["sidebar"])
        try:
            search = sidebar.locator(self.s["search"]).filter(visible=True)
            if search.count() != 1:
                raise RuntimeError(f"Expected one sidebar search field, got {search.count()}")
            # Only fill a textbox scoped to the sidebar, never the message composer.
            search.fill(self.config.chat_name)
            self.page.wait_for_timeout(2000)
            matches = sidebar.locator(self.s["chat_titles"]).filter(visible=True)
            exact = [x for x in matches.all() if x.get_attribute("title") == self.config.chat_name]
            if len(exact) != 1:
                raise RuntimeError(f"Found {len(exact)} exact chat-name matches; refusing ambiguous selection")
            exact[0].click()
            self.main.wait_for(state="visible")
            self.assert_chat()
        except Exception:
            log.exception("Automatic chat selection failed")
            snapshot(self.page, self.debug_dir, "chat-selection")
            if self.headless:
                raise
            input(f"Open the intended chat {self.config.chat_name!r} manually in the browser, then press Enter here: ")
            self.assert_chat()

    def assert_chat(self):
        titles = self.main.locator(self.s["header_titles"]).all()
        names = [e.get_attribute("title") for e in titles if e.is_visible()]
        log.debug("Chat header titles: %r", names)
        if self.config.chat_name not in names:
            raise RuntimeError(f"Cannot verify exact chat header {self.config.chat_name!r}; observed {names!r}. Run --debug-ui.")

    def visible_attachments(self):
        self.assert_chat()
        found = {}
        rows = self.main.locator(self.s["message"])
        for row in rows.all():
            if not row.is_visible():
                continue
            message_id = row.get_attribute("data-id")
            if not message_id:
                continue
            for node in row.locator(self.s["filename"]).all():
                if not node.is_visible():
                    continue
                name = (node.get_attribute("title") or node.get_attribute("download") or node.inner_text()).strip()
                if not is_arw(name) or "\n" in name:
                    continue
                try:
                    name = safe_filename(name)
                except ValueError:
                    log.debug("Rejected filename candidate: %r", name)
                    continue
                # Require attachment evidence, not just a text message mentioning .ARW.
                if not row.locator(self.s["download"]).count() and not row.locator(self.s["document"]).count():
                    log.debug("No document evidence for %s in %s", name, message_id)
                    continue
                key = hashlib.sha256((self.config.chat_name + "\0" + message_id + "\0" + name).encode()).hexdigest()
                found[key] = Attachment(key, name, message_id)
        return list(found.values())

    def row(self, item):
        # JSON string escaping is valid for CSS quoted attribute values here.
        return self.main.locator(f'[data-id={json.dumps(item.message_id)}]')

    def download_button(self, item):
        self.assert_chat()
        row = self.row(item)
        if row.count() != 1:
            raise RuntimeError(f"Message is no longer uniquely rendered: {item.name}")
        row.hover()
        candidates = row.locator(self.s["download"]).filter(visible=True)
        # Icons and their enclosing button may both match: deduplicate by clickable ancestor.
        candidates.evaluate_all("""els => els.forEach(e => {
            const target=e.closest('button,[role="button"],a[download]') || e;
            target.setAttribute('data-arw-tool-download','true');
        })""")
        controls = row.locator('[data-arw-tool-download="true"]').filter(visible=True)
        if controls.count() != 1:
            log.debug("Download candidates: %s", candidates.evaluate_all(ATTRIBUTES_JS))
            raise RuntimeError(f"Expected one download control for {item.name}; found {controls.count()}. Run --debug-ui.")
        return controls

    def scroll(self, bottom=False):
        # Locate a real vertical scroll container by geometry, scoped to this chat.
        result = self.main.evaluate("""(root, bottom) => {
            const candidates=[root,...root.querySelectorAll('*')].filter(e => {
                const r=e.getBoundingClientRect(), style=getComputedStyle(e);
                return r.width>200 && r.height>150 && e.scrollHeight>e.clientHeight+5
                    && /auto|scroll/.test(style.overflowY);
            }).sort((a,b)=>b.clientHeight-a.clientHeight);
            if (!candidates.length) return null;
            const e=candidates[0], before=e.scrollTop;
            e.scrollTop=bottom ? e.scrollHeight : Math.max(0,e.scrollTop-e.clientHeight*0.7);
            e.dispatchEvent(new Event('scroll',{bubbles:true}));
            return {before, after:e.scrollTop, height:e.scrollHeight};
        }""", bottom)
        log.debug("Chat scroll: %r", result)
        self.page.wait_for_timeout(self.config.scroll_pause_ms)
        return result

    def debug_ui(self):
        log.info("Debug UI mode: no attachments will be downloaded.")
        while True:
            snapshot(self.page, self.debug_dir, "ui")
            # Inspect even when the normal message/filename selectors do not match.
            arw = self.page.get_by_text(re.compile(r"\.arw\s*$", re.I))
            for node in arw.all()[:50]:
                if node.is_visible():
                    log.info("ARW element / ancestors: %s", node.evaluate("""e => {
                        const out=[]; for(let i=0;e && i<5;i++,e=e.parentElement)
                        out.push(e.outerHTML.slice(0,6000)); return out;
                    }"""))
            log.info("Candidate download controls: %s", self.main.locator(self.s["download"]).evaluate_all(ATTRIBUTES_JS))
            if self.headless:
                return
            answer = input("Scroll to an ARW in the browser, then Enter to inspect again; type q to finish: ").strip().lower()
            if answer == "q":
                return

    def walk(self, callback):
        seen, names = set(), set()
        # Opening a chat can restore a historical viewport. Start at newest first.
        for _ in range(5):
            pos = self.scroll(bottom=True)
            if pos is None or pos["before"] == pos["after"]:
                break
        idle = 0
        for iteration in range(self.config.max_scrolls):
            new = 0
            for item in self.visible_attachments():
                if item.key in seen:
                    continue
                seen.add(item.key)
                names.add(item.name.casefold())
                new += 1
                log.info("Found %d ARW files... (%d distinct filenames)", len(seen), len(names))
                callback(item, len(seen))
                if len(seen) >= self.config.max_files:
                    log.info("Stopped at max_files=%d; older attachments may remain.", self.config.max_files)
                    return len(seen)
            idle = 0 if new else idle + 1
            if idle >= self.config.idle_scrolls:
                log.info("Stopped after %d scans without new ARWs. Older files may remain beyond a long gap.", idle)
                return len(seen)
            self.scroll()
        log.info("Stopped at max_scrolls=%d; history may be incomplete.", self.config.max_scrolls)
        return len(seen)
