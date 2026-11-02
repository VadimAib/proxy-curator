                                                                             

                                                                        
                                                                      
                                                                    
                                                         
                       

                                                                    
                                                                         
from typing import Dict, Optional, Set
from ..log import LOG

VALID_FINGERPRINTS = {
    "chrome", "firefox", "safari", "ios", "android",
    "edge", "360", "qq", "random", "randomized",
    "randomizednoalpn", "unsafe",
}













REALITY_FINGERPRINTS = VALID_FINGERPRINTS - {"unsafe"}




_FP_SUBSTITUTIONS: Dict[str, int] = {}


def _resolve_fingerprint(raw: str, default: str = "chrome",
                         allowed: Optional[Set[str]] = None) -> str:
                                                                            

                                                                           
                                                                            
                                                                

                                                                         
                                                                 
                                                                      
                               
                                                                     
                                                                   
                                                                      
                                                                           
                                                                          
                                                                           
                                                                       
                                                                              
                                                                             
                                                                         
                                 

                                                                         
                           

                                                                        
                                                          
                            

                                                                         
                                                                      
                                                                
       
    allowed = VALID_FINGERPRINTS if allowed is None else allowed
    fp = (raw or "").strip().lower()
    if not fp:
        return default
    if fp in allowed:
        return fp
    first_time = fp not in _FP_SUBSTITUTIONS
    _FP_SUBSTITUTIONS[fp] = _FP_SUBSTITUTIONS.get(fp, 0) + 1
    if first_time:
        LOG(f"[xray] fp={fp!r} not in project list — substituted with {default!r}")
    return default


def log_fingerprint_substitutions() -> None:
                                                                                                
    if not _FP_SUBSTITUTIONS:
        return
    total = sum(_FP_SUBSTITUTIONS.values())
    top = ", ".join(f"{k}×{v}" for k, v in
                    sorted(_FP_SUBSTITUTIONS.items(), key=lambda x: -x[1])[:5])
    LOG(f"[xray] substituted fp for {total} node(s): {top}")

