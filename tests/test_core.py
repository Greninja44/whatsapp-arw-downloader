import os
import tempfile
import unittest
from pathlib import Path
from src.config import Config
from src.files import DownloadStore, is_arw, safe_filename
from src.converter import should_skip, convert_all


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_filter(self):
        for name in ("DSC04819.ARW", "DSC04730.arw", "Mixed.ArW"):
            self.assertTrue(is_arw(name))
        for name in ("", "file.pdf", "file.ARW.zip", "file.jpg", "file.mp4"):
            self.assertFalse(is_arw(name))

    def test_chat_must_be_chosen_for_downloads(self):
        config = Config.load(self.root / "missing.json")
        self.assertEqual(config.chat_name, "")
        config.validate()  # Offline conversion needs no target.
        with self.assertRaisesRegex(ValueError, "Choose a chat"):
            config.validate(require_chat=True)
        config.chat_name = "Example Group"
        config.validate(require_chat=True)

    def test_unsafe_names(self):
        for name in ("../a.ARW", "C:\\a.ARW", "CON.ARW", "a:bad.ARW"):
            with self.assertRaises(ValueError):
                safe_filename(name)

    def test_resume_and_same_size_corruption(self):
        store = DownloadStore(self.root)
        path = store.destination("message1", "DSC.ARW")
        path.write_bytes(b"complete file")
        store.record("message1", path)
        reloaded = DownloadStore(self.root)
        self.assertTrue(reloaded.complete("message1"))
        self.assertFalse(reloaded.complete("message2"))
        path.write_bytes(b"corrupted!!!!")
        self.assertFalse(reloaded.complete("message1"))

    def test_filename_collision(self):
        store = DownloadStore(self.root)
        first = store.destination("1", "DSC.ARW")
        first.write_bytes(b"raw")
        store.record("1", first)
        self.assertEqual(store.destination("1", "DSC.ARW"), first)
        self.assertEqual(store.destination("2", "dsc.arw").name, "dsc (2).arw")

    def test_output_directories(self):
        config = Config.load(self.root / "config.json")
        config.make_directories()
        self.assertTrue(config.download_dir.is_dir())
        self.assertEqual(config.jpeg_dir, self.root / "output" / "jpeg")
        self.assertTrue(config.jpeg_dir.is_dir())

    def test_conversion_skip(self):
        raw = self.root / "DSC.ARW"
        jpeg = self.root / "DSC.jpg"
        raw.write_bytes(b"raw")
        self.assertFalse(should_skip(raw, jpeg))
        jpeg.write_bytes(b"jpeg")
        os.utime(raw, ns=(2_000_000_000, 2_000_000_000))
        os.utime(jpeg, ns=(3_000_000_000, 3_000_000_000))
        self.assertTrue(should_skip(raw, jpeg))
        os.utime(jpeg, ns=(1_000_000_000, 1_000_000_000))
        self.assertFalse(should_skip(raw, jpeg))
        jpeg.write_bytes(b"")
        self.assertFalse(should_skip(raw, jpeg))

    def test_corrupt_raw_continues(self):
        for name in ("bad.ARW", "other.arw"):
            (self.root / name).write_bytes(b"not raw data")
        with self.assertLogs("src.converter", level="ERROR"):
            result = convert_all(self.root, self.root / "jpeg")
        self.assertEqual(result["failed"], 2)
        self.assertEqual(result["completed"], 0)
        self.assertEqual(list((self.root / "jpeg").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
