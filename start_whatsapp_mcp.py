"""Run the local bridge and show an automatically refreshing QR pairing page."""
import io
import subprocess
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import qrcode

ROOT = Path(__file__).resolve().parent
BRIDGE = ROOT / "integrations/whatsapp-mcp/whatsapp-bridge"
PORT = 18766


def connected():
    try:
        with socket.create_connection(("127.0.0.1", 18080), timeout=1):
            return True
    except OSError:
        return False


class Pairing(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        token = BRIDGE / "store/pairing-qr.txt"
        if self.path == "/qr.png" and token.exists() and not connected():
            output = io.BytesIO()
            qrcode.make(token.read_text(encoding="utf-8")).save(output, format="PNG")
            data, mime = output.getvalue(), "image/png"
        elif self.path == "/":
            if connected():
                body = "<h1>WhatsApp connected</h1><p>You can now run the downloader. Keep the bridge running.</p>"
            elif token.exists():
                body = '<h1>Link WhatsApp</h1><p>On your phone: WhatsApp &rarr; Linked devices &rarr; Link a device.</p><img src="/qr.png" width="420"><p>Read and download tools only. The code refreshes automatically.</p>'
            else:
                body = "<h1>Connecting to WhatsApp...</h1><p>Waiting for a pairing code. Check logs/whatsapp-bridge.log if this persists.</p>"
            data = ('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="4"><title>WhatsApp MCP pairing</title><style>body{font:20px system-ui;margin:40px;max-width:800px}img{image-rendering:pixelated}</style>' + body).encode()
            mime = "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def main():
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Pairing)
    except OSError:
        server = None
    (ROOT / "logs").mkdir(exist_ok=True)
    if not connected():
        (BRIDGE / "store").mkdir(exist_ok=True)
        (BRIDGE / "store/pairing-qr.txt").unlink(missing_ok=True)
        with (ROOT / "logs/whatsapp-bridge.log").open("ab") as log:
            proc = subprocess.Popen([str(BRIDGE / "whatsapp-bridge.exe")], cwd=BRIDGE,
                stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW)
        (ROOT / "logs/whatsapp-bridge.pid").write_text(str(proc.pid))
    url = f"http://127.0.0.1:{PORT}"
    print(f"WhatsApp pairing page: {url}", flush=True)
    threading.Timer(1, lambda: webbrowser.open(url)).start()
    if server is not None:
        server.serve_forever()


if __name__ == "__main__":
    main()
