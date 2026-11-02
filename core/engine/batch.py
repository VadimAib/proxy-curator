                                            

                                                                           
                                                                                
                                                                           
                                                                              
                                                                   

                                                                             
                                                                           
                                               
   
import time
from typing import Dict, List, Optional, Tuple

from ..config import Config
from .engines import EngineRuntime
from ..log import LOG, dlog
from ..models import Node
from ..ui import ProgressBar
from ..utils import first_line


def run_batch_tests(
    engine_items: Dict[str, List[Tuple[Node, float]]],
    runtime: EngineRuntime, cfg: Config, verbose: bool,
    bar: Optional[ProgressBar] = None,
    batch_size: int = 50,
    connectivity_only: bool = False,
    fail_detail: Optional[Dict[str, str]] = None,
) -> Tuple[List[Tuple[Node, float]], Dict[str, int], bool, List[Tuple[Node, float]]]:
                                                             

                                                                             

                                                                               
                                                                       
                                                                         
                                                                            
                                                           

                                                                         
                                                                     
                                                                        
                                                 
       
    nodes_list = [n for items in engine_items.values() for n, _ in items]
    total = len(nodes_list)
    if total == 0:



        return [], {}, False, []

    timeout = cfg.testing.timeout
    conn_timeout = getattr(cfg.testing, 'connectivity_timeout', 0.0)
    if connectivity_only:



        cap = getattr(cfg.testing, 'connectivity_prefilter_timeout', 1.0)
        if cap > 0:
            timeout = min(timeout, cap)
            if conn_timeout:
                conn_timeout = min(conn_timeout, cap)

    final = []
    fail_reasons: Dict[str, int] = {}
    tested = 0
    last_log_time = time.time()


    HEARTBEAT_INTERVAL = 15.0

    for batch_start in range(0, total, batch_size):
        batch_nodes = nodes_list[batch_start:batch_start + batch_size]
        batch_ports = [runtime.engine.port_pool.get_port() for _ in batch_nodes]

        try:
            for n, port, ms, err in runtime.engine.run_batch_test(
                batch_nodes, batch_ports, str(runtime.binary), timeout,
                cfg.connectivity_urls, cfg.bypass_urls,
                getattr(cfg, 'critical_urls', []),
                critical_timeout=cfg.testing.critical_timeout,
                connectivity_timeout=conn_timeout,
                bypass_timeout=getattr(cfg.testing, 'bypass_timeout', 0.0),
                critical_mode=getattr(cfg.testing, 'critical_mode', 'all'),
                connectivity_only=connectivity_only,
            ):

                try:
                    runtime.engine.port_pool.release_port(port)
                except Exception as e:

                    dlog(f"release_port({port}) failed: {first_line(e)}")

                if ms is not None:
                    final.append((n, ms))
                    if bar:
                        bar.update(True)
                    if verbose:
                        tcp_ms = next((m for items in engine_items.values() for nn, m in items if nn is n), 0)
                        LOG(f"  [{tested+1:>3}/{total}] OK   tcp={tcp_ms:>5.0f}ms "
                            f"e2e={ms:>6.0f}ms  {n.protocol.value:<6} {n.name[:45]}")
                else:
                    key = err or "unknown"
                    fail_reasons[key] = fail_reasons.get(key, 0) + 1
                    if fail_detail is not None:
                        fail_detail[n.key()] = key
                    if bar:
                        bar.update(False)
                    if verbose:
                        tcp_ms = next((m for items in engine_items.values() for nn, m in items if nn is n), 0)
                        LOG(f"  [{tested+1:>3}/{total}] DEAD tcp={tcp_ms:>5.0f}ms "
                            f"({err})  {n.protocol.value:<6} {n.name[:45]}")
                tested += 1


                now = time.time()
                if verbose and (now - last_log_time >= HEARTBEAT_INTERVAL or tested % 20 == 0):
                    LOG(f"[delay][{runtime.name}] progress: {tested}/{total} done, "
                        f"{len(final)} OK, {sum(fail_reasons.values())} failed")
                    last_log_time = now

        except Exception as e:
            err_msg = first_line(e, 200)
            if verbose:
                LOG(f"[delay][{runtime.name}] batch exception: {err_msg}")
            else:
                LOG(f"[delay][{runtime.name}] batch exception: {err_msg}", console=False)
            for n in batch_nodes:
                fail_reasons[err_msg] = fail_reasons.get(err_msg, 0) + 1
                if fail_detail is not None:
                    fail_detail[n.key()] = err_msg

            for port in batch_ports:
                try:
                    runtime.engine.port_pool.release_port(port)
                except Exception as e:
                    dlog(f"release_port({port}) on batch failure: {first_line(e)}")
            continue


    if verbose and tested > 0:
        LOG(f"[delay][{runtime.name}] finished: {tested}/{total} done, "
            f"{len(final)} OK, {sum(fail_reasons.values())} failed")

    return final, fail_reasons, False, []
