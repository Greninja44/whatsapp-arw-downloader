import logging
from .diagnostics import snapshot
from .files import DownloadStore, is_arw

log = logging.getLogger(__name__)


class Downloader:
    def __init__(self, ui, config):
        self.ui, self.config = ui, config
        self.store = DownloadStore(config.download_dir)
        self.completed = self.skipped = self.failed = self.discovered = 0
        self.failures = []

    def download(self, item, index):
        self.discovered = index
        if self.store.complete(item.key):
            self.skipped += 1
            log.info("[%d] Already complete: %s", index, item.name)
            return
        # Adopt a pre-existing untracked RAW only after LibRaw successfully unpacks it.
        existing = self.config.download_dir / item.name
        owned = {entry["path"].casefold() for entry in self.store.entries.values()}
        if existing.is_file() and existing.name.casefold() not in owned:
            try:
                import rawpy
                with rawpy.imread(str(existing)) as raw:
                    if raw.raw_image.size == 0:
                        raise ValueError("RAW contains no pixels")
                self.store.record(item.key, existing)
                self.skipped += 1
                log.info("[%d] Validated existing RAW: %s", index, existing.name)
                return
            except Exception:
                log.debug("Existing file did not pass RAW validation: %s", existing, exc_info=True)
        destination = self.store.destination(item.key, item.name)
        temporary = destination.with_suffix(destination.suffix + ".part")
        for attempt in range(1, 4):
            try:
                log.info("[%d/up to %d] Downloading %s (attempt %d/3)", index, self.config.max_files, item.name, attempt)
                button = self.ui.download_button(item)
                with self.ui.page.expect_download(timeout=self.config.download_timeout_seconds * 1000) as pending:
                    button.click()
                download = pending.value
                if not is_arw(download.suggested_filename) or download.suggested_filename.casefold() != item.name.casefold():
                    download.cancel()
                    raise RuntimeError(f"Unexpected download: {download.suggested_filename!r}")
                # save_as waits for completion; only atomically publish completed bytes.
                download.save_as(str(temporary))
                if download.failure() or temporary.stat().st_size == 0:
                    raise RuntimeError(f"Incomplete download: {download.failure()}")
                temporary.replace(destination)
                self.store.record(item.key, destination)
                self.completed += 1
                log.info("Download complete: %s", destination.name)
                return
            except Exception:
                log.exception("Download failed for %s, attempt %d/3", item.name, attempt)
                temporary.unlink(missing_ok=True)
                if attempt < 3:
                    self.ui.page.wait_for_timeout(1500 * attempt)
        self.failed += 1
        self.failures.append(item.name)
        snapshot(self.ui.page, self.ui.debug_dir, "download-failure")
