# Optional WhatsApp bridge setup (Windows)

This alternative downloads synced Sony document attachments without browser automation. It uses the community [lharries/whatsapp-mcp](https://github.com/lharries/whatsapp-mcp) bridge and the source patch included here. Python 3.11+, Git, and Windows x64 are required. Start in the project directory with the virtual environment from the README activated.

## Install and build

```powershell
python -m pip install -r requirements.txt -r requirements-mcp.txt
git clone https://github.com/lharries/whatsapp-mcp.git integrations/whatsapp-mcp
git -C integrations/whatsapp-mcp checkout 7d6a06dcdce1f01dfb24f60e1030d5efba9f3b88
python prepare_mcp.py
python setup_mcp_toolchain.py
powershell -NoProfile -File .\build_mcp.ps1
```

`prepare_mcp.py` applies the complete source and dependency patch, or detects that it is already applied. It refuses other upstream revisions. The patch updates the WhatsApp library, preserves signed media URL query parameters, directs upstream Python diagnostics to stderr, removes the send HTTP endpoint, binds the API to localhost port 18080, and isolates downloads by message ID. Portable Go and Zig downloads are verified against published SHA-256 hashes and stored in the ignored `toolchain/` directory.

## Pair and download

```powershell
python start_whatsapp_mcp.py
```

Open the local pairing page at http://127.0.0.1:18766. On your phone, open WhatsApp > Linked devices > Link a device and scan the QR code. Leave the bridge running and allow contact/history sync to finish.

In another terminal with the environment activated:

```powershell
python download_via_mcp.py --chat "Example Contact" --max-files 100
# Or use chat_name and limits from your local config.json:
python download_via_mcp.py
python check_whatsapp_connection.py
```

The batch command accepts `--config`, `--chat`, and `--max-files`. It requires one exact contact or group name match. Downloads are checked against WhatsApp size and SHA-256 metadata, saved under the configured `download_dir`, and converted to `jpeg_dir`. The resume manifest supports reruns and each download retries up to three times. Use separate output directories in separate configs to keep different chats organized.

The bridge currently accepts only `DSC` followed by five digits and `.ARW`, case-insensitively, such as `DSC00001.ARW`. The browser workflow accepts other `.ARW` filenames too. The bridge batch scans up to 1,000 matching synced attachments per run. Old or expired media and history unavailable to the linked device cannot be recovered.

## Optional MCP client

The standalone batch command does not require an AI client. To use MCP, configure your client to run the absolute path to `.venv/Scripts/python.exe` with the absolute path to `mcp_server.py` as its argument. The server uses STDIO and exposes ten read/download tools with no sending tools. Keep the bridge running separately. `register_whatsapp_mcp.py` is an optional client-specific registration helper; inspect it before use.

## Local data and lifecycle

Session keys, synced chats, and initial media downloads live in `integrations/whatsapp-mcp/whatsapp-bridge/store`. Logs live in `logs/`. These directories are ignored by Git. MCP queries can expose the requested chat information to whichever client you connect.

```powershell
# Restart using the saved linked-device session:
powershell -NoProfile -File .\restart_whatsapp_bridge.ps1
# Local fixture database and STDIO handshake checks; no account required:
python -m tests.mcp_smoke
```

The restart script verifies the executable for the recorded PID before stopping it and writes timestamped logs. `logs/bridge-current-path.txt` identifies the active log. Closing the pairing page does not stop the bridge. To stop it, verify that the PID in `logs/whatsapp-bridge.pid` belongs to this project's bridge executable before stopping that process. Revoke the session from Linked devices on your phone when finished.
