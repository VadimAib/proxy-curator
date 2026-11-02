                                                                                                                               
from __future__ import annotations

import json
import time
from pathlib import Path
from core import stress_tests as st
from core import stress_advice
from core import tune_plan
from core.config import Config
from core.log import LOG
from core.net.netlabel import network_fingerprint
from core.paths import rp
from server_config import CONFIG_PATH, _read_summary
from server_stress import _disk_free_mb, _measure_channel



def _current_values(cfg) -> dict:
                                                                                                                 
    return {
        "speedtest.light_bytes": cfg.speedtest.light_bytes,
        "speedtest.light_timeout": cfg.speedtest.light_timeout,
        "speedtest.full_bytes": cfg.speedtest.full_bytes,
        "speedtest.full_timeout": cfg.speedtest.full_timeout,
        "speedtest.quick_bytes": cfg.speedtest.quick_bytes,
        "speedtest.quick_timeout": cfg.speedtest.quick_timeout,
        "speedtest.workers": cfg.speedtest.workers,
        "speedtest.full_max_measure": cfg.speedtest.full_max_measure,
        "fetching.workers": cfg.fetching.workers,
        "fetching.timeout": cfg.fetching.timeout,
    }


def _selfcheck_path() -> Path:
                                                    

                                                                             
                                                                             
                                                                              
                              
       
    cfg = Config.load(CONFIG_PATH)
    return rp(cfg.output.summary).parent / "selfcheck.json"


def _read_selfcheck() -> dict:
                                                                                                                          
    try:
        data = json.loads(_selfcheck_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_selfcheck(data: dict) -> None:
                                                                                                                                   
    path = _selfcheck_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    except OSError as exc:
        LOG(f"[tune] selfcheck marker not written: {exc}")


def _mark_selfcheck(result: dict) -> dict:
                                                                

                                                                           
                                                                         
                                                      

                                                                        
                             
       
    from core.net.netlabel import network_fingerprint
    m = result.get("measurements") or {}
    payload = {
        "measured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mbps": m.get("mbps"),
        "rtt_ms": m.get("rtt_ms"),
        "jitter_ms": m.get("jitter_ms"),
        "profile": m.get("profile"),
        "proposals": len(result.get("proposals") or []),
        "network": network_fingerprint(),
    }
    _write_selfcheck(payload)
    return payload


def _selfcheck_state() -> dict:
                                                   

                                                                          
                                                                       
                                                  
       
    data = _read_selfcheck()
    if not data:
        return {"ok": True, "measured": False}
    try:
        from core.net.netlabel import network_fingerprint
        current = network_fingerprint()
    except Exception:
        current = ""
    stored = str(data.get("network") or "")
    changed = bool(stored and current and stored != current)
    data["network_changed"] = changed
    data["measured"] = True
    return {"ok": True, **data}


def _clear_selfcheck_proposals() -> None:
                                                                                                                                           
    data = _read_selfcheck()
    if not data or not data.get("proposals"):
        return
    data["proposals"] = 0
    _write_selfcheck(data)


def _merge_proposals(*groups) -> list[dict]:
                                                                                                                                 
    merged: list[dict] = []
    seen: set[str] = set()
    for group in groups:
        for proposal in group:
            path = proposal.get("path")
            if not path or path in seen:
                continue
            seen.add(path)
            merged.append(proposal)
    return merged


def _run_notes_and_proposals() -> dict:
                                                                   

                                                                      
                                                                 
                                                                        
                                                                       
                                                                        
                      
       
    from core import tune_plan
    current = _current_values(Config.load(CONFIG_PATH))
    proposals, notes = tune_plan.plan_from_run(run=_read_summary(),
                                                current=current)
    return {"notes": notes, "proposals": proposals, "current": current}


def _check_everything(payload: dict | None = None,
                      cancel: st.CancelCheck = None) -> dict:
                                                                           

                                                                        
                                                                              
                                                                             
                                                                      

                                                                           
                                                                           
                           
       
    from core import tune_plan
    params = payload or {}
    cfg = Config.load(CONFIG_PATH)
    current = _current_values(cfg)
    cache_dir = rp(cfg.output.cache_dir)
    run = _read_summary()
    reference_nodes = run.get("links_total") if run else None
    if not isinstance(reference_nodes, int) or reference_nodes <= 0:
        reference_nodes = None
    free_mb = _disk_free_mb()

    channel = _measure_channel(params.get("network"), cancel=cancel)
    if cancel is not None and cancel():
        return {"cancelled": True}
    cpu = st.run_cpu_stress(cancel=cancel, **params.get("cpu", {}))
    if cancel is not None and cancel():
        return {"cancelled": True}
    disk = st.run_disk_stress(dir=str(cache_dir), cancel=cancel,
                              **params.get("disk", {}))
    if cancel is not None and cancel():
        return {"cancelled": True}

    results = {
        "cpu": {**cpu._asdict(),
                "verdict": stress_advice.verdict_for(
                    "cpu", cpu, reference_nodes=reference_nodes)},
        "network": {**channel["network"]._asdict(),
                    "verdict": stress_advice.verdict_for(
                        "network", channel["network"])},
        "disk": {**disk._asdict(),
                 "verdict": stress_advice.verdict_for(
                     "disk", disk, free_mb=free_mb)},
    }
    live = tune_plan.plan_internet_tune(
        mbps=channel["mbps"], rtt_ms=channel["rtt_ms"],
        jitter_ms=channel["jitter_ms"], current=current)
    run_proposals, notes = tune_plan.plan_from_run(run=run, current=current)
    return {
        "results": results,
        "measurements": {
            "mbps": channel["mbps"],
            "rtt_ms": channel["rtt_ms"],
            "jitter_ms": channel["jitter_ms"],
            "profile": tune_plan.recommend_profile(
                channel["mbps"], channel["rtt_ms"], channel["jitter_ms"]),
            "reference_nodes": reference_nodes,
            "disk_free_mb": round(free_mb) if free_mb is not None else None,
        },
        "current": current,
        "proposals": _merge_proposals(live, run_proposals),
        "notes": notes,
    }
