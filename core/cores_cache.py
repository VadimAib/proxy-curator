from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from .cores_fetch import DOWNLOAD_URL
from .cores_specs import CoreSpec
from .log import LOG
from .paths import rp
from .utils import first_line


CHECK_TTL_SEC = 6 * 3600
CACHE_FILE = "cache/core_check.json"



def _cache_path() -> Path:
    return rp(CACHE_FILE)


def load_cache() -> Dict[str, Dict[str, object]]:
                                                                         

                                                                          
                                                                         
                                                                       
           
       
    try:
        data = json.loads(_cache_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if isinstance(v, dict)}


def save_cache(cache: Dict[str, Dict[str, object]]) -> None:
                                                                                                                
    path = _cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        tmp.replace(path)
    except OSError as e:
        LOG(f"[cores] WARNING: check cache not written ({first_line(e)})")


def _entry_fresh(entry: object, now: float) -> bool:
                                                                                                                     
    if not isinstance(entry, dict):
        return False
    try:
        age = now - float(entry["checked"])
    except (KeyError, TypeError, ValueError):
        return False
    return 0 <= age < CHECK_TTL_SEC


def _entry_size(entry: Dict[str, object]) -> int:
                                                                              

                                                                          
                                                                               
                                                                           
                                                                          
                                                

                                                                           
                                                                          
                                                                           
                                                                         
                                                     
       
    raw = entry.get("size")
    if isinstance(raw, bool) or not isinstance(raw, (int, str)):
        return 0
    try:
        return max(int(raw), 0)
    except ValueError:
        return 0



def describe_entry(spec: CoreSpec, tag: str, sizes: Dict[str, int],
                   now: float) -> Dict[str, object]:
                                                                 

                                                                             
                                                                       
                                                  
       
    version = tag.lstrip("v")
    asset = spec.asset.format(version=version)
    if asset not in sizes:
        raise ValueError(f"release {tag} has no asset {asset}")
    digest = spec.digest.format(version=version) if spec.digest else ""
    return {
        "checked": now,
        "tag": tag,
        "version": version,
        "asset": asset,
        "size": int(sizes.get(asset, 0)),
        "url": DOWNLOAD_URL.format(repo=spec.repo, tag=tag, asset=asset),
        "digest_url": (DOWNLOAD_URL.format(repo=spec.repo, tag=tag, asset=digest)
                       if digest else ""),
    }
