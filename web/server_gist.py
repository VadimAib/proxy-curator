                                                                 

                                                                           
                                                                          
                                                                            
                                                                            
   
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from server_share import _share_nodes_text

from core.gist_names import DEFAULT_BASE, describe
from core.paths import ROOT

OUTPUT_DIR = ROOT / "output"
GIST_STATUS_FILE = OUTPUT_DIR / "gist_status.json"
GIST_ID_FILE = OUTPUT_DIR / "gist_id.txt"



GIST_NAME_FILE = OUTPUT_DIR / "gist_name.txt"
GIST_SCRIPT = ROOT / "upload_to_gist.py"













GIST_TIMEOUT_S = 150


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _gist_links() -> dict:
    return {
        "sub": _read_text_file(OUTPUT_DIR / "subscription_url.txt"),
        "clash": _read_text_file(OUTPUT_DIR / "subscription_url_clash.txt"),
    }


def _gist_last() -> dict:
                                                                                              
    try:
        data = json.loads(GIST_STATUS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _saved_name() -> str:
                                                                                                            
    return _read_text_file(GIST_NAME_FILE)


def _save_name(base: str) -> None:
                                                                                                                            
    try:
        if base == DEFAULT_BASE:
            GIST_NAME_FILE.unlink(missing_ok=True)
            return
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        GIST_NAME_FILE.write_text(base + "\n", encoding="utf-8")
    except OSError:


        pass


def _owner_and_id() -> tuple[str, str]:
                                                                           

                                                                             
                                                                          
                                        
       
    gist_id = _read_text_file(GIST_ID_FILE)
    last = _gist_last()
    owner = ""
    for url in (str(last.get("gist_url") or ""),
                str(last.get("subscription_url") or "")):
        m = re.search(r"gist\.github(?:usercontent)?\.com/[^/]+/"
                      r"(?P<id>[0-9a-f]+)?", url)
        if not m:
            continue
        owner = url.split(".com/", 1)[1].split("/", 1)[0]
        if not gist_id and m.group("id"):
            gist_id = m.group("id")
        if owner:
            break
    return owner, gist_id


def _url_preview(name: dict) -> dict | None:
                                                                                                                      
    owner, gist_id = _owner_and_id()
    if not owner or not gist_id:
        return None
    base = f"https://gist.githubusercontent.com/{owner}/{gist_id}/raw/"
    return {"sub": base + name["uri"], "clash": base + name["clash"]}


def _name_info(raw: str | None) -> dict:
                                                                                                                  
    name = describe(raw if raw is not None else _saved_name())
    return {"name": name, "preview": _url_preview(name)}


def _gist_info(name_raw: str | None = None) -> dict:
    info = {

        "env_token": bool(os.environ.get("GITHUB_TOKEN", "").strip()),
        "has_nodes": bool(_share_nodes_text().strip()),
        "last": _gist_last(),
        "links": _gist_links(),
    }
    info.update(_name_info(name_raw))
    return info


def _publish_gist(token: str, name_raw: str | None = None) -> dict:
                                                                   

                                                                          
                                                                         
                                                                      
                                                                        
                                                     
       
    if not GIST_SCRIPT.exists():
        return {"ok": False, "error": f"{GIST_SCRIPT.name} not found"}

    name = describe(name_raw if name_raw is not None else _saved_name())
    _save_name(name["base"])

    env = os.environ.copy()
    env["GITHUB_TOKEN"] = token
    env["GIST_NAME"] = name["base"]
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    try:
        r = subprocess.run(
            [sys.executable, "-u", str(GIST_SCRIPT)],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIST_TIMEOUT_S,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "gist upload timed out"}
    except OSError as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    output = ((r.stdout or "") + (r.stderr or "")).strip()
    result = {
        "ok": r.returncode == 0,
        "exit_code": r.returncode,
        "output": output[-4000:],
        "last": _gist_last(),
        "links": _gist_links(),
    }
    result.update(_name_info(name["base"]))
    if not result["ok"]:


        result["error"] = (
            (result["last"] or {}).get("error")
            or f"upload failed (exit code {r.returncode})"
        )
    return result
