                                                                        

                                                                    
                                                            
                                                                 
                                                                    
                                                                     
                                                                          
                                                                    
                                                                       
                                       
                                                 
                                                                          
                     

                                                                   
                                                    
                                                          

                                                         
                                                                       
                                                                      
   
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

from .log import dlog
from .models import Node
from .utils import first_line


DEAD_NODES_FILE = "dead_nodes.json"


DEFAULT_TTL_HOURS = 24.0


def load_dead_nodes_cache(path: Path) -> Dict[str, Dict]:
                                                                        

                                                                       
                                                                
       
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items()
            if isinstance(v, dict)
            and isinstance(v.get("timestamp"), (int, float))}


def save_dead_nodes_cache(path: Path, cache: Dict[str, Dict]) -> None:
                                                                      

                                                                        
                                                                    
                                                                 
                                                

                                                                       
                                                                 
       
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        payload = {
            key: ({k: v for k, v in entry.items() if k != "raw"}
                  if isinstance(entry, dict) else entry)
            for key, entry in cache.items()
        }
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        tmp.replace(path)
    except Exception as e:
        dlog(f"save_dead_nodes_cache failed: {first_line(e)}")


def prune_dead_nodes(cache: Dict[str, Dict],
                     ttl_hours: float = DEFAULT_TTL_HOURS
                     ) -> Dict[str, Dict]:
                                                                                                                                 
    limit = time.time() - max(0.0, float(ttl_hours)) * 3600.0
    return {k: v for k, v in cache.items()
            if float(v.get("timestamp", 0)) >= limit}


def _cache_path(cache_dir: Path) -> Path:
    return Path(cache_dir) / DEAD_NODES_FILE


def _cache_key(node: Node, network_fingerprint: str | None) -> str:
                                                       

                                                                           
                                                                        
                                                                   
       
    base = node.dedup_key()
    fp = network_fingerprint or "unknown"
    return f"{base}|{fp}"


def record_conn_drops(cache_dir: Path,
conn_drops: Dict[str, Tuple[Node, str]],
ttl_hours: float = DEFAULT_TTL_HOURS,
network_fingerprint: str | None = None,
source_nodes: List[Node] | None = None
                  ) -> int:
                                                                            

                                                                      
                                                                
                                                            
                                                          
                                                              
                                                                  
                                                            
                                                                   
               

                                                                 
                                                                
                                                                      
                                                   

                                                                  
                                                                      
                                                             
                                                                  
           
       
    cache = prune_dead_nodes(load_dead_nodes_cache(_cache_path(cache_dir)),
                             ttl_hours)
    now = time.time()
    written = 0
    for node, reason in conn_drops.values():
        if reason == "no_connectivity":

            continue
        cache[_cache_key(node, network_fingerprint)] = {"timestamp": now,
                                                        "reason": reason}
        written += 1



    if source_nodes is not None:
        source_keys = {n.dedup_key() for n in source_nodes}
        cache = {k: v for k, v in cache.items()
                 if k.rsplit("|", 1)[0] in source_keys}
    if not cache:

        try:
            _cache_path(cache_dir).unlink(missing_ok=True)
        except Exception:
            pass
        return 0
    save_dead_nodes_cache(_cache_path(cache_dir), cache)
    return written


def skip_dead_nodes(cache_dir: Path,
                    alive: List[Tuple[Node, float]],
                    ttl_hours: float = DEFAULT_TTL_HOURS,
                    network_fingerprint: str | None = None
                    ) -> Tuple[List[Tuple[Node, float]], int]:
                                                   

                                                                  
                                                                   
                                                                     
                                                               
       
    cache = prune_dead_nodes(load_dead_nodes_cache(_cache_path(cache_dir)),
                             ttl_hours)
    if not cache:
        return list(alive), 0
    kept = [(n, m) for n, m in alive
            if _cache_key(n, network_fingerprint) not in cache]
    return kept, len(alive) - len(kept)
