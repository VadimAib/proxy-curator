                                                                     

                                                                           
                                                                        
                                                                            
                                                 

                                                                              
                                                              
                                                          

                                                                 
                                                                   
                                                                     
                                                                 

                                                                        
                                                                         
                                                     

                                                                          
                                          
   
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

from .connectivity_recheck import maybe_recheck, run_first_round
from ..engine.batch import run_batch_tests
from ..config import Config
from ..engine.engines import EngineRuntime, engine_name_for
from ..log import LOG
from ..models import Node
from ..engine.ports import PortPool
from ..state import PipelineState
from ..ui import ProgressBar
from ..utils import reason_key


def _conn_work(groups: Dict[str, List[Tuple[Node, float]]],
               engines: Dict[str, EngineRuntime],
               batch_size: int) -> List[Tuple[str, List[Tuple[Node, float]]]]:
                                                                        

                                                                                  
                                                                          
       
    work: List[Tuple[str, List[Tuple[Node, float]]]] = []
    for name, items in groups.items():
        rt = engines.get(name)
        if rt is None or not rt.available():
            continue
        for batch in _conn_batches(items, batch_size):
            work.append((name, batch))
    return work


def _conn_cap(cfg: Config) -> float:
                                                              

                                                              
                                                                 
                                                                               
       
    cap = getattr(cfg.testing, 'connectivity_prefilter_timeout', 1.0) or 1.0
    return min(cfg.testing.timeout, cap)


def _conn_batches(items: List[Tuple[Node, float]],
                  batch_size: int) -> List[List[Tuple[Node, float]]]:
                                                                                                                     
    return [items[i:i + batch_size]
            for i in range(0, len(items), batch_size)]


def _phase_input(state: PipelineState,
                 ) -> Tuple[Dict[str, List[Tuple[Node, float]]],
                            Dict[str, Node], int]:
                                                                                                                    
    groups: Dict[str, List[Tuple[Node, float]]] = {}
    index: Dict[str, Node] = {}
    for n, tcp_ms in state.alive:
        name = engine_name_for(n)
        if name:
            groups.setdefault(name, []).append((n, tcp_ms))
            index[n.key()] = n
    return groups, index, sum(len(v) for v in groups.values())


def _move_no_engine_to_final(state: PipelineState,
                            stats: Dict[str, Any]) -> None:
                                                               

                                                                     
                                                                    
                                                                    
                                                                 
                                                                      
                                                    
                                                                    
                                          

                                                        
       
    no_engine = [pair for pair in state.alive
                 if not engine_name_for(pair[0])]
    if not no_engine:
        return
    state.final.extend(no_engine)
    stats["mtproto_unverified"] = len(no_engine)
    protos = ", ".join(sorted({n.protocol.value for n, _ in no_engine}))
    LOG(f"[conn] no-engine nodes ({len(no_engine)}, {protos}, secret "
        f"unverified) -> final")
    state.alive = [pair for pair in state.alive
                   if engine_name_for(pair[0])]


def connectivity_phase(
    state: PipelineState,
    engines: Dict[str, EngineRuntime], cfg: Config,
    port_pool: PortPool,
    bar: Optional[ProgressBar] = None,
) -> None:
                                                                      

                                                                          
                                                                    
                                                                           
                                                                       

                                                                                  
                                                                          
                                       
       
    stats = state.stats

    _move_no_engine_to_final(state, stats)
    groups, index, total_conn = _phase_input(state)

    if total_conn == 0:
        state.alive = []
        return

    conn_batch = cfg.testing.connectivity_batch_size
    max_parallel = cfg.testing.connectivity_workers


    LOG(f"[conn] pre-filter connectivity check: {total_conn} nodes, "
        f"connectivity-only timeout={_conn_cap(cfg)}s, batch_size={conn_batch}, "
        f"max_parallel={max_parallel}, port_pool={cfg.testing.port_pool_size}")

    if bar is None:
        bar = ProgressBar(total_conn, "conn", log_progress=True, unit="nodes")
    bar.begin()




    rnd = run_first_round(_conn_work(groups, engines, conn_batch),
                          engines, cfg, bar, max_parallel, _run_conn_round)
    connectivity_ok, conn_fail = rnd.ok, rnd.fail
    fail_detail = rnd.fail_detail



    maybe_recheck(fail_detail, index, connectivity_ok, conn_fail, engines,
                  getattr(cfg.testing, "recheck_pause_sec", 0.0),
                  conn_batch, max_parallel, bar, cfg,
                  _conn_work, _run_conn_round, sleep=time.sleep)

    bar.finish()
    _conn_report(stats, connectivity_ok, conn_fail, total_conn)
    state.alive = connectivity_ok

    state.conn_drops = {k: (index[k], reason)
                        for k, reason in fail_detail.items() if k in index}







def _conn_report(stats: Dict[str, Any],
                 connectivity_ok: List[Tuple[Node, float]],
                 conn_fail: Dict[str, int], total_conn: int) -> None:
                                                 

                                                                         
                                                                             
                                                  
       
    skipped = total_conn - len(connectivity_ok)
    LOG(f"[conn] pre-filter: {len(connectivity_ok)} passed, {skipped} dropped")
    if conn_fail:
        for e, c in sorted(conn_fail.items(), key=lambda x: -x[1])[:5]:
            LOG(f"         -{c:<5} {e}")
    stats["connectivity_filtered"] = len(connectivity_ok)
    stats["connectivity_dropped"] = skipped




    stats["connectivity_drop_reasons"] = dict(conn_fail)


def _run_conn_round(work: List[Tuple[str, List[Tuple[Node, float]]]],
                    engines: Dict[str, EngineRuntime], cfg: Config,
                    bar, max_parallel: int,
                    fail_detail: Optional[Dict[str, str]] = None,
                    ) -> Dict[int, Tuple[List, Dict]]:
                                             

                                                                             
                                                               
                                                                      
                                                                           
                                                  
                                                                
                                                                

                                                                          
                                                                         
                                                                 
       
    results: Dict[int, Tuple[List, Dict]] = {}
    errors: List[BaseException] = []
    lock = threading.Lock()

    def _run(idx: int, name: str, items: List[Tuple[Node, float]]) -> None:
        rt = engines.get(name)
        if rt is None:
            return
        try:
            ok, fr, _, _ = run_batch_tests(
                {name: items}, rt, cfg, verbose=False, bar=bar,
                batch_size=len(items), connectivity_only=True,
                fail_detail=fail_detail,
            )
            with lock:
                results[idx] = (ok, fr)
        except BaseException as e:
            with lock:
                errors.append(e)

    pending: List[Tuple[int, str, List]] = [
        (i, n, it) for i, (n, it) in enumerate(work)
    ]
    active: Dict = {}

    with ThreadPoolExecutor(max_workers=max_parallel) as ex:
        while pending or active:
            while pending and len(active) < max_parallel:
                item = pending.pop(0)
                if len(item) != 3:
                    continue
                idx, name, items = item
                active[ex.submit(_run, idx, name, items)] = (idx, name, items)

            if not active:
                break




            done = next(as_completed(active))
            active.pop(done, None)
            done.result()

    if errors:
        raise errors[0]
    return results


def _merge_conn(results: Dict[int, Tuple[List, Dict]],
                ) -> Tuple[List[Tuple[Node, float]], Dict[str, int]]:
                                                                      

                                                                        
                                                     
       
    ok_all: List[Tuple[Node, float]] = []
    fail: Dict[str, int] = {}
    for _idx, (ok, fr) in results.items():
        ok_all.extend(ok)
        for k, v in fr.items():
            key = reason_key(k)
            fail[key] = fail.get(key, 0) + v
    return ok_all, fail
