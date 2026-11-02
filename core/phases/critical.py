                                                                     

                                                                        
                                                                         
                                                               
                      

                                                                           
                                                                             
                                                                           
                                                               
                                                                
                                                                  
                                                                        
                                                                     

                                                              
   
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple
from urllib.error import HTTPError
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener

from ..config import Config, TestUrlConfig
from ..log import LOG
from ..state import PipelineState



_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


_DIRECT_OPENER = build_opener(ProxyHandler({}), HTTPSHandler(context=_SSL_CTX))


def _direct_url_ok(url_cfg: TestUrlConfig, timeout: float) -> Tuple[bool, str]:
                                                                        

                                                                    
                                                                     
                                                                 
                                                                     
              

                                                                           
                                                                              
                                                                             
                                                    
       
    try:
        req = Request(url_cfg.url, headers={
            "User-Agent": "Mozilla/5.0",
            "Connection": "close",
        })
        with _DIRECT_OPENER.open(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            if status in url_cfg.ok_statuses:
                return True, ""
            return False, f"http {status}"
    except HTTPError as e:
        if e.code in url_cfg.ok_statuses:
            return True, ""
        return False, f"http {e.code}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def critical_canary(cfg: Config, stats: Dict[str, Any]) -> List[TestUrlConfig]:
                                                                            

                                                                            
                                                                           
                                                                    
                                                                       
                                                 
                                                                         
                                                                          
                                              

                                                                  
                                                                     
                                                               
                                 

                                                                        
                                                                          
                                                                     
                                                                           
                                                                      
                                                                      
                                          
       
    urls = cfg.critical_urls
    if not urls:
        return []
    timeout = cfg.testing.critical_timeout or cfg.testing.timeout



    results: Dict[str, Tuple[bool, str]] = {}
    with ThreadPoolExecutor(max_workers=min(len(urls), 4)) as executor:
        future_map = {executor.submit(_direct_url_ok, u, timeout): u
                      for u in urls}
        for future in as_completed(future_map):
            url_cfg = future_map[future]
            try:
                results[url_cfg.url] = future.result()
            except Exception as e:
                results[url_cfg.url] = (False, f"{type(e).__name__}: {e}")
    down = [u for u in urls if not results.get(u.url, (False, ""))[0]]
    stats["critical_canary"] = {
        "checked": [u.url for u in urls],
        "down": [u.url for u in down],
        "down_reasons": {u.url: results.get(u.url, (False, ""))[1]
                         for u in down},
        "active": len(down) < len(urls),
    }
    if down:
        LOG(f"[critical] WARNING: canary — {len(down)}/{len(urls)} "
            "url unreachable from host, excluded from critical for this run:")
        for u in down:
            LOG(f"[critical]   down: {u.name or u.url} "
                f"({results.get(u.url, (False, '?'))[1]})")
        cfg.critical_urls = [u for u in urls if u not in down]
        if not cfg.critical_urls:
            LOG("[critical] all required urls unreachable from host — "
                "stage 3 (critical) disabled for this run")
    else:
        LOG(f"[critical] canary: {len(urls)}/{len(urls)} url reachable "
            "from host — stage 3 active in this run")
    return down


def critical_audit(state: PipelineState, stats: Dict[str, Any]) -> None:
                                                                     

                                                                    
                                                                             

                                                                           
                                                                          
                                                                       
                                                                    

                                                                           
                                                                    
                                                                  
                                   
       
    canary = stats.get("critical_canary")
    if not canary or not canary.get("active"):
        return
    rescued = set(stats.get("rescued") or [])
    drops = stats.get("delay_drop_reasons") or {}
    ok = failed = unchecked = 0
    for node, _ms in state.final:
        if node.key() in rescued:
            if drops.get(node.key(), "").startswith("critical_failed:"):
                failed += 1
            else:
                unchecked += 1
        else:
            ok += 1
    stats["critical_audit"] = {"ok": ok, "failed": failed,
                               "unchecked": unchecked}
    LOG(f"[critical] audit: ok={ok}, failed={failed}, "
        f"unchecked={unchecked} (output {len(state.final)}, "
        f"urls {len(canary.get('checked') or [])})")
