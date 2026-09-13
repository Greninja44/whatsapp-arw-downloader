# WhatsApp ARW Downloader

A configurable Windows tool for any contact or group you select. Downloads Sony `.ARW` document attachments from one exact-name WhatsApp Web chat and converts them to full-resolution JPEGs. Uses Python 3.11+, Playwright, rawpy/LibRaw, and Pillow. Source RAW files are retained.

An authenticated **WhatsApp MCP alternative** is included as an optional integration. See [MCP_SETUP.md](MCP_SETUP.md). Once the local bridge is running, `python download_via_mcp.py` downloads the configured chat's `DSC00000.ARW` documents and runs the same JPEG converter, without browser UI automation.

## PowerShell setup

```powershell
cd whatsapp-arw-downloader
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
# On a fresh checkout, create config.json and edit the chat name:
Copy-Item config.example.json config.json
notepad config.json
python main.py
```

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` instead of `python`; activation is optional.

## Brave

```powershell
python main.py --browser-executable "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" --chat "Example Contact" --max-files 100
```

Or set `browser_executable` to that path in JSON, using forward slashes or escaped backslashes. This opens a separate Brave window using `browser_profile/`. Your ordinary open Brave window cannot be attached to without a remote-debugging launch; this tool does not close it, copy its cookies, or change its profile. Log into the tool's window once. Subsequent runs reuse that session until WhatsApp expires it. Only one tool instance may use the profile at a time.

The default browser is installed Chrome; missing Chrome falls back to Playwright Chromium. Use `"browser_channel": "chromium"` with an empty `browser_executable` to select the downloaded browser explicitly.

## Workflow and commands

1. Start visibly, and complete WhatsApp QR linking manually if requested. No credentials are requested by the script. Login waits up to 300 seconds (configurable).
2. The script searches only the sidebar and requires one exact chat-name match plus an exact header match. If this fails, visible mode asks you to open the intended chat manually. Identically named contacts require you to verify their identity yourself.
3. It starts at the newest messages and scans upward, downloading visible ARW documents immediately before WhatsApp can unmount them. It reports the discovered count and an **up-to** limit during downloads because the final total is not known yet.
4. Each download waits for Playwright's download event and completion, retries up to three total attempts, and publishes the file atomically from `.part`. Conversion then processes all ARWs in the configured download folder, including previously downloaded files.
5. Read the final counts, any failed filenames, and the absolute JPEG folder. Exit code 1 indicates errors (including no detected ARWs); Ctrl+C exits with 130. Completed downloads survive interruption.

```powershell
python main.py
python main.py --chat "Example Contact" --max-files 100
python main.py --download-only
python main.py --convert-only
python main.py --headless
python main.py --debug-ui
python main.py --config .\my-config.json
```

`--download-only`, `--convert-only`, and `--debug-ui` are mutually exclusive. Headless mode requires an already authenticated tool profile. `--max-files` limits discovered message attachments per scan, including previously completed ones; it does not limit conversion of local files.

## Configuration

See `config.example.json`. Relative paths resolve against the configuration file's directory. Set `chat_name` to the exact contact or group title, or pass `--chat`. There is no default target. `--convert-only` does not require a chat. Without config.json, other defaults apply. CLI options override corresponding config values.

| Setting | Default | Meaning |
| --- | --- | --- |
| chat_name | empty | Required exact contact or group title for downloads |
| download_dir | downloads/arw | Source RAW files and resume manifest |
| jpeg_dir | output/jpeg | Converted JPEG files |
| browser_profile | browser_profile | Tool's persistent login profile |
| jpeg_quality | 95 | JPEG quality, 1–100 |
| max_files | 100 | Maximum distinct message attachments per run |
| max_scrolls | 1000 | Maximum history scans |
| idle_scrolls | 12 | Stop after this many scans with no new ARWs |
| scroll_pause_ms | 1500 | Wait for history rendering after each scroll |
| login_timeout_seconds | 300 | Manual login allowance |
| download_timeout_seconds | 180 | Wait for a download event; transfer completion is awaited separately |
| browser_channel | chrome | Installed Chrome or Playwright chromium |
| browser_executable | empty | Optional Brave/Chromium executable path |
| selectors | {} | CSS overrides described below |

A long gap without ARWs can trigger the idle stop before older attachments are reached. Increase `idle_scrolls` (for example to 100) and `max_scrolls` when needed. Increase `scroll_pause_ms` on a slow connection. The final count means files discovered in the scanned UI, not proof that every historical file exists locally. WhatsApp may not expose all old history on a linked device, and expired/unavailable documents cannot be recovered by this tool.

## Resume, duplicates, and conversion

`downloads/arw/.downloads.json` records stable message identity, filename, completed size, and SHA-256. Reruns validate hashes before skipping. Different messages with the same filename get `name (2).ARW`, preserving both files; duplicate filenames are tracked separately from message identities. An untracked local file is adopted only if LibRaw can unpack it. Unverified existing files are preserved and a numbered destination is used. Keep the manifest alongside the files, and run only one tool instance per output folder.

Conversion uses camera white balance, full resolution, 8-bit sRGB output, JPEG quality 95, and `subsampling=0`, with an embedded sRGB profile. It does not copy camera EXIF metadata. JPEGs are skipped only if nonempty and strictly newer than their source. Bad RAW files are reported and processing continues. JPEG creation uses an atomic temporary file. No source ARWs are deleted or changed.

## DOM inspection and selector limitations

WhatsApp Web can change its DOM. Authenticated browser selectors are candidate strategies and may need adjustment for your UI. Use the inspection mode below if chat selection or downloads fail.
Run:

```powershell
python main.py --debug-ui
```

Log in, open the target chat if prompted, and scroll manually to visible ARW documents. Press Enter in PowerShell to inspect; repeat as needed and type `q` to exit. This mode prints matching ARW elements and ancestors plus candidate download controls, and saves HTML, screenshots, and control attributes in `debug/`. It never downloads or converts files. Even if automatic chat verification fails, it allows page inspection. In headless debug mode it takes a single snapshot.

Candidate selectors live in `src/selectors.py`; override keys using `config.json`'s `selectors` object. Available keys: `sidebar`, `main`, `search`, `chat_titles`, `header_titles`, `message`, `filename`, `download`, `document`. Chat-title strategies expect `title` attributes; message identity expects `data-id`. Structural changes beyond CSS matching may require updating `src/whatsapp.py`. Labels for download/search are English; localized UI may need selector overrides. Generated CSS classes are not used.

The tool only clicks an unambiguous document download control within its message. It does not use message menus or guess at generic buttons. A UI requiring an initial document fetch before exposing a save control may need an updated strategy after inspecting its DOM. Unexpected download filenames are rejected. Critical failures save diagnostic screenshots/HTML and log stack traces to `logs/tool.log`; DEBUG logs include DOM and selector details.

Opening a conversation can mark it read as normal WhatsApp behavior. The tool never composes/sends messages, deletes messages, changes chat settings, or bypasses authentication/CAPTCHAs. Debug snapshots and logs can contain private chat content; the profile contains your authenticated session. These folders and config.json are gitignored.

## Checks

```powershell
python -m compileall -q main.py src tests
python -m unittest discover -s tests -v
# Optional: launches a headless browser against a local fixture, without WhatsApp:
python -m tests.browser_smoke
```

Tests cover filtering, Windows filename safety, manifest duplicate detection and corruption, output directory creation, conversion skip logic, and continuing after corrupt RAW files. A successful real-photo conversion and authenticated WhatsApp downloads require your files/session.

API references: [Playwright downloads](https://playwright.dev/python/docs/downloads), [persistent browser contexts](https://playwright.dev/python/docs/api/class-browsertype#browser-type-launch-persistent-context), [rawpy processing parameters](https://letmaik.github.io/rawpy/api/rawpy.Params.html).

## Repository privacy

Only source code, examples, and documentation belong in Git. Local `config.json`, browser sessions, bridge databases, downloaded photos, JPEG output, logs, debug snapshots, integrations, and compiler downloads are excluded by `.gitignore`. If you use custom paths, exclude those before committing as well. Each user links their own WhatsApp account.

## Project layout

- `main.py` and `src/`: browser download, resume tracking, and RAW conversion.
- `config.example.json`: reusable configuration template.
- `download_via_mcp.py` and `mcp_server.py`: optional local bridge access.
- `MCP_SETUP.md`: reproduce the optional Windows bridge setup.
- `tests/`: unit tests and local smoke checks.
