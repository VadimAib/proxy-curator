#!/usr/bin/env python3
                                                  

                                                                                 
                                                                                      

                                                                             
                                                                          
                                                                                   
                                                          

                                                                                  
                                                                                 
                                                                             

                                                                              
                                                                               
                                                                              
                                                           

                                                                            
                                                                            
                              
   

from __future__ import annotations

import json
import re
import time
import yaml
import os
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))


from core.config import Config
from core.engine.winjob import assign_to_job
from core.log import LOG
from core.paths import ROOT
from core.speed_profile import normalize_speed_profile
from core.working_lists import apply_mode, backup_previous
from core import stress_tests as st
from core.cores import (CorePlan, apply_plans, Cancelled, check_cores,
                        core_state, plan_cores)




_WEB_DIR = str(Path(__file__).resolve().parent)
if _WEB_DIR not in sys.path:
    sys.path.insert(0, _WEB_DIR)
from _progress_parser import is_progress_bar_line, update_progress_from_line

from server_advisor import (_check_everything, _run_notes_and_proposals,
    _selfcheck_state, _mark_selfcheck, _clear_selfcheck_proposals)
from server_config import (ConfigError, restore_config_text, save_config_text)
from server_gist import _gist_info, _publish_gist
from server_logs import (_LOG_TAIL_LINES_FILE, _LOG_TAIL_LINES_FRESH,
    _LOGS_CLEAN_DAYS, _log_files, _log_path,
    _is_run_log, _is_ui_run_log, _strip_query, _tail,
    _write_delete_audit)
from server_security import (_DESTRUCTIVE_ROUTES, _UI_API_TOKEN, _origin_allowed,
    _token_valid)
import server_logs
from server_share import _share_info, share_start, share_stop
from server_sources import (SourcesError, _sources_error_body,
    load_sources_data, restore_sources_text, save_sources_data)
from server_stress import _run_stress_worker, _stress_kwargs
import server_stress

HOST = "127.0.0.1"

WEB_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
LOG_DIR = ROOT / "logs"
CONFIG_PATH = ROOT / "config.yaml"

CONFIG_PREV = CONFIG_PATH.with_name(CONFIG_PATH.name + ".prev")
SOURCES_PATH = ROOT / "sources.txt"
SOURCES_PREV = SOURCES_PATH.with_name(SOURCES_PATH.name + ".prev")

GIST_SCRIPT = ROOT / "upload_to_gist.py"
GIST_STATUS_FILE = OUTPUT_DIR / "gist_status.json"



RETEST_CKS_PATH = ROOT / "temp" / "retest_cks.txt"


_CK_RE = re.compile(r"^[0-9a-f]{16}$")



_progress_state: dict = {
    "running": False,
    "phase": "",
    "phase_num": 0,
    "phase_total": 11,
    "percent": 0,
    "done": 0,
    "total": 0,
    "label": "",
}








_cores_job: dict = {
    "running": False,
    "phase": "",
    "percent": 0,
    "done": 0,
    "total": 0,
    "label": "",
    "result": None,
    "error": None,
    "cancel": threading.Event(),
}
_cores_lock = threading.Lock()




def _load_ui_port() -> int:
                                  

              
                                                                                 
                                                                       
                                                                  
                                                         

                                                                           
                                                                       
       
    raw = os.environ.get("UI_PORT", "").strip()
    if raw:
        port = int(raw)
        if not (1 <= port <= 65535):
            raise ValueError(f"UI_PORT={port} out of range 1..65535")
        return port





    try:
        cfg = Config.load(CONFIG_PATH)
        return cfg.ui.port
    except Exception:
        pass
    try:
        data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return 8765
    ui = data.get("ui") or {}
    port = ui.get("port", 8765)
    if isinstance(port, bool) or not isinstance(port, int) \
            or not (1 <= port <= 65535):
        raise ValueError(f"ui.port={port!r} in config.yaml invalid "
                         f"(need int 1..65535)")
    return port




PORT = _load_ui_port()






_run_proc: subprocess.Popen | None = None
_run_lock = threading.Lock()
_run_output: list[str] = []
_output_cond = threading.Condition()




_run_generation = 0
_run_mode: str = "replace"




_run_kind: str = "full"




_run_log_path: Path | None = None



def _backup_working_lists() -> None:
                                                                                                           
    backup_previous(OUTPUT_DIR)


def _merge_subprocess() -> int:
                                                                                                                        
    try:
        r = subprocess.run(
            [sys.executable, "-u", str(ROOT / "curate.py"),
             "--merge", "--log-file", str(_latest_log() or (LOG_DIR / "ui_run.log"))],
            cwd=str(ROOT),
            capture_output=True,
            timeout=600,
        )
    except Exception:
        return 1
    return r.returncode


def _apply_run_mode(mode: str) -> str:
                                                                                                                          
    note, _ = apply_mode(mode, OUTPUT_DIR, merge=_merge_subprocess)
    return note


def _log_path_from_cmd(cmd: list[str]) -> Path | None:
                                                                  

                                                                             
                                                                              
                                                
       
    try:
        i = cmd.index("--log-file")
    except ValueError:
        return None
    if i + 1 >= len(cmd):
        return None
    return Path(cmd[i + 1])


def _latest_log() -> Path | None:
                              

                                                                      
                                                                  
                                 
       
    if not server_logs.LOG_DIR.is_dir():
        return None
    found: list[tuple[float, Path]] = []
    for p in server_logs.LOG_DIR.glob("run_*.log"):
        try:
            found.append((p.stat().st_mtime, p))
        except OSError:
            continue
    if not found:
        return None
    found.sort(key=lambda item: item[0], reverse=True)
    return found[0][1]


def _active_run_log() -> Path | None:
                                                  

                                                                         
                                                                           
                                               
       
    with _run_lock:
        proc = _run_proc
    if proc is None or proc.poll() is not None:
        return None
    return _run_log_path


def _console_history() -> list[str]:
                                                                  

                                                                            
                                                                            
       
    with _run_lock:
        proc = _run_proc
    if proc is None or proc.poll() is not None:
        return []
    with _output_cond:
        return [l for l in _run_output[-200:] if not is_progress_bar_line(l)]


def _reader_thread(proc: subprocess.Popen) -> None:
                                                                                                                      
    global _run_output
    assert proc.stdout is not None
    for raw in iter(proc.stdout.readline, b""):
        try:
            line = raw.decode("utf-8", "replace").rstrip("\n")
        except Exception:
            line = "<decode failed>"
        update_progress_from_line(line, _progress_state)
        with _output_cond:
            _run_output.append(line)

            if len(_run_output) > 5000:
                del _run_output[:-5000]
            _output_cond.notify_all()
    proc.stdout.close()


def _spawn_run(cmd: list[str], mode: str) -> subprocess.Popen:
                                                                           

                                                            
                                                                          
                                                                       
                                                                       
                                                      

                                                                      
                                                    
       
    global _run_proc, _run_output, _run_mode, _run_generation, _run_kind
    global _run_log_path
    _run_kind = ("retest" if "--retest" in cmd
                 else "selftest" if "--selftest" in cmd else "full")
    _run_log_path = _log_path_from_cmd(cmd)
    _run_mode = mode
    _progress_state.update({
        "running": True,
        "phase": "",
        "phase_num": 0,
        "phase_total": 11,
        "percent": 0,
        "done": 0,
        "total": 0,
        "label": "",
    })
    with _output_cond:
        _run_output = []




        _run_generation += 1
        _output_cond.notify_all()
    env = os.environ.copy()




    env["CURATE_FORCE_TTY"] = "0"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    _run_proc = proc
    threading.Thread(target=_reader_thread, args=(proc,), daemon=True).start()
    threading.Thread(target=_watch_run_finished, args=(proc,), daemon=True).start()
    assign_to_job(proc)
    return proc


def _watch_run_finished(proc: subprocess.Popen | None) -> None:
                                                                  

                                                                     
                                                                           
                                                                       
                                               
       
    global _run_proc
    if proc is None:
        return
    try:
        rc = proc.wait()
    except Exception:
        return
    current = _run_proc
    with _run_lock:
        if proc is not current:
            return
        mode = _run_mode
        _run_proc = None
        _progress_state["running"] = False
    if _run_kind == "retest":


        return
    if rc != 0:



        return
    note = _apply_run_mode(mode)
    try:
        log_path = _run_log_path or _latest_log()
        if log_path is not None:
            with log_path.open("a", encoding="utf-8") as f:
                f.write(note + "\n")
    except OSError:
        pass


class Handler(BaseHTTPRequestHandler):
                                                    

    def log_message(self, format, *args):

        pass

    def _send_json(self, data, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        try:
            data = path.read_bytes()
        except OSError:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))


        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)



    def _api_forbidden(self, reason: str) -> None:
                                                                                                                        
        self._drain_body()
        self._send_json({"error": f"forbidden: {reason}"}, 403)

    def _drain_body(self) -> None:
                                                             

                                                                        
                                                                       
                                                                      
                                                                     
                                                        
           
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
        except (TypeError, ValueError):
            return
        if length <= 0:
            return
        try:
            self.connection.settimeout(0.2)
        except OSError:
            return
        try:
            self.rfile.read(min(length, self._MAX_CONTENT_LENGTH))
        except (OSError, ValueError):
            pass
        finally:
            try:
                self.connection.settimeout(None)
            except OSError:
                pass

    def _read_json_payload(self) -> dict:
                                                                

                                                                     
                                                                    
                                                                           
                                                                          
                                                                       
                                                 
           
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
        except (TypeError, ValueError):
            return {}
        if length <= 0:
            return {}
        if length > self._MAX_CONTENT_LENGTH:
            self._drain_body()
            return {}
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _api_preflight(self) -> bool:
                                                                  

                                                                               
                                                                         
                                                   

                                                                               
                                                                              
                                                                   
           
        origin = self.headers.get("Origin")
        referer = self.headers.get("Referer")
        token = self.headers.get("X-UI-Token")



        server_port = int(getattr(self.server, "server_address")[1])
        expected = f"http://{HOST}:{server_port}"





        if not _origin_allowed(origin, referer, expected):
            self._api_forbidden(f"origin/host not allowed (expected {expected})")
            return False
        if self.command == "POST" and not origin:
            self._api_forbidden("missing Origin header on POST")
            return False


        if token and self.path != "/api/token" and not _token_valid(token):
            self._api_forbidden("invalid X-UI-Token")
            return False



        if self.path in _DESTRUCTIVE_ROUTES and not _token_valid(token):
            self._api_forbidden("X-UI-Token required for a destructive route")
            return False
        return True

    def do_GET(self) -> None:


        path, _, query = self.path.partition("?")
        self.path = path



        params = parse_qs(query, keep_blank_values=True)
        if self.path.startswith("/api/") and not self._api_preflight():
            return
        if self.path == "/":
            self._send_file(WEB_DIR / "index.html", "text/html; charset=utf-8")
        elif self.path == "/qrcode.js":
            self._send_file(WEB_DIR / "qrcode.js", "application/javascript; charset=utf-8")
        elif self.path == "/guide.js":

            self._send_file(WEB_DIR / "guide.js", "application/javascript; charset=utf-8")
        elif self.path == "/logs.js":

            self._send_file(WEB_DIR / "logs.js", "application/javascript; charset=utf-8")
        elif self.path == "/guide.json":


            self._send_file(WEB_DIR / "guide" / "guide.json", "application/json; charset=utf-8")
        elif self.path == "/api/share/status":
            self._send_json(_share_info())
        elif self.path == "/api/gist/status":
            self._send_json(_gist_info())
        elif self.path == "/api/cores":

            self._send_cores_state()
        elif self.path == "/api/cores/status":

            self._send_cores_status()
        elif self.path == "/api/token":



            self._send_json({"token": _UI_API_TOKEN})
        elif self.path == "/api/summary":
            p = OUTPUT_DIR / "summary.json"
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}
            self._send_json(data)
        elif self.path == "/api/tune/last":



            self._send_json(_selfcheck_state())
        elif self.path == "/api/tune/plan":




            try:
                self._send_json({"ok": True, **_run_notes_and_proposals()})
            except Exception as exc:


                LOG(f"[tune/plan] {type(exc).__name__}: {exc}")
                self._send_json({"ok": False,
                                 "error": f"{type(exc).__name__}: {exc}"}, 500)
        elif self.path == "/api/logs":

            files = _log_files()
            self._send_json({
                "dir": str(LOG_DIR),
                "files": files,
                "count": len(files),
                "total_size": sum(int(f["size"]) for f in files),


                "clean_days": _LOGS_CLEAN_DAYS,
            })
        elif self.path == "/api/log":

            if "file" in params:
                name = params["file"][0]
                if not name:



                    self._send_json(
                        {"ok": False, "code": "bad_request",
                         "error": "empty log file name",
                         "detail": "file="}, 400)
                    return
                p = _log_path(name)
                if p is None:
                    self._send_json(
                        {"ok": False, "code": "unknown_log",
                         "error": "unknown log file",
                         "detail": name}, 400)
                    return
                if not p.is_file():

                    self._send_json(
                        {"ok": False, "code": "not_found",
                         "error": "log file not found",
                         "detail": name}, 404)
                    return
                tail_lines = _LOG_TAIL_LINES_FILE
            else:


                p = _active_run_log() or _latest_log()
                tail_lines = _LOG_TAIL_LINES_FRESH



            try:
                lines, _tail_bytes, truncated = (
                    _tail(p, tail_lines) if p else ([], 0, False))
            except OSError as exc:


                self._send_json(
                    {"ok": False, "code": "io_error",
                     "error": "cannot read log file",
                     "detail": f"{type(exc).__name__}: {exc}"}, 500)
                return


            meta: dict = {"file": None, "mtime": None, "size": 0, "truncated": truncated}
            if p is not None:
                meta["file"] = p.name
                try:
                    st = p.stat()
                    meta["mtime"] = st.st_mtime
                    meta["size"] = st.st_size
                except OSError:
                    pass
            self._send_json({
                "lines": [l for l in lines if not is_progress_bar_line(l)],
                **meta,
            })
        elif self.path == "/api/nodes":
            self._handle_api_nodes()
        elif self.path == "/api/nodes/delete":


            self._send_json({"ok": False, "error": "use DELETE"}, 405)
        elif self.path == "/api/nodes/test":


            self._send_json({"ok": False, "error": "use POST"}, 405)
        elif self.path == "/api/status":
            with _run_lock:
                running = _run_proc is not None and _run_proc.poll() is None
            self._send_json({"running": running})
        elif self.path == "/api/progress":
            with _run_lock:
                state = dict(_progress_state)
                state["running"] = _run_proc is not None and _run_proc.poll() is None
            self._send_json(state)
        elif self.path == "/api/config":
            try:
                text = CONFIG_PATH.read_text(encoding="utf-8")
            except OSError:
                text = ""
            self._send_json({"config": text, "has_prev": CONFIG_PREV.exists()})
        elif self.path == "/api/sources":
            try:
                self._send_json(load_sources_data())
            except SourcesError as e:
                self._send_json(_sources_error_body(e), 400)
            except OSError as e:
                self._send_json({"error": str(e)}, 500)
        elif self.path == "/api/health":
            self._send_json({"ok": True, "version": "1.0"})
        elif self.path == "/api/log-stream":

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()


            with _output_cond:
                pos = len(_run_output)
                gen = _run_generation





            for line in _console_history():
                try:
                    self.wfile.write(f"data: {line}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    return


            try:
                while True:
                    with _output_cond:


                        if _run_generation != gen:
                            gen = _run_generation
                            pos = 0
                        _output_cond.wait(timeout=3)
                        if pos < len(_run_output):
                            new_lines = [l for l in _run_output[pos:]
                                         if not is_progress_bar_line(l)]
                            pos = len(_run_output)
                        else:
                            new_lines = []
                    for line in new_lines:
                        try:
                            self.wfile.write(f"data: {line}\n\n".encode("utf-8"))
                            self.wfile.flush()
                        except (BrokenPipeError, ConnectionResetError):
                            return

                    with _run_lock:
                        proc = _run_proc
                    if proc is not None and proc.poll() is not None:

                        with _output_cond:
                            if pos < len(_run_output):
                                new_lines = _run_output[pos:]
                                for line in new_lines:
                                    try:
                                        self.wfile.write(f"data: {line}\n\n".encode("utf-8"))
                                        self.wfile.flush()
                                    except (BrokenPipeError, ConnectionResetError):
                                        return
                        break
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self.send_response(404)
            self.end_headers()



    def _read_working_nodes_json(self) -> list:
                                                                                                         
        try:
            path = OUTPUT_DIR / "working_nodes.json"
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    def _read_working_nodes_txt(self) -> list:
                                                                                        
        try:
            p = OUTPUT_DIR / "working_nodes.txt"
            text = p.read_text(encoding="utf-8", errors="replace")
            return [l.strip() for l in text.splitlines() if l.strip()]
        except OSError:
            return []

    def _write_working_nodes_txt(self, nodes: list) -> None:
                                                                                       
        p = OUTPUT_DIR / "working_nodes.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(nodes) + ("\n" if nodes else ""), encoding="utf-8")

    def _handle_api_nodes(self) -> None:
                                                                             

                                                                       
                                                                         
           
        nodes_txt = self._read_working_nodes_txt()
        nodes_json = self._read_working_nodes_json()

        out = []
        for i, uri in enumerate(nodes_txt):
            item = {"uri": uri, "ck": "", "dead": False}
            if i < len(nodes_json) and isinstance(nodes_json[i], dict):
                entry = nodes_json[i]
                item["ck"] = entry.get("ck", "")
                item["protocol"] = entry.get("protocol", "")
                item["host"] = entry.get("host", "")
                item["port"] = entry.get("port", 0)
                item["name"] = entry.get("name", "")
                item["ms"] = entry.get("ms", 0)
                item["speed_mbps"] = entry.get("speed_mbps")
                item["speed_quick_mbps"] = entry.get("speed_quick_mbps")
                item["net"] = entry.get("net")
                item["security"] = entry.get("security")
                item["sni"] = entry.get("sni")
                item["fp"] = entry.get("fp")
                item["flow"] = entry.get("flow")
                item["exit_country"] = entry.get("exit_country")
            out.append(item)

        self._send_json({"nodes": out, "count": len(out)})

    def _handle_api_nodes_delete(self, payload: dict | None = None) -> None:
                                                                              

                                                                           
                                                                              
                                                                      
           
        payload = payload or {}
        cks = payload.get("cks", [])
        if not isinstance(cks, list):
            self._send_json({"ok": False, "error": "cks must be a list"}, 400)
            return

        nodes_txt = self._read_working_nodes_txt()
        nodes_json = self._read_working_nodes_json()

        cks_set = set(cks)
        kept_txt = []
        kept_json = []
        removed = 0

        for idx, uri in enumerate(nodes_txt):



            entry = nodes_json[idx] if idx < len(nodes_json) else None
            ck = entry.get("ck", "") if isinstance(entry, dict) else ""
            if ck in cks_set:
                removed += 1
            else:
                kept_txt.append(uri)

        for entry in nodes_json:
            if isinstance(entry, dict) and entry.get("ck") in cks_set:
                continue
            kept_json.append(entry)

        self._write_working_nodes_txt(kept_txt)

        try:
            path = OUTPUT_DIR / "working_nodes.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(kept_json, f, ensure_ascii=False, separators=(",", ":"))
        except OSError:
            pass

        self._send_json({"ok": True, "removed": removed, "kept": len(kept_txt)})

    def _handle_api_nodes_test(self, payload: dict | None = None) -> None:
                                                                        

                                                                           
                                                                           
                                                                            
                                                                       
                                                                   
                                                                               

                                                                           
                                               
           
        payload = payload or {}
        cks = payload.get("cks", [])
        if not isinstance(cks, list) or not cks:
            self._send_json({"ok": False, "error": "cks must be a non-empty list"},
                            400)
            return
        clean = [ck for ck in cks if isinstance(ck, str) and _CK_RE.match(ck)]
        if not clean:
            self._send_json({"ok": False, "error": "no valid ck in cks"}, 400)
            return
        with _run_lock:
            if _run_proc is not None and _run_proc.poll() is None:
                self._send_json({"ok": False, "error": "already running"}, 409)
                return
            try:
                RETEST_CKS_PATH.parent.mkdir(parents=True, exist_ok=True)
                RETEST_CKS_PATH.write_text("\n".join(clean) + "\n",
                                           encoding="utf-8")
            except OSError as exc:
                self._send_json(
                    {"ok": False,
                     "error": f"cannot write retest selection: {exc}"}, 500)
                return
            cmd = [
                sys.executable, "-u", str(ROOT / "curate.py"),
                "--log-file", str(LOG_DIR / "ui_run.log"),
                "--retest", str(RETEST_CKS_PATH),
            ]



            cmd.extend(["--speed-profile",
                        normalize_speed_profile(payload.get("profile")) or "auto"])
            _spawn_run(cmd, "none")
        self._send_json({"ok": True, "started": True, "tested": len(clean)})



    _MAX_CONTENT_LENGTH = 1_048_576
    _MAX_STRESS_DURATION_S = 60.0
    _MAX_STRESS_BYTES_PER_FILE = 100_000_000

    def do_POST(self) -> None:
        global _run_proc, _run_output, _run_mode, _run_generation

        self.path = _strip_query(self.path)
        if not self._api_preflight():
            return
        length = int(self.headers.get("Content-Length", 0))
        if length > self._MAX_CONTENT_LENGTH:



            self._drain_body()
            self._send_json(
                {"ok": False, "error": f"request body too large (max {self._MAX_CONTENT_LENGTH} bytes)"},
                413,
            )
            return
        body = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}

        if self.path == "/api/tune/cancel":



            server_stress._stress_cancel.set()
            self._send_json({"ok": True, "cancelled": True})
            return

        if self.path.startswith("/api/stress/"):
            kind = self.path.rsplit("/", 1)[-1]
            if kind not in st.KWARGS:
                self._send_json({"ok": False, "error": "unknown stress kind: " + repr(kind)}, 400)
                return

            kwargs, ceiling_error = _stress_kwargs(
                kind, payload,
                max_duration_s=self._MAX_STRESS_DURATION_S,
                max_bytes=self._MAX_STRESS_BYTES_PER_FILE)
            if ceiling_error:
                self._send_json({"ok": False, "error": ceiling_error}, 400)
                return


            server_stress._stress_cancel.clear()
            threading.Thread(target=_run_stress_worker, args=(kind, kwargs), daemon=True).start()
            with server_stress._stress_cond:
                deadline = time.monotonic() + 300.0
                while server_stress._stress_result is None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        self._send_json({"ok": False, "error": "stress test timed out"}, 504)
                        return
                    server_stress._stress_cond.wait(remaining)
                result = server_stress._stress_result
                if not isinstance(result, dict):
                    result = result._asdict()



            self._send_json({"ok": True, "result": result,
                             **_run_notes_and_proposals()})
            return

        if self.path == "/api/tune/check":



            params: dict = {}
            for kind in ("cpu", "network", "disk"):
                kwargs, ceiling_error = _stress_kwargs(
                    kind, payload,
                    max_duration_s=self._MAX_STRESS_DURATION_S,
                    max_bytes=self._MAX_STRESS_BYTES_PER_FILE)
                if ceiling_error:
                    self._send_json({"ok": False, "error": ceiling_error}, 400)
                    return
                params[kind] = kwargs
            server_stress._stress_cancel.clear()
            try:
                result = _check_everything(params, cancel=_cancel_check)
            except Exception as exc:
                self._send_json(
                    {"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 500)
                return
            if result.get("cancelled"):


                self._send_json({"ok": True, "cancelled": True})
                return

            marker = _mark_selfcheck(result)
            result.setdefault("measurements", {})["measured_at"] = \
                marker["measured_at"]
            self._send_json({"ok": True, **result})
            return

        if self.path == "/api/logs/delete":

            name = str(payload.get("name") or "")
            older_than = payload.get("older_than_days")
            with _run_lock:
                running = _run_proc is not None and _run_proc.poll() is None
            deleted: list[str] = []
            errors: list[str] = []
            if name:
                path = _log_path(name)
                if path is None:
                    self._send_json(
                        {"ok": False, "code": "unknown_log",
                         "error": "unknown log file",
                         "detail": name}, 400)
                    return


                if running and _is_ui_run_log(path):
                    self._send_json(
                        {"ok": False, "code": "run_in_progress",
                         "error": "run in progress",
                         "detail": path.name}, 409)
                    return
                try:
                    path.unlink()
                    deleted.append(path.name)
                except OSError as exc:
                    errors.append(f"{path.name}: {exc}")
                _write_delete_audit("name", deleted, errors)
            elif "older_than_days" in payload:





                if isinstance(older_than, bool) or not isinstance(older_than, (int, float)):
                    self._send_json(
                        {"ok": False, "code": "bad_request",
                         "error": "older_than_days must be a number",
                         "detail": repr(older_than)}, 400)
                    return
                days = float(older_than)
                if days < 1:
                    self._send_json(
                        {"ok": False, "code": "bad_request",
                         "error": "older_than_days must be 1 or more",
                         "detail": repr(older_than)}, 400)
                    return
                if not payload.get("confirm"):
                    self._send_json(
                        {"ok": False, "code": "confirm_required",
                         "error": "confirmation required"}, 400)
                    return
                cutoff = time.time() - days * 86400
                for item in _log_files():
                    fname = str(item["name"])



                    if not _is_run_log(fname):
                        continue
                    path = _log_path(fname)
                    if path is None:
                        continue
                    if running and _is_ui_run_log(path):
                        continue
                    try:
                        if path.stat().st_mtime < cutoff:
                            path.unlink()
                            deleted.append(path.name)
                    except OSError as exc:
                        errors.append(f"{path.name}: {exc}")
                _write_delete_audit(f"older_than_{days:g}d", deleted, errors)
            else:
                self._send_json(
                    {"ok": False, "code": "bad_request",
                     "error": "name or older_than_days required"}, 400)
                return



            self._send_json({"ok": not errors, "deleted": deleted, "errors": errors})
            return

        if self.path == "/api/logs/open-folder":

            try:
                LOG_DIR.mkdir(parents=True, exist_ok=True)
                os.startfile(str(LOG_DIR))
            except (AttributeError, OSError) as exc:
                self._send_json({"ok": False, "error": str(exc)}, 500)
                return
            self._send_json({"ok": True, "dir": str(LOG_DIR)})
            return

        if self.path == "/api/cores/check":


            if self._cores_in_progress():
                self._send_json({"ok": False, "error": "a cores job is already running"}, 409)
                return
            try:
                plans = check_cores(Config.load(CONFIG_PATH), force=False)
            except Exception as exc:
                self._send_json(
                    {"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 500)
                return
            self._send_json({
                "ok": True,
                "up_to_date": not plans,
                "message": ("All cores up to date" if not plans
                            else f"{len(plans)} core(s) need update"),
                "plans": [{"name": p.name, "current": p.label,
                           "latest": p.version, "size": p.size} for p in plans],
            })
            return

        if self.path == "/api/cores/update":



            if self._cores_in_progress():
                self._send_json({"ok": False, "error": "a cores job is already running"}, 409)
                return
            raw = payload.get("plans")
            names = [str(p.get("name") or "") for p in raw
                     if isinstance(p, dict)] if isinstance(raw, list) else None
            try:
                self._start_cores_job(names)
            except Exception as exc:
                self._send_json(
                    {"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 500)
                return
            self._send_json({"ok": True, "started": True})
            return

        if self.path == "/api/cores/cancel":


            with _cores_lock:
                _cores_job["cancel"].set()
            self._send_json({"ok": True})
            return

        if self.path == "/api/run":
            with _run_lock:
                if _run_proc is not None and _run_proc.poll() is None:
                    self._send_json({"error": "already running"}, 409)
                    return


                profile = normalize_speed_profile(payload.get("profile")) or "auto"
                only = payload.get("only", "")
                selftest = bool(payload.get("selftest"))
                mode = payload.get("mode") or "replace"
                if mode not in ("replace", "append", "keep"):
                    mode = "replace"
                if selftest:


                    _run_mode = "none"
                else:
                    _run_mode = mode
                    _backup_working_lists()
                cmd = [
                    sys.executable, "-u", str(ROOT / "curate.py"),
                    "--log-file", str(LOG_DIR / "ui_run.log"),
                ]
                if selftest:
                    cmd.append("--selftest")
                else:
                    cmd.extend(["--speed-profile", profile])
                    if only:
                        cmd.extend(["--only", only])
                proc = _spawn_run(cmd, _run_mode)
            self._send_json({"pid": proc.pid})
        elif self.path == "/api/stop":
            with _run_lock:
                if _run_proc is not None and _run_proc.poll() is None:
                    try:
                        _run_proc.terminate()
                        _run_proc.wait(timeout=10)
                    except Exception:
                        try:
                            _run_proc.kill()
                        except Exception:
                            pass
                    _run_proc = None
                _progress_state["running"] = False
            self._send_json({"stopped": True})
        elif self.path == "/api/shutdown":







            with _run_lock:
                if _run_proc is not None and _run_proc.poll() is None:
                    try:
                        _run_proc.terminate()
                        _run_proc.wait(timeout=10)
                    except Exception:
                        try:
                            _run_proc.kill()
                        except Exception:
                            pass
                _run_proc = None
                _progress_state["running"] = False
            self._send_json({"stopping": True})
            share_stop()
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        elif self.path == "/api/config":
            try:
                save_config_text(str(payload.get("config", "")))
            except ConfigError as e:
                self._send_json({"error": str(e)}, 400)
                return
            except OSError as e:
                self._send_json({"error": str(e)}, 500)
                return


            _clear_selfcheck_proposals()
            self._send_json({"saved": True})
        elif self.path == "/api/config/restore":
            try:
                text = restore_config_text()
            except ConfigError as e:
                self._send_json({"error": str(e)}, 400)
                return
            except OSError as e:
                self._send_json({"error": str(e)}, 500)
                return
            self._send_json({"restored": True, "config": text})
        elif self.path == "/api/sources":
            data = payload
            if not isinstance(data, dict) or "sections" not in data:
                self._send_json({"error": "expected JSON with 'sections'", "code": "bad_request"}, 400)
                return
            try:
                save_sources_data(data)
            except SourcesError as e:
                self._send_json(_sources_error_body(e), 400)
                return
            except OSError as e:
                self._send_json({"error": str(e)}, 500)
                return
            self._send_json({"saved": True})
        elif self.path == "/api/sources/restore":
            try:
                restore_sources_text()
            except SourcesError as e:
                self._send_json(_sources_error_body(e), 400)
                return
            except OSError as e:
                self._send_json({"error": str(e)}, 500)
                return
            self._send_json({"restored": True})
        elif self.path == "/api/gist/publish":
            with _run_lock:
                running = _run_proc is not None and _run_proc.poll() is None
            if running:
                self._send_json(
                    {"ok": False, "error": "run in progress; publish after it finishes"},
                    409,
                )
                return
            token = str(payload.get("token", "")).strip()
            if not token:
                token = os.environ.get("GITHUB_TOKEN", "").strip()
            if not token:
                self._send_json({
                    "ok": False,
                    "error": ("GITHUB_TOKEN is not set. Paste a token with the "
                              "gist scope or set the environment variable."),
                }, 400)
                return
            if len(token) > 512:
                self._send_json(
                    {"ok": False, "error": "token is too long"}, 400)
                return
            self._send_json(_publish_gist(token))
        elif self.path == "/api/share/start":
            try:
                self._send_json(share_start())
            except OSError as e:
                self._send_json({"error": str(e)}, 500)
        elif self.path == "/api/share/stop":
            self._send_json(share_stop())
        elif self.path == "/api/nodes/delete":
            self._handle_api_nodes_delete(payload)
        elif self.path == "/api/nodes/test":
            self._handle_api_nodes_test(payload)
        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self) -> None:
        self.path = _strip_query(self.path)
        if not self._api_preflight():
            return
        if self.path == "/api/nodes/delete":


            self._handle_api_nodes_delete(self._read_json_payload())
        else:
            self.send_response(404)
            self.end_headers()



    def _cores_job_snapshot(self) -> dict:
                                                                                                                       
        with _cores_lock:
            return {
                "running": bool(_cores_job["running"]),
                "phase": _cores_job["phase"],
                "percent": _cores_job["percent"],
                "done": _cores_job["done"],
                "total": _cores_job["total"],
                "label": _cores_job["label"],
                "result": _cores_job["result"],
                "error": _cores_job["error"],
            }

    def _send_cores_state(self) -> None:
                                                                                                     
        try:
            cores = core_state(Config.load(CONFIG_PATH))
        except Exception as exc:
            self._send_json({"cores": [], "job": self._cores_job_snapshot(),
                             "error": f"{type(exc).__name__}: {exc}"})
            return
        self._send_json({"cores": cores, "job": self._cores_job_snapshot()})

    def _send_cores_status(self) -> None:
                                                                                        
        self._send_json(self._cores_job_snapshot())

    def _cores_in_progress(self) -> bool:
                                                                                                                     
        with _run_lock:
            run_busy = _run_proc is not None and _run_proc.poll() is None
        with _cores_lock:
            cores_busy = bool(_cores_job["running"])
        return run_busy or cores_busy

    def _cores_worker(self, cfg: Config, plans: list[CorePlan]) -> None:
                                                                              

                                                                             
                                                                            
                                                                       
           
        del cfg
        try:
            def progress(written: int, total: int) -> None:
                with _cores_lock:
                    _cores_job["done"] = written
                    _cores_job["total"] = total
                    _cores_job["percent"] = int(written * 100 / total) if total else 0
                    _cores_job["phase"] = "downloading"


                    if _cores_job["label"] == "" and plans:
                        _cores_job["label"] = plans[0].name

            def cancelled() -> bool:
                with _cores_lock:
                    return _cores_job["cancel"].is_set()

            result = apply_plans(plans, progress=progress, cancel=cancelled)
            with _cores_lock:
                _cores_job["result"] = result
                _cores_job["phase"] = "done"
                _cores_job["percent"] = 100
        except Cancelled as exc:
            with _cores_lock:
                _cores_job["error"] = f"cancelled: {exc}"
                _cores_job["phase"] = "cancelled"
        except Exception as exc:
            with _cores_lock:
                _cores_job["error"] = f"{type(exc).__name__}: {exc}"
                _cores_job["phase"] = "error"
        finally:
            with _cores_lock:
                _cores_job["running"] = False

    def _start_cores_job(self, names: list[str] | None = None) -> None:
                                                                

                                                                          
                                                                        
                                                                       
                                                             
           
        cfg = Config.load(CONFIG_PATH)
        plans = plan_cores(cfg, force=False)
        if names:
            wanted = {n for n in names if n}
            plans = [p for p in plans if p.name in wanted]
        with _cores_lock:
            if _cores_job["running"]:
                raise RuntimeError("a cores job is already running")
            _cores_job.update({
                "running": True,
                "phase": "updating",
                "percent": 0,
                "done": 0,
                "total": len(plans),
                "label": "",
                "result": None,
                "error": None,
            })
            _cores_job["cancel"].clear()
        if not plans:
            with _cores_lock:
                _cores_job["result"] = []
                _cores_job["phase"] = "done"
                _cores_job["percent"] = 100
                _cores_job["running"] = False
            return
        threading.Thread(target=self._cores_worker, args=(cfg, plans),
                         daemon=True).start()


def main() -> None:



    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"UI server: http://{HOST}:{PORT}")
    if "--share" in sys.argv[1:]:
        try:
            info = share_start()
            print(f"LAN share: {info['urls'].get('sub', '') or '(no links)'}")
        except OSError as e:
            print(f"LAN share not started: {e}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        share_stop()
        server.server_close()


if __name__ == "__main__":
    main()

