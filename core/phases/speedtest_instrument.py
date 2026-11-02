                                                           

                                                                           
                                                                            
                                                                      
                                                               
                         

                                                                  
                                                                           
                                                          
   
from __future__ import annotations

import threading
from typing import Optional














_READ_CHUNK = 32 * 1024






_CAP_SLACK = 64 * 1024








_TRANSFER_DEADLINE_FACTOR = 6.0


_MIN_TRANSFER_DEADLINE = 30.0











_TIMEOUT_ESCALATION = 2.0



_READ_TIMEOUT_MARKERS = ("timed out", "timeout")









_saved_by_escalation = 0
_saved_lock = threading.Lock()


def escalation_saved() -> int:
                                                                                                                             
    return _saved_by_escalation


def _reset_escalation_counter() -> None:
    global _saved_by_escalation
    with _saved_lock:
        _saved_by_escalation = 0


def _count_saved_by_escalation() -> None:
    global _saved_by_escalation
    with _saved_lock:
        _saved_by_escalation += 1


def _is_read_timeout(err: Optional[str]) -> bool:
                                                                     

                                                                          
                                                                        

                                                                        
                                                                          
                                       
       
    if not err:
        return False
    low = err.lower()
    if "transfer exceeded" in low:
        return False
    return any(m in low for m in _READ_TIMEOUT_MARKERS)




def transfer_deadline(timeout: float) -> float:
                                                                   

                                                                       
                                                                         
                                                                  
                                                                           
                                                                        
       
    return max(float(timeout) * _TRANSFER_DEADLINE_FACTOR,
               _MIN_TRANSFER_DEADLINE)


def timeout_for_budget(seconds: float) -> float:
                                                                  

                                                                       
                                                                      
                                                               
       
    return round(max(float(seconds), 0.0) / _TRANSFER_DEADLINE_FACTOR, 1)




def calc_mbps(nbytes: int, elapsed_sec: float) -> float:
                                                          

                                                             
                                                                           
                                                          
       
    if elapsed_sec <= 0:
        return 0.0
    return (nbytes * 8) / (elapsed_sec * 1_000_000)
