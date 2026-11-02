                                                             

                                                                           
                                                                      
                                                                
                       

                                                                        
                                                                         

                                                                           
                                                                        
                                                                     
       

                                                                           
                                                                           
                                                                     
                                                                            
                                        

                                                                       
                                                                         
                                                                         
                                                                       

                                                          
                                                                    
                                                                            
                                               

                                                            
                                                                        
                                                                      
   
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from .log import LOG
from .models import Node



QUALITY_GATE_RELAX_KEEP = 10


def _keep_count(output_cfg) -> int:
                                                                               

                                                                          
                                                                      
                                                 
       
    raw = getattr(output_cfg, "quality_gate_min_keep", QUALITY_GATE_RELAX_KEEP)
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return QUALITY_GATE_RELAX_KEEP



def _mbps_of(node: Node, stats: Dict[str, Any]) -> Optional[float]:
                                                                                                                                
    for field in ("speedtest", "speedtest_quick"):
        hit = (stats.get(field) or {}).get(node.key())
        if not isinstance(hit, dict) or hit.get("mbps") is None:
            continue
        try:
            return float(hit["mbps"])
        except (TypeError, ValueError):
            continue
    return None


def _latency_snapshot(final: List[Tuple[Node, float]]
                      ) -> Tuple[List[float], int]:
                                                                         

                                                                  
                                                                       
                                                                       
                                                

                                                                        
                                                                         
                                                                         
                                                                 
                                                                    
                                            
       
    known = sorted(round(float(ms), 1) for _, ms in final
                   if float(ms or 0.0) > 0)
    return known, len(final) - len(known)


def _relaxed_top(final: List[Tuple[Node, float]],
                 stats: Dict[str, Any],
                 keep: int = QUALITY_GATE_RELAX_KEEP
                 ) -> List[Tuple[Node, float]]:
                                                                     

                                                                       
                                                     
       
    def rank(item: Tuple[Node, float]):
        speed = _mbps_of(item[0], stats)
        return (speed is not None, speed if speed is not None else -1.0,
                -float(item[1] or 0.0))

    return sorted(final, key=rank, reverse=True)[:keep]


def apply_quality_gate(final: List[Tuple[Node, float]],
                       stats: Dict[str, Any],
                       output_cfg) -> List[Tuple[Node, float]]:
                                                                   

                                                                         
                                                                          
                                                                          
                                                                       
                                                                              
       
    min_mbps = float(getattr(output_cfg, "min_speed_mbps", 0.0) or 0.0)
    max_ms = float(getattr(output_cfg, "max_latency_ms", 0) or 0.0)
    enabled = min_mbps > 0 or max_ms > 0

    reasons: Counter = Counter()
    kept: List[Tuple[Node, float]] = list(final)
    unmeasured = 0

    if enabled and final:
        LOG(f"[quality] gate: min speed {min_mbps:g} Mbps, "
            f"max latency {max_ms:g} ms")
        kept = []
        for node, ms in final:
            speed = _mbps_of(node, stats)
            if speed is None and min_mbps > 0:
                unmeasured += 1


            if max_ms > 0 and float(ms or 0.0) > max_ms:
                reasons["latency"] += 1
                continue
            if min_mbps > 0 and speed is not None and speed < min_mbps:
                reasons["speed"] += 1
                continue
            kept.append((node, ms))

    relaxed = False
    if enabled and final and not kept:
        keep = _keep_count(output_cfg)
        if keep > 0:
            kept = _relaxed_top(final, stats, keep)
            relaxed = True
            LOG(f"[quality] gate would drop all {len(final)} node(s) — "
                f"safety valve keeps top {len(kept)} by speed (relaxed)")

    latency_ms, latency_unknown = _latency_snapshot(final)
    gate = {
        "enabled": enabled,
        "min_speed_mbps": min_mbps,
        "max_latency_ms": max_ms,
        "checked": len(final),
        "kept": len(kept),
        "dropped": len(final) - len(kept),
        "drop_reasons": dict(reasons),
        "unmeasured_speed": unmeasured,
        "relaxed": relaxed,




        "latency_ms": latency_ms,
        "latency_unknown": latency_unknown,
    }
    stats["quality_gate"] = gate

    if enabled and final and not relaxed:
        detail = ", ".join(f"{k} {v}" for k, v in reasons.most_common())
        unmeasured_note = (f", {unmeasured} without speed (kept)"
                           if unmeasured else "")
        LOG(f"[quality] kept {len(kept)}/{len(final)}, "
            f"dropped {gate['dropped']}"
            + (f" ({detail})" if detail else "")
            + unmeasured_note)
    return kept


def apply_latency_prefilter(final: List[Tuple[Node, float]],
                            stats: Dict[str, Any],
                            output_cfg) -> List[Tuple[Node, float]]:
                                                                          

                                                                          
                                                                           
                                                                           
                                                                    
                                                                       

                                                                     
                                                                    
                                                        
                                                                       
                                                     

                                                                        
                                                                          
                                                  

                                                                    
                                                                              
                                                      
       
    max_ms = float(getattr(output_cfg, "max_latency_ms", 0) or 0.0)
    keep = _keep_count(output_cfg)
    enabled = max_ms > 0
    kept = list(final)
    dropped = 0
    relaxed = False
    if enabled and final:


        kept = [(node, ms) for node, ms in final
                if not (float(ms or 0.0) > max_ms)]
        dropped = len(final) - len(kept)
        if not kept and keep > 0:
            kept = sorted(final, key=lambda it: float(it[1] or 0.0))[:keep]
            relaxed = True
            LOG(f"[quality] prefilter would drop all {len(final)} node(s) — "
                f"safety valve keeps top {len(kept)} by latency")

    latency_ms, latency_unknown = _latency_snapshot(final)
    stats["quality_prefilter"] = {
        "enabled": enabled,
        "max_latency_ms": max_ms,
        "checked": len(final),
        "kept": len(kept),
        "dropped": dropped,
        "relaxed": relaxed,



        "latency_ms": latency_ms,
        "latency_unknown": latency_unknown,
    }
    if enabled and dropped and not relaxed:
        LOG(f"[quality] prefilter: kept {len(kept)}/{len(final)}, "
            f"dropped {dropped} over {max_ms:g} ms (before full speedtest)")
    return kept
