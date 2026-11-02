                                                                                

                                                                       
                                                                       
                                                                        
   
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple

from ..engine.engines import EngineRuntime, engine_name_for
from ..models import Node


@dataclass
class ConnRound:
                                                                                                            

    ok: List[Tuple[Node, float]] = field(default_factory=list)
    fail: Dict[str, int] = field(default_factory=dict)
    fail_detail: Dict[str, str] = field(default_factory=dict)


def run_first_round(work, engines, cfg, bar, max_parallel,
                    _run_round) -> ConnRound:
                                                                                                                         
    from .connectivity import _merge_conn
    rnd = ConnRound()
    results = _run_round(work, engines, cfg, bar, max_parallel,
                         fail_detail=rnd.fail_detail)
    rnd.ok, rnd.fail = _merge_conn(results)
    return rnd


def _recheck_nodes(fail_detail: Dict[str, str],
                   index: Dict[str, Node]) -> List[Node]:
                                                          

                                                                           
                                                                         
       
    return [index[k] for k, r in fail_detail.items()
            if r == "no_connectivity" and k in index]


def _recheck_groups(nodes: List[Node]) -> Dict[str, List[Tuple[Node, float]]]:
                                                                                         
    groups: Dict[str, List[Tuple[Node, float]]] = {}
    for n in nodes:
        name = engine_name_for(n)
        if name:
            groups.setdefault(name, []).append((n, 0.0))
    return groups


def _merge_recheck(connectivity_ok: List[Tuple[Node, float]],
                   conn_fail: Dict[str, int],
                   fail_detail: Dict[str, str],
                   retry_ok: List[Tuple[Node, float]],
                   retry_fail: Dict[str, int]) -> None:
                                                                                                                        
    if not retry_ok:
        return
    ok_keys = {n.key() for n, _ in retry_ok}
    connectivity_ok.extend(retry_ok)
    for k in [k for k in fail_detail if k in ok_keys]:
        del fail_detail[k]
        conn_fail["no_connectivity"] -= 1
        if conn_fail["no_connectivity"] <= 0:
            del conn_fail["no_connectivity"]
    for k, v in retry_fail.items():
        conn_fail[k] = conn_fail.get(k, 0) + v


def maybe_recheck(fail_detail: Dict[str, str],
                  index: Dict[str, Node],
                  connectivity_ok: List[Tuple[Node, float]],
                  conn_fail: Dict[str, int],
                  engines: Dict[str, EngineRuntime],
                  pause_sec: float,
                  conn_batch: int,
                  max_parallel: int,
                  bar,
                  cfg,
                  _work, _run_round,
                  sleep: Callable[[float], None] = time.sleep) -> None:
                                                                          

                                                                              
                                                                             
                                                               
       
    if pause_sec <= 0:
        return
    retry_nodes = _recheck_nodes(fail_detail, index)
    if not retry_nodes:
        return
    sleep(pause_sec)
    from .connectivity import _merge_conn
    retry_results = _run_round(
        _work(_recheck_groups(retry_nodes), engines, conn_batch),
        engines, cfg, bar, max_parallel, fail_detail=fail_detail)
    retry_ok, retry_fail = _merge_conn(retry_results)
    _merge_recheck(connectivity_ok, conn_fail, fail_detail,
                   retry_ok, retry_fail)


def _merge_conn_results(results):
                                                                     

                                                                        
                                                                         
       
    from .connectivity import _merge_conn
    return _merge_conn(results)
