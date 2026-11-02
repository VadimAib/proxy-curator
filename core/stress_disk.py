                                                                

                                                  
   

from __future__ import annotations

import os
import statistics
import tempfile
import time
from pathlib import Path
from typing import Optional

from .stress_common import (CancelCheck, StressResult,
                            _cancel_requested, _cancelled_result,
                            _empty_result, _fill_pattern, _round2)







_DISK_DEFAULT_BYTES = 14_000_000




_DISK_DEFAULT_ITERATIONS = 20



_DISK_WARMUP = 2


def run_disk_stress(
    *,
    bytes_per_file: int = _DISK_DEFAULT_BYTES,
    iterations: int = _DISK_DEFAULT_ITERATIONS,
    dir: Optional[str] = None,
    cancel: CancelCheck = None,
) -> StressResult:
                                                                          

                                                                          
                                                                            
                                                                       
                                                                            
                                                                               
                        

                                                                              
                                                                             
                                                                    
                                                                      
                                                              
                                                                              
                                                                            
                                   

                                                                            
                                                                             
                                                                         
                                                                           
                                                                         
                               

                                                                      
                                       
       
    if bytes_per_file <= 0 or iterations <= 0:
        return _empty_result(
            "Disk stress", "disk",
            "bytes_per_file and iterations must be positive",
        )
    _buf = _fill_pattern(bytes_per_file)
    own_tmp = dir is None

    base = Path(dir) if dir else Path(tempfile.mkdtemp(prefix="pc_stress_disk_"))
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _empty_result("Disk stress", "disk",
                             f"cannot use dir {base}: {exc}")
    prefix = f"pc_stress_disk_{os.getpid()}_"
    names: list[Path] = []
    write_rates: list[float] = []
    cached_rates: list[float] = []
    try:







        t0 = time.perf_counter()
        for i in range(iterations + _DISK_WARMUP):
            if _cancel_requested(cancel):
                return _cancelled_result("Disk stress", "disk")
            p = base / f"{prefix}{i:03d}.dat"
            t_w = time.perf_counter()
            with open(p, "wb") as fh:
                fh.write(_buf)
                t_cached = time.perf_counter()
                fh.flush()
                os.fsync(fh.fileno())
            t_device = time.perf_counter()
            names.append(p)
            if i >= _DISK_WARMUP:
                if t_device > t_w:
                    write_rates.append(bytes_per_file / 1_000_000.0 / (t_device - t_w))
                if t_cached > t_w:
                    cached_rates.append(
                        bytes_per_file / 1_000_000.0 / (t_cached - t_w))


        read_rates: list[float] = []
        for p in names:
            if _cancel_requested(cancel):
                return _cancelled_result("Disk stress", "disk")
            t_r = time.perf_counter()
            read_bytes = 0
            with open(p, "rb") as fh:
                while True:
                    chunk = fh.read(1024 * 1024)
                    if not chunk:
                        break
                    read_bytes += len(chunk)
            dt = time.perf_counter() - t_r
            if dt > 0:
                read_rates.append(read_bytes / 1_000_000.0 / dt)


        for p in names:
            for pos in (0, len(_buf) // 2, len(_buf) - 1):
                with open(p, "rb") as fh:
                    fh.seek(pos)
                    chunk = fh.read(1)
                    if chunk != _buf[pos:pos + 1]:
                        raise AssertionError(f"disk verification failed at {p}:{pos}")
        t2 = time.perf_counter()

        if write_rates:
            write_mbps = statistics.median(write_rates)
            write_min = min(write_rates)
            write_max = max(write_rates)
        else:
            write_mbps = (iterations * bytes_per_file) / 1_000_000.0 / max(1e-6, (t2 - t0))
            write_min = write_max = write_mbps
        read_mbps = statistics.median(read_rates) if read_rates else 0.0
        cached_mbps = statistics.median(cached_rates) if cached_rates else 0.0
        return StressResult(
            name="Disk (temp files)" if own_tmp else "Disk (cache dir)",
            kind="disk",
            success=True,
            duration_s=_round2(t2 - t0),
            units="MB/s",
            value=_round2(write_mbps),
            value_min=_round2(write_min),
            value_max=_round2(write_max),
            samples=iterations,
            write_mbps=_round2(write_mbps),
            read_mbps=_round2(read_mbps),
            error=None,
            write_cached_mbps=_round2(cached_mbps),
            coverage=1.0,
        )
    finally:
        for p in names:
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
        if own_tmp:
            try:
                base.rmdir()
            except OSError:
                pass
