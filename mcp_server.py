"""Local WhatsApp MCP: read tools plus downloads limited to DSC00000.ARW names."""
import re
import sqlite3
import sys
import requests
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "integrations/whatsapp-mcp/whatsapp-mcp-server"))
import whatsapp
from mcp.server.fastmcp import FastMCP

whatsapp.WHATSAPP_API_BASE_URL = "http://127.0.0.1:18080/api"
mcp = FastMCP("whatsapp-readonly")
for name in ("search_contacts", "list_messages", "get_chat",
             "get_direct_chat_by_contact", "get_contact_chats",
             "get_last_interaction", "get_message_context"):
    mcp.add_tool(getattr(whatsapp, name), name=name)


def database():
    path = Path(whatsapp.MESSAGES_DB_PATH).resolve()
    return sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)


@mcp.tool()
def list_chats(query: str = "", limit: int = 20, page: int = 0, include_last_message: bool = False, sort_by: str = "last_active") -> list[dict]:
    """Find synced chats by saved contact name or chat title, including recently linked devices."""
    if not 1 <= limit <= 1000 or page < 0:
        raise ValueError("Invalid pagination")
    contact_path = Path(whatsapp.MESSAGES_DB_PATH).with_name("whatsapp.db").resolve()
    with closing(sqlite3.connect(contact_path.as_uri() + "?mode=ro", uri=True)) as contacts:
        matches = contacts.execute("SELECT their_jid,full_name FROM whatsmeow_contacts WHERE lower(full_name) LIKE lower(?) OR their_jid LIKE ?", (f"%{query}%", f"%{query}%")).fetchall()
    names = dict(matches)
    order = "last_message_time DESC" if sort_by == "last_active" else "name"
    with closing(database()) as db:
        db.row_factory = sqlite3.Row
        placeholders = ",".join("?" for _ in names) or "NULL"
        rows = db.execute(f"SELECT jid,name,last_message_time FROM chats WHERE lower(name) LIKE lower(?) OR jid LIKE ? OR jid IN ({placeholders}) ORDER BY {order} LIMIT ? OFFSET ?", (f"%{query}%", f"%{query}%", *names, limit, page * limit)).fetchall()
        results = [dict(row) for row in rows]
        for row in results:
            row["name"] = names.get(row["jid"]) or row["name"]
            if include_last_message:
                last = db.execute("SELECT content FROM messages WHERE chat_jid=? ORDER BY timestamp DESC LIMIT 1", (row["jid"],)).fetchone()
                row["last_message"] = last[0] if last else None
    return results


@mcp.tool()
def list_arw_documents(chat_jid: str, limit: int = 100, offset: int = 0) -> list[dict]:
    """List synced DSC plus five digit ARW documents in one chat, with message IDs and filenames."""
    if not 1 <= limit <= 1000 or offset < 0:
        raise ValueError("limit must be 1..1000 and offset nonnegative")
    with closing(database()) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT id, chat_jid, filename, timestamp, file_length FROM messages WHERE chat_jid = ? AND media_type = 'document' ORDER BY timestamp DESC", (chat_jid,)).fetchall()
    return [dict(r) for r in rows if re.fullmatch(r"DSC[0-9]{5}\.ARW", r["filename"] or "", re.I)][offset:offset + limit]


@mcp.tool()
def download_media(message_id: str, chat_jid: str) -> dict:
    """Download a DSC00000.ARW document identified by chat and message ID. Never sends messages."""
    with closing(database()) as db:
        row = db.execute("SELECT filename, media_type FROM messages WHERE id = ? AND chat_jid = ?", (message_id, chat_jid)).fetchone()
    if not row or row[1] != "document" or not re.fullmatch(r"DSC[0-9]{5}\.ARW", row[0] or "", re.I):
        raise ValueError("The selected message is not a DSC plus five digits .ARW document")
    response = requests.post("http://127.0.0.1:18080/api/download", json={"message_id": message_id, "chat_jid": chat_jid}, timeout=(10, 300))
    if not response.ok:
        raise RuntimeError(f"WhatsApp bridge HTTP {response.status_code}: {response.text[:1500]}")
    result = response.json()
    return {"success": bool(result.get("success")), "file_path": result.get("path"), "message": result.get("message")}


if __name__ == "__main__":
    mcp.run(transport="stdio")
