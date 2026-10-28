"""Startet den Rechnungs-Extraktor in einem eigenen Fenster (Doppelklick-App)."""
import socket
import threading

import webview

from app import app


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


if __name__ == "__main__":
    port = free_port()
    threading.Thread(target=lambda: app.run(port=port, threaded=True), daemon=True).start()
    webview.create_window("Rechnungs-Extraktor", f"http://127.0.0.1:{port}", width=1100, height=800)
    webview.start()
