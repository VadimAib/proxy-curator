                                                        

                                                  
   

from __future__ import annotations

import socket
import ssl
import statistics
import time
from typing import Any, Optional

from .stress_common import (CancelCheck, StressResult,
                            _cancel_requested, _cancelled_result,
                            _empty_result, _round2)






_RECV_CHUNK = 64 * 1024



_CAP_SLACK = 64 * 1024


_MAX_HEADERS = 64 * 1024



_MIN_SAMPLES = 2



_MIN_TOPUP_BYTES = 64 * 1024
_MIN_WINDOW_LEFT = 0.1





_MAX_TOPUPS = 20


def _parse_status(header: bytes) -> int:
                                                                                                                         
    line = header.split(b"\r\n", 1)[0]
    parts = line.split(b" ", 2)
    if len(parts) < 2:
        return 0
    try:
        return int(parts[1])
    except ValueError:
        return 0


def _read_http_body(ssock: Any, cap: int) -> tuple[int, int, float]:
                                                                          

                                                                           
                                                                
                                                                           
                                                                             
                                                                            

                                                                         
                                                                         
                                                               
       
    header = b""
    while b"\r\n\r\n" not in header:
        if len(header) > _MAX_HEADERS:
            return 0, 0, 0.0
        chunk = ssock.recv(_RECV_CHUNK)
        if not chunk:
            return 0, 0, 0.0
        header += chunk
    split = header.find(b"\r\n\r\n") + 4
    status = _parse_status(header[:split])
    t_headers = time.perf_counter()
    total = len(header) - split
    while total < cap:
        chunk = ssock.recv(min(_RECV_CHUNK, cap - total))
        if not chunk:
            break
        total += len(chunk)
    t_end = time.perf_counter()
    return status, total, max(t_end - t_headers, 0.0)


def _fetch_once(ctx: Any, host: str, port: int, host_header: str,
                size: int, timeout_s: float
                ) -> tuple[Optional[float], int, Optional[str]]:
                                                                 

                                                                               
                                                                            
                                                                          
       
    cap = int(size) + _CAP_SLACK
    try:
        with socket.create_connection((host, int(port)), timeout=timeout_s) as raw:
            with ctx.wrap_socket(raw, server_hostname=host_header) as ssock:
                ssock.settimeout(30.0)
                req = (
                    f"GET /__down?bytes={int(size)} HTTP/1.1\r\n"
                    f"Host: {host_header}\r\n"
                    "User-Agent: ProxyCurator-stdlib/1.0\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                )
                ssock.sendall(req.encode("ascii"))
                status, got, transfer = _read_http_body(ssock, cap)
    except Exception as exc:
        return None, 0, str(exc)[:120]
    if status and not 200 <= status < 300:
        return None, status, f"HTTP {status}"
    if got <= 0 or transfer <= 0:
        return None, status, "empty download"
    return (got * 8.0) / (transfer * 1_000_000.0), status, None


def _size_for_rate(mbps: float, cap: int) -> int:
                                                                 

                                                                            
                                                                        
       
    one_second = int(mbps * 1_000_000.0 / 8.0)
    return max(_MIN_TOPUP_BYTES, min(int(cap), one_second))


def run_network_stress(
    *,
    host: str = "speed.cloudflare.com",
    port: int = 443,
    host_header: Optional[str] = None,
    bytes_per_request: int = 1024 * 1024,
    requests: int = 20,
    duration_s: float = 10.0,
    cancel: CancelCheck = None,
) -> StressResult:
                                                              

                                                                               
                                                                            
                                                                                 
                                                                                
                                                                           
           

                                                                                
                                                                              
                                                                              
                                                                            
                                                       

                                                                   
                                                                               
                                                                       
                                                                           
                                                                           
                                                               
       
    if bytes_per_request <= 0 or requests <= 0 or host is None:
        return _empty_result(
            "Network stress", "network",
            "bytes_per_request, requests and host must be positive",
        )
    if host_header is None:
        host_header = host
    ctx = ssl.create_default_context()
    per_request: list[float] = []
    errors: list[str] = []
    rejected: list[int] = []
    start = time.perf_counter()
    sent = 0
    for _ in range(int(requests)):
        if _cancel_requested(cancel):
            return _cancelled_result("Network stress", "network")
        if time.perf_counter() - start >= duration_s:
            break
        rate, status, error = _fetch_once(ctx, host, int(port), host_header,
                                          int(bytes_per_request), duration_s)
        sent += 1
        if status and not 200 <= status < 300:


            rejected.append(status)
        if rate is None:
            errors.append(error or "measurement failed")
            if status in (403, 429):


                break
            continue
        per_request.append(rate)








    probe = per_request[0] if per_request else None
    samples = per_request[1:]
    elapsed = time.perf_counter() - start
    if not samples and probe is not None:
        samples = [probe]
    topups = 0
    while True:
        if _cancel_requested(cancel):
            return _cancelled_result("Network stress", "network")





        if duration_s - elapsed <= _MIN_WINDOW_LEFT + 1e-6:
            break
        if probe is None:
            break
        if topups >= _MAX_TOPUPS:


            break
        topups += 1
        size = _size_for_rate(statistics.median([probe, *samples]),
                              int(bytes_per_request))
        rate, status, error = _fetch_once(ctx, host, int(port), host_header,
                                          size, duration_s)
        sent += 1
        if status and not 200 <= status < 300:
            rejected.append(status)
        if rate is None:
            errors.append(error or "measurement failed")


            elapsed = time.perf_counter() - start
            if status in (403, 429):
                break
            continue
        samples.append(rate)
        elapsed = time.perf_counter() - start

    if not samples:
        if rejected:


            return _empty_result(
                "Network stress", "network",
                f"server rejected the measurement: HTTP {rejected[0]}"
                f" ({len(rejected)} of {int(requests)} requests)",
                error_code=f"http_{rejected[0]}",
            )
        return _empty_result(
            "Network stress", "network",
            "no responses; " + ("; ".join(errors[:3]) if errors else "timeout"),
        )
    return StressResult(
        name=f"Internet ({host})",
        kind="network",
        success=True,
        duration_s=_round2(elapsed),
        units="Mbps",
        value=_round2(statistics.median(samples)),
        value_min=_round2(min(samples)),
        value_max=_round2(max(samples)),
        samples=len(samples),
        write_mbps=0.0,
        read_mbps=0.0,
        error=None,
        rejected=len(rejected),
        coverage=elapsed / duration_s if duration_s else 0.0,
    )
