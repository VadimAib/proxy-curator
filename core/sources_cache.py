                                                       

                                                             
                                                                        
                                                                      
                                                                              
import json
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.request import Request, urlopen
from .log import LOG, dlog
from .utils import first_line
from .sources_fetch import UA, http_get



def _parse_iso(v) -> Optional[datetime]:
    if not v:
        return None
    try:
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return (dt if dt.tzinfo
                else dt.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    except Exception:
        return None




def header_last_modified(url: str, timeout: int = 15) -> Optional[datetime]:
    try:
        with urlopen(Request(url, headers=UA, method="HEAD"),
                     timeout=timeout) as r:
            return _parse_iso(r.headers.get("Last-Modified"))
    except Exception:
        return None




_RAW_RE = re.compile(
    r"https://raw.githubusercontent.com/([^/]+)/([^/]+)/([^/]+)/(.+)$")




def atom_last_modified(url: str, timeout: int = 15) -> Optional[datetime]:
    m = _RAW_RE.match(url)
    if not m:
        return None
    o, r, b, p = m.groups()
    feed = f"https://github.com/{o}/{r}/commits/{b}/{p}.atom"
    try:
        root = ET.fromstring(http_get(feed, timeout=timeout))
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        stamps = [d for d in (_parse_iso(e.text)
                              for e in root.findall(".//atom:updated", ns))
                  if d]
        return max(stamps) if stamps else None
    except Exception:
        return None




def load_date_cache(path: Path) -> Dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)



        return data if isinstance(data, dict) else {}
    except Exception:
        return {}




def cached_url_count(path: Path) -> int:
                                                                               

                                                                              
                                                                           
                                                                            
       
    return len(load_date_cache(path))




def save_date_cache(path: Path, cache: Dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=1)
        tmp.replace(path)
    except Exception as e:

        dlog(f"save_date_cache failed: {first_line(e)}")




def resolve_file_dates(urls: List[str], cache_path: Optional[Path],
                       ttl_days: int = 7, workers: int = 16) -> Dict:
                                                                      

                                                                  
                                                                        
       
    cache = load_date_cache(cache_path) if cache_path else {}
    now = datetime.now(timezone.utc).timestamp()
    ttl = max(0, ttl_days) * 86400
    result, to_check = {}, []

    for u in urls:
        e = cache.get(u)
        if e and (now - float(e.get("checked", 0))) < ttl:
            result[u] = e.get("lm")
        else:
            to_check.append(u)

    if to_check:
        def probe(u):
            dt = header_last_modified(u)
            return dt if dt is not None else atom_last_modified(u)

        with ThreadPoolExecutor(min(workers, len(to_check))) as ex:
            futs = {ex.submit(probe, u): u for u in to_check}
            for f in as_completed(futs):
                u = futs[f]
                try:
                    dt = f.result()
                except Exception:
                    dt = None
                result[u] = dt.isoformat() if dt else None
                cache[u] = {"lm": result[u], "checked": now}

    if cache_path:




        current = set(urls)
        stale = [u for u in cache if u not in current]
        if stale:
            for u in stale:
                del cache[u]
            dlog(f"date_cache: pruned {len(stale)} stale key(s), "
                f"{len(current)} current")
        save_date_cache(cache_path, cache)

    return result




def filter_by_age(urls: List[str], dates: Dict, max_age_days: int,
                  report: bool = False) -> Tuple[List[str], List]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    fresh, skipped = [], []

    for u in urls:
        dt = _parse_iso(dates.get(u))
        if dt is None or dt >= cutoff:
            fresh.append(u)
        else:
            skipped.append((u, dt))

    if report:
        for u, dt in skipped:
            LOG(f"   skip {u.rsplit('/', 1)[-1]:<28} {dt:%Y-%m-%d}")

    return fresh, skipped

