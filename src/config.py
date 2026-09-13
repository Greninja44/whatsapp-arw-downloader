import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    chat_name: str = ""
    download_dir: Path = Path("downloads/arw")
    jpeg_dir: Path = Path("output/jpeg")
    browser_profile: Path = Path("browser_profile")
    jpeg_quality: int = 95
    max_files: int = 100
    max_scrolls: int = 1000
    idle_scrolls: int = 12
    scroll_pause_ms: int = 1500
    login_timeout_seconds: int = 300
    download_timeout_seconds: int = 180
    browser_channel: str = "chrome"
    browser_executable: str = ""
    selectors: dict = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path):
        data = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
        unknown = set(data) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"Unknown configuration keys: {sorted(unknown)}")
        cfg = cls(**data)
        if cfg.browser_executable:
            cfg.browser_executable = str(Path(cfg.browser_executable).expanduser().resolve())
        for key in ("download_dir", "jpeg_dir", "browser_profile"):
            value = Path(getattr(cfg, key)).expanduser()
            setattr(cfg, key, (path.parent / value).resolve())
        cfg.validate()
        return cfg

    def validate(self, require_chat=False):
        for key in ("max_files", "max_scrolls", "idle_scrolls", "scroll_pause_ms",
                    "login_timeout_seconds", "download_timeout_seconds", "jpeg_quality"):
            value = getattr(self, key)
            if type(value) is not int or value < 1:
                raise ValueError(f"{key} must be a positive integer")
        if self.jpeg_quality > 100:
            raise ValueError("jpeg_quality must be at most 100")
        if not isinstance(self.chat_name, str):
            raise ValueError("chat_name must be a string")
        if require_chat and not self.chat_name.strip():
            raise ValueError("Choose a chat: set chat_name in config.json or pass --chat")
        if not isinstance(self.selectors, dict):
            raise ValueError("selectors must be an object")

    def make_directories(self):
        for path in (self.download_dir, self.jpeg_dir, self.browser_profile):
            path.mkdir(parents=True, exist_ok=True)
