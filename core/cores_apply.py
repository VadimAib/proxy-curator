                                                                     

                                                                       
                                                                          
                                  
   
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from .cores_fetch import (API_TIMEOUT, _download, _extract_binary, _fetch,
                          _sha256, digest_from_dgst)
from .cores_specs import CorePlan, CoreSpec, spec_for
from .cores_version import probe_version
from .log import LOG
from .paths import rp
from .utils import first_line

TEMP_DIR = "temp"



def install_binary(staged: Path, target: Path) -> Optional[Path]:
                                                                     

                                                                                
                                                                             
                                                                       
                                                                      

                                                                     
       
    target.parent.mkdir(parents=True, exist_ok=True)
    backup: Optional[Path] = None
    if target.exists():
        backup = target.with_name(target.name + ".bak")
        shutil.copy2(target, backup)
    os.replace(staged, target)
    return backup


def rollback(target: Path, backup: Optional[Path]) -> bool:
                                                                                                  
    if not backup or not backup.exists():
        return False
    os.replace(backup, target)
    return True


def apply_plan(plan: CorePlan, spec: CoreSpec, temp_dir: Path,
               *, progress: Optional[Callable[[int, int], None]] = None,
               cancel: Optional[Callable[[], bool]] = None
               ) -> Tuple[bool, str]:
                                                                

                                                                                 
                                                                            
                                                                               
                                                                        

                                                                           
                                                         
       
    work = temp_dir / f"core_update_{plan.name}"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    try:
        _download(plan.url, work / plan.asset, plan.size, plan.name,
                  progress=progress, cancel=cancel)
        if plan.digest_url:
            want = digest_from_dgst(
                _fetch(plan.digest_url, API_TIMEOUT).decode("utf-8", "replace"))
            got = _sha256(work / plan.asset)
            if got != want:
                raise ValueError(f"archive sha256 mismatch: {got} expected {want}")
            note = "sha256 verified against .dgst"
        else:
            note = "core publishes no checksums — verified by launch and version"
        staged = _extract_binary(work / plan.asset, spec, work)
        got_version = probe_version(staged, spec)
        if got_version != plan.version:
            raise ValueError(f"downloaded binary reports version "
                             f"{got_version or '?'}, expected {plan.version}")
        backup = install_binary(staged, plan.binary)
        after = probe_version(plan.binary, spec)
        if after != plan.version:
            if rollback(plan.binary, backup):
                LOG(f"[cores] {plan.name}: rolled back to previous binary")
            raise ValueError(f"in place version {after or '?'} instead of "
                             f"{plan.version}"
                             + ("" if backup else ", nothing to roll back to"))
        return True, (f"{note}; previous binary: "
                      f"{backup.name if backup else 'none'}")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _apply(plan: CorePlan) -> Tuple[bool, str]:
                                                                                                                      
    try:
        return apply_plan(plan, spec_for(plan.name), rp(TEMP_DIR))
    except Exception as e:
        return False, first_line(e)




def _apply_plan_guarded(plan: CorePlan,
                        *, progress: Optional[Callable[[int, int], None]] = None,
                        cancel: Optional[Callable[[], bool]] = None
                        ) -> Tuple[bool, str]:
                                                                  

                                                                        
                                            
       
    try:
        return apply_plan(plan, spec_for(plan.name), rp(TEMP_DIR),
                          progress=progress, cancel=cancel)
    except Exception as e:
        return False, first_line(e)


def apply_plans(plans: List[CorePlan],
                *, progress: Optional[Callable[[int, int], None]] = None,
                cancel: Optional[Callable[[], bool]] = None
                ) -> List[dict]:
                                                                         

                                                                           
                                                                      
                                                                    

                                                                           
                                               
       
    results: List[dict] = []
    for plan in plans:
        if cancel is not None and cancel():
            results.append({
                "name": plan.name,
                "ok": False,
                "message": "cancelled by user",
                "version": plan.version,
            })
            continue
        ok, message = _apply_plan_guarded(plan, progress=progress, cancel=cancel)
        results.append({
            "name": plan.name,
            "ok": ok,
            "message": message,
            "version": plan.version,
        })
        if ok:
            LOG(f"[cores] {plan.name}: updated to {plan.version} ({message})")
        else:
            LOG(f"[cores] {plan.name}: NOT updated — {message}")
    return results
