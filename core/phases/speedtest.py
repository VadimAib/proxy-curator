                                                     

                                                                  

                                                                          
                                                                              
                        
                                                                         
                                                                           
                                 
                                                                        
                                                         

                                                                          
                                                                            
                                                                                 
   
from collections import Counter
from typing import Dict, List, Tuple
from ..config import Config
from ..engine.engines import EngineRuntime
from ..log import LOG
from ..models import Node
from ..engine.ports import PortPool
from ..state import PipelineState
from .speedtest_measure import (_detect_channel_profile_from_state, _run_tier,
                                escalation_saved)
from ..speed_profile import (normalize_speed_profile,
                             speed_profile_for_channel)

RESCUABLE_REASONS = ("no_bypass", "critical_failed:", "tcp_latency_soft")




def speedtest_quick_phase(state: PipelineState,
                           engines: Dict[str, EngineRuntime], cfg: Config,
                           port_pool: PortPool) -> None:
                                                                

                                                                           
                                                                           
                                                                         
                                                                           

                                                                            
                                                                           
                                                               
       
    speed_cfg = getattr(cfg, "speedtest", None)
    if speed_cfg is None or not getattr(speed_cfg, "enabled", True):
        LOG("[speedtest] quick tier skipped (speedtest disabled)")
        return
    if not getattr(speed_cfg, "quick_enabled", True):
        LOG("[speedtest] quick tier skipped (quick.enabled=false)")
        return
    if not state.alive:
        LOG("[speedtest] quick: no candidates to test")
        state.stats.setdefault("speedtest_quick", {})
        return

    nbytes = int(speed_cfg.quick_bytes)
    timeout = float(speed_cfg.quick_timeout)
    retries = int(speed_cfg.quick_retries)
    workers = max(1, int(speed_cfg.quick_workers))
    min_mbps = float(speed_cfg.quick_min_mbps)
    drop_failed = bool(speed_cfg.quick_drop_failed)
    url = str(speed_cfg.url) + str(nbytes)
    total = len(state.alive)
    LOG(f"[speedtest] quick tier: {total} candidates, bytes={nbytes}, "
        f"timeout={timeout}s, workers={workers}, retries={retries}, "
        f"min_mbps={min_mbps}, drop_failed={drop_failed}")


    state.quick_pool = list(state.alive)
    results, fail_detail = _run_tier(state.alive, engines, url, nbytes, timeout,
                                     retries, workers, "speed-q")


    state.stats["speedtest_quick_saved_by_escalation"] = escalation_saved()


    for node, tcp_ms in state.alive:
        hit = results.get(node.key())
        if hit is not None:
            hit["tcp_ms"] = round(float(tcp_ms), 1)

    kept: List[Tuple[Node, float]] = []



    drops: Counter = Counter()
    for item in state.alive:
        key = item[0].key()
        hit = results.get(key)
        if hit is None:
            if drop_failed:




                drops[fail_detail.get(key, "quick_failed")] += 1
                continue
        elif min_mbps > 0 and float(hit["mbps"]) < min_mbps:
            drops["quick_slow"] += 1
            continue
        kept.append(item)
    state.alive = kept

    state.stats["speedtest_quick"] = results
    state.stats["speedtest_quick_tested"] = total
    state.stats["speedtest_quick_ok"] = len(results)
    state.stats["speedtest_quick_dropped"] = total - len(kept)
    state.stats["speedtest_quick_drop_reasons"] = dict(drops)
    LOG(f"[speedtest] quick done: {len(results)}/{total} measured, "
        f"{total - len(kept)} dropped, {len(kept)} -> DELAY")
    for reason, cnt in drops.most_common(5):
        LOG(f"         -{cnt:<5} {reason}")




def speedtest_phase(state: PipelineState,
                   engines: Dict[str, EngineRuntime], cfg: Config,
                   port_pool: PortPool) -> None:
                                                              

                                                                         
                                                          
       
    speed_cfg = getattr(cfg, "speedtest", None)
    if speed_cfg is None or not getattr(speed_cfg, "enabled", True):
        LOG("[speedtest] disabled")
        return
    if not state.final:
        LOG("[speedtest] no working nodes to test")
        state.stats.setdefault("speedtest", {})
        return

    stats = state.stats
    detected = _detect_channel_profile_from_state(state)
    LOG(f"[speedtest] channel profile: {detected}")



    override = normalize_speed_profile(
        stats.get("profile_override")) or ""
    manual = override in ("full", "light")
    if manual:
        net_type = override
        LOG(f"[speedtest] profile overridden by owner: {net_type} "
            f"(auto-detect said {detected})")
    else:
        net_type = speed_profile_for_channel(detected)
    if net_type == "light":
        nbytes = int(speed_cfg.light_bytes)
        timeout = float(speed_cfg.light_timeout)
    else:
        nbytes = int(speed_cfg.full_bytes)
        timeout = float(speed_cfg.full_timeout)
    full_url = str(speed_cfg.url) + str(nbytes)
    retries = int(getattr(speed_cfg, "retries", 1))
    workers = max(1, int(getattr(speed_cfg, "workers", 5)))








    cap = max(0, int(getattr(speed_cfg, "full_max_measure", 0)))
    to_measure = state.final
    if cap and len(to_measure) > cap:
        quick = stats.get("speedtest_quick") or {}


        to_measure = sorted(
            to_measure,
            key=lambda it: float((quick.get(it[0].key()) or {})
                                 .get("mbps", -1.0) or -1.0),
            reverse=True)[:cap]
        skipped = len(state.final) - cap
        stats["speedtest_full_skipped"] = skipped
        LOG(f"[speedtest] full tier capped: {cap}/{len(state.final)} nodes "
            f"(top by quick speed); {skipped} keep quick measurement only")
    LOG(f"[speedtest] testing {len(state.final)} nodes, profile="
        f"{net_type}"
        f" (bytes={nbytes}, timeout={timeout}s, workers={workers}, "
        f"retries={retries})")

    results, fail_detail = _run_tier(to_measure, engines, full_url, nbytes,
                                     timeout, retries, workers, "speedtest")
    state.stats["speedtest"] = results
    state.stats["speedtest_saved_by_escalation"] = escalation_saved()



    if fail_detail:
        state.stats["speedtest_fail_reasons"] = dict(Counter(
            fail_detail.values()))
    state.stats["speedtest_network"] = detected
    state.stats["speedtest_profile"] = net_type


    state.stats["speedtest_profile_source"] = "manual" if manual else "auto"



    order = {k: v.get("mbps", -1.0) for k, v in results.items()}
    state.final.sort(key=lambda n: order.get(n[0].key(), -1.0), reverse=True)

    ok_n = len(results)
    if ok_n:
        top = [f"{results[n.key()]['mbps']:.1f}Mbps {n.name[:40]}"
               for n, _ in state.final[:3] if n.key() in results]
        LOG(f"[speedtest] done: {ok_n}/{len(state.final)} measured"
            + ("; top: " + "; ".join(top) if top else ""))
        return
    LOG(f"[speedtest] done: 0/{len(state.final)} measured")




def is_rescuable_reason(reason: str) -> bool:
                                                                                                                                         
    return any(reason == r or reason.startswith(r) for r in RESCUABLE_REASONS)


def rescue_phase(state: PipelineState, cfg: Config) -> None:
                                                                                    

                                                       
                                                                              
                                                                                
                                                                         
                                                                       
                                                       

                                                                          
                                                                         
                                                                    
                                                                   

                                                                       
                                                                      
                                                                    

                                                                         
                                                   
                                                                      
                                                                          
       
    stats = state.stats
    stats["rescued"] = []
    stats["rescued_count"] = 0
    speed_cfg = getattr(cfg, "speedtest", None)
    if speed_cfg is None or not getattr(speed_cfg, "rescue_enabled", False):
        LOG("[rescue] skipped (rescue disabled)")
        return
    dropped = stats.get("delay_drop_reasons") or {}
    overshoot = set(stats.get("tcp_latency_overshoot") or [])
    quick = stats.get("speedtest_quick") or {}
    if not dropped and not overshoot or not quick or not state.quick_pool:
        LOG("[rescue] nothing to rescue (no quick measurements or drop reasons)")
        return

    floor = float(speed_cfg.rescue_min_mbps)
    in_final = {n.key() for n, _ in state.final}
    rescued_keys: List[str] = []
    rejected: Counter = Counter()
    for node, tcp_ms in state.quick_pool:
        key = node.key()
        if key in in_final:
            continue

        reason = dropped.get(key)

        if reason is None and key in overshoot:
            reason = "tcp_latency_soft"
        if reason is None:
            continue
        if not is_rescuable_reason(reason):
            rejected[reason] += 1
            continue
        hit = quick.get(key)
        if not isinstance(hit, dict) or "mbps" not in hit:
            rejected[f"{reason} (slow/no-measure)"] += 1
            continue
        mbps = float(hit["mbps"])
        if mbps < floor:
            rejected[f"{reason} (slow/no-measure)"] += 1
            continue


        latency = float(hit.get("tcp_ms", tcp_ms) or tcp_ms or 0.0)
        state.final.append((node, latency))
        in_final.add(key)
        rescued_keys.append(key)

    stats["rescued"] = rescued_keys
    stats["rescued_count"] = len(rescued_keys)
    if rescued_keys:
        shown = ", ".join(f"{quick.get(k, {}).get('mbps')}Mbps"
                          for k in rescued_keys[:5])
        LOG(f"[rescue] returned {len(rescued_keys)} node(s) to output "
            f"(quick >= {floor}Mbps): {shown}")
    else:
        LOG(f"[rescue] nothing returned (floor={floor}Mbps)")
    for reason, cnt in rejected.most_common(5):
        LOG(f"         skip {cnt:<5} {reason}")

