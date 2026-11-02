                                                             

                                                   
                                                                        
                                                                                                 
                                                 
   
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from ..config import Config
from .harness import CREATE_NO_WINDOW
from ..log import LOG
from .ports import PortPool
from .singbox import SingBoxEngine
from .xray import XrayEngine


def get_kernel_version(binary: Path, args: Tuple[str, ...] = ("version",)) -> str:
                                                                                                                
    try:
        out = subprocess.run(
            [str(binary), *args], capture_output=True, text=True,
            timeout=10, creationflags=CREATE_NO_WINDOW
        )
        lines = (out.stdout or out.stderr or "").strip().splitlines()
        return lines[0] if lines else "unknown"
    except Exception as e:
        return f"version error: {e}"


def _probe_report(name: str, want_ok: bool, ms: Optional[float],
                  err: str) -> Tuple[str, bool]:
                                                           

                                                                     
                                                                           
                                                                          
                                                                
       
    if want_ok:
        good = ms is not None
        detail = f"OK {ms:.0f}ms" if good else f"FAIL ({err})"
    else:
        good = ms is None
        detail = "BLOCKED (expected)" if good else f"CONNECTED {ms:.0f}ms"
    mark = "" if good else "  <-- UNEXPECTED"
    return f"[selftest]   {name:<18}: {detail}{mark}", good


def run_selftest(xray: Path, port_pool: PortPool, cfg: Config,
                 singbox: Optional[Path] = None) -> bool:
                                                                          
    engine = XrayEngine.from_config(port_pool, cfg.xray)
    tests = [
        ("freedom(direct)", "freedom", True),
        ("blackhole(block)", "blackhole", False)
    ]
    ok = True
    for name, proto, want_ok in tests:
        port = port_pool.get_port()
        probe_cfg = {
            "log": {"loglevel": "none"},
            "inbounds": [{
                "listen": "127.0.0.1", "port": port,
                "protocol": "http", "settings": {"timeout": 10}
            }],
            "outbounds": [{"protocol": proto}],
        }
        ms, err, _ = engine.run_test(
            probe_cfg, str(xray), port, cfg.testing.timeout,
            cfg.connectivity_urls, [], [],
            critical_timeout=cfg.testing.critical_timeout
        )
        line, good = _probe_report(name, want_ok, ms, err)
        ok = ok and good
        LOG(line)
    ok = _selftest_singbox(singbox, port_pool, cfg) and ok
    LOG(f"[selftest] {'PASS' if ok else 'FAIL'}")
    return ok


def _selftest_singbox(singbox: Optional[Path], port_pool: PortPool,
                      cfg: Config) -> bool:
                                                                                          
    if singbox is None or not singbox.exists():
        LOG(f"[selftest]   {'singbox(direct)':<18}: SKIPPED "
            f"(no singbox.path in config.yaml)")
        return True
    if not bool(getattr(getattr(cfg, "singbox", None), "enabled", True)):
        LOG(f"[selftest]   {'singbox(direct)':<18}: SKIPPED "
            f"(singbox.enabled=false)")
        return True
    engine = SingBoxEngine.from_config(port_pool, cfg.singbox)
    port = port_pool.get_port()
    probe_cfg = {
        "log": {"level": "error"},
        "inbounds": [{
            "type": "http", "tag": "http-in",
            "listen": "127.0.0.1", "listen_port": port,
        }],
        "outbounds": [{"type": "direct", "tag": "direct"}],
    }
    ms, err, _ = engine.run_test(
        probe_cfg, str(singbox), port, cfg.testing.timeout,
        cfg.connectivity_urls, [], [],
        critical_timeout=cfg.testing.critical_timeout)
    line, good = _probe_report("singbox(direct)", True, ms, err)
    LOG(line)
    return good

