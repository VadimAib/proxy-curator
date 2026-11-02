                                                                

                                                                           
                                                                           
                                                                          
                                       

                                                                  
                                                                          
                                                                
   
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
from urllib.request import ProxyHandler, Request, build_opener

from ..engine.engines import EngineRuntime, engine_name_for
from ..log import LOG
from ..models import Node
from ..net.netmon import detect_channel_profile, measure_local_link
from ..state import PipelineState
from ..ui import ProgressBar
from ..utils import first_line, reason_key
from .speedtest_instrument import (_CAP_SLACK, _READ_CHUNK, _TIMEOUT_ESCALATION,
                                   _count_saved_by_escalation,
                                   _is_read_timeout,
                                   _reset_escalation_counter, calc_mbps,
                                   escalation_saved, transfer_deadline)


def _detect_channel_profile_from_state(state: PipelineState) -> str:
                                                                                     

                                                                              
                                                                      
                                                                           
                                                                              
                                                                       
                                             

                                                  
                                                                      
                                                                          
                                                                        
                                                                        
       
    stats = state.stats or {}
    cached = stats.get("local_link")
    if isinstance(cached, (list, tuple)) and len(cached) == 2:
        try:
            return detect_channel_profile(float(cached[0]), float(cached[1]))
        except (TypeError, ValueError):
            pass

    measured = measure_local_link()
    if measured is None:
        LOG("[speedtest] local link unmeasured, assuming full profile")
        return "unknown"
    rtt_ms, jitter_ms = measured
    stats["local_link"] = [round(rtt_ms, 1), round(jitter_ms, 1)]
    return detect_channel_profile(rtt_ms, jitter_ms)




def _download_via_proxy(local_port: int, url: str, timeout: float,
                        max_bytes: int) -> Tuple[int, float, float]:
                                            

                                                                            
                                                                           

                                                                          
                                                                             
                                                                            
                                                                           
                                                                                     
                                                                        
                                                                              
                           

                                                                          
                                                                                
                                                                          
                                                                              
                                                                               
                                    

                                                                          
                                                                     
                                         

                                                                      
                                                                        
                                                               

                                                                        
                                                                         
                             
       
    cap = max(int(max_bytes), 0) + _CAP_SLACK
    budget = transfer_deadline(timeout)
    proxy_url = f"http://127.0.0.1:{local_port}"
    opener = build_opener(ProxyHandler({"http": proxy_url,
                                        "https": proxy_url}))
    req = Request(url, headers={"User-Agent": "Mozilla/5.0",
                                "Connection": "close"})
    t0 = time.perf_counter()
    with opener.open(req, timeout=timeout) as resp:
        t_headers = time.perf_counter()
        parts: List[bytes] = []
        total = 0
        while total < cap:
            if time.perf_counter() - t_headers > budget:


                raise TimeoutError(
                    f"transfer exceeded {budget:.0f}s "
                    f"({total} of {max_bytes} bytes)")
            chunk = resp.read(min(_READ_CHUNK, cap - total))
            if not chunk:
                break
            parts.append(chunk)
            total += len(chunk)
        t_end = time.perf_counter()
    return (total, max(t_end - t_headers, 0.0),
            max(t_headers - t0, 0.0))




def _run_speed_via_engine(node: Node, rt: EngineRuntime,
                          full_url: str, timeout: float,
                          nbytes: int) -> Tuple[int, float, float]:
                                                                             

                                                                           
                                                                             
                                                                
                                                                            
                                           

                                                                 
                                                                        
                                                                          
                    

                                                                            
                                                                             
                                                                   
                                                                          
                                                     
                                                                              
                                             
                                                                            
                                                    
       
    engine = rt.engine
    port = engine.port_pool.get_port()
    try:
        with engine.probe_session(node, str(rt.binary), port):
            return _download_via_proxy(port, full_url, timeout, nbytes)
    finally:


        try:
            engine.port_pool.release_port(port)
        except Exception:
            pass




def _measure_one(node: Node, engines: Dict[str, EngineRuntime],
                 full_url: str, nbytes: int, timeout: float,
                 retries: int) -> Tuple[Optional[float], Optional[str]]:
                                                                        

                                                                           
                                                                     
                                                                      
                                                                         
                                                                    
                                                                        
                                                                         

                                                                           
                                                                         
                      
       
    name = engine_name_for(node)
    rt = engines.get(name) if name else None
    if rt is None or not rt.available():
        return None, "no-engine"
    attempts = max(0, int(retries)) + 1
    last_err: Optional[str] = None
    for attempt in range(attempts):
        window = float(timeout)
        escalated = False
        if attempt and _is_read_timeout(last_err):
            window = float(timeout) * _TIMEOUT_ESCALATION
            escalated = True
        try:
            got, transfer, _setup = _run_speed_via_engine(node, rt, full_url,
                                                          window, nbytes)
            if transfer <= 0 or got <= 0:
                last_err = "empty-download"
                continue
            if escalated and window > float(timeout):


                _count_saved_by_escalation()
            return calc_mbps(got, transfer), None
        except Exception as e:
            last_err = first_line(e, 200)
            continue
    return None, last_err or "download-failed"




def _run_tier(items: List[Tuple[Node, float]],
              engines: Dict[str, EngineRuntime], url: str, nbytes: int,
              timeout: float, retries: int, workers: int,
              label: str) -> Tuple[Dict[str, Dict], Dict[str, str]]:
                                                                              

                                                                               
                                                                      
                                                                        
                                         

                                                                          
                                                                          
                                                                           
                                                            
       
    results: Dict[str, Dict] = {}
    fail_detail: Dict[str, str] = {}
    if not items:
        return results, fail_detail

    _reset_escalation_counter()
    lock = threading.Lock()



    fail_counts: Dict[str, int] = {}


    bar = ProgressBar(len(items), label, log_progress=True, unit="nodes")

    def _task(node: Node) -> None:
        mbps, err = _measure_one(node, engines, url, nbytes, timeout, retries)
        if err is not None:
            rk = reason_key(err)
            with lock:
                fail_detail[node.key()] = rk
                fail_counts[rk] = fail_counts.get(rk, 0) + 1
        if mbps is not None:
            with lock:
                results[node.key()] = {"mbps": round(mbps, 2),
                                       "bytes": nbytes}
        bar.update(mbps is not None)

    try:
        with ThreadPoolExecutor(max_workers=min(workers, len(items)),
                                thread_name_prefix=label) as ex:
            futs = [ex.submit(_task, node) for node, _ in items]
            for fut in as_completed(futs):
                try:
                    fut.result()
                except BaseException:
                    bar.update(False)
    finally:
        bar.finish()
    if fail_counts:
        total = sum(fail_counts.values())
        LOG(f"[{label}] {total} of {len(items)} nodes failed, top reasons:")
        for reason, count in sorted(fail_counts.items(),
                                    key=lambda x: -x[1])[:8]:
            LOG(f"         -{count:<5} {reason}")
    saved = escalation_saved()
    if saved:


        LOG(f"[{label}] {saved} node(s) saved by the widened retry window")
    return results, fail_detail
