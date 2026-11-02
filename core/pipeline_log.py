                                                                          

                                                                           
                                                                             
                                                                          
                                 

                                                                        
                                                                            
                                                                         
                                                                           
                                                                        
                                                                              
                                                  
   
from typing import Any, Dict, List, Optional, Tuple

from .log import LOG
from .models import Node


def _stop_note(ping_only: bool, skip_to_phase: Optional[str]) -> str:
                                                                           

                                                                        
       
    return ("  [skipped: --ping-only]" if ping_only else
            "  [skipped: resume]" if skip_to_phase == "delay" else "")


def _log_engines(engines: Dict[str, Any], stats: Dict[str, Any]) -> None:
                                                                     

                                                                           
                                                                        
           
       
    LOG("[engines] " + ", ".join(
        f"{rt.name}={'on' if rt.available() else 'off'}"
        for rt in engines.values()))
    stats["engines"] = {rt.name: {"path": str(rt.binary or ""),
                                  "available": rt.available()}
                        for rt in engines.values()}


def _log_route_by_engine(stats: Dict[str, Any]) -> None:
                                                                                          
    by_engine = stats.get("delay_ok_by_engine", {})
    LOG("[route] working by engine: " + ", ".join(
        f"{k}={v}" for k, v in sorted(by_engine.items())))


def _log_out_count(final: List[Tuple[Node, float]], stats: Dict[str, Any],
                   ping_only: bool, tcping_only: bool) -> None:
                                                                        

                                                                            
                                                                              
                                        
       
    rescued_n = stats.get("rescued_count", 0)
    if ping_only or tcping_only:
        LOG(f"[out] {len(final)} candidate(s) — http_test NOT run")
    else:
        LOG(f"[delay] {max(0, len(final) - rescued_n)} fully working nodes"
            + (f" + {rescued_n} rescued" if rescued_n else ""))
