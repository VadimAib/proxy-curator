                                                                   

                                                                          
                                                                               
                                            
   

from __future__ import annotations

from collections import namedtuple
from typing import Callable, Optional




KWARGS = {
    "cpu": {"duration_s"},
    "network": {"host", "port", "host_header", "bytes_per_request",
                "requests", "duration_s"},
    "disk": {"bytes_per_file", "iterations"},
}


StressResult = namedtuple(
    "StressResult",
    [
        "name",
        "kind",
        "success",
        "duration_s",
        "units",
        "value",
        "value_min",
        "value_max",
        "samples",
        "write_mbps",
        "read_mbps",
        "error",


        "write_cached_mbps",
        "rejected",
        "error_code",
        "coverage",
    ],
    defaults=(0.0, 0, None, 0.0),
)





def _empty_result(name: str, kind: str, error: Optional[str] = None,
                  error_code: Optional[str] = None) -> StressResult:
    return StressResult(
        name=name,
        kind=kind,
        success=False,
        duration_s=0.0,
        units="",
        value=0.0,
        value_min=0.0,
        value_max=0.0,
        samples=0,
        write_mbps=0.0,
        read_mbps=0.0,
        error=error,
        error_code=error_code,
    )


def _round2(value: float) -> float:
    return round(value, 2)





CancelCheck = Optional[Callable[[], bool]]


def _cancel_requested(cancel: CancelCheck) -> bool:
                                                                                                                          
    try:
        return bool(cancel is not None and cancel())
    except Exception:
        return False


def _cancelled_result(name: str, kind: str) -> StressResult:
                                                                                                                         
    return _empty_result(name, kind, "cancelled", error_code="cancelled")


def _fill_pattern(size: int) -> bytes:
                                                                
    pattern = bytes(range(256))
    if size <= len(pattern):
        return pattern[:size]
    return (pattern * (size // len(pattern) + 1))[:size]
