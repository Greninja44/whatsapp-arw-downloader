import argparse
import logging
from pathlib import Path
from src.config import Config
from src.logging_setup import setup_logging

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Download Sony ARW documents from WhatsApp Web and convert to JPEG.")
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    parser.add_argument("--chat")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--download-only", action="store_true")
    mode.add_argument("--convert-only", action="store_true")
    mode.add_argument("--debug-ui", action="store_true")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--max-files", type=int)
    parser.add_argument("--browser-executable", help="Path to Brave, Chrome, or Chromium executable")
    args = parser.parse_args()
    setup_logging(ROOT)
    log = logging.getLogger(__name__)
    downloader = None
    conversions = {"completed": 0, "skipped": 0, "failed": 0, "failures": []}
    error = False
    try:
        config = Config.load(args.config.resolve())
        if args.chat is not None:
            config.chat_name = args.chat
        if args.max_files is not None:
            config.max_files = args.max_files
        if args.browser_executable:
            config.browser_executable = str(Path(args.browser_executable).resolve())
        config.validate(require_chat=not args.convert_only)
        config.make_directories()
    except Exception:
        log.exception("Invalid configuration")
        return 1
    try:
        if not args.convert_only:
            from src.browser import browser_session
            from src.whatsapp import WhatsApp
            from src.downloader import Downloader
            from src.diagnostics import snapshot
            with browser_session(config, args.headless) as page:
                ui = WhatsApp(page, config, ROOT / "debug", args.headless)
                try:
                    ui.open()
                    if args.debug_ui:
                        ui.debug_ui()
                    else:
                        downloader = Downloader(ui, config)
                        ui.walk(downloader.download)
                        if not downloader.discovered:
                            log.warning("No ARW documents detected. Run --debug-ui to inspect selectors and history.")
                            snapshot(page, ROOT / "debug", "no-arws")
                            error = True
                except Exception:
                    snapshot(page, ROOT / "debug", "critical")
                    if args.debug_ui:
                        log.exception("Chat could not be verified; inspect the page manually in debug mode")
                        ui.debug_ui()
                        error = True
                    else:
                        raise
    except KeyboardInterrupt:
        log.warning("Interrupted. Completed downloads are retained; rerun to resume.")
        return 130
    except Exception:
        log.exception("Browser operation failed; use --debug-ui and inspect logs/tool.log")
        error = True
    if not args.download_only and not args.debug_ui:
        try:
            from src.converter import convert_all
            conversions = convert_all(config.download_dir, config.jpeg_dir, config.jpeg_quality)
        except Exception:
            log.exception("Conversion could not start")
            error = True
    if args.debug_ui:
        return int(error)
    log.info("\n%s", "=" * 40)
    log.info("ARW files discovered: %d", downloader.discovered if downloader else 0)
    for label, field in (("completed", "completed"), ("skipped", "skipped"), ("failed", "failed")):
        log.info("Downloads %s: %d", label, getattr(downloader, field, 0))
    for label in ("completed", "skipped", "failed"):
        log.info("JPEG conversions %s: %d", label, conversions[label])
    if downloader and downloader.failures:
        log.error("Download failures: %s", ", ".join(downloader.failures))
    if conversions["failures"]:
        log.error("Conversion failures: %s", ", ".join(conversions["failures"]))
    log.info("\nJPEG folder:\n%s\n%s", config.jpeg_dir, "=" * 40)
    return int(error or bool(getattr(downloader, "failed", 0)) or bool(conversions["failed"]))


if __name__ == "__main__":
    raise SystemExit(main())
