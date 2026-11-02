                                                     

           
                                                       
                                                                   

                                                                
                                                                      
                                                                
                                                                   
                                                                      
                       
   

from __future__ import annotations

import re

_PHASE_RE = re.compile(r"^===\s*PHASE\s*(\d+)/(\d+):\s*(.+?)\s*===")
_PROGRESS_RE = re.compile(r"^\[([^\]]+)\s*\]\s*\[[#\.]+\]\s*(\d+)%\s*(\d+)/(\d+)")


def is_progress_bar_line(line: str) -> bool:
                                                                                          
    return _PROGRESS_RE.match(line) is not None


def update_progress_from_line(line: str, state: dict) -> None:
                                                                                                               
    m = _PHASE_RE.match(line)
    if m:
        state["phase_num"] = int(m.group(1))
        state["phase_total"] = int(m.group(2))
        state["phase"] = m.group(3).strip()
        state["percent"] = 0


        state["label"] = ""
        state["done"] = 0
        state["total"] = 0
        return
    m = _PROGRESS_RE.match(line)
    if m:
        state["label"] = m.group(1)
        state["percent"] = int(m.group(2))
        state["done"] = int(m.group(3))
        state["total"] = int(m.group(4))
