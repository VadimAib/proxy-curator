                                                 

                                                                           
                                                                               
                                                                       
                                       

                                                                           
                                               
   
import socket
import time
from typing import Optional, Tuple, Callable, List, Dict, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..log import LOG
from ..models import Node, Protocol
from .netutil import ERR_NO_IPV4, filter_addrs
from .udping import QUIC_PROBE_SIZE, needs_udping, udping_nodes
from ..utils import first_line

def tcping(host: str, port: int, timeout: float,
           prefer_ipv4: bool = False,
           max_addrs: int = 3,
           ipv6_mode: str = "auto",
           ipv6_ok: bool = True) -> Tuple[Optional[float], Optional[str]]:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM,
                                   proto=socket.IPPROTO_TCP)
    except Exception as e:
        return None, first_line(e, 80)
    if not infos:
        return None, "getaddrinfo failed"

    if prefer_ipv4:
        ipv4 = [x for x in infos if x[0] == socket.AF_INET]
        if ipv4:
            infos = ipv4



    infos = filter_addrs(infos, ipv6_mode, ipv6_ok)
    if not infos:
        return None, ERR_NO_IPV4

    candidates = infos[:max_addrs]
    last_err = "connect failed"
    for family, _, _, _, sockaddr in candidates:
        try:
            t0 = time.perf_counter()
            with socket.socket(family, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect(sockaddr)
                return (time.perf_counter() - t0) * 1000.0, None
        except Exception as e:
            last_err = first_line(e, 80)
    return None, last_err

def _is_dns_error(err: Optional[str]) -> bool:
                                                           

                                                                       
                                                                        
                                                                       
                                                                        
                                   
       
    if not err:
        return False
    low = err.lower()
    return "getaddrinfo" in low or "gaierror" in low


def tcping_nodes(nodes: list, timeout: float, workers: int,
                 prefer_ipv4: bool = False, max_addrs: int = 3,
                 progress_cb=None,
                 ipv6_mode: str = "auto",
                 ipv6_ok: bool = True,
                 dns_retries: int = 1,
                 probe_retries: int = 0,
                 retry_timeout: float = 0.0,
                 retry_cb=None) -> Tuple[list, dict, list]:
                                                            
                                                                                     

                                                                        
                                                                             
                                                                   
                                

                                                                       
                                                                          
                                                                          
                                                                        
                                                                        
                                                               
                                                                       

                                                                           
                                                                          
                                                                  
                                                                        
                                                                            
                                                                       
                                                          

                                                                          
                                                                           
                                                                      

                                                                         
                                                                         
                                                                       
                                                                           
                                                                    
       
    endpoints = {}
    for n, _ in nodes:
        key = (n.host.lower(), n.port)
        endpoints.setdefault(key, []).append(n)

    def _probe(eps: dict, to: float = 0.0) -> None:
                                                                                                     
        if not eps:
            return
        tmo = to if to and to > 0 else timeout
        with ThreadPoolExecutor(workers) as ex:
            futs = {
                ex.submit(tcping, h, p, tmo, prefer_ipv4, max_addrs,
                          ipv6_mode, ipv6_ok): (h, p)
                for h, p in eps
            }
            for f in as_completed(futs):
                ep_res[futs[f]] = f.result()
                if progress_cb:
                    progress_cb(ep_res[futs[f]][0] is not None)

    ep_res: dict = {}
    _probe(endpoints)




    for attempt in range(max(0, dns_retries)):
        failed_dns = {ep: res for ep, res in ep_res.items()
                      if res[0] is None and _is_dns_error(res[1])}
        if not failed_dns:
            break
        LOG(f"[ping] DNS failure: retry {attempt + 1}/{dns_retries} for "
            f"{len(failed_dns)} endpoint(s) (getaddrinfo failed)")
        if retry_cb:
            retry_cb(len(failed_dns))
        _probe(failed_dns)




    for attempt in range(max(0, probe_retries)):
        failed = {ep: res for ep, res in ep_res.items()
                  if res[0] is None and not _is_dns_error(res[1])}
        if not failed:
            break
        LOG(f"[ping] retry {attempt + 1}/{probe_retries} for "
            f"{len(failed)} endpoint(s) (timeout/refused)")
        if retry_cb:
            retry_cb(len(failed))
        _probe(failed, retry_timeout)

    alive, dead, tcp_drops = [], [], {}
    for n, _ in nodes:
        ms, err = ep_res.get((n.host.lower(), n.port), (None, "not tested"))
        if ms is not None:
            alive.append((n, ms))
        else:
            dead.append((n, err or "unknown"))
            tcp_drops[err or "unknown"] = tcp_drops.get(err or "unknown", 0) + 1

    alive.sort(key=lambda x: x[1])
    return alive, tcp_drops, dead


def ping_nodes(nodes: Sequence[Tuple[Node, Optional[float]]], timeout: float,
               workers: int,
               prefer_ipv4: bool = False, max_addrs: int = 3,
               progress_cb: Optional[Callable[[bool], None]] = None,
               udp_timeout: Optional[float] = None,
               udp_workers: Optional[int] = None,
               udp_attempts: int = 2,
               udp_probe_size: int = QUIC_PROBE_SIZE,
               udp_max_consecutive_timeouts: int = 5,
               ipv6_mode: str = "auto",
                ipv6_ok: bool = True,
                probe_retries: int = 0,
                retry_timeout: float = 0.0,
                retry_cb: Optional[Callable[[int], None]] = None
               ) -> Tuple[List[Tuple[Node, float]], Dict[str, int],
                          List[Tuple[Node, str]]]:
                                                           

                                                                
                                                               
                                                                          
                                                                

         
                                                                            
                                                                          
                                                                         
                                                                               
                                                                   
                                                                            
                                           
                                                
           

            
                                 
                                                                                         
                                                                                                        
                                                                                           
       


    defer_part = [(n, m) for n, m in nodes
                  if n.protocol == Protocol.WIREGUARD]
    tcp_part = [(n, m) for n, m in nodes
                if n.protocol != Protocol.WIREGUARD and not needs_udping(n)]
    udp_part = [(n, m) for n, m in nodes if needs_udping(n)]

    alive: List[Tuple[Node, float]] = [(n, 0.0) for n, _ in defer_part]
    dead: List[Tuple[Node, str]] = []
    drops: Dict[str, int] = {}

    def _merge(part) -> None:
        p_alive, p_drops, p_dead = part
        alive.extend(p_alive)
        dead.extend(p_dead)
        for k, v in p_drops.items():
            drops[k] = drops.get(k, 0) + v

    if tcp_part:
        _merge(tcping_nodes(tcp_part, timeout, workers, prefer_ipv4,
                            max_addrs, progress_cb, ipv6_mode, ipv6_ok,
                            probe_retries=probe_retries, retry_timeout=retry_timeout,
                            retry_cb=retry_cb))
    if udp_part:
        _merge(udping_nodes(udp_part,
                            udp_timeout if udp_timeout else timeout,
                            udp_workers or workers, prefer_ipv4, max_addrs,
                            udp_probe_size, udp_attempts, progress_cb,
                            ipv6_mode, ipv6_ok,
                            udp_max_consecutive_timeouts))

    alive.sort(key=lambda x: x[1])
    return alive, drops, dead