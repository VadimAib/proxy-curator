                                                                        

                                                                              
                                                                                
                                                   

                                                                   
                                                                 
                                                     
                                                                        
                                  

           
                                                                         
                                                                                  
                                                            
                                                                             
                                                        
                                                                                 
                                                                          

                                                                                
   
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple
from urllib.error import HTTPError
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener

from ..config import TestUrlConfig





_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def _build_opener(local_port: int):
    proxy_url = f"http://127.0.0.1:{local_port}"
    return build_opener(
        ProxyHandler({"http": proxy_url, "https": proxy_url}),
        HTTPSHandler(context=_SSL_CTX),
    )


def _check_single_URL(opener, test_url: TestUrlConfig, timeout: float) -> bool:
    try:
        req = Request(test_url.url, headers={
            "User-Agent": "Mozilla/5.0",
            "Connection": "close",
        })
        with opener.open(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            return status in test_url.ok_statuses
    except HTTPError as e:
        return e.code in test_url.ok_statuses
    except Exception:
        return False


def _test_url_group_any(local_port: int, urls: List[TestUrlConfig], timeout: float) -> bool:
    if not urls:
        return False
    opener = _build_opener(local_port)
    executor = ThreadPoolExecutor(max_workers=min(len(urls), 3))
    futures = [executor.submit(_check_single_URL, opener, u, timeout) for u in urls]
    try:
        for future in as_completed(futures):
            if future.result():
                return True
        return False
    finally:






        executor.shutdown(wait=False, cancel_futures=True)


def _test_url_group_all(
    local_port: int, urls: List[TestUrlConfig], timeout: float
) -> Tuple[bool, List[str]]:
    if not urls:
        return True, []
    opener = _build_opener(local_port)
    failed = []
    with ThreadPoolExecutor(max_workers=min(len(urls), 4)) as executor:
        future_map = {executor.submit(_check_single_URL, opener, u, timeout): u for u in urls}
        for future in as_completed(future_map):
            url_cfg = future_map[future]
            try:
                ok = future.result()
            except Exception:
                ok = False
            if not ok:
                failed.append(url_cfg.url)
    return (len(failed) == 0), failed


def http_test(
    local_port: int,
    connectivity_urls: List[TestUrlConfig],
    bypass_urls: List[TestUrlConfig],
    critical_urls: List[TestUrlConfig],
    timeout: float,
    critical_timeout: Optional[float] = None,
    connectivity_timeout: Optional[float] = None,
    bypass_timeout: Optional[float] = None,
    critical_mode: str = "all",
) -> Optional[str]:
                                                                           

                            
                                        
                                        
                                              
       

    conn_t = connectivity_timeout if connectivity_timeout else timeout
    if connectivity_urls:
        if not _test_url_group_any(local_port, connectivity_urls, conn_t):
            return "no_connectivity"


    byp_t = bypass_timeout if bypass_timeout else timeout
    if bypass_urls:
        if not _test_url_group_any(local_port, bypass_urls, byp_t):
            return "no_bypass"


    if critical_urls:
        ct = critical_timeout if critical_timeout is not None else timeout
        if critical_mode == "any":
            if not _test_url_group_any(local_port, critical_urls, ct):
                names = [u.name or u.url.split("/")[2][:20] for u in critical_urls]
                return f"critical_failed:{','.join(names)}"
        else:
            all_ok, failed = _test_url_group_all(local_port, critical_urls, ct)
            if not all_ok:
                names = []
                for url in failed:
                    if "telegram" in url.lower():
                        names.append("telegram")
                    elif "whatsapp" in url.lower():
                        names.append("whatsapp")
                    elif "instagram" in url.lower():
                        names.append("instagram")
                    else:
                        names.append(url.split("/")[2][:20])
                return f"critical_failed:{','.join(names)}"
    return None
