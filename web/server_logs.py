                                                                                                       
from __future__ import annotations

import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
OUTPUT_DIR = ROOT / "output"

_LOG_MAX_BYTES = 4 * 1024 * 1024


def _tail(path: Path, lines: int = 200) -> tuple[list[str], int, bool]:
                                                                             

                                                                          
                                                                        
                                                       

                                                                           
                                                              
                                                                        
                               

                                                                            
                               

                                                                        
                                                                         
                      
       
    with path.open("rb") as f:
        f.seek(0, 2)
        size = f.tell()
        block = 65536
        chunks: list[bytes] = []
        read_bytes = 0
        newlines = 0
        ptr = size
        while ptr > 0 and newlines <= lines and read_bytes < _LOG_MAX_BYTES:
            read_size = min(block, ptr, _LOG_MAX_BYTES - read_bytes)
            if read_size <= 0:
                break
            ptr -= read_size
            f.seek(ptr)
            chunk = f.read(read_size)
            if not chunk:
                break
            chunks.append(chunk)
            read_bytes += len(chunk)
            newlines += chunk.count(b"\n")
        data = b"".join(reversed(chunks))
        out = data.decode("utf-8", "replace").splitlines()

        partial = ptr > 0
        if partial and out:
            out = out[1:]
        truncated = partial or len(out) > lines
        if len(out) > lines:
            out = out[-lines:]
        return out, read_bytes, truncated






_LOG_NAME_RE = re.compile(r"[A-Za-z0-9._-]{1,120}")




_LOG_TAIL_LINES_FRESH = 200

_LOG_TAIL_LINES_FILE = 2000





_LOGS_CLEAN_DAYS = 14


def _strip_query(raw: str) -> str:
                             

                                                                     
                                                                           
                                              
       
    return raw.partition("?")[0]






def _log_name_ok(name: str) -> bool:
                                        

                                                                      
                                                                   
                                          
       
    if not name or not _LOG_NAME_RE.fullmatch(name):
        return False

    if name.startswith("."):
        return False
    return True


def _log_path(name: str) -> Path | None:
                                                              

                                                                        
                                                                            
       
    if not _log_name_ok(name):
        return None
    path = LOG_DIR / name
    try:
        if path.resolve().parent != LOG_DIR.resolve():
            return None
    except OSError:
        return None
    return path


def _is_run_log(name: str) -> bool:
                                                              

                                                                     
                                                           
                                                                           
                                                        
                                                  
       
    return name == "ui_run.log" or (name.startswith("run_") and name.endswith(".log"))


def _is_ui_run_log(path: Path) -> bool:
                                   

                                                                     
                                                                  
                                                                
       
    return path.name.lower() == "ui_run.log"


def _log_files() -> list[dict]:
                                                                                                                  
    if not LOG_DIR.is_dir():
        return []
    out: list[dict] = []
    try:
        entries = list(LOG_DIR.iterdir())
    except OSError:
        return []
    for p in entries:
        try:
            if not p.is_file():
                continue



            if not _log_name_ok(p.name):
                continue
            st = p.stat()
        except OSError:
            continue
        out.append({"name": p.name, "size": st.st_size, "mtime": st.st_mtime})
    out.sort(key=lambda item: item["mtime"], reverse=True)
    return out


def _write_delete_audit(mode: str, deleted: list[str], errors: list[str]) -> None:
                                    

                                                                        
                                                                       
                                                            
                                                             
       
    record = {
        "ts": time.time(),
        "mode": mode,
        "deleted": deleted,
        "errors": errors,
    }
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with (OUTPUT_DIR / "logs_audit.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:

        pass
