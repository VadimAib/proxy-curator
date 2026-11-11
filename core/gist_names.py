                                                                                

                                                                          
                                                                            
                                                                              
                                                                     
                      

                                                                     
                                                                        
                                                                           
                                                                     
                                                    

                                                                                  
                                                                            
                                                                          
                                           

                                                                          
                                                                              
                                                                           
             
   
from __future__ import annotations

import re



DEFAULT_BASE = "working_nodes"


URI_EXT = ".txt"


CLASH_EXT = ".yaml"


MAX_BASE_LEN = 64




KNOWN_EXTS = (URI_EXT, CLASH_EXT, ".yml")





_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,%d}" % (MAX_BASE_LEN - 1))


def _strip_known_ext(raw: str) -> str:
                                                                                     
    lowered = raw.lower()
    for ext in KNOWN_EXTS:
        if lowered.endswith(ext):
            return raw[: -len(ext)]
    return raw


def _is_valid(base: str) -> bool:
    return bool(base) and _NAME_RE.fullmatch(base) is not None


def effective_base(raw: str | None) -> str:
                                                          

                                                                         
                                                                    
       
    base = _strip_known_ext((raw or "").strip())
    return base if _is_valid(base) else DEFAULT_BASE


def pair(base: str) -> tuple[str, str]:
                                                                                                          
    return base + URI_EXT, base + CLASH_EXT


def describe(raw: str | None) -> dict:
                                                         

                                                                             
                                                                    
                                                                             
                           
       
    raw_text = (raw or "").strip()
    base = effective_base(raw_text)
    uri, clash = pair(base)
    return {
        "raw": raw_text,
        "base": base,
        "uri": uri,
        "clash": clash,
        "replaced": bool(raw_text) and not _is_valid(_strip_known_ext(raw_text)),
    }
