                                                         

                                                        
                                                             
   
import socket
import threading
import time
import urllib.request
from typing import List, Optional, Tuple

from ..log import LOG
from ..ui import fmt_dur



_PROBE_TCP = (("1.1.1.1", 443), ("8.8.8.8", 443), ("77.88.8.8", 443))
_PROBE_HTTP = (
    "http://www.gstatic.com/generate_204",
    "http://cp.cloudflare.com/generate_204",
)




_IPV6_PROBE_HOST = "2001:4860:4860::8888"
_IPV6_PROBE_PORT = 53




LIGHT_RTT_MS = 120.0
LIGHT_JITTER_MS = 120.0

FULL_RTT_MS = 60.0




_IPV6_CACHE: "bool | None" = None


def detect_ipv6_support(timeout: float = 2.0) -> bool:
                                                                      

                                                                         
                                                                         
                                                                          
                                                                   
                                                                         
                                                                       
       
    global _IPV6_CACHE
    if _IPV6_CACHE is not None:
        return _IPV6_CACHE
    try:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        try:
            s.settimeout(timeout)
            s.connect((_IPV6_PROBE_HOST, _IPV6_PROBE_PORT))
        finally:
            s.close()
        _IPV6_CACHE = True
    except OSError:
        _IPV6_CACHE = False
    return _IPV6_CACHE


def reset_ipv6_cache() -> None:
                                                                           

                                                                       
                                                                          
                                                           

                                                                         
                                                                       
                                                                         
                                                                         
                                                                       
                                                          
       
    global _IPV6_CACHE
    _IPV6_CACHE = None


def get_local_ip() -> str:
                                               

                                                                    
                                                                    
                                                                       
                                                                  
                                                                  
       
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 53))
            return sock.getsockname()[0]
        finally:
            sock.close()
    except OSError:
        return "127.0.0.1"


def _probe_once(addr: Tuple[str, int], timeout: float) -> Optional[float]:
                                                                       

                                                                 
       
    start = time.perf_counter()
    try:
        with socket.create_connection(addr, timeout=timeout):
            pass
    except OSError:
        return None
    return (time.perf_counter() - start) * 1000.0


def measure_local_link(samples: int = 5, timeout: float = 2.0
                       ) -> Optional[Tuple[float, float]]:
                                                                           

                                                                       
                                                                         
                                                                          
                                                                         
                                                                      
                          

                                                          
                                                                        
                                                                     
                  
       
    best: Optional[Tuple[float, Tuple[str, int]]] = None
    for addr in _PROBE_TCP:
        elapsed = _probe_once(addr, timeout)
        if elapsed is None:
            continue
        time.sleep(0.02)
        if best is None or elapsed < best[0]:
            best = (elapsed, addr)
    if best is None:
        return None

    target = best[1]
    rtts: List[float] = [best[0]]
    for _ in range(max(0, samples - 1)):
        elapsed = _probe_once(target, timeout)
        if elapsed is not None:
            rtts.append(elapsed)

    min_rtt = min(rtts)
    jitter = max(rtts) - min_rtt
    return min_rtt, jitter


def detect_channel_profile(avg_latency_ms: float,
                           jitter_ms: float) -> str:
                                                                                     

                                                                       
                                                           
                                                                        
                                                                          
                                                                          
                                                 
                                                                      
       

    if avg_latency_ms < FULL_RTT_MS:
        return "full"

    if avg_latency_ms > LIGHT_RTT_MS or jitter_ms > LIGHT_JITTER_MS:
        return "light"
    return "unknown"


    return "unknown"


def _tcp_probe(addr: tuple, timeout: float) -> bool:
                                                                                                                          
    try:
        with socket.create_connection(addr, timeout=timeout):
            return True
    except Exception:
        return False


def check_direct_internet(timeout: float = 5.0) -> bool:
                                                                                                                                     
    for addr in _PROBE_TCP:
        if _tcp_probe(addr, min(timeout, 3.0)):
            return True
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for url in _PROBE_HTTP:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with opener.open(req, timeout=timeout) as resp:
                if resp.status in (200, 204):
                    return True
        except Exception:
            continue
    return False









WAIT_INTERNET_MAX_S = 1800.0


def wait_internet(monitor: 'NetworkMonitor', heartbeat: float = 30.0,
                  max_wait: float = WAIT_INTERNET_MAX_S) -> float:
                                                                                   

                                                                           
                                                                          
                                 
       
    t0 = time.time()
    last = 0.0
    while monitor.is_down:
        el = time.time() - t0
        if el >= max_wait:
            LOG(f"[net] WARNING: still down after {fmt_dur(el)} "
                f"(max_wait={fmt_dur(max_wait)}) — probe verdict may be false "
                "(captive portal/TUN fake-IP), continuing anyway")
            break
        time.sleep(2)
        el = time.time() - t0
        if el - last >= heartbeat:
            last = el
            LOG(f"[net] still waiting for connection... ({fmt_dur(el)})")
    return time.time() - t0


class NetworkMonitor:
                                         

                                                                           
                                                                           
                                                               
       



    FAIL_THRESHOLD = 3

    def __init__(self, interval: float = 5.0,
                 fail_threshold: int = FAIL_THRESHOLD,
                 probe_timeout: float = 4.0):
        self.interval = interval
        self.fail_threshold = max(1, fail_threshold)
        self.probe_timeout = probe_timeout
        self.is_down = False
        self._fails = 0
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _run(self):
        while not self._stop_event.is_set():
            if check_direct_internet(timeout=self.probe_timeout):
                if self.is_down:
                    LOG("[net] OK: direct internet restored!")
                self.is_down = False
                self._fails = 0
            else:
                self._fails += 1
                if self._fails >= self.fail_threshold and not self.is_down:
                    LOG(f"[net] WARNING: direct internet is down "
                        f"({self._fails} probes in a row)!")
                    self.is_down = True
            self._stop_event.wait(self.interval)
