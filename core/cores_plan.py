                                                                       

                                                                          
                                                                       
                                  
   
from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional

from .config import Config
from .cores_cache import (_entry_fresh, _entry_size, describe_entry,
                          load_cache, save_cache)
from .cores_fetch import latest_release
from .cores_specs import CORE_SPECS, CorePlan, CoreSpec
from .cores_version import is_newer, probe_version
from .log import LOG
from .paths import rp
from .utils import first_line



def build_plan(spec: CoreSpec, binary: Path, current: str, label: str,
               entry: Dict[str, object], *, force: bool = False
               ) -> Optional[CorePlan]:
                                                                       

                                                                    
                                                                            
                                                                          
                                                                      

                                                                        
                                                                        
       
    version = str(entry.get("version") or "")
    if not version:
        return None
    if not force and not is_newer(version, current):
        return None
    return CorePlan(name=spec.name, binary=binary, label=label,
                    tag=str(entry.get("tag") or ""), version=version,
                    asset=str(entry.get("asset") or ""),
                    url=str(entry.get("url") or ""),
                    digest_url=str(entry.get("digest_url") or ""),
                    size=_entry_size(entry))


def plan_cores(cfg: Config, *, force: bool = False,
               now: Optional[float] = None) -> List[CorePlan]:
                                                           

                                                                            
                                                               
       
    now = time.time() if now is None else now
    cache = load_cache()
    plans: List[CorePlan] = []
    for spec in CORE_SPECS:
        section = getattr(cfg, spec.name, None)
        raw_path = str(getattr(section, "path", "") or "")
        if not raw_path:
            LOG(f"[cores] {spec.name}: path not set in config.yaml — skipped")
            continue
        if not bool(getattr(section, "enabled", True)):
            LOG(f"[cores] {spec.name}: enabled=false — leaving as is")
            continue
        binary = rp(raw_path)
        exists = binary.exists()
        current = probe_version(binary, spec) if exists else ""
        label = current or ("not responding" if exists else "no binary")
        if exists and not current:
            LOG(f"[cores] WARNING: {spec.name}: {binary.name} did not report a "
                f"version — will be reinstalled")
        entry = cache.get(spec.name)
        if force or not _entry_fresh(entry, now):
            try:
                tag, sizes = latest_release(spec.repo)
                entry = describe_entry(spec, tag, sizes, now)
            except Exception as e:



                LOG(f"[cores] WARNING: {spec.name}: GitHub did not respond "
                    f"({first_line(e)})")
                if not _entry_fresh(entry, now):
                    entry = None
            if entry is not None:
                cache[spec.name] = entry
        if not isinstance(entry, dict):
            continue
        plan = build_plan(spec, binary, current, label, entry, force=force)
        if plan is not None:
            plans.append(plan)



    save_cache(cache)
    return plans


def core_state(cfg: Config) -> List[dict]:
                                                   

                                                                            
                                                                    
       
    now = time.time()
    cache = load_cache()
    states: List[dict] = []
    for spec in CORE_SPECS:
        section = getattr(cfg, spec.name, None)
        raw_path = str(getattr(section, "path", "") or "")
        enabled = bool(getattr(section, "enabled", True))
        binary = rp(raw_path) if raw_path else None
        exists = binary is not None and binary.exists()
        current = probe_version(binary, spec) if exists else ""
        entry = cache.get(spec.name)
        latest = str(entry.get("version") or "") if isinstance(entry, dict) else ""
        size = _entry_size(entry) if isinstance(entry, dict) else 0
        if not raw_path:
            status = "not configured"
        elif not exists:
            status = "missing"
        elif not current:
            status = "not responding"
        elif latest and is_newer(latest, current):
            status = "outdated"
        elif latest:
            status = "up-to-date"
        else:
            status = "unknown"
        states.append({
            "name": spec.name,
            "binary": str(binary) if binary else "",
            "enabled": enabled,
            "current": current,
            "latest": latest,
            "status": status,
            "size": size,
        })
    return states


def check_cores(cfg: Config, *, force: bool = False) -> List[CorePlan]:
                                                              

                                                                        
                                                                       
                                                                  
       
    return plan_cores(cfg, force=force)
