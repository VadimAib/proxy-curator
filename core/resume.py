                                  

                                                                             
                                          

                                                                                
                                                                           
                   
   
import json
import time
from typing import Dict, List, Optional, Tuple

from .log import LOG
from .models import Node
from .paths import ROOT
from .state import PipelineState

RESUME_FILE = ROOT / "temp" / "curate_resume.json"
RESUME_TTL = 4 * 3600


def _write_checkpoint(phase: str, candidates: List[Tuple[Node, float]],
                      ok_all: List[Tuple[Node, float]], stats: Dict,
                      quick_pool: Optional[List[Tuple[Node, float]]] = None
                      ) -> None:
                                                                            
                                                                

                                                                             
                                                                            
                                                               
       
    try:
        RESUME_FILE.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "version": "8.2",
            "timestamp": time.time(),
            "phase": phase,
            "candidates": [{"raw": n.raw, "tcp_ms": m}
                           for n, m in candidates if n and n.raw],
            "ok_all": [{"raw": n.raw, "ms": m}
                       for n, m in ok_all if n and n.raw],
            "quick_pool": [{"raw": n.raw, "tcp_ms": m}
                           for n, m in (quick_pool or []) if n and n.raw],
            "stats": stats
        }
        tmp = RESUME_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        tmp.replace(RESUME_FILE)
    except Exception as e:
        LOG(f"[resume] save error: {e}")


def save_state(state: PipelineState) -> None:
                                                                 

                                                                      
                                                                           
                                                                      
                                                                              

                                                                    
                                                                            
                                                                      
                                                                             
                                                  
       
    if not getattr(state, "save_checkpoint", True):
        return
    _write_checkpoint(state.current_phase, state.alive, state.final,
                      state.stats, state.quick_pool)


def load_state() -> Optional[Dict]:
    if not RESUME_FILE.exists():
        return None
    try:
        data = json.loads(RESUME_FILE.read_text(encoding="utf-8"))
        if time.time() - data.get("timestamp", 0) < RESUME_TTL:




            if "version" not in data:
                LOG("[resume] old state format detected, skipping (will rescan)")
                RESUME_FILE.unlink(missing_ok=True)
                return None
            return data
        else:
            LOG("[resume] state file expired")
            RESUME_FILE.unlink(missing_ok=True)
    except Exception:
        RESUME_FILE.unlink(missing_ok=True)
    return None


def clear_state() -> None:
    RESUME_FILE.unlink(missing_ok=True)
