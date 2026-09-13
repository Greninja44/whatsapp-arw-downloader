import logging
from contextlib import contextmanager
from playwright.sync_api import sync_playwright

log = logging.getLogger(__name__)


@contextmanager
def browser_session(config, headless=False):
    with sync_playwright() as playwright:
        options = dict(user_data_dir=str(config.browser_profile), headless=headless,
                       accept_downloads=True, viewport={"width": 1440, "height": 1000})
        if config.browser_executable:
            options["executable_path"] = config.browser_executable
        elif config.browser_channel and config.browser_channel != "chromium":
            options["channel"] = config.browser_channel
        try:
            context = playwright.chromium.launch_persistent_context(**options)
        except Exception as exc:
            # Only fall back for a missing executable; never work around profile locks.
            if "executable" not in str(exc).lower() or "channel" not in options:
                raise
            log.warning("Chrome executable unavailable; trying Playwright Chromium")
            options.pop("channel")
            context = playwright.chromium.launch_persistent_context(**options)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.set_default_timeout(10000)
            yield page
        finally:
            context.close()
