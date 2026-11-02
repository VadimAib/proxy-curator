                                                                             

                                                                            
                                                                                
                                                                              
                                                                         
                               

                                                                           
                                                  

                                                                             
                                                                          
                                                                  

         

                                                                          
                                                                      
                                                 
                                                                   
                                                                              
                                              
                                        
                                                                             
                                                                   
                                                                             
                                                                            
                                                                          
                                            

                                              

                                                                            
                                                              
                                                                               
                                                                         
                                                          
                                                                          
                                              
   
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Set, Tuple

from ..log import LOG, dlog
from ..models import Node, Security
from .udping import needs_udping
from ..ui import ProgressBar
from ..utils import first_line



DEAD_VERDICTS = frozenset({"refused", "reset", "dns", "timeout"})

ALIVE_VERDICTS = frozenset({"tls-ok"})

NOT_APPLICABLE = "not-applicable"

KNOWN_VERDICTS = (DEAD_VERDICTS | ALIVE_VERDICTS
                  | {NOT_APPLICABLE, "no-sni", "tls-error", "error"})


def probe_endpoint(host: str, port: int, sni: str, timeout: float,
                   prefer_ipv4: bool = True, max_addrs: int = 2) -> str:
                                                                          

                                                                            
                                                                
       
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM,
                                   proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return "dns"
    except Exception as e:
        return "dns" if _looks_like_dns(e) else "error:" + first_line(e, 40)
    if not infos:
        return "dns"
    if prefer_ipv4:
        v4 = [i for i in infos if i[0] == socket.AF_INET]
        if v4:
            infos = v4

    if not sni:

        return "no-sni"

    ctx = _tls_context()
    last = "timeout"
    for family, _t, _p, _c, sockaddr in infos[:max(1, max_addrs)]:
        try:
            with socket.socket(family, socket.SOCK_STREAM) as raw:
                raw.settimeout(timeout)
                raw.connect(sockaddr)
                with ctx.wrap_socket(raw, server_hostname=sni) as tls:
                    tls.version()
            return "tls-ok"
        except ssl.SSLError as e:

            last = "tls-error"
            dlog(f"[diag] tls probe {host}:{port} sni={sni}: {first_line(e, 80)}")
        except socket.gaierror:
            return "dns"
        except ConnectionRefusedError:
            return "refused"
        except (TimeoutError, socket.timeout):
            last = "timeout"
        except OSError as e:
            last = "reset" if _is_reset(e) else "error:" + first_line(e, 40)
        except Exception as e:
            last = "error:" + first_line(e, 40)
    return last


def _tls_context() -> ssl.SSLContext:
                                                                             

                                                                         
                                                            
       
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _looks_like_dns(e: BaseException) -> bool:
                                                                                                 
    low = first_line(e, 200).lower()
    return "getaddrinfo" in low or "gaierror" in low


def _is_reset(e: BaseException) -> bool:
                                                                                                       
    if isinstance(e, ConnectionResetError):
        return True
    return "reset" in first_line(e, 200).lower()


def is_applicable(n: Node) -> bool:
                                                                                                                             
    if needs_udping(n):
        return False
    return n.security != Security.REALITY


def endpoint_of(n: Node) -> Tuple[str, int, str]:
                                                                                                                               
    return n.host, n.port, str(n.extra.get("sni") or "").strip()


def counts_key(verdict: str) -> str:
                                                                         

                                                                    
                                                               
                             
       
    return verdict if verdict in KNOWN_VERDICTS else "other"


def diagnose(nodes: List[Node], timeout: float, workers: int,
             prefer_ipv4: bool = True, max_addrs: int = 2,
             bar: Optional[ProgressBar] = None) -> Dict[str, Any]:
                                                            

                                                                          
                                                     

                                                                             
                                                                              
                                                              

                                                                         
                                                                             
                                                                          
                                                                     

                                                                             
                                                                            
                                                             

                                                                             
                                                                           
                                                                          
                                                                            
                                                       
       
    applicable = [n for n in nodes if is_applicable(n)]
    verdicts = _probe_unique(applicable, timeout, workers, prefer_ipv4,
                             max_addrs, bar=bar)

    counts: Dict[str, int] = {}
    for n in applicable:
        key = counts_key(verdicts.get(endpoint_of(n), "timeout"))
        counts[key] = counts.get(key, 0) + 1
    na = len(nodes) - len(applicable)
    if na:
        counts[NOT_APPLICABLE] = counts.get(NOT_APPLICABLE, 0) + na

    return {
        "counts": counts,
        "nodes": len(nodes),
        "endpoints": len(verdicts),
        "dead": sum(c for k, c in counts.items() if k in DEAD_VERDICTS),
        "alive": sum(c for k, c in counts.items() if k in ALIVE_VERDICTS),
        "not_applicable": counts.get(NOT_APPLICABLE, 0),
        "verdicts": _verdict_rows(verdicts),
    }


def _verdict_rows(verdicts: Dict[Tuple[str, int, str], str]) -> List[list]:
                                                                 

                                                                             
                                                                           
                                                                            
                                                                      
                                                

                                                                             
                                             
       
    return [[host, port, sni, counts_key(v)]
            for (host, port, sni), v in sorted(verdicts.items())]


def _probe_unique(nodes: List[Node], timeout: float, workers: int,
                  prefer_ipv4: bool, max_addrs: int,
                  bar: Optional[ProgressBar] = None,
                  ) -> Dict[Tuple[str, int, str], str]:
                                                                         

                                                                             
                                                                              
                                           
       
    targets: List[Tuple[str, int, str]] = []
    seen: Set[Tuple[str, int, str]] = set()
    out: Dict[Tuple[str, int, str], str] = {}
    for n in nodes:
        key = endpoint_of(n)
        if key in seen:
            continue
        seen.add(key)
        if not key[2]:



            out[key] = "no-sni"
            continue
        targets.append(key)
    if not targets:
        if bar is not None:
            bar.set_total(len(out))
            for _ in out:
                bar.update()
            bar.finish()
        return out

    if bar is not None:
        bar.set_total(len(targets))




        LOG(f"[diag] probing {len(targets)} unique endpoint(s), "
            f"timeout={timeout}s, workers={workers}")
    try:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
            futures = {ex.submit(probe_endpoint, h, p, s, timeout,
                                 prefer_ipv4, max_addrs): (h, p, s)
                       for h, p, s in targets}
            for fut, key in futures.items():
                try:
                    out[key] = str(fut.result())
                except Exception as e:
                    out[key] = "error:" + first_line(e, 40)
                if bar is not None:
                    bar.update()
    finally:
        if bar is not None:
            bar.finish()
    return out
