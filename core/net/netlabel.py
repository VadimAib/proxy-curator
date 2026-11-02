                                                    

                                                
                                                                   
                                                                      
             

                                                                       
                                                                           
                                                               
                                                         
                                                               
         

                                                                     
                                                                        
                                                                        
                                                                      
                                                                         
                                                          

                                                                       
                                                                            
                                                                 
                                                                      
                                                                      
             

                                                                        
                                                                     
                                                                      
                                                                       
                                                                 
   
import hashlib
from typing import Any, Dict

from ..log import LOG
from .netmon import detect_channel_profile, get_local_ip, measure_local_link




NET_LABELS = ("full", "light", "unknown")





_FALLBACK = "unknown"




_ALLOWED = set("abcdefghijklmnopqrstuvwxyz0123456789-")


def network_fingerprint() -> str:
                                                              

                                                                           
                                                                       
                                                                          
                                                      
       
    return _network_fingerprint(get_local_ip())


def _network_fingerprint(local_ip: str) -> str:
                                                                    

                                                                        
                                                                          
                                                                          
                                                                       

                                                                    
                                                                         
                                                                   
                                               
       
    if not local_ip:
        return ""
    return hashlib.sha1(local_ip.encode("utf-8")).hexdigest()[:8]


def resolve_run_network(stats: Dict[str, Any]) -> str:
                                                                     

                                                                  
                                                                         
                                                                       
                                              

                                                                
                                        
       
    cached = stats.get("local_link")
    if isinstance(cached, (list, tuple)) and len(cached) == 2:
        try:
            label = detect_channel_profile(float(cached[0]), float(cached[1]))
            return label if label in NET_LABELS else _FALLBACK
        except (TypeError, ValueError):
            pass

    measured = measure_local_link()
    if measured is None:
        return _FALLBACK
    rtt_ms, jitter_ms = measured
    stats["local_link"] = [round(float(rtt_ms), 1), round(float(jitter_ms), 1)]
    try:
        label = detect_channel_profile(float(rtt_ms), float(jitter_ms))
    except (TypeError, ValueError):
        return _FALLBACK
    return label if label in NET_LABELS else _FALLBACK


def log_run_network(stats: Dict[str, Any]) -> str:
                                                                 

                                                                        
                                                                        
                                                       
                                                                  

                                                                   
                                                                   
                                                                     
                                                                        
                                                     

                                                                  
                                                           
                      
       
    label = str(stats.get("run_network") or _FALLBACK)
    if stats.get("local_link"):
        origin = f" (auto-detect: local_link={stats['local_link']})"
    else:
        origin = " (label not set)"
    LOG(f"[net] {label}{origin}")
    return label


def safe_dirname(label: str) -> str:
                                         

                                                                          
                                                                       
                                                                      
                                                        
       
    text = str(label or "").strip().lower()
    cleaned = "".join(ch if ch in _ALLOWED else "-" for ch in text)
    cleaned = cleaned.strip("-")
    return cleaned or _FALLBACK
