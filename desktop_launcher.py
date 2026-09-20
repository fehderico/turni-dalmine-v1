from __future__ import annotations

import os
from pathlib import Path
import socket
import sys
import threading
import time
import webbrowser

from streamlit.web import cli as streamlit_cli


HOST = "127.0.0.1"
PORT = 8501
URL = f"http://{HOST}:{PORT}"


def resource_path(filename: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / filename


def server_is_running() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=0.25):
            return True
    except OSError:
        return False


def open_when_ready() -> None:
    for _ in range(120):
        if server_is_running():
            webbrowser.open(URL, new=1)
            return
        time.sleep(0.25)


def main() -> None:
    if server_is_running():
        webbrowser.open(URL, new=1)
        return

    app_path = resource_path("app.py")
    if not app_path.exists():
        raise FileNotFoundError(f"File applicazione non trovato: {app_path}")

    os.environ["TURNI_DESKTOP_MODE"] = "1"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    threading.Thread(target=open_when_ready, daemon=True).start()
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--global.developmentMode=false",
        "--server.headless=true",
        f"--server.address={HOST}",
        f"--server.port={PORT}",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    raise SystemExit(streamlit_cli.main())


if __name__ == "__main__":
    main()
