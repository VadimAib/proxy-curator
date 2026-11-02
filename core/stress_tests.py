                                                             

                                                                             

                                                                               
                                                                           
                                                                       
                                                                                 
                                                                           
                                                                                
                                                 
                                                                               
                                                                              
                                                                               
                        

                                                                               
                                                                          
                                                                       
   







from __future__ import annotations

from typing import Any

from .stress_common import KWARGS, CancelCheck, StressResult, _empty_result
from .stress_cpu import run_cpu_stress
from .stress_disk import run_disk_stress
from .stress_net import run_network_stress

__all__ = [
    "StressResult",
    "run_cpu_stress",
    "run_network_stress",
    "run_disk_stress",
    "run_stress",
]





def run_stress(stress: str, **kwargs: Any) -> StressResult:
                                                                          
    mapping = {
        "cpu": run_cpu_stress,
        "network": run_network_stress,
        "disk": run_disk_stress,
    }
    func = mapping.get(stress)
    if func is None:
        return _empty_result(
            f"stress {stress}", stress,
            f"unknown stress kind {stress!r} (want cpu|network|disk)",
        )
    try:
        return func(**kwargs)
    except Exception as exc:
        return _empty_result(
            f"Stress {stress}", stress, f"{type(exc).__name__}: {exc}"
        )
