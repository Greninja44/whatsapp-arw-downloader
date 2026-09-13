"""Print sync status for the configured target chat, without message content."""
from pathlib import Path
from src.config import Config
import mcp_server

config = Config.load(Path(__file__).resolve().parent / "config.json")
config.validate(require_chat=True)
chats = [chat for chat in mcp_server.list_chats(config.chat_name, limit=100) if chat["name"] == config.chat_name]
print("Exact target chat matches:", len(chats))
if len(chats) == 1:
    items = mcp_server.list_arw_documents(chats[0]["jid"], limit=1000)
    print("Chat:", config.chat_name)
    print("Matching ARW documents synced:", len(items))
