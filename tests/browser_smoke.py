"""Optional local DOM smoke test; uses Brave/Chrome without accessing WhatsApp.

Run from the project root: python -m tests.browser_smoke
"""
import tempfile
from pathlib import Path
from src.browser import browser_session
from src.config import Config
from src.downloader import Downloader
from src.whatsapp import WhatsApp


def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        config = Config(browser_channel="chromium")
        config.browser_profile = root / "profile"
        config.download_dir = root / "arw"
        config.jpeg_dir = root / "jpeg"
        config.make_directories()
        with browser_session(config, headless=True) as page:
            page.set_content('''<div id="main"><header><span title="Example Contact">Example Contact</span></header>
                <div data-id="one"><span title="DSC.ARW">DSC.ARW</span>
                <a download="DSC.ARW" href="data:application/octet-stream;base64,YXJ3">Download</a></div>
                <div data-id="two"><span title="DSC.ARW">DSC.ARW</span>
                <a download="DSC.ARW" href="data:application/octet-stream;base64,YXJ3Mg==">Download</a></div>
                <div data-id="pdf"><a download="other.pdf">other.pdf</a></div>
                <div data-id="text"><span>caption.ARW</span></div></div>''')
            config.chat_name = "Example Contact"
            ui = WhatsApp(page, config, root / "debug", headless=True)
            items = ui.visible_attachments()
            assert len(items) == 2, items
            download = Downloader(ui, config)
            for index, item in enumerate(items, 1):
                download.download(item, index)
            assert download.completed == 2 and download.failed == 0
            assert (config.download_dir / "DSC.ARW").read_bytes() == b"arw"
            assert (config.download_dir / "DSC (2).ARW").read_bytes() == b"arw2"
            resumed = Downloader(ui, config)
            for index, item in enumerate(items, 1):
                resumed.download(item, index)
            assert resumed.skipped == 2 and resumed.completed == 0
        print("Brave/Chrome smoke test passed: filtering, downloads, collisions, and resume.")


if __name__ == "__main__":
    main()
