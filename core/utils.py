                       
import re
from pathlib import Path
from typing import Any, Dict, Optional, Union




_DIGITS = re.compile(r"\d+")
_WS = re.compile(r"\s+")


def reason_key(reason: Optional[str], limit: int = 100) -> str:
                                                                             

                                                                        
                                                                            
                                                                            
                                                                       
                                            

                                                                   
                                                                      
                                                                         
                                                                       
                                                                           
                                                

                                                                            
                                                                        
                                                                       
       
    text = _WS.sub(" ", _DIGITS.sub("#", str(reason or ""))).strip()
    if not text:
        return "unknown"
    return text[:limit]


def first(d: Dict[str, Any], key: str, default: str = "") -> str:
                                                               
    if not isinstance(d, dict):
        return default
    v = d.get(key, default)
    if isinstance(v, list):
        v = v[0] if v else default
    if v is None:
        return default
    return str(v).strip()


def first_line(exc: BaseException, limit: int = 120) -> str:
                                                                         

                                                                           
                                                                            
                                                                               
                                                                           
                                                           
       
    text = str(exc).strip()
    if not text:
        text = type(exc).__name__
    lines = text.splitlines()
    return (lines[0] if lines else type(exc).__name__)[:limit]


def write_text_atomic(path: Union[str, Path], text: str,
                      encoding: str = "utf-8") -> None:
                                                                

                                                                           
                                                                           
                                                                         
                                                             
                                                                         
                                                                        

                                                                           
                                                                          
                                                                 

                                                                   
                                                            
       
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    try:
        tmp.write_text(text, encoding=encoding)
        tmp.replace(target)
    except OSError:


        try:
            tmp.unlink()
        except OSError:
            pass
        raise