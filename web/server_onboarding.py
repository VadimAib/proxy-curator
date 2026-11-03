                                                                        

                                                                           
                                                                            
                                                                  

                                                                             
                                  
                                                                       
                                                          
                                                                         
                                                                       
                                                                            

                                                                       
                                                                         
                                                                     
   
from __future__ import annotations

import ipaddress
import json
import socket
import time
from pathlib import Path

from core.config import Config
from core.cores import core_state, missing_core_binaries
from core.utils import write_text_atomic
from server_advisor import _read_selfcheck
from server_config import CONFIG_PATH, _read_summary, artifact_paths
from server_sources import load_sources_data




_FAKE_IP_NET = ipaddress.ip_network("198.18.0.0/15")



_CHECK_HOST = "api.github.com"


def first_run_path() -> Path:
                                                                                                                                   
    return artifact_paths()["summary"].parent / "first_run.json"


def _read_marker() -> dict:
                                                                                                                                
    try:
        data = json.loads(first_run_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _enabled_sources() -> int:
                                                                                                                
    try:
        sections = load_sources_data().get("sections", [])
    except Exception:
        return 0
    return sum(1 for section in sections
               for item in section.get("items", [])
               if item.get("enabled"))


def _is_fake_ip(address: str) -> bool:
                                                                                          
    try:

        return ipaddress.ip_address(address.split("%", 1)[0]) in _FAKE_IP_NET
    except ValueError:
        return False


def network_check(host: str = _CHECK_HOST) -> dict:
                                                     

                                                                  
                                                                         
                                                                        
                                         
       
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        return {
            "ok": False,
            "host": host,
            "address": "",
            "addresses": [],
            "fake_ip": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    addresses: list[str] = []
    for info in infos:
        address = str(info[4][0])
        if address not in addresses:
            addresses.append(address)
    fake = [address for address in addresses if _is_fake_ip(address)]
    if not addresses:
        return {
            "ok": False,
            "host": host,
            "address": "",
            "addresses": [],
            "fake_ip": False,
            "error": "no addresses returned",
        }
    return {
        "ok": True,
        "host": host,
        "address": fake[0] if fake else addresses[0],
        "addresses": addresses,
        "fake_ip": bool(fake),
        "error": "",
    }


def onboarding_state() -> dict:
                                                              

                                                                           
                                                                         
                                                                             
                                      

                                                                        
                                     
       
    cfg = Config.load(CONFIG_PATH)
    cores = core_state(cfg)
    missing = missing_core_binaries(cfg)
    enabled_cores = [str(c.get("name") or "") for c in cores if c.get("enabled")]
    sources = _enabled_sources()
    measured = bool(_read_selfcheck())
    has_run = _read_summary() is not None
    marker = _read_marker()

    reasons: list[str] = []
    if missing:
        reasons.append("cores_missing")
    if sources == 0:
        reasons.append("sources_empty")
    if not marker and not has_run:
        reasons.append("first_run")

    needed = bool(missing) or (not marker and not has_run)
    state = {
        "ok": True,
        "needed": needed,
        "reasons": reasons,
        "marker": marker or None,
        "cores": {
            "missing": missing,
            "enabled": enabled_cores,
            "items": cores,
        },
        "sources": sources,
        "measured": measured,
        "has_run": has_run,
    }
    if needed:
        state["network"] = network_check()
    else:
        state["network"] = {
            "ok": None,
            "skipped": True,
            "host": _CHECK_HOST,
            "address": "",
            "addresses": [],
            "fake_ip": False,
            "error": "",
        }
    return state


def complete_onboarding() -> dict:
                                                                                                                                    
    marker = {
        "version": 1,
        "status": "done",
        "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    write_text_atomic(
        first_run_path(),
        json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
    )
    return marker
