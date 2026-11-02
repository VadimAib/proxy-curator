                                                         

                                                                          
                                                                             
                                                                           
                                                          

                                                                              
                                                                    
                                                                           
                                            
   
from typing import Dict, List, Optional, Tuple

from .log import LOG
from .models import Node
from .parsers import parse_node
from .state import PipelineState

















_SESSION_SCOPED_KEYS = (
    "started", "args", "xray", "singbox",
    "profile_override", "speedtest_profile", "speedtest_profile_source",
    "speedtest_network",
    "local_ip", "network_fingerprint",




    "run_network",






    "local_link",
)


def _restore_resume(state: PipelineState) -> Tuple[Optional[str], List[Node]]:
                                                                               

                                                                       
                                                                       
                                     

                                                                  
                                                                         
                                      
       
    if not state.resume_data:
        return None, []
    data = state.resume_data
    LOG(f"[resume] restoring session (phase: {data['phase']})...")


    session = {k: state.stats[k] for k in _SESSION_SCOPED_KEYS
               if k in state.stats}
    state.stats.update(data.get("stats", {}))
    state.stats.update(session)
    if session:
        LOG("[resume] session keys not inherited from the previous run: "
            + ", ".join(sorted(session)))

    if data["phase"] == "delay":
        for item in data.get("candidates", []):
            n = parse_node(item["raw"])
            if n:
                state.alive.append((n, _tcp_ms(data, n.raw)))
        for item in data.get("ok_all", []):
            n = parse_node(item["raw"])
            if n:
                state.final.append((n, _final_ms(data, n.raw)))


        for item in data.get("quick_pool", []):
            n = parse_node(item["raw"])
            if n:
                state.quick_pool.append((n, _tcp_ms(data, n.raw)))
        LOG(f"[resume] skipping fetch and tcping, resuming delay tests "
            f"({len(state.alive)} node(s), {len(state.quick_pool)} in quick "
            f"pool)...")
        return "delay", []

    if data["phase"] == "tcping":
        nodes = []
        for item in data.get("candidates", []):
            n = parse_node(item["raw"])
            if n:
                nodes.append(n)
        LOG(f"[resume] skipping fetch, resuming from TCPing "
            f"({len(nodes)} node(s))...")
        return "tcping", nodes

    return None, []


def _tcp_ms(data: Dict, raw: str) -> float:
                                                         

                                                                        
                                                                          
                    
       
    for item in data.get("candidates", []) + data.get("quick_pool", []):
        if item.get("raw") == raw:
            return float(item.get("tcp_ms", 0.0))
    return 0.0


def _final_ms(data: Dict, raw: str) -> float:
                                                                                                           
    for item in data.get("ok_all", []):
        if item.get("raw") == raw:
            return float(item.get("ms", 0.0))
    return 0.0
