                                                                            

                                                                            
                                                                      
                                                                      
                                                               
               

                                                                     
                                                                       
                                                           
                                         

                                                                 
                                                                   
   
import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from ..log import dlog
from ..paths import ROOT
from ..utils import first_line

GEO_CACHE_FILE = "geo_cache.json"
GEO_CACHE_PATH = ROOT / "cache" / GEO_CACHE_FILE

_geo_persistent: Dict[str, Dict[str, Any]] = {}
_geo_cache_enabled: bool = False
_geo_cache_ttl_s: float = 0.0





_geo_path: Optional[Path] = None
_geo_cache_lock = threading.Lock()


def init_geo_cache(enabled: bool, ttl_hours: float,
                   path: Optional[Path] = None) -> None:
                                                                            

                                                                          
                                                                    
                                                                             
                                                                            
                                                     

                                                                      
                                                                    
                                                            
       
    global _geo_persistent, _geo_cache_enabled, _geo_cache_ttl_s, _geo_path
    target = Path(path) if path is not None else None
    with _geo_cache_lock:
        _geo_path = target
        _geo_cache_enabled = bool(enabled)
        _geo_cache_ttl_s = float(ttl_hours) * 3600.0
        _geo_persistent = (load_geo_cache(target or GEO_CACHE_PATH)
                           if _geo_cache_enabled else {})


def load_geo_cache(path: Path = GEO_CACHE_PATH) -> Dict[str, Dict[str, Any]]:
                                                                     

                                                                   
                                                                     
       
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        dlog(f"[geo] cache: {first_line(e)}")
        return {}
    if not isinstance(data, dict):
        dlog("[geo] cache: file is not an object — empty cache")
        return {}
    return data


def save_geo_cache(path: Optional[Path] = None) -> None:
                                                                         

                                                                            
                                                                              
                                  
                                                                  
                                       
       
    with _geo_cache_lock:
        enabled = _geo_cache_enabled
        data = _geo_persistent
        target = Path(path) if path is not None else (_geo_path or GEO_CACHE_PATH)
    if not enabled:
        return
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        tmp.replace(target)
    except Exception as e:
        dlog(f"[geo] save_geo_cache: {first_line(e)}")


def get_persistent_country(host: str) -> Optional[str]:
                                                                           

                                                       
                                                                    
                                                                
                    
       
    with _geo_cache_lock:
        if not _geo_cache_enabled:
            return None
        entry = _geo_persistent.get(host)
        if (entry is not None
                and (time.time() - float(entry.get("ts", 0.0)))
                < _geo_cache_ttl_s):
            return entry.get("country")
    return None


def set_persistent_country(host: str, code: Optional[str]) -> None:
                                                                     

                                                            
       
    with _geo_cache_lock:
        if _geo_cache_enabled:
            _geo_persistent[host] = {"country": code, "ts": time.time()}
