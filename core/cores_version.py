from __future__ import annotations

import re
from pathlib import Path
from typing import Tuple, Optional

from .cores_specs import CoreSpec
from .engine.selftest import get_kernel_version

_VERSION_RE = re.compile(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z][0-9A-Za-z.\-]*)?")


def parse_version(text: str) -> str:
                                           

                                                                               
                                                 

                                                                               
                                                     
       
    m = _VERSION_RE.search(text or "")
    return m.group(0) if m else ""


def version_key(version: str) -> Tuple:
                                                                              

                                                                             
                                                                               
                                                                            
                                                            
       
    base, _, pre = str(version or "").partition("-")
    nums = [int(p) for p in base.split(".") if p.isdigit()][:3] or [0]
    release = tuple(nums + [0] * (3 - len(nums)))
    if not pre:
        return (release, 1, ())
    parts = tuple(
        (0, int(tok), "") if tok.isdigit() else (1, 0, tok)
        for tok in pre.split(".") if tok
    )
    return (release, 0, parts)


def is_newer(candidate: str, current: str) -> bool:
                                                                

                                                                            
                                                                         
          
       
    if not candidate:
        return False
    if not current:
        return True
    return version_key(candidate) > version_key(current)


def probe_version(binary: Optional[Path], spec: CoreSpec) -> str:
                                                                           

                                                                                  
                                                                                    
                                                                              
                                                      
       
    if binary is None:
        return ""
    return parse_version(get_kernel_version(binary, spec.version_args))
