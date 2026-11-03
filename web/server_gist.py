                                                                                                               
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from server_share import _share_nodes_text

from core.paths import ROOT

OUTPUT_DIR = ROOT / "output"
GIST_STATUS_FILE = OUTPUT_DIR / "gist_status.json"
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


def _gist_info() -> dict:
    return {

        "env_token": bool(os.environ.get("GITHUB_TOKEN", "").strip()),
        "has_nodes": bool(_share_nodes_text().strip()),
        "last": _gist_last(),
        "links": _gist_links(),
    }


def _publish_gist(token: str) -> dict:
                                                                             

                                                                          
                                                                         
                                                                      
               
    if not GIST_SCRIPT.exists():
        return {"ok": False, "error": f"{GIST_SCRIPT.name} not found"}

    env = os.environ.copy()
    env["GITHUB_TOKEN"] = token
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
    if not result["ok"]:


        result["error"] = (
            (result["last"] or {}).get("error")
            or f"upload failed (exit code {r.returncode})"
        )
    return result
