                                                                       

                                                                         
                                                                     
                    

                                                                 
                                                                    
                                                                 
                                                           
                                                            
                                                       
                      

                                                                    
                                                                   
                                                                       
                                                                     

                                                                      
                                                                     
                                                                     
                                                              
                                                         

                                                                       
                                                                         
   

import json
import threading
from collections import deque
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import ProxyHandler, Request, build_opener

from .geo_cache import get_persistent_country, set_persistent_country
from ..log import dlog










GEO_URL = "https://ipinfo.io/json"







GEO_TRACE_URL = "https://www.cloudflare.com/cdn-cgi/trace"



GEO_TIMEOUT = 3.0





GEO_BREAKER_THRESHOLD = 3



_MIN_CC_LEN = 2




_NOT_COUNTRIES = frozenset({"NULL", "NONE", "NAN", "N/A", "NA", "UNK",
                            "UNKNOWN", "XX", "T1", "ZZ", "FALSE", "TRUE"})









_FALLBACK_URLS = (
    "https://ipwho.is?fields=country_code",
    "https://ip-api.com/json/?fields=countryCode,country",
)




_country_by_host: Dict[str, Optional[str]] = {}


def get_cached_country(host: str) -> Optional[str]:
                                                                    

                                                                       
                                                                   
                               
       
    code = _country_by_host.get(host)
    if code is not None:
        return code
    persistent = get_persistent_country(host)
    if persistent:
        _country_by_host[host] = persistent
    return persistent


def set_cached_country(host: str, code: Optional[str]) -> None:
                                                           

                                                                        
                                                                       
                     

                                                                
                                                                     
                                                                         
                                                
       
    _country_by_host[host] = code
    set_persistent_country(host, code)


class GeoBreaker:
                                                                  

                                                                   
                                                                
                                                         
                                                                      
                           

                                                                     
                                                                   
                                                                     
                                           

                                                                  
                                                                      
                                                                      
                                                   

                                                                     
                                                                  
                                                
       

    def __init__(self, window: int = 10, failure_ratio: float = 0.7,
                 threshold: Optional[int] = None) -> None:
        self.window = max(1, int(window))


        self._fail_open_ratio = float(failure_ratio)


        self.threshold = (threshold if threshold is not None
                          else GEO_BREAKER_THRESHOLD)
        self._outcomes: deque[bool] = deque(maxlen=self.window)
        self.asked = 0
        self.answered = 0
        self._lock = threading.Lock()

    def record(self, success: bool) -> bool:
                                                               

                                                                       
                                                         
           
        with self._lock:
            self.asked += 1
            if success:
                self.answered += 1
            self._outcomes.append(success)
            return self._open_now()

    def _open_now(self) -> bool:
                                                                 

                                                                   
                                                  
           
        if self.threshold <= 0:
            return False
        if not self._outcomes:
            return False
        failures = sum(1 for ok in self._outcomes if not ok)
        if failures >= self.threshold:
            return True
        if len(self._outcomes) == self.window:
            ratio = failures / len(self._outcomes)
            return ratio >= self._fail_open_ratio
        return False

    def failure_ratio(self) -> float:
                                                                   
                                                                  
                                                 
           
        with self._lock:
            if not self._outcomes:
                return 0.0
            return sum(1 for ok in self._outcomes if not ok) / len(
                self._outcomes)

    @property
    def is_open(self) -> bool:
                                                             

                                                           
           
        with self._lock:
            return self._open_now()


class GeoState:
                                                                

                                                                         
                                                                           
                                                                           
                                                                         
                                
       

    def __init__(self, breaker: Optional["GeoBreaker"] = None) -> None:
        self.countries: Dict[str, str] = {}
        self.breaker = breaker if breaker is not None else GeoBreaker()






        self.unknown_action: Optional[str] = None

    def add(self, node_key: str, code: Optional[str]) -> None:
                                                                                              
        if code:
            self.countries[node_key] = code

    def summary(self) -> Dict[str, int]:
                                                                                 
        out: Dict[str, int] = {}
        for code in self.countries.values():
            key = (code or "?").upper() or "?"
            out[key] = out.get(key, 0) + 1
        return out


def fetch_country_via_port(
    local_port: int,
    timeout: float = GEO_TIMEOUT,
    url: str = GEO_URL,
    breaker: Optional["GeoBreaker"] = None,
) -> Optional[str]:
                                                              

                                                                      
                                                              
                                                                     
                   

                                                                            
                                                                          
                                                                     
                                                                          
                                                                          
                                                          

                                                                   
                                                                       
                                                                           
                                                                         
           
       
    if breaker is not None and breaker.is_open:
        return None
    opener = build_opener(
        ProxyHandler({"http": f"http://127.0.0.1:{local_port}",
                      "https": f"http://127.0.0.1:{local_port}"}),
    )

    def _read(target: str) -> bytes:
        with opener.open(Request(target, headers={
            "User-Agent": "proxy-curator/geo",
        }), timeout=timeout) as resp:
            return resp.read()




    sources = [(GEO_TRACE_URL, _parse_trace), (url, _json_code)]
    sources += [(target, _json_code) for target in _FALLBACK_URLS]
    for i, (target, parse) in enumerate(sources):
        try:
            code = parse(_read(target))
        except Exception as e:

            if i == 0:
                dlog(f"[geo] {local_port}: {type(e).__name__}")

            continue
        if code is not None:
            if breaker is not None:
                breaker.record(True)
            return code
    if breaker is not None:
        breaker.record(False)
    return None


def _clean_code(value: Any) -> Optional[str]:
                                                                           

                                                                   
                                                                        
                                        
       
    if not isinstance(value, str):
        return None
    code = value.strip().upper()
    if (len(code) < _MIN_CC_LEN or not code.isalpha()
            or not code.isascii() or code in _NOT_COUNTRIES):
        return None
    return code


def _json_code(raw: bytes) -> Optional[str]:
                                                                                     
    return _extract_code(json.loads(raw.decode("utf-8", "replace")))


def _parse_trace(raw: bytes) -> Optional[str]:
                                                                           

                                                                      
                                                 
       
    text = raw.decode("utf-8", "replace")
    for line in text.splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "loc":
            return _clean_code(value)
    return None





GEO_SOURCES: Tuple[Tuple[str, Any], ...] = (
    (GEO_TRACE_URL, _parse_trace),
    (GEO_URL, _json_code),
    *((target, _json_code) for target in _FALLBACK_URLS),
)


def _extract_code(data: Any) -> Optional[str]:
                                                                  

                                                                 
                                                                     
                                                     
       
    if not isinstance(data, dict):
        return None
    for key in ("countryCode", "country_code", "country"):
        code = _clean_code(data.get(key))
        if code is not None:
            return code
    return None


def parse_country(body: bytes) -> Optional[str]:
                                                              

                                                                
       
    try:
        data: Any = json.loads(body.decode("utf-8", "replace"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    code = data.get("countryCode")
    if not isinstance(code, str):
        return None
    code = code.strip().upper()
    if len(code) < _MIN_CC_LEN or not code.isalpha() or not code.isascii():
        return None
    if code in _NOT_COUNTRIES:
        return None
    return code


def keep_or_drop(countries: Dict[str, str], blacklist: List[str],
                 ) -> Tuple[List[str], List[Tuple[str, str]]]:
                                                              

                                                               
                                                                      
                                                                   
                                                                    
                                                             
       
    blocked = {c.strip().upper() for c in blacklist if c and c.strip()}
    if not blocked:
        return sorted(countries), []
    keep, drop = [], []
    for key, code in countries.items():
        cc = (code or "").strip().upper()
        if cc and cc in blocked:
            drop.append((key, cc))
        else:
            keep.append(key)
    return sorted(keep), sorted(drop)


def format_summary(countries: Dict[str, str]) -> str:
                                                                          
    counts: Dict[str, int] = {}
    for code in countries.values():
        counts[(code or "?").upper() or "?"] = \
            counts.get((code or "?").upper() or "?", 0) + 1
    return ", ".join(f"{k}={v}" for k, v in
                     sorted(counts.items(), key=lambda x: (-x[1], x[0])))
