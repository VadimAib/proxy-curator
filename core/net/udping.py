                                                              

                                                                              
                                                                            
                                                                           
                                                                           
                                                                              
                                                                        

                                                                    
                                                                     
                                                                            
                                                                            
                                                                        
                         

                                                                                                 
   
import os
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from ..log import LOG, dlog
from ..models import Node, QUIC_PROTOCOLS
from .netutil import ERR_NO_IPV4, filter_addrs
from ..utils import first_line


QUIC_PROBE_SIZE = 1200

_QUIC_LONG_HEADER = 0xC0


_QUIC_UNSUPPORTED_VERSION = 0x0A0A0A0B

ERR_REFUSED = "udp refused (icmp)"
ERR_TIMEOUT = "timeout"


ERR_UDP_BLOCKED = "udp-blocked"
_REFUSED_WINERR = (10054, 10061)


def build_quic_probe(size: int = QUIC_PROBE_SIZE,
                      version: int = _QUIC_UNSUPPORTED_VERSION) -> bytes:
                                                                             

                                                                         
                                                                           
       
    dcid, scid = os.urandom(8), os.urandom(8)
    pkt = bytes((_QUIC_LONG_HEADER,)) + version.to_bytes(4, "big") \
        + bytes((len(dcid),)) + dcid \
        + bytes((len(scid),)) + scid
    if len(pkt) < size:
        pkt += b"\x00" * (size - len(pkt))
    return pkt


def needs_udping(node: Node) -> bool:
                                                                                                          
    return node.protocol in QUIC_PROTOCOLS


def udping(host: str, port: int, timeout: float,
           prefer_ipv4: bool = False, max_addrs: int = 3,
           payload: Optional[bytes] = None, attempts: int = 2,
           ipv6_mode: str = "auto", ipv6_ok: bool = True
           ) -> Tuple[Optional[float], Optional[str]]:
                                                                                                            
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_DGRAM)
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

    probe = payload if payload is not None else build_quic_probe()

    wait = max(0.05, timeout / max(1, attempts))
    last_err, refused = ERR_TIMEOUT, False

    for family, _, _, _, sockaddr in infos[:max_addrs]:
        sock = None
        try:
            sock = socket.socket(family, socket.SOCK_DGRAM)
            sock.settimeout(wait)
            sock.connect(sockaddr)
            t0 = time.perf_counter()
            for _ in range(max(1, attempts)):
                sock.send(probe)
                try:
                    sock.recv(2048)
                    return (time.perf_counter() - t0) * 1000.0, None
                except TimeoutError:
                    continue
            last_err = ERR_TIMEOUT
        except (ConnectionRefusedError, ConnectionResetError):
            refused, last_err = True, ERR_REFUSED
        except TimeoutError:
            last_err = ERR_TIMEOUT
        except OSError as e:
            if getattr(e, "winerror", None) in _REFUSED_WINERR:
                refused, last_err = True, ERR_REFUSED
            else:
                last_err = first_line(e, 80)
        except Exception as e:
            last_err = first_line(e, 80)
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
        dlog(f"udping {host}:{port} -> {last_err}")

    return None, (ERR_REFUSED if refused else last_err)


def udping_nodes(nodes: Sequence[Tuple[Node, Optional[float]]], timeout: float,
                 workers: int,
                 prefer_ipv4: bool = False, max_addrs: int = 3,
                 probe_size: int = QUIC_PROBE_SIZE, attempts: int = 2,
                 progress_cb: Optional[Callable[[bool], None]] = None,
                 ipv6_mode: str = "auto", ipv6_ok: bool = True,
                 max_consecutive_timeouts: int = 0,
                 ) -> Tuple[List[Tuple[Node, float]], Dict[str, int],
                            List[Tuple[Node, str]]]:
                                                              

                                                                                  

                                                                                
                                                                                
                                                                           
                                                                      
                                                                    
                                                                         
                                                                      
       
    endpoints: Dict[Tuple[str, int], List[Node]] = {}
    for n, _ in nodes:
        endpoints.setdefault((n.host.lower(), n.port), []).append(n)

    stop_event = threading.Event()
    state_lock = threading.Lock()



    tested = 0
    timeouts = 0
    alive_count = 0
    try:
        min_tests = int(max_consecutive_timeouts or 0)
    except (TypeError, ValueError):
        min_tests = 0
    min_tests = max(0, min_tests)


    TIMEOUT_RATIO = 0.95

    def _probe_one(h: str, p: int, probe: bytes
                   ) -> Tuple[Optional[float], Optional[str]]:
        nonlocal tested, timeouts, alive_count
        if stop_event.is_set():
            return None, ERR_UDP_BLOCKED
        ms, err = udping(h, p, timeout, prefer_ipv4, max_addrs,
                         probe, attempts, ipv6_mode, ipv6_ok)
        if stop_event.is_set():


            if ms is not None:
                return ms, err
            return None, ERR_UDP_BLOCKED
        with state_lock:
            tested += 1
            if ms is not None:
                alive_count += 1
            elif err == ERR_TIMEOUT:
                timeouts += 1




            if (min_tests > 0 and tested >= min_tests and alive_count == 0
                    and timeouts / tested >= TIMEOUT_RATIO
                    and not stop_event.is_set()):
                stop_event.set()
                LOG(f"[udping] {timeouts}/{tested} timeouts ({timeouts/tested:.0%}) "
                    f"with 0 alive — UDP may be systematically blocked by router/ISP; "
                    f"marking remaining QUIC nodes as '{ERR_UDP_BLOCKED}'")
        return ms, err

    ep_res: Dict[Tuple[str, int], Tuple[Optional[float], Optional[str]]] = {}
    if endpoints:
        probe = build_quic_probe(probe_size)
        with ThreadPoolExecutor(workers) as ex:
            futs = {
                ex.submit(_probe_one, h, p, probe): (h, p)
                for h, p in endpoints
            }
            for f in as_completed(futs):
                ep_res[futs[f]] = f.result()
                if progress_cb:
                    progress_cb(ep_res[futs[f]][0] is not None)

    alive: List[Tuple[Node, float]] = []
    dead: List[Tuple[Node, str]] = []
    drops: Dict[str, int] = {}
    for n, _ in nodes:
        ms, err = ep_res.get((n.host.lower(), n.port), (None, "not tested"))
        if ms is not None:
            alive.append((n, ms))
        else:
            key = err or "unknown"
            dead.append((n, key))
            drops[key] = drops.get(key, 0) + 1

    alive.sort(key=lambda x: x[1])
    return alive, drops, dead
