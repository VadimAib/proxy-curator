                                                                  

                                                                         
                                                                     
                                                                            
                                                                       
                                                              

                                                                           
                                                                           

                                                                         

                                                                       
                                                            
                   

                                                                          
                                                                       
                                                                            
                                    

                                                                       
                                                              
                                                                             
                                                                        
                                                                       
                                                                        
                                                                       
                                                                      
                                                                            
                
   
from collections import Counter
from typing import Dict, List, Tuple

from ..config import Config
from ..engine.engines import EngineRuntime, engine_name_for
from ..log import LOG
from ..models import Node
from ..net.netmon import NetworkMonitor, wait_internet
from ..engine.ports import PortPool
from ..resume import save_state
from ..state import PipelineState
from ..ui import ProgressBar, fmt_dur
from ..engine.xray_fp import log_fingerprint_substitutions
from .critical import critical_canary
from .critical_tunnel import critical_tunnel_canary, make_probe
from .delay_rounds import (_apply_e2e_cap, _build_pools, _pending_by_engine,
                           _rebuild_pending, _run_delay_round)


def _record_delay_stats(stats: Dict, drop_details: Dict[str, str],
                        fail_all: Dict[str, int],
                        final: List[Tuple[Node, float]]) -> None:
                                                   

                                                                       
                                                                       
                                                                            
                                                                        
       
    stats["delay_drop_reasons"] = drop_details
    stats.update({"delay_ok": len(final), "delay_fail_reasons": fail_all})


def _tcping_only_exit(state: PipelineState) -> None:
                                                                        

                                                  
                                       
                                                                        
                                                                     
                                                                       
                                                                
                                                                          
       



    no_engine = [p for p in state.final if not engine_name_for(p[0])]
    state.final = list(state.alive) + no_engine
    LOG(f"[delay] skipped (--tcping-only): {len(state.final)} nodes as-is"
        + (f" ({len(no_engine)} no-engine, secret unverified)"
           if no_engine else ""))
    state.stats.update({"delay_tested": 0, "delay_ok": 0,
                        "delay_fail_reasons": {}, "mode": "tcping_only"})


def _wait_for_outage(monitor: NetworkMonitor, attempt: int,
                     ok_all: List[Tuple[Node, float]],
                     remaining: List[Tuple[Node, float]]) -> bool:
                                                                               

                                                                
                                                                           
                                                                      
       
    LOG(f"[net] outage {attempt}: {len(ok_all)} ok saved, "
        f"{len(remaining)} in queue, waiting for connection...")
    w = wait_internet(monitor)
    if monitor.is_down:
        LOG(f"[net] still down after {fmt_dur(w)} (wait cap) — "
            f"continuing anyway ({len(remaining)} left)")
        return False
    LOG(f"[net] OK: connection restored in {fmt_dur(w)}, "
        f"continuing ({len(remaining)} left)")
    return True


def delay_phase(state: PipelineState,
                 engines: Dict[str, EngineRuntime], cfg: Config, args,
                 monitor: NetworkMonitor, port_pool: PortPool) -> None:
                                                                      

                                                                               
                                                                               
                                                            
       
    stats = state.stats
    candidates = state.alive

    if args.tcping_only:
        _tcping_only_exit(state)
        return


    excluded = critical_canary(cfg, stats)

    pools, _ = _build_pools(state, engines)




    if excluded and pools:
        critical_tunnel_canary(
            cfg, stats,
            make_probe(engines, [n for _, items in pools for n, _ in items], cfg),
            excluded)

    stats["delay_tested"] = sum(len(items) for _, items in pools)
    stats["delay_pools"] = {rt.name: len(items) for rt, items in pools}

    if not pools and not state.final:
        LOG("[delay] no candidates to test")
        stats.update({"delay_ok": 0, "delay_fail_reasons": {}})
        return

    LOG(f"[ports] pool of {port_pool.size} ports shared by {len(pools)} "
        "engine pool(s): "
        + (", ".join(f"{rt.name}={len(items)}" for rt, items in pools) or "-"))
    for rt, _ in pools:
        LOG(f"[delay] pool {rt.name}: {rt.binary}")

    verbose = len(candidates) <= 200 or args.report
    total_nodes = sum(len(items) for _, items in pools)
    batch_size = getattr(cfg.testing, 'batch_size', 15)
    batch_workers = getattr(cfg.testing, 'batch_workers', 1)
    batch_stagger_ms = getattr(cfg.testing, 'batch_stagger_ms', 0)
    LOG(f"[delay] testing {total_nodes} nodes across {len(pools)} engine(s), "
        f"batch_size={batch_size}, batch_workers={batch_workers}, "
        f"batch_stagger_ms={batch_stagger_ms}, "
        f"verbose={'on' if verbose else 'off'}")

    ok_all: List[Tuple[Node, float]] = list(state.final)
    fail_all: Dict[str, int] = {}




    drop_details: Dict[str, str] = {}
    remaining = list(candidates)
    attempt = 0

    total_tasks = len(remaining) + len(ok_all)
    bar = ProgressBar(total_tasks, "delay", log_progress=True, unit="nodes")
    bar.done = len(ok_all)
    bar.ok = sum(1 for _, ms in ok_all if ms is not None)

    try:
        while remaining:


            state.alive = remaining
            state.current_phase = "delay"
            save_state(state)

            pending = _pending_by_engine(remaining, pools)
            results = _run_delay_round(
                pending, cfg, verbose, bar, batch_size, ok_all, fail_all,
                drop_details, batch_workers)

            if not pending:
                remaining = []
                break

            remaining = _rebuild_pending(remaining, results, pools)

            attempt += 1
            if monitor.is_down:
                _wait_for_outage(monitor, attempt, ok_all, remaining)
            else:



                break
    finally:
        bar.finish()

    if fail_all:
        LOG("[delay] final failures:")
        for e, c in sorted(fail_all.items(), key=lambda x: -x[1])[:8]:
            LOG(f"         -{c:<5} {e}")

    final = _apply_e2e_cap(ok_all, cfg, fail_all)

    by_engine = Counter(engine_name_for(n) or "unknown" for n, _ in final)
    stats["delay_ok_by_engine"] = dict(sorted(by_engine.items()))
    if by_engine:
        LOG("[delay] ok by engine: " + ", ".join(
            f"{k}={v}" for k, v in sorted(by_engine.items())))


    final.sort(key=lambda x: x[1])

    state.final = final
    _record_delay_stats(stats, drop_details, fail_all, final)

    log_fingerprint_substitutions()
