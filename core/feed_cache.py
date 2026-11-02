                                                                  

                                                                
                                                                               
                            

                                                                      
                      
                                          
                                                                       
                                                                          
                                                                       
                                                                         
                         

                                                              
                                                                         
                                                                        
                                                                          
                                                                    
                                                  
   
import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .log import dlog
from .parsers import parse_node
from .sources_fetch import FORMAT_URI, Subscription
from .utils import first_line


FEED_CACHE_FILE = "feed_cache.json"



_LM_SKEW_SEC = 2.0



_TTL_SLACK_SEC = 3600.0


@dataclass(frozen=True)
class FeedCacheContext:
                                                                          

                                                                        
                                                                           
                                                           
                                                                      
                                 
       
    cache_dir: Path
    ttl_hours: float
    lm_dates: Dict[str, Optional[str]]


def feed_cache_context(cache_dir: Path, dates: Dict[str, Optional[str]],
                       enabled: bool, ttl_hours: float
                       ) -> Optional[FeedCacheContext]:
                                                                                                                
    return (FeedCacheContext(Path(cache_dir), float(ttl_hours), dates)
            if enabled else None)


def feed_content_hash(text: str) -> str:
                                                                                                                   
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_feed_cache(path: Path) -> Dict[str, Dict[str, Any]]:
                                                                        

                                                                          
                                                               
                                                    
       
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items()
            if isinstance(v, dict)
            and isinstance(v.get("fetched_at"), (int, float))}


def save_feed_cache(path: Path, cache: Dict[str, Dict[str, Any]]) -> None:
                                                                      

                                                                       
                                                             
       
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=1)
        tmp.replace(path)
    except Exception as e:
        dlog(f"save_feed_cache failed: {first_line(e)}")


def cache_parsed_nodes(cache: Dict[str, Dict[str, Any]], feed_url: str,
                       content_hash: str, sub: Subscription
                       ) -> Dict[str, Any]:
                                                                        

                                                                 
                                                                     
                                                                       
                                                                       
       
    items = ([{"raw": link} for link in sub.links]
             if sub.fmt == FORMAT_URI
             else [{"raw": node.raw} for node in sub.nodes])
    entry: Dict[str, Any] = {"content_hash": content_hash,
                             "fetched_at": time.time(),
                             "fmt": sub.fmt, "items": items}
    cache[feed_url] = entry
    return entry


def cached_subscription(url: str, entry: Dict[str, Any]) -> Subscription:
                                                              

                                                                     
                                                                    
                                                    
       
    items = entry.get("items")
    raws = [i["raw"] for i in (items if isinstance(items, list) else [])
            if isinstance(i, dict) and isinstance(i.get("raw"), str)]
    if entry.get("fmt") == FORMAT_URI:
        return Subscription(url=url, fmt=FORMAT_URI, links=raws)
    nodes = [n for n in (parse_node(r) for r in raws) if n is not None]
    return Subscription(url=url, fmt=entry.get("fmt", ""), nodes=nodes)


def get_cached_nodes(cache: Dict[str, Dict[str, Any]], feed_url: str,
                     content_hash: str) -> Optional[List[Dict[str, str]]]:
                                                                    

                                                                  
                                                                
       
    entry = cache.get(feed_url)
    if entry is None or entry.get("content_hash") != content_hash:
        return None
    items = entry.get("items")
    if not isinstance(items, list):
        return []
    return [i for i in items
            if isinstance(i, dict) and isinstance(i.get("raw"), str)]


def entry_fresh(entry: Dict[str, Any], ttl_hours: float,
                 now: Optional[float] = None) -> bool:
                                                                         

                                                                      
                           
       
    if now is None:
        now = time.time()
    if ttl_hours <= 0:
        return True
    age = now - float(entry.get("fetched_at", 0.0))
    return age <= max(0.0, float(ttl_hours)) * 3600.0 + _TTL_SLACK_SEC


def lm_unchanged_since(entry: Dict[str, Any],
                       lm_iso: Optional[str]) -> bool:
                                             

                                                                    
                                                                  
                                                  
       
    if lm_iso is None:
        return False
    try:
        lm_ts = datetime.fromisoformat(
            str(lm_iso).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return False
    return lm_ts <= float(entry.get("fetched_at", 0.0)) + _LM_SKEW_SEC


def prune_feed_cache(cache: Dict[str, Dict[str, Any]], urls: List[str],
                     ttl_hours: float = 0.0,
                     now: Optional[float] = None
                     ) -> Dict[str, Dict[str, Any]]:
                                                                      

                                                                    
                                               
       
    if now is None:
        now = time.time()
    keep = set(urls)
    return {u: e for u, e in cache.items()
            if u in keep and entry_fresh(e, ttl_hours, now)}
