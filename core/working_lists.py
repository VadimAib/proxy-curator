                                                                       

                                                                       
                                                                            
                                                                        

       

                                                                         
                                                                            
                                                                     
                                                                
                                                               
   
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Tuple

from .merge import merge_working_lists
from .paths import ROOT


BACKUP_PAIRS: Tuple[Tuple[str, str], ...] = (
    ("working_nodes.txt", "working_nodes.prev.txt"),
    ("working_nodes_b64.txt", "working_nodes_b64.prev.txt"),
    ("working_nodes.json", "working_nodes.prev.json"),
    ("summary.json", "summary.prev.json"),
)

MODES = ("replace", "append", "keep", "none")



Status = str


def resolve_mode(raw: str) -> str:
                                                                                                         
    mode = (raw or "").strip().lower()
    if mode in ("a", "append"):
        return "append"
    if mode in ("k", "keep"):
        return "keep"
    if mode in ("n", "none", "selftest"):
        return "none"
    return "replace"


def _output_dir(outdir: Optional[Path]) -> Path:
    return outdir if outdir is not None else (ROOT / "output")


def backup_previous(outdir: Optional[Path] = None) -> int:
                                                                                 

                                                                             
                                                                            
                                                     
       
    d = _output_dir(outdir)
    copied = 0
    for name, prev_name in BACKUP_PAIRS:
        src = d / name
        if not src.exists():
            continue
        try:
            (d / prev_name).write_bytes(src.read_bytes())
            copied += 1
        except OSError:
            pass
    return copied


def clear_backups(outdir: Optional[Path] = None) -> None:
                                                                                

                                                                
                                                                               
                                                                        
                                              
       
    d = _output_dir(outdir)
    for _, prev_name in BACKUP_PAIRS:
        try:
            (d / prev_name).unlink(missing_ok=True)
        except OSError:
            pass


def restore_previous(outdir: Optional[Path] = None) -> bool:
                                                                                                                                
    d = _output_dir(outdir)
    if not (d / "working_nodes.prev.txt").exists():
        return False
    for name, prev_name in BACKUP_PAIRS:
        prev = d / prev_name
        if not prev.exists():
            continue
        try:
            (d / name).write_bytes(prev.read_bytes())
        except OSError:
            pass
    clear_backups(d)
    return True


def apply_mode(
    mode: str,
    outdir: Optional[Path] = None,
    merge: Optional[Callable[[], int]] = None,
) -> Tuple[str, Status]:
                                                                                 

                                                                            
                                                                             
                                                              
       
    canonical = resolve_mode(mode)
    d = _output_dir(outdir)

    if canonical == "none":
        return ("mode=selftest: service run, outputs untouched", "ok")

    if canonical == "keep":
        if restore_previous(d):
            return ("mode=keep: previous list restored", "restored")
        return ("mode=keep: no previous list, fresh list kept", "ok")

    if canonical == "append":
        if not (d / "working_nodes.prev.txt").exists():
            return ("mode=append: no previous list, fresh list kept", "ok")
        runner = merge or merge_working_lists
        try:
            rc = runner()
        except Exception as e:
            return (f"mode=append: merge failed ({e}), fresh list kept", "failed")
        if rc != 0:
            return (f"mode=append: merge rc={rc}, fresh list kept", "failed")
        clear_backups(d)
        return ("mode=append: fresh + previous merged", "ok")

    clear_backups(d)
    return ("mode=replace: fresh list kept", "ok")
