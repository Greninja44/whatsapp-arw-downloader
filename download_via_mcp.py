"""Download the exact configured chat's synced Sony documents through the local MCP bridge."""
import argparse
import hashlib
import logging
import shutil
import time
from contextlib import closing
from pathlib import Path
import mcp_server
from src.config import Config
from src.converter import convert_all
from src.files import DownloadStore, sha256
from src.logging_setup import setup_logging

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    parser.add_argument("--chat", help="Exact contact or group name")
    parser.add_argument("--max-files", type=int)
    args = parser.parse_args()
    setup_logging(ROOT)
    log = logging.getLogger(__name__)
    cfg = Config.load(args.config.resolve())
    if args.chat is not None:
        cfg.chat_name = args.chat
    if args.max_files is not None:
        cfg.max_files = args.max_files
    cfg.validate(require_chat=True)
    cfg.make_directories()
    chats = [c for c in mcp_server.list_chats(cfg.chat_name, limit=100) if c["name"] == cfg.chat_name]
    if len(chats) != 1:
        raise RuntimeError(f"Expected one exact chat named {cfg.chat_name!r}, found {len(chats)}")
    jid = chats[0]["jid"]
    items = mcp_server.list_arw_documents(jid, limit=min(cfg.max_files, 1000))
    store = DownloadStore(cfg.download_dir)
    completed = skipped = failed = 0
    failures = []
    log.info("Confirmed chat: %s. Found %d matching ARW documents.", cfg.chat_name, len(items))
    for index, item in enumerate(items, 1):
        key = hashlib.sha256(("mcp\0" + jid + "\0" + item["id"]).encode()).hexdigest()
        if store.complete(key):
            skipped += 1
            log.info("[%d/%d] Already complete: %s", index, len(items), item["filename"])
            continue
        destination = store.destination(key, item["filename"])
        for attempt in range(1, 4):
            try:
                log.info("[%d/%d] Downloading %s (attempt %d/3)", index, len(items), item["filename"], attempt)
                result = mcp_server.download_media(item["id"], jid)
                if not result["success"]:
                    raise RuntimeError(result)
                source = Path(result["file_path"]).resolve()
                bridge_store = ROOT / "integrations/whatsapp-mcp/whatsapp-bridge/store"
                if not source.is_relative_to(bridge_store.resolve()):
                    raise RuntimeError("Bridge returned a path outside its store")
                with closing(mcp_server.database()) as db:
                    expected = db.execute("SELECT file_sha256,file_length FROM messages WHERE id=? AND chat_jid=?", (item["id"], jid)).fetchone()
                if source.stat().st_size != expected[1] or sha256(source) != bytes(expected[0]).hex():
                    raise RuntimeError("Downloaded RAW failed WhatsApp size/SHA-256 verification")
                temporary = destination.with_suffix(".ARW.part")
                shutil.copy2(source, temporary)
                temporary.replace(destination)
                store.record(key, destination)
                completed += 1
                log.info("Download complete")
                break
            except Exception:
                log.exception("Download failed: %s (attempt %d)", item["filename"], attempt)
                if attempt == 3:
                    failed += 1
                    failures.append(item["filename"])
                else:
                    time.sleep(attempt * 2)
    conversion = convert_all(cfg.download_dir, cfg.jpeg_dir, cfg.jpeg_quality)
    log.info("\n%s\nARW files discovered: %d\nDownloads completed: %d\nDownloads skipped: %d\nDownloads failed: %d\nJPEG conversions completed: %d\nJPEG conversions skipped: %d\nJPEG conversions failed: %d\n\nJPEG folder:\n%s\n%s", "="*40, len(items), completed, skipped, failed, conversion["completed"], conversion["skipped"], conversion["failed"], cfg.jpeg_dir, "="*40)
    if failures or conversion["failures"]:
        log.error("Download failures: %s; conversion failures: %s", failures, conversion["failures"])
    return int(bool(failed or conversion["failed"]))


if __name__ == "__main__":
    raise SystemExit(main())
