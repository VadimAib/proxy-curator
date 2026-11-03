#!/usr/bin/env python3
                                                                                

                        

                                                                    
                               
                                                                        
                                                                   

                                                                      
                                                               
                                                              

                                                                         
                                                                     
                                                                      
                                                                       
                                                                           
                                                                            

                                                                           
                                                                      
                                                               
                                                                          
                                 
   
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import yaml











from core.config import Config
from core.log import LOG
from core.paths import ROOT, rp
from core.utils import first_line

OUT_DIR = ROOT / "output"


def _configured_nodes_file() -> Path:
                                                              

                                                                       
                                                                    
                                                                           
                                                      
                                                                          
                         
       
    try:
        return Path(rp(Config.load(ROOT / "config.yaml").output.working_nodes))
    except Exception:
        return OUT_DIR / "working_nodes.txt"


GIST_ID_FILE = OUT_DIR / "gist_id.txt"
NODES_FILE = _configured_nodes_file()
URL_FILE = OUT_DIR / "subscription_url.txt"
CLASH_URL_FILE = OUT_DIR / "subscription_url_clash.txt"
STATUS_FILE = OUT_DIR / "gist_status.json"
NODES_NAME = "working_nodes.txt"


CLASH_NAME = "working_nodes.yaml"




STALE_NAMES = ("working_nodes_clash.yaml",)
API = "https://api.github.com"



RETRY_ATTEMPTS = 3
RETRY_BACKOFF_S = 1.0


def _write_status(ok: bool, **fields) -> None:
                                                                        

                                                                           
                                                                         
                                                                          
                                                       
       
    payload = {
        "ok": ok,
        "time": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    payload.update(fields)
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        tmp = STATUS_FILE.with_name(STATUS_FILE.name + ".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        tmp.replace(STATUS_FILE)
    except OSError as e:
        LOG(f"[gist] WARNING: failed to write status file: {first_line(e)}")


def prune_stale(token: str, gist_id: str, present: dict,
                names: tuple[str, ...] = STALE_NAMES) -> list[str]:
                                                              

                                                                  
                                                                         
                                                                   
       
    gone = [n for n in names if n in present]
    if not gone:
        return []
    payload = {"files": {n: None for n in gone}}
    try:
        github_api_request(f"{API}/gists/{gist_id}", token, payload, "PATCH")
        return gone
    except (HTTPError, URLError, TimeoutError, OSError) as e:
        LOG(f"[gist] WARNING: failed to delete stale files "
            f"({', '.join(gone)}): {first_line(e)}")
        return []


def github_api_request(url: str, token: str, payload: dict | None = None, method: str = "GET") -> dict:
                                                    
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(url, data=data, method=method, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "curate-uploader",
    })
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _clash_yaml(nodes_text: str) -> str:
                                                                           

                                                                         
                                                                        
                                                                       
       
    try:
        from tools.to_clash import render
    except Exception as e:
        LOG(f"[gist] WARNING: failed to import tools/to_clash.py: "
            f"{first_line(e)}")
        return ""
    try:
        return render(nodes_text)
    except Exception as e:
        LOG(f"[gist] WARNING: Clash config not built ({first_line(e)}); "
            "only the URI subscription is published")
        return ""


def build_payload(content: str, clash: str = "") -> dict:
                                                                                                       
    files = {NODES_NAME: {"content": content}}
    if clash:
        files[CLASH_NAME] = {"content": clash}
    return {
        "description": "VPN working nodes (auto-updated by curator)",
        "public": False,
        "files": files,
    }


def get_gist_id() -> str | None:
                                                                                    
    if GIST_ID_FILE.exists():
        gist_id = GIST_ID_FILE.read_text(encoding="utf-8").strip()
        return gist_id if gist_id else None
    return None


def save_gist_id(gist_id: str) -> None:
                                                                          
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    GIST_ID_FILE.write_text(gist_id + "\n", encoding="utf-8")


def _retryable_http(code: int) -> bool:
                                                                                                     
    return code == 429 or 500 <= code < 600


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        msg = "GITHUB_TOKEN environment variable is not set."
        LOG(f"ERROR: {msg}")
        _write_status(False, error=msg)
        return 1

    if not NODES_FILE.exists():
        msg = f"{NODES_FILE} not found. Run run_curate.bat first."
        LOG(f"ERROR: {msg}")
        _write_status(False, error=msg)
        return 1

    content = NODES_FILE.read_text(encoding="utf-8")
    if not content.strip():
        msg = "working_nodes.txt is empty. Nothing to upload."
        LOG(f"ERROR: {msg}")
        _write_status(False, error=msg)
        return 1

    nodes_count = sum(1 for line in content.splitlines() if line.strip())
    LOG(f"Preparing to upload {nodes_count} node(s)...")

    clash = _clash_yaml(content)
    if clash:


        n_clash = len(yaml.safe_load(clash).get("proxies", []))
        LOG(f"Clash config ready: {n_clash} proxies")
    payload = build_payload(content, clash)
    gist_id = get_gist_id()
    res = None

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        is_update = bool(gist_id)
        endpoint = f"{API}/gists/{gist_id}" if is_update else f"{API}/gists"
        method = "PATCH" if is_update else "POST"

        try:
            if is_update:
                LOG(f"Updating existing secret gist ({gist_id})...")
            else:
                LOG("Creating new secret gist...")

            res = github_api_request(endpoint, token, payload, method)

            if not is_update:
                gist_id = res.get("id")
                if not gist_id:
                    msg = "Gist created but no ID returned."
                    LOG(f"ERROR: {msg}")
                    _write_status(False, nodes=nodes_count, error=msg)
                    return 1
                save_gist_id(gist_id)
                LOG(f"Created new gist: {gist_id}")
            break

        except HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")[:500]
            except Exception as berr:
                LOG(f"[gist] failed to read response body: "
                    f"{first_line(berr)}")

            if e.code == 404 and is_update and attempt < RETRY_ATTEMPTS:
                LOG("Gist not found (probably deleted). Creating a new one...")
                GIST_ID_FILE.unlink(missing_ok=True)
                gist_id = None
                continue

            if _retryable_http(e.code) and attempt < RETRY_ATTEMPTS:
                LOG(f"[gist] WARNING: HTTP {e.code}; retrying "
                    f"({attempt}/{RETRY_ATTEMPTS - 1})...")
                time.sleep(RETRY_BACKOFF_S * attempt)
                continue

            LOG(f"ERROR: GitHub API returned HTTP {e.code} {e.reason}")
            if body:
                LOG(f"Response body: {body}")
            _write_status(False, nodes=nodes_count,
                          error=f"HTTP {e.code} {e.reason}",
                          response=body[:500])
            return 1

        except (URLError, TimeoutError, OSError) as e:
            if attempt < RETRY_ATTEMPTS:
                LOG(f"[gist] WARNING: network error; retrying "
                    f"({attempt}/{RETRY_ATTEMPTS - 1}): {first_line(e)}")
                time.sleep(RETRY_BACKOFF_S * attempt)
                continue
            LOG(f"ERROR: Network error during API request: {e}")
            _write_status(False, nodes=nodes_count, error=first_line(e))
            return 1

    if not res or "files" not in res or NODES_NAME not in res["files"]:
        msg = "Unexpected API response structure."
        LOG(f"ERROR: {msg}")
        if res:
            LOG(json.dumps(res, indent=2, ensure_ascii=False)[:500])
        _write_status(False, nodes=nodes_count, error=msg)
        return 1


    owner = res.get("owner", {}).get("login", "")
    gist_id = res.get("id", "")
    html_url = res.get("html_url", "")
    files = res.get("files") or {}

    base = f"https://gist.githubusercontent.com/{owner}/{gist_id}/raw/"
    if owner and gist_id:

        subscription_url = base + NODES_NAME
    else:

        subscription_url = res["files"][NODES_NAME].get("raw_url", "")





    clash_published = bool(clash) and CLASH_NAME in files
    if clash_published and owner and gist_id:
        clash_url = base + CLASH_NAME
    elif clash_published:
        clash_url = (files.get(CLASH_NAME) or {}).get("raw_url", "")
    else:
        clash_url = ""

    if clash and not clash_published:
        LOG(f"[gist] WARNING: {CLASH_NAME} was built but is absent from the "
            "API response; the Clash link is not saved")

    links_saved = True
    try:
        if subscription_url:
            URL_FILE.write_text(subscription_url + "\n", encoding="utf-8")
        if clash_url:
            CLASH_URL_FILE.write_text(clash_url + "\n", encoding="utf-8")
        else:


            CLASH_URL_FILE.unlink(missing_ok=True)
    except OSError as e:
        links_saved = False
        LOG(f"[gist] WARNING: failed to save subscription links: "
            f"{first_line(e)}")

    stale_names: list[str] = list(STALE_NAMES)
    if not clash_published:


        stale_names.append(CLASH_NAME)
    pruned = prune_stale(token, gist_id, files, tuple(stale_names))
    for name in pruned:
        LOG(f"Removed stale gist file: {name}")

    LOG("=" * 60)
    LOG("Upload successful!")
    if html_url:
        LOG(f"Gist URL: {html_url}")
    if subscription_url:
        LOG(f"Subscription URL (v2ray/URI): {subscription_url}")
        LOG(f"Saved to: {URL_FILE}")
    if clash_url:
        LOG(f"Subscription URL (Clash YAML): {clash_url}")
        LOG(f"Saved to: {CLASH_URL_FILE}")
    elif clash:
        LOG(f"WARNING: {CLASH_NAME} is not published; the Clash link was cleared")
    LOG("=" * 60)

    _write_status(True, nodes=nodes_count, gist_id=gist_id,
                  gist_url=html_url, subscription_url=subscription_url,
                  clash_url=clash_url, clash_published=clash_published,
                  pruned=pruned, links_saved=links_saved)
    return 0


if __name__ == "__main__":
    sys.exit(main())
