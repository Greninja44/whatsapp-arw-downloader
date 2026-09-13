"""Register only this server, preserving existing user Codex settings."""
import json
import os
import shutil
import tomllib
from datetime import datetime
from pathlib import Path

root = Path(__file__).resolve().parent
config = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
text = config.read_text(encoding="utf-8") if config.exists() else ""
data = tomllib.loads(text)
if "whatsapp" in data.get("mcp_servers", {}):
    raise SystemExit("A whatsapp server is already configured; left it unchanged.")
tools = ["search_contacts", "list_messages", "list_chats", "get_chat", "get_direct_chat_by_contact",
         "get_contact_chats", "get_last_interaction", "get_message_context", "list_arw_documents", "download_media"]
section = '\n[mcp_servers.whatsapp]\n'
section += 'command = ' + json.dumps(str(root / ".venv/Scripts/python.exe")) + '\n'
section += 'args = [' + json.dumps(str(root / "mcp_server.py")) + ']\n'
section += 'cwd = ' + json.dumps(str(root)) + '\n'
section += 'enabled_tools = ' + json.dumps(tools) + '\n'
section += 'startup_timeout_sec = 30\ntool_timeout_sec = 300\n'
tomllib.loads(text + section)
config.parent.mkdir(exist_ok=True)
if config.exists():
    backup = config.with_name(f"config.toml.before-whatsapp-{datetime.now():%Y%m%d-%H%M%S}.bak")
    shutil.copy2(config, backup)
    print(f"Backup: {backup}")
config.write_text(text + section, encoding="utf-8")
print(f"Registered whatsapp MCP with {len(tools)} allowed read/download tools in {config}")
