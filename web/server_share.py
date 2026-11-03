                                                                                                       
from __future__ import annotations

import base64
import os
import secrets
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from server_logs import _strip_query
from server_config import artifact_paths

from core.paths import ROOT




OUTPUT_DIR = ROOT / "output"











SHARE_HOST = "0.0.0.0"


def _load_share_port() -> int:
                                                    

                                                                          
                                                              
       
    raw = os.environ.get("UI_SHARE_PORT", "").strip()
    if raw:
        port = int(raw)
        if not (1 <= port <= 65535):
            raise ValueError(f"UI_SHARE_PORT={port} out of range 1..65535")
        return port
    return 8766


SHARE_PORT = _load_share_port()

_share_lock = threading.Lock()
_share_server: ThreadingHTTPServer | None = None
_share_thread: threading.Thread | None = None
_share_token = ""
_share_port = SHARE_PORT


def _lan_ip() -> str:
                                                                          
                                                                                           
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def _share_nodes_text() -> str:
    try:
        return artifact_paths()["nodes"].read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _share_clash_yaml() -> str:
                                                                                                                
    text = _share_nodes_text()
    if not text.strip():
        return ""
    try:
        from tools.to_clash import render
        return render(text)
    except Exception:
        return ""


class _ShareHandler(BaseHTTPRequestHandler):
                                                                                                     

    def log_message(self, format, *args):
        pass

    def _text(self, body: str, content_type: str = "text/plain; charset=utf-8") -> None:
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _not_found(self) -> None:
        self.send_response(404)
        self.end_headers()

    def do_GET(self) -> None:
        prefix = f"/{_share_token}/"
        if not _share_token or not self.path.startswith(prefix):
            self._not_found()
            return
        name = _strip_query(self.path[len(prefix):])
        if name == "sub.txt":
            self._text(_share_nodes_text())
        elif name == "sub.b64":
            self._text(base64.b64encode(_share_nodes_text().encode("utf-8")).decode("ascii"))
        elif name == "clash.yaml":
            clash = _share_clash_yaml()
            if not clash:
                self._not_found()
            else:
                self._text(clash, "text/yaml; charset=utf-8")
        else:
            self._not_found()


def _share_info() -> dict:
                                                                                                               
    running = _share_server is not None
    base = f"http://{_lan_ip()}:{_share_port}/{_share_token}" if running and _share_token else ""
    return {
        "running": running,
        "token": _share_token,
        "port": _share_port,
        "has_nodes": bool(_share_nodes_text().strip()),
        "urls": {
            "sub": f"{base}/sub.txt",
            "b64": f"{base}/sub.b64",
            "clash": f"{base}/clash.yaml",
        } if base else {},
    }


def share_start() -> dict:
                                                                                                                              
    global _share_server, _share_thread, _share_token, _share_port
    with _share_lock:
        if _share_server is None:
            _share_token = secrets.token_hex(8)
            server = ThreadingHTTPServer((SHARE_HOST, _share_port), _ShareHandler)
            _share_port = server.server_address[1]
            _share_server = server
            _share_thread = threading.Thread(target=server.serve_forever, daemon=True)
            _share_thread.start()
    return _share_info()


def share_stop() -> dict:
                                                                            
                                                                                                                      
    global _share_server, _share_thread, _share_token
    with _share_lock:
        server = _share_server
        _share_server = None
        _share_thread = None
        _share_token = ""
    if server is not None:
        try:
            server.shutdown()
        except Exception:
            pass
        server.server_close()
    return _share_info()
