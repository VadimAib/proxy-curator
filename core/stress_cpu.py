                                                             

                                                  
   

from __future__ import annotations

import base64
import json
import statistics
import time
from typing import Optional

from .stress_common import (CancelCheck, StressResult,
                            _cancel_requested, _cancelled_result,
                            _empty_result, _round2)








_CPU_ROUNDS = 3


_CPU_MIN_ROUND_S = 0.2



_CPU_CORPUS_URI_LINKS = 200
_CPU_CORPUS_YAML_PROXIES = 200

_CPU_UUID = "cd60668d-28d0-4070-8179-47ad0d151dd5"



_CPU_CORPUS: Optional[tuple[list[str], str]] = None


def _build_cpu_corpus() -> tuple[list[str], str]:
                                                                              

                                                                             
                                                                              
                                                                 
       
    links: list[str] = []
    for i in range(_CPU_CORPUS_URI_LINKS):
        kind = i % 4
        if kind == 0:
            links.append(
                f"vless://{_CPU_UUID}@82.202.{i % 255}.{(i * 3) % 255}:443"
                f"?security=reality&pbk=vZ22ThhkpXUd5&type=tcp"
                f"&flow=xtls-rprx-vision#n{i}"
            )
        elif kind == 1:
            links.append(
                f"vless://user@host{i}.com:2053?security=tls&type=ws&path=/"
                f"&host=host{i}.com#n{i}"
            )
        elif kind == 2:
            links.append(
                f"trojan://pw{i}@172.67.{i % 255}.{(i * 5) % 255}:443"
                f"?security=tls&type=tcp#n{i}"
            )
        elif kind == 3:
            links.append(
                f"ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ=@82.38.{i % 255}."
                f"{(i * 11) % 255}:8080#GB{i}"
            )
        else:
            obj = {
                "v": "2", "ps": f"n{i}", "add": f"1.2.{i % 255}.{(i * 7) % 255}",
                "port": "443", "id": _CPU_UUID, "aid": "0", "net": "ws",
                "type": "none", "host": "ex.com", "path": "/ws", "tls": "tls",
            }
            links.append("vmess://"
                         + base64.b64encode(json.dumps(obj).encode()).decode())
    yaml_lines = ["proxies:"]
    for i in range(_CPU_CORPUS_YAML_PROXIES):
        yaml_lines.append(
            f"  - {{name: n{i}, type: ss, server: 1.2.{i % 255}."
            f"{(i * 3) % 255}, port: 8388, cipher: aes-256-gcm, "
            f"password: pass}}"
        )
    return links, "\n".join(yaml_lines) + "\n"


def _cpu_corpus() -> tuple[list[str], str]:
    global _CPU_CORPUS
    if _CPU_CORPUS is None:
        _CPU_CORPUS = _build_cpu_corpus()
    return _CPU_CORPUS


def _cpu_round(duration_s: float,
               cancel: CancelCheck = None) -> Optional[tuple[float, float]]:
                                                                                

                                                                  
                                                                               
                                                                        
                                                                              

                                                                    
                                                                        
       
    from .parsers._dispatch import parse_config_text, parse_node
    links, yaml_text = _cpu_corpus()
    start = time.perf_counter()
    nodes = 0
    while True:
        if _cancel_requested(cancel):
            return None
        for link in links:
            if parse_node(link) is not None:
                nodes += 1
        nodes += len(parse_config_text(yaml_text, "yaml"))
        if time.perf_counter() - start >= duration_s:
            break
    elapsed = time.perf_counter() - start
    return (nodes / elapsed if elapsed > 0 else 0.0), elapsed


def run_cpu_stress(
    *,
    duration_s: float = 5.0,
    rounds: int = _CPU_ROUNDS,
    cancel: CancelCheck = None,
) -> StressResult:
                                                                          

                                                                 
                                                                              
                                                                        
                                                                           
                                                                        

                                                                       
                                                                      
       
    if duration_s <= 0:
        return _empty_result("CPU stress", "cpu", "duration_s must be > 0")
    n_rounds = max(1, int(rounds))
    per_round = max(_CPU_MIN_ROUND_S, duration_s / (n_rounds + 1))
    rates: list[float] = []
    burn = 0.0
    if _cancel_requested(cancel):
        return _cancelled_result("Feed parsing", "cpu")


    if _cpu_round(per_round, cancel) is None:
        return _cancelled_result("Feed parsing", "cpu")
    burn += per_round
    for _ in range(n_rounds):
        if _cancel_requested(cancel):
            return _cancelled_result("Feed parsing", "cpu")
        measured = _cpu_round(per_round, cancel)
        if measured is None:
            return _cancelled_result("Feed parsing", "cpu")
        rate, wall = measured
        burn += wall
        if rate > 0:
            rates.append(rate)
    if not rates:
        return _empty_result("CPU stress", "cpu", "measurement loop did not run")
    return StressResult(
        name="Feed parsing",
        kind="cpu",
        success=True,
        duration_s=_round2(burn),
        units="nodes/s",
        value=_round2(statistics.median(rates)),
        value_min=_round2(min(rates)),
        value_max=_round2(max(rates)),
        samples=len(rates),
        write_mbps=0.0,
        read_mbps=0.0,
        error=None,
        coverage=_round2(min(1.0, burn / duration_s)),
    )
