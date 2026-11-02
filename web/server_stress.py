                                                                                                              
from __future__ import annotations

import shutil
import threading
from core import stress_advice
from core import stress_tests as st
from core.config import Config
from core.paths import rp
from server_config import CONFIG_PATH, _read_summary



_stress_result: dict | None = None
_stress_cond = threading.Condition()





_stress_cancel = threading.Event()


def _cancel_check() -> bool:
                                                                                                      
    return _stress_cancel.is_set()


def _run_stress(kind: str, payload: dict) -> dict:
                                                                                   
    try:
        kwargs = {
            k: v
            for k, v in payload.items()
            if k in st.KWARGS.get(kind, ())
        }
        if kind == "disk":


            kwargs["dir"] = str(rp(Config.load(CONFIG_PATH).output.cache_dir))


        kwargs["cancel"] = _cancel_check
        result = st.run_stress(kind, **kwargs)
        out = result._asdict()



        out["verdict"] = stress_advice.verdict_for(
            kind, result,
            reference_nodes=_run_reference_nodes() if kind == "cpu" else None,
            free_mb=_disk_free_mb() if kind == "disk" else None,
        )
        return out
    except Exception as exc:
        return {
            "name": kind,
            "kind": kind,
            "success": False,
            "duration_s": 0.0,
            "units": "",
            "value": 0.0,
            "value_min": 0.0,
            "value_max": 0.0,
            "samples": 0,
            "write_mbps": 0.0,
            "read_mbps": 0.0,
            "write_cached_mbps": 0.0,
            "rejected": 0,
            "error": f"{type(exc).__name__}: {exc}",
            "error_code": None,
            "verdict": None,
        }


def _run_stress_worker(kind: str, payload: dict) -> None:
                                                                            

                                                                            
                                                                      
                                                     
       
    global _stress_result
    with _stress_cond:
        _stress_result = None


    result = _run_stress(kind, payload)
    with _stress_cond:
        _stress_result = result
        _stress_cond.notify_all()


def _run_reference_nodes() -> int | None:
                                                                                                           
    run = _read_summary()
    value = run.get("links_total") if run else None
    return int(value) if isinstance(value, int) and value > 0 else None


def _disk_free_mb() -> float | None:
                                                                                                                                
    try:
        usage = shutil.disk_usage(rp(Config.load(CONFIG_PATH).output.cache_dir))
        return usage.free / 1_000_000.0
    except Exception:
        return None


def _measure_channel(net_kwargs: dict | None = None,
                     cancel: st.CancelCheck = None) -> dict:
                                                                                                                        
    from core.net.netmon import measure_local_link
    link = measure_local_link()
    rtt_ms = link[0] if link else None
    jitter_ms = link[1] if link else None
    options = {"requests": 8, "duration_s": 8.0}
    options.update(net_kwargs or {})
    net = st.run_network_stress(cancel=cancel, **options)
    mbps = net.value if net.success else None
    return {
        "mbps": mbps,
        "rtt_ms": rtt_ms,
        "jitter_ms": jitter_ms,
        "network": net,
    }


def _stress_kwargs(kind: str, payload: dict, *,
                   max_duration_s: float,
                   max_bytes: int) -> tuple[dict, str | None]:
                                                                           

                                                                            
                                                                       
                                    
       
    section = payload.get(kind)
    if not isinstance(section, dict):
        section = payload
    kwargs = {k: v for k, v in section.items() if k in st.KWARGS.get(kind, ())}
    duration_s = kwargs.get("duration_s")
    if isinstance(duration_s, (int, float)) and duration_s > max_duration_s:
        return {}, f"duration_s too large (max {max_duration_s}s)"
    bytes_per_file = kwargs.get("bytes_per_file")
    if isinstance(bytes_per_file, (int, float)) and bytes_per_file > max_bytes:
        return {}, f"bytes_per_file too large (max {max_bytes} bytes)"
    return kwargs, None
