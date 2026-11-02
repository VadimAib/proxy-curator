                                                                          
      

                                                      
                                                                         
                                                                       
                                                       
                                                                    
                                                                       
         

                                                                           
                                                                     
                                                                     
                                                                        
                                                                     
                                                                   
                                                                    
                                                                     
                                                                    

                                                                       
                                                                  
                                                                        
                                                                        

                                                         
                                                                        
                                                                       
                         
   
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, FrozenSet, List, Tuple

from .log import dlog
from .models import Node
from .utils import first_line

if TYPE_CHECKING:
    from .config import Config



DEFAULT_TTL_HOURS = 1.0


def _trusted_cks(data) -> List[str]:
                                                          

                                                                       
                                                                        
                                                                       
                                                                        
                                                                      
                                                                     
                                                                 
       
    if isinstance(data, dict):
        data = data.get("nodes") or data.get("working") or []
    if not isinstance(data, list):
        return []
    return [e["ck"] for e in data
            if isinstance(e, dict) and isinstance(e.get("ck"), str)]


def load_trusted_nodes(prev_json_path: Path,
                       ttl_hours: float = DEFAULT_TTL_HOURS
                       ) -> FrozenSet[str]:
                                                        

                                                                        
                                                                       
                                                                      
                                                                        
                                    
                                                                        
                                                                 
                          
       
    try:
        path = Path(prev_json_path)
        age_hours = (time.time() - path.stat().st_mtime) / 3600.0
        if age_hours > max(0.0, float(ttl_hours)):
            dlog(f"load_trusted_nodes: {path.name} is older than the TTL "
                 f"({age_hours:.1f}h > {ttl_hours}h) — trust revoked")
            return frozenset()
        with open(path, "r", encoding="utf-8") as f:
            cks = _trusted_cks(json.load(f))
    except Exception as e:
        dlog(f"load_trusted_nodes: {prev_json_path}: {first_line(e)}")
        return frozenset()
    return frozenset(cks)


def split_trusted_nodes(alive: List[Tuple[Node, float]],
                        trusted_ck: FrozenSet[str]
                        ) -> Tuple[List[Tuple[Node, float]],
                                   List[Tuple[Node, float]]]:
                                                           

                                                                         
                                                                      
                                                                      
                                                     
                                                              
                                                                     
                                                                  
             
       
    trusted: List[Tuple[Node, float]] = []
    normal: List[Tuple[Node, float]] = []
    for item in alive:
        (trusted if item[0].ck() in trusted_ck else normal).append(item)
    return trusted, normal


def apply_trusted_bypass(alive: List[Tuple[Node, float]], out_path: Path,
                         cfg: "Config"
                         ) -> Tuple[List[Tuple[Node, float]],
                                    List[Tuple[Node, float]]]:
                                                                      

                                                                       
                                                                   
                                                                        
                                                             
       
    if not cfg.testing.trusted_nodes_enabled:
        return [], list(alive)
    cks = load_trusted_nodes(
        out_path.with_name(out_path.stem + ".json"),
        cfg.testing.trusted_nodes_ttl_hours)
    if not cks:
        return [], list(alive)
    return split_trusted_nodes(alive, cks)
