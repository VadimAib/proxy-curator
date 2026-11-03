                                                                                                              
from __future__ import annotations

import ipaddress
import itertools
import shutil
import socket
import threading
from typing import Any
from core import stress_advice
from core import stress_tests as st
from core.config import Config
from core.paths import rp
from server_config import CONFIG_PATH, _read_summary










class StressRun:
                                                                                                             

    _ids = itertools.count(1)

    def __init__(self, kind: str) -> None:
        self.id = next(StressRun._ids)
        self.kind = kind
        self.cancel = threading.Event()
        self.cond = threading.Condition()
        self.result: dict | None = None


_active: list[StressRun] = []
_active_lock = threading.Lock()


def _register(run: StressRun) -> None:
    with _active_lock:
        _active.append(run)


def _unregister(run: StressRun) -> None:
    with _active_lock:
        if run in _active:
            _active.remove(run)


def cancel_all() -> int:
                                                               

                                                                             
                                                                 
       
    with _active_lock:
        runs = list(_active)
    for run in runs:
        run.cancel.set()
    return len(runs)


def _run_stress(kind: str, payload: dict, run: StressRun) -> dict:
                                                                                   
    try:
        kwargs = {
            k: v
            for k, v in payload.items()
            if k in st.KWARGS.get(kind, ())
        }
        if kind == "disk":


            kwargs["dir"] = str(rp(Config.load(CONFIG_PATH).output.cache_dir))


        kwargs["cancel"] = run.cancel.is_set
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


def _run_stress_worker(run: StressRun, payload: dict) -> None:
                                                                            

                                                                           
                                                                              
                                    
       
    result = _run_stress(run.kind, payload, run)
    with run.cond:
        run.result = result
        run.cond.notify_all()


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





_LOCAL_SUFFIXES = (".localhost", ".local", ".internal", ".home.arpa")


def _forbidden_ip(addr: str) -> bool:
                                                                                                          
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_multicast or ip.is_unspecified)


def _resolves_to_internal(host: str, port: int) -> bool:
                                                                         

                                                                          
                                                                         
                                                  
       
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError):
        return False
    except OSError:
        return False
    return any(_forbidden_ip(str(info[4][0])) for info in infos)


def network_target_error(kwargs: dict[str, Any]) -> str | None:
                                                            

                                                                    
                                                                        
                                                                           
                                                              
                                                
       
    host = kwargs.get("host")
    if host is None:
        return None
    if not isinstance(host, str):
        return "host must be a string"
    name = host.strip()
    if not name:
        return "host is empty"
    if "://" in name or "/" in name or " " in name:


        return "host must be a bare hostname (no scheme, path or spaces)"
    try:
        port = int(kwargs.get("port") or 443)
    except (TypeError, ValueError):
        return "port must be a number"
    if not 1 <= port <= 65535:
        return "port must be 1..65535"
    lowered = name.lower().rstrip(".")
    if lowered == "localhost" or lowered.endswith(_LOCAL_SUFFIXES):
        return "localhost is not a measurement target"
    if _forbidden_ip(lowered):
        return f"private address {name} is not a measurement target"
    if _resolves_to_internal(lowered, port):
        return f"host {name} resolves to a private address"
    header = kwargs.get("host_header")
    if header is not None:


        if not isinstance(header, str):
            return "host_header must be a string"
        bare = header.strip()
        if (not bare or "://" in bare or "/" in bare
                or any(ch.isspace() for ch in bare)):
            return "host_header must be a bare hostname (no scheme, path or spaces)"
    return None
