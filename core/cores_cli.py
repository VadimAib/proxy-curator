                                                                          

                                                                        
                                                                           
                                                                 
   
from __future__ import annotations

import sys
from typing import Callable, Optional

from .config import Config
from .cores_apply import _apply
from .cores_plan import plan_cores
from .cores_specs import CorePlan
from .log import LOG



def interactive() -> bool:
                                                          

                                                                           
                                                                         
                                                                          
                                 
       
    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except (AttributeError, ValueError):
        return False


def _fmt_size(size: int) -> str:
    return f"{size / 1048576:.1f} MB" if size else "size unknown"


def confirm_update(plan: CorePlan, ask: Callable[[str], str]) -> bool:
                                                                       

                                                                               
                                                                             
                     
       
    answer = ask(f"  Update {plan.name} {plan.label} → {plan.version}? [Y/n] ")
    if answer.strip().lower() in ("", "y", "yes"):
        return True
    LOG(f"[cores] {plan.name}: kept {plan.label} "
        f"(answer: {answer.strip() or 'empty'})")
    return False


def _confirm_or_skip(plan: CorePlan,
                     ask: Callable[[str], str]) -> Optional[bool]:
                                                                       

                                                                         
                                                                            
                                                                           
       
    if not interactive():
        return None
    try:
        return confirm_update(plan, ask)
    except EOFError:
        return None


def update_cores(cfg: Config, *, assume_yes: bool = False,
                 check_only: bool = False, force: bool = False,
                 ask: Optional[Callable[[str], str]] = None) -> int:
                                                                                    

                                                                            
                                                                             
                                                  
       
    plans = plan_cores(cfg, force=force)
    if not plans:
        LOG("[cores] no updates")
        return 0
    prompt = ask if ask is not None else input
    failures = 0
    for plan in plans:
        LOG(f"[cores] {plan.name}: {plan.label} → {plan.version} "
            f"({_fmt_size(plan.size)}, {plan.tag})")
        if check_only:
            continue
        if not assume_yes:
            agreed = _confirm_or_skip(plan, prompt)
            if agreed is None:
                LOG(f"[cores] {plan.name}: no interactive console — "
                    f"kept {plan.label}")
                continue
            if not agreed:
                continue
        ok, message = _apply(plan)
        if ok:
            LOG(f"[cores] {plan.name}: updated to {plan.version} ({message})")
        else:
            failures += 1
            LOG(f"[cores] {plan.name}: NOT updated — {message}")
    return 1 if failures else 0
