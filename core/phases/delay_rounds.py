                                                                     

                                                                  
                                                                         
                                                                          
                                                                             

                                                                                    

                                                                           
                                               
                                                                          
                                                 
                                                                    
                                                                     
                                                
   
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

from ..engine.batch import run_batch_tests
from ..config import Config
from ..engine.engines import EngineRuntime, engine_name_for
from ..log import LOG
from ..models import Node
from ..state import PipelineState


def _stagger_sleep(sec: float) -> None:
                                                 

                                                                          
                                                                        
                                                                      
                                                                   
                                                                          
                       
       
    time.sleep(sec)


def _build_pools(state: PipelineState, engines: Dict[str, EngineRuntime],
                 ) -> Tuple[List[Tuple[EngineRuntime, List[Tuple[Node, float]]]], int]:
                                                                     

                                                                        
                                                                         
                                                                          
       
    groups: Dict[str, List[Tuple[Node, float]]] = {}
    no_engine = 0
    for item in state.alive:
        name = engine_name_for(item[0])
        if not name:
            no_engine += 1
            continue
        groups.setdefault(name, []).append(item)

    pools: List[Tuple[EngineRuntime, List[Tuple[Node, float]]]] = []
    for name, items in groups.items():
        rt = engines.get(name)
        if rt is None:
            reason = "no engine in registry"
        elif not rt.enabled:
            reason = "disabled in config.yaml"
        elif rt.binary is None:
            reason = "binary path not set"
        elif not rt.available():
            reason = f"binary not found ({rt.binary})"
        else:
            pools.append((rt, items))
            continue
        state.stats[f"delay_skipped_{name}"] = len(items)
        LOG(f"[delay] engine {name} unavailable ({reason}) — "
            f"{len(items)} node(s) skipped")

    if no_engine:
        state.stats["delay_no_engine"] = no_engine
        LOG(f"[delay] {no_engine} node(s) without engine — skipped")
    return pools, no_engine


def _pending_by_engine(
    remaining: List[Tuple[Node, float]],
    pools: List[Tuple[EngineRuntime, List[Tuple[Node, float]]]],
) -> List[Tuple[EngineRuntime, List[Tuple[Node, float]]]]:
                                                                                                                                
    pending: List[Tuple[EngineRuntime, List[Tuple[Node, float]]]] = []
    for rt, _ in pools:
        items = [it for it in remaining if engine_name_for(it[0]) == rt.name]
        if items:
            pending.append((rt, items))
    return pending


def _run_delay_round(pending: List[Tuple[EngineRuntime, List[Tuple[Node, float]]]],
                     cfg: Config, verbose: bool, bar, batch_size: int,
                     ok_all: List[Tuple[Node, float]],
                     fail_all: Dict[str, int],
                     drop_details: Dict[str, str],
                     batch_workers: int = 1) -> Dict[str, Tuple]:
                                                             

                                                                         
                                                                          
                                                                            

                                                                    
                                                                      
                                                                            
                                                                       
                                        

                                                                         
                                                      
                                                                      
                                                                   

                                                
                                                                           
                                                   
                                                       
                                                                        
       
    results: Dict[str, Tuple] = {}
    pool_errors: List[BaseException] = []
    results_lock = threading.Lock()

    def _run_pool(rt: EngineRuntime, items: List[Tuple[Node, float]]) -> None:


        detail: Dict[str, str] = {}
        try:
            if batch_workers <= 1 or len(items) <= batch_size:

                res = run_batch_tests(
                    {rt.name: items}, rt, cfg, verbose, bar=bar,
                    batch_size=batch_size, connectivity_only=False,
                    fail_detail=detail,
                )
                with results_lock:
                    results[rt.name] = res
                    drop_details.update(detail)
                return




            chunks = [items[i:i + batch_size]
                      for i in range(0, len(items), batch_size)]
            parts: List[Optional[Tuple]] = [None] * len(chunks)
            part_details: List[Dict[str, str]] = [{} for _ in chunks]

            def _run_chunk(idx: int) -> None:
                parts[idx] = run_batch_tests(
                    {rt.name: chunks[idx]}, rt, cfg, verbose, bar=bar,
                    batch_size=batch_size, connectivity_only=False,
                    fail_detail=part_details[idx],
                )






            stagger_s = getattr(cfg.testing, 'batch_stagger_ms', 0) / 1000.0
            with ThreadPoolExecutor(max_workers=batch_workers,
                                    thread_name_prefix="delay-batch") as ex:
                futures = []
                for i in range(len(chunks)):
                    futures.append(ex.submit(_run_chunk, i))



                    if stagger_s > 0 and i < len(chunks) - 1:
                        _stagger_sleep(stagger_s)
                for fut in futures:
                    fut.result()

            ok_all_parts: List[Tuple[Node, float]] = []
            fr: Dict[str, int] = {}
            for part, det in zip(parts, part_details):
                if part is None:
                    continue
                ok_part, fr_part, _, _ = part
                ok_all_parts.extend(ok_part)
                for k, v in fr_part.items():
                    fr[k] = fr.get(k, 0) + v
                detail.update(det)
            with results_lock:
                results[rt.name] = (ok_all_parts, fr, False, [])
                drop_details.update(detail)
        except BaseException as e:
            pool_errors.append(e)

    with ThreadPoolExecutor(max_workers=len(pending),
                            thread_name_prefix="delay") as ex:
        futs = {ex.submit(_run_pool, rt, items): rt for rt, items in pending}
        LOG("[delay] pools launched: " + ", ".join(
            f"{rt.name}({len(items)} nodes)"
            for rt, items in pending))

        for fut in as_completed(futs):
            rt = futs[fut]
            try:
                fut.result()
            except BaseException as e:
                pool_errors.append(e)
                continue
            with results_lock:
                res = results.get(rt.name)
            if res is None:
                continue
            ok_batch, fr, _, _ = res
            ok_all.extend(ok_batch)
            for k, v in fr.items():
                fail_all[k] = fail_all.get(k, 0) + v
            bar.done += len(ok_batch)
            bar.ok += sum(1 for _, ms in ok_batch if ms is not None)
            LOG(f"[delay][{rt.name}] finished: "
                f"{len(ok_batch)} OK, {sum(fr.values())} failed")

    if pool_errors:
        raise pool_errors[0]
    return results


def _rebuild_pending(
    remaining: List[Tuple[Node, float]],
    results: Dict[str, Tuple],
    pools: List[Tuple[EngineRuntime, List[Tuple[Node, float]]]],
) -> List[Tuple[Node, float]]:
                                                                     

                                                                          
                                                          
       
    pending = _pending_by_engine(remaining, pools)

    for rt, items in pending:
        res = results.get(rt.name)
        if res is None:
            continue
        ok_batch, _, _, _ = res
        ok_keys = {n.key() for n, _ in ok_batch}
        failed_this_round = [n for n, _ in items if n.key() not in ok_keys]
        if failed_this_round:
            LOG(f"[delay] {len(failed_this_round)} {rt.name} node(s) failed this round, removing from queue")



    tested_keys = {n.key() for rt, items in pending for n, _ in items}
    return [(n, m) for n, m in remaining if n.key() not in tested_keys]


def _apply_e2e_cap(final: List[Tuple[Node, float]], cfg: Config,
                   fail_all: Dict[str, int]) -> List[Tuple[Node, float]]:
                                                                                                       
    max_e2e = getattr(cfg.testing, 'max_e2e_latency_ms', 0)
    if max_e2e > 0:
        before = len(final)
        final = [(n, ms) for n, ms in final if ms <= max_e2e]
        dropped = before - len(final)
        if dropped > 0:
            LOG(f"[filter] e2e latency > {max_e2e}ms: dropped {dropped} nodes")
            fail_all[f"e2e_latency>{max_e2e}ms"] = dropped
    return final
