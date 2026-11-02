                                                                            

                                                                            
                                                                          
                                                                          
                         

                                                                   
                                                            
                                                                      
                                         
   
from typing import Any, Dict, Optional

from .log import LOG


_FUNNEL_STEPS = (
    ("files_resolved", "files"),
    ("files_fetched", "fetched"),
    ("links_total", "links"),
    ("policy_survive", "policy"),
    ("tcping_alive", "ping"),
    ("connectivity_filtered", "conn"),
    ("speedtest_quick_ok", "quick"),
    ("delay_ok", "delay"),
    ("rescued_count", "rescued"),
)


def _log_funnel(stats: Dict[str, Any],
                out_count: Optional[int] = None) -> None:
                                                       

                                                                           
                                                                         
                                                                    

                                                                           
                              

                                                                         
                                                                        
                                                                       
                                                                          
                                                                 
                                                                    

                                                                     
                                                                   
                                                                         
                                                                        
                                                    

                                                                          
                                                                             
                                                 
       
    parts = [f"{label}={stats[key]}" for key, label in _FUNNEL_STEPS
             if isinstance(stats.get(key), int)]
    if not parts:
        return
    LOG("")
    LOG("=== FUNNEL ===  " + " -> ".join(parts))
    _log_yield(stats, out_count)


def _log_yield(stats: Dict[str, Any],
               out_count: Optional[int] = None) -> None:
                                                                               

                                                                            

                                                                            
                                                                   
                                                                        
                                                                        
                                                                   
                                                              

                                                                             
                                                    

                                                                           
                                                                          
                                                                 
                                                                   
       
    if stats.get("mode"):
        return
    alive = stats.get("tcping_alive")
    delay_ok = stats.get("delay_ok")
    if not isinstance(alive, int) or not isinstance(delay_ok, int):
        return
    if alive <= 0:
        return
    if isinstance(out_count, int):
        out = out_count
    else:
        rescued = stats.get("rescued_count")
        out = delay_ok + (rescued if isinstance(rescued, int) else 0)
    LOG(f"[yield] {out}/{alive} = {out * 100 / alive:.2f}% of alive")
