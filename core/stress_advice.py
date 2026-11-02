                                                               

                                                                            
                                                                          
                                                                          
                                                                              
                                                                              
                                                                          
                                                                         

                                                                  

                                                                              
                                                                             
                                                                            
                                                                          
                                                                              
                                                                          
                                                                           
                                                                             
                                                                            
                                                                            

                                                                        
                                                                   
   
from typing import Any, Dict, Optional

from .tune_plan import SLOW_MBPS



_CPU_REFERENCE_NODES = 35_000


_CPU_SLOW_SECONDS = 10.0


_DISK_REFERENCE_MB = 14.0


_DISK_SLOW_SECONDS = 1.0


_DISK_MIN_FREE_MB = 500.0


def cpu_verdict(nodes_per_s: float,
                reference_nodes: Optional[int] = None) -> Optional[Dict[str, Any]]:
                                                                                  

                                                                                
                                                                             
                                                                            
                                                                                
       
    if nodes_per_s <= 0:
        return None
    ref = int(reference_nodes) if reference_nodes and reference_nodes > 0 \
        else _CPU_REFERENCE_NODES
    seconds = ref / nodes_per_s
    slow = seconds > _CPU_SLOW_SECONDS
    return {
        "level": "slow" if slow else "ok",
        "action": "reduce_sources" if slow else None,
        "seconds": round(seconds, 1),
        "reference_nodes": ref,
        "reference_source": "run" if (reference_nodes and reference_nodes > 0) else "fallback",
    }


def disk_verdict(write_mbps: float, read_mbps: float,
                 cached_mbps: Optional[float] = None,
                 free_mb: Optional[float] = None) -> Optional[Dict[str, Any]]:
                             

                                                                            
                                                                          
                                                            
                                                                         
       
    if write_mbps <= 0:
        return None
    low_space = free_mb is not None and free_mb < _DISK_MIN_FREE_MB
    slow = write_mbps < _DISK_REFERENCE_MB / _DISK_SLOW_SECONDS
    level = "low_space" if low_space else ("slow" if slow else "ok")
    action = "free_space" if low_space else ("move_cache_dir" if slow else None)
    return {
        "level": level,
        "action": action,
        "write_mbps": round(write_mbps, 1),
        "read_mbps": round(read_mbps, 1),
        "cached_mbps": round(cached_mbps, 1) if cached_mbps is not None else None,
        "free_mb": round(free_mb) if free_mb is not None else None,
    }


def network_verdict(mbps: Optional[float]) -> Optional[Dict[str, Any]]:
                                                                          

                                                                              
                                                      
       
    if mbps is None or mbps <= 0:
        return None
    slow = mbps < SLOW_MBPS
    return {
        "level": "slow" if slow else "ok",
        "action": "use_light_profile" if slow else None,
        "mbps": round(mbps, 1),
        "threshold_mbps": SLOW_MBPS,
    }


def verdict_for(kind: str, res: Any, *,
                reference_nodes: Optional[int] = None,
                free_mb: Optional[float] = None) -> Optional[Dict[str, Any]]:
                                                                         

                                                                        
                                                        
                                                                    
                                                      
       
    if not getattr(res, "success", False):
        return None
    if kind == "cpu":
        return cpu_verdict(res.value, reference_nodes)
    if kind == "disk":
        return disk_verdict(
            res.write_mbps, res.read_mbps,
            cached_mbps=getattr(res, "write_cached_mbps", None),
            free_mb=free_mb)
    if kind == "network":
        return network_verdict(res.value)
    return None
