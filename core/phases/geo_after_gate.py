                                                                             

                                                                           
                                                                         
                                                                     
                                                                            
                                                                            
                                                                          
                                                       
                                                                    

                                                                          
                                                                      
                                                         
                                                                    
                                                             

        

                                                                           
                                                                 
                                                                      
                                                                    
                                                                          
                                                                      
           
                                                                      
                                                                      
                                                          

                                                                       
                                                        
                                                                           
                                                    
   
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

from ..config import Config
from ..engine.engines import EngineRuntime, engine_name_for
from ..filters import geo_lookup_enabled
from ..log import LOG
from ..models import Node
from ..net.geo_cache import GEO_CACHE_FILE, init_geo_cache, save_geo_cache
from ..net.geoip import (GEO_TIMEOUT, GeoState, fetch_country_via_port,
                         get_cached_country, set_cached_country)
from ..output_quality import _keep_count
from ..paths import rp
from ..state import PipelineState
from ..ui import ProgressBar
from .geofilter import _drop_by_exit_country
from .geo_record import _record_geo




GEO_PROBE_WORKERS = 4


def _country_through(node: Node, rt: EngineRuntime, timeout: float,
                     geo: GeoState) -> Optional[str]:
                                                                      

                                                                       
                                                                   
                                                                         
                                        
       
    engine = rt.engine
    port = engine.port_pool.get_port()
    try:
        with engine.probe_session(node, str(rt.binary), port):
            return fetch_country_via_port(port, timeout, breaker=geo.breaker)
    finally:
        try:
            engine.port_pool.release_port(port)
        except Exception:
            pass


def _probe_countries(state: PipelineState,
                     engines: Dict[str, EngineRuntime],
                     cfg: Config, geo: GeoState) -> None:
                                                                      

                                                                           
                                                                   
                                                                        
                               
       
    timeout = getattr(cfg.testing, "geoip_timeout", 0.0) or GEO_TIMEOUT
    workers = GEO_PROBE_WORKERS
    pending: List[Tuple[Node, EngineRuntime]] = []
    cached = 0
    for node, _ in state.final:
        host_port = f"{node.host.lower()}:{node.port}"
        code = get_cached_country(host_port)
        if code is not None:
            geo.add(node.key(), code)
            cached += 1
            continue



        if geo.breaker.is_open:
            continue
        rt = engines.get(engine_name_for(node))
        if rt is None or not rt.available():
            continue
        pending.append((node, rt))

    if not pending:
        if cached:
            LOG(f"[geo] {cached} country(ies) from cache, no probe needed")
        return

    LOG(f"[geo] probing exit country for {len(pending)} node(s) "
        f"({cached} from cache)")

    def _one(item: Tuple[Node, EngineRuntime]) -> Tuple[Node, Optional[str]]:
        node, rt = item
        if geo.breaker.is_open:
            return node, None
        try:
            return node, _country_through(node, rt, timeout, geo)
        except Exception:
            return node, None

    bar = ProgressBar(len(pending), "geo", log_progress=True, unit="nodes")
    bar.begin()
    try:
        with ThreadPoolExecutor(max_workers=workers,
                                thread_name_prefix="geo") as ex:
            futures = [ex.submit(_one, item) for item in pending]
            for fut in as_completed(futures):
                node, code = fut.result()
                if code is not None:


                    set_cached_country(f"{node.host.lower()}:{node.port}",
                                       code)
                geo.add(node.key(), code)
                bar.update(code is not None)
    finally:
        bar.finish()

    asked = geo.breaker.answered
    LOG(f"[geo] service answered for {asked}/{len(pending)} probed node(s)")


def _unknown_valve(final: List[Tuple[Node, float]], geo: GeoState,
                   keep: int) -> List[Tuple[Node, float]]:
                                                                      

                                                                          
                                                                         
                                                                     
                                                          
       
    if keep <= 0:
        return []
    return [(n, ms) for n, ms in final
            if n.key() not in geo.countries][:keep]


def _collect_countries(state: PipelineState,
                       engines: Dict[str, EngineRuntime],
                       cfg: Config) -> Optional[GeoState]:
                                                        

                                                                         
                                          
       
    if not geo_lookup_enabled(cfg.filters):
        return None
    init_geo_cache(cfg.filters.geo_cache_enabled, cfg.filters.geo_cache_ttl_hours,
                   path=rp(cfg.output.cache_dir) / GEO_CACHE_FILE)
    geo = GeoState()
    _probe_countries(state, engines, cfg, geo)
    return geo


def record_countries(state: PipelineState,
                     engines: Dict[str, EngineRuntime],
                     cfg: Config) -> None:
                                                                               

                                                                         
                                                                        
                                                                     
                                                                       
                                                                           
                                                  

                                                                         
                                                                          
                                                                        
                                                                       
                                         

                                                                          
       
    if not state.final:
        return
    geo = _collect_countries(state, engines, cfg)
    if geo is None:
        LOG("[geo] skipped (country filter disabled in config)")
        return
    _record_geo(state.stats, geo)
    save_geo_cache()


def geo_after_gate_phase(state: PipelineState,
                         engines: Dict[str, EngineRuntime],
                         cfg: Config) -> None:
                                                               

                                                                           
                                                                       
                                                                
       
    stats = state.stats
    if not state.final:
        LOG("[geo] skipped (no nodes left after quality gate)")
        return
    geo = _collect_countries(state, engines, cfg)
    if geo is None:
        LOG("[geo] skipped (country filter disabled in config)")
        return

    before = state.final
    final = _drop_by_exit_country(before, geo, cfg)
    relaxed = False
    valve_kept: List[Tuple[Node, float]] = []
    if before and not final:
        valve_kept = _unknown_valve(before, geo, _keep_count(cfg.output))
        if valve_kept:
            final = valve_kept
            relaxed = True
            LOG(f"[geo] country filter would drop all {len(before)} node(s) "
                f"— safety valve keeps top {len(valve_kept)} unknown "
                "(no blacklisted country returned)")
        else:
            LOG(f"[geo] country filter dropped all {len(before)} node(s) "
                "and no unknown node is available — output is empty")

    state.final = final
    stats["geo_gate"] = {
        "checked": len(before),
        "kept": len(final),
        "dropped": len(before) - len(final),
        "relaxed": relaxed,
        "valve_unknown_kept": len(valve_kept),
    }


    _record_geo(stats, geo)
    save_geo_cache()
