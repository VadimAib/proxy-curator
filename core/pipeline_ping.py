                                                                         

                                                                                                                  
                                                                        
                                                                          
                                                              
                                                                     
                                                                          
                                           
   
from pathlib import Path
from typing import Any

from .config import Config
from .log import LOG
from .nodes_cache import skip_dead_nodes
from .phases.probe import tcping_phase
from .resume import save_state
from .state import PipelineState
from .trusted_nodes import load_trusted_nodes, split_trusted_nodes


def run_ping_block(state: PipelineState, cfg: Config,
                   cache_dir: Path, monitor: Any) -> None:
                                                                             

                                                                         
                                                                           
                                                                
       

    state.current_phase = "tcping"
    state.alive = [(n, 0.0) for n in state.nodes]
    state.final = []
    save_state(state)













    if cfg.testing.dead_nodes_cache_enabled:
        trusted: list = []
        normal = list(state.alive)
        if cfg.testing.trusted_nodes_enabled:
            trusted_ck = load_trusted_nodes(
                Path(cfg.output.working_nodes).with_suffix(".json"),
                cfg.testing.trusted_nodes_ttl_hours)
            if trusted_ck:
                trusted, normal = split_trusted_nodes(state.alive, trusted_ck)
        normal, dead_skipped = skip_dead_nodes(
            cache_dir, normal, cfg.testing.dead_nodes_ttl_hours,
            state.stats.get("network_fingerprint"))
        state.alive = trusted + normal
        if dead_skipped:
            state.nodes = [n for n, _ in state.alive]
            LOG(f"[ping] skipped {dead_skipped} dead nodes from cache")
    tcping_phase(state, cfg, monitor)




    if cfg.testing.max_tcp_latency > 0:
        before = len(state.alive)
        hard_limit = cfg.testing.max_tcp_latency
        soft_limit = cfg.testing.max_tcp_latency_soft
        kept: list = []
        overshoot: list = []
        for n, m in state.alive:
            if m > hard_limit:
                continue
            if soft_limit > 0 and m > soft_limit:
                overshoot.append(n.key())
            kept.append((n, m))
        state.stats["tcp_latency_overshoot"] = overshoot
        state.alive = kept
        if before != len(state.alive):
            LOG(f"[ping] max_tcp_latency {hard_limit} ms: "
                f"{before} -> {len(state.alive)}")
        if overshoot:
            LOG(f"[ping] tcp_latency_overshoot {soft_limit}<ms<={hard_limit}: "
                f"{len(overshoot)} node(s)")
