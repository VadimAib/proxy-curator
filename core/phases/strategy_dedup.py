# -*- coding: utf-8 -*-
                                                                     
                                                             

                                                                     
                                                                            
                                                                          
                                                                        
                                                                          
                                                                     
                                                                  

                                                                               
                                                                        
                                                                          
                                                                       

                                                                            
                                                                   
                                                               
   
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from ..config import Config
from ..log import LOG
from ..models import Node
from ..state import PipelineState



_STRATEGY_FIELDS = ("fp", "sni", "flow", "path", "alpn", "obfs", "insecure")


def _strategy_sig(node: Node) -> Tuple:
                                                                         
                                                                          
                           
    e = node.extra
    net = str(e.get("net") or node.transport.value)
    parts: List[str] = [node.protocol.value, node.security.value, net]
    for f in _STRATEGY_FIELDS:
        val = e.get(f)
        parts.append(str(val).lower() if f == "sni" else str(val or ""))
    return tuple(parts)


def _best(item: Tuple[Node, float],
          quick: Dict[str, Dict[str, Any]]) -> Tuple[float, float]:
                                                                       
                                                                                                              
    node, tcp_ms = item
    hit = quick.get(node.key()) or {}
    mbps = float(hit.get("mbps", -1.0) or -1.0)
    q_ms = hit.get("tcp_ms")
    ms = float(q_ms if q_ms is not None else tcp_ms or 0.0)
    return (mbps, -ms)


def strategy_dedup_phase(state: PipelineState, cfg: Config) -> None:
                                                                       

                                                                            
                                                                             
                                                            
                                                                          
       
    dedup_on = bool(getattr(cfg.filters, "strategy_dedup", False))
    if not dedup_on:
        LOG("[dedup] strategy skipped (filters.strategy_dedup=false)")
        return
    if not state.alive:
        LOG("[dedup] strategy: no candidates")
        return

    quick = state.stats.get("speedtest_quick") or {}
    groups: Dict[Tuple, List[Tuple[Node, float]]] = defaultdict(list)
    for item in state.alive:
        node = item[0]
        groups[((node.host.lower(), node.port),) + _strategy_sig(node)].append(item)

    kept: List[Tuple[Node, float]] = []
    collapsed = 0
    n_groups = 0
    for members in groups.values():
        if len(members) > 1:
            n_groups += 1
            collapsed += len(members) - 1
        kept.append(max(members, key=lambda it: _best(it, quick)))

    before = len(state.alive)

    state.alive = kept
    state.stats["strategy_dedup"] = {"groups": n_groups, "collapsed": collapsed}
    LOG(f"[dedup] strategy: {before} -> {len(kept)} "
        f"(collapsed {collapsed}, groups {n_groups})")
