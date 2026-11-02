                                                                   

                                                                          
                                                                          
                                                                             
                                                             
                                                                           
                                                   

                                                                             
                                                                          
                                                                        
                                                                     
                                                                           
                  

                                                                    
                                                                            
                                                                         
                                                                         
                                   
   
from typing import Any, Callable, Dict, List, Optional

from ..config import Config, TestUrlConfig
from ..engine.engines import EngineRuntime, engine_name_for
from ..engine.httptest import http_test
from ..log import LOG
from ..models import Node




TUNNEL_CANARY_ATTEMPTS = 3



Probe = Callable[[TestUrlConfig], Optional[bool]]


def _open_through(node: Node, rt: EngineRuntime, url_cfg: TestUrlConfig,
                  timeout: float) -> bool:
                                                                         

                                                                            
                                                             
       
    engine = rt.engine
    port = engine.port_pool.get_port()
    try:
        with engine.probe_session(node, str(rt.binary), port):
            err = http_test(port, [], [], [url_cfg], timeout,
                            critical_timeout=timeout, critical_mode="any")
            return err is None
    finally:
        try:
            engine.port_pool.release_port(port)
        except Exception:
            pass


def make_probe(engines: Dict[str, EngineRuntime], nodes: List[Node],
               cfg: Config) -> Probe:
                                                                       

                                                            
                                                                           
                                                                      
                                                                           
                                                  
       
    pending = list(nodes)
    timeout = cfg.testing.critical_timeout or cfg.testing.timeout

    def probe(url_cfg: TestUrlConfig) -> Optional[bool]:
        while pending:
            node = pending.pop(0)
            rt = engines.get(engine_name_for(node))
            if rt is None or not rt.available():
                continue
            try:
                return _open_through(node, rt, url_cfg, timeout)
            except Exception:
                continue
        return None

    return probe


def critical_tunnel_canary(cfg: Config, stats: Dict[str, Any],
                           probe: Probe,
                           excluded: List[TestUrlConfig],
                           max_attempts: int = TUNNEL_CANARY_ATTEMPTS) -> None:
                                                                             

                                                                            
                                                                            
                                                                               
                                                                          
                                         

                                                                        
                                     
       
    if not excluded:
        return

    restored: List[TestUrlConfig] = []
    no_tunnel: List[str] = []
    closed: List[str] = []
    attempts = max(1, int(max_attempts))
    for url_cfg in excluded:



        verdict: Optional[bool] = None
        for _ in range(attempts):
            verdict = probe(url_cfg)
            if verdict:
                break
        if verdict is None:
            no_tunnel.append(url_cfg.url)
        elif verdict:
            restored.append(url_cfg)
        else:
            closed.append(url_cfg.url)

    stats["critical_tunnel_canary"] = {
        "excluded": [u.url for u in excluded],
        "restored": [u.url for u in restored],
        "closed": closed,
        "no_tunnel": no_tunnel,
    }

    if not restored:
        LOG(f"[critical] tunnel check: 0/{len(excluded)} url restored "
            f"(closed={len(closed)}, no tunnel={len(no_tunnel)})")
        return

    cfg.critical_urls = list(cfg.critical_urls) + restored
    canary = stats.get("critical_canary")
    if isinstance(canary, dict):
        canary["active"] = True
        restored_urls = {u.url for u in restored}
        canary["down"] = [u for u in canary.get("down", [])
                          if u not in restored_urls]
        reasons = canary.get("down_reasons")
        if isinstance(reasons, dict):
            for url in restored_urls:
                reasons.pop(url, None)
    LOG(f"[critical] tunnel check: {len(restored)}/{len(excluded)} url "
        "opens through a node — returned to required:")
    for url_cfg in restored:
        LOG(f"[critical]   restored: {url_cfg.name or url_cfg.url}")
