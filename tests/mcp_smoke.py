"""Verify a real STDIO handshake and filtering without accessing WhatsApp."""
import asyncio
import sqlite3
import sys
import tempfile
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import mcp_server


async def main():
    with tempfile.TemporaryDirectory() as folder:
        dbpath = Path(folder) / "messages.db"
        with sqlite3.connect(dbpath) as db:
            db.execute("CREATE TABLE messages(id TEXT, chat_jid TEXT, filename TEXT, timestamp TEXT, file_length INTEGER, media_type TEXT)")
            db.executemany("INSERT INTO messages VALUES (?, ?, ?, '', 1, 'document')", [
                ("1", "target", "DSC04726.ARW"), ("2", "target", "dsc04727.arw"),
                ("3", "target", "other.ARW"), ("4", "target", "DSC0472.ARW"),
                ("5", "other-chat", "DSC04728.ARW"), ("6", "target", "DSC04726.ARW.zip")])
        db.close()
        mcp_server.whatsapp.MESSAGES_DB_PATH = str(dbpath)
        assert len(mcp_server.list_arw_documents("target")) == 2
        try:
            mcp_server.download_media("3", "target")
            raise AssertionError("Invalid filename was accepted")
        except ValueError:
            pass
        # Recently linked chats may have numeric titles until contacts sync.
        with sqlite3.connect(dbpath) as db:
            db.execute("CREATE TABLE chats(jid TEXT, name TEXT, last_message_time TEXT)")
            db.execute("INSERT INTO chats VALUES ('target','123456','2026-09-13')")
        db.close()
        with sqlite3.connect(Path(folder) / "whatsapp.db") as contacts:
            contacts.execute("CREATE TABLE whatsmeow_contacts(their_jid TEXT, full_name TEXT)")
            contacts.execute("INSERT INTO whatsmeow_contacts VALUES ('target','Example Contact')")
        contacts.close()
        chats = mcp_server.list_chats("Example Contact")
        assert len(chats) == 1 and chats[0]["jid"] == "target" and chats[0]["name"] == "Example Contact"
    root = Path(__file__).resolve().parents[1]
    async with stdio_client(StdioServerParameters(command=sys.executable, args=[str(root / "mcp_server.py")], cwd=str(root))) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {t.name for t in (await session.list_tools()).tools}
            assert len(names) == 10 and "list_arw_documents" in names
            assert not any(name.startswith("send") for name in names)
    print("MCP handshake, read/download tool list, exact filename filtering, and chat scoping passed.")


if __name__ == "__main__":
    asyncio.run(main())
