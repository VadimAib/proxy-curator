                                                                                  

                                                                              
                                                                             
                                                                     
   
from collections import Counter
from pathlib import Path
import shutil
from datetime import datetime
from typing import Any, Dict, List, Tuple
import time

from .config import Config
from .exporters import (copy_to_clipboard, export_nodes, export_summary,
                        export_working_nodes_json, nodes_text)
from .log import LOG
from .models import Node
from .pipeline_funnel import _log_funnel
from .resume import clear_state
from .state import PipelineState




def resolve_output_paths(out_path: Path, summary_path: Path,
                         tcping_only: bool = False,
                         ping_only: bool = False) -> Tuple[Path, Path]:
                                                           

                                                                           
                                                                     
                                                                           
                                                                          
                                                                       
                                                                           
                                                                       
                                                          
                          

                                                                           
                                                                        
                                 
       
    if ping_only:
        return (out_path.with_name(out_path.stem + ".ping.txt"),
                summary_path.with_name("summary.ping.json"))
    if not tcping_only:
        return out_path, summary_path
    return (out_path.with_name(out_path.stem + ".tcping.txt"),
            summary_path.with_name("summary.tcping.json"))


def _apply_output_limits(nodes: List[Tuple[Node, float]],
                         output_cfg) -> List[Tuple[Node, float]]:
    max_per_ep = getattr(output_cfg, 'max_nodes_per_endpoint', 0)
    if max_per_ep > 0:
        ep_counts = Counter()
        limited = []
        for n, ms in nodes:
            ep = (n.host.lower(), n.port)
            if ep_counts[ep] < max_per_ep:
                limited.append((n, ms))
                ep_counts[ep] += 1
        nodes = limited

    max_nodes = getattr(output_cfg, 'max_nodes', 0)
    if max_nodes > 0 and len(nodes) > max_nodes:
        LOG(f"[out] truncated to max_nodes={max_nodes}")
        nodes = nodes[:max_nodes]

    return nodes


def _rank_final(final: List[Tuple[Node, float]],
                output_cfg) -> List[Tuple[Node, float]]:
                                                                           

                                                                                 
                                                                              
                                                                        
                                                                              
                                                                          
                                                      
                                                                           

                                                                          
                                                                    
                                             
       
    return _apply_output_limits(sorted(final, key=lambda x: x[1]), output_cfg)


def _stop_after_ping(state: PipelineState) -> List[Tuple[Node, float]]:
                                                                          

                                                                          
                                                                        
                                                                                
                                                                     
                                                       

                                                                          
                                                                            
       
    state.final = list(state.alive)
    state.stats.update({"delay_tested": 0, "delay_ok": 0,
                        "delay_fail_reasons": {}, "mode": "ping_only"})
    LOG(f"[ping-only] {len(state.final)} TCP-alive node(s) as-is, "
        f"http_test not run (delay_ok: 0)")
    return state.final




def _archive_old_output_files(out_dir: Path, log_dir: Path) -> None:
                                                                              

                                                            
                                                                    
                                                                     
                                                                  
                                                                       
                                                  

                                                                      
                                                                  
                                                                   
                                                                  
                           

                                                                     
                                                            
       
    service_artifacts = (
        "working_nodes.ping.txt", "working_nodes.ping.json",
        "summary.ping.json",
        "working_nodes.tcping.txt", "working_nodes.tcping.json",
        "working_nodes.ping_b64.txt", "working_nodes.tcping_b64.txt",
        "summary.tcping.json",
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    for name in service_artifacts:
        src = out_dir / name
        if not src.exists():
            continue
        dst = log_dir / name
        if dst.exists():


            dst = log_dir / (f"{src.stem}_{datetime.now():%Y%m%d_%H%M%S}"
                             f"{src.suffix}")
        shutil.move(str(src), str(dst))
        LOG(f"[out] archived to logs/: {src.name} -> {dst.name}")


def _export_phase(final: List[Tuple[Node, float]], stats: Dict[str, Any],
                  cfg: Config, nodes_out: Path, summary_out: Path,
                  tcping_only: bool, ping_only: bool = False) -> None:
                                                                               

                                                                       
                                                             
                                                                         
                                                                            
                                

                                                              
                                                                   
           
       
    LOG("")





    _archive_old_output_files(nodes_out.parent,
                              nodes_out.parent.parent / "logs")
    LOG("=== PHASE 11/11: EXPORT ===")
    if tcping_only:
        LOG("[out] --tcping-only: verified list left intact "
            f"(-> {nodes_out.name})")
    export_nodes(final, nodes_out)
    LOG(f"[out] {len(final)} nodes -> {nodes_out}")


    if cfg.output.clip_to_clipboard and final:
        copy_to_clipboard(nodes_text(final))
    json_path = nodes_out.with_name(nodes_out.stem + ".json")
    export_working_nodes_json(final, stats, json_path)
    LOG(f"[out] {len(final)} nodes -> {json_path}")
    rescued_keys = set(stats.get("rescued") or [])
    for n, ms in final[:5]:
        speed = stats.get("speedtest", {}).get(n.key(), {}).get("mbps")
        suffix = f" {speed:>6.1f}Mbps" if speed is not None else ""
        mark = " [rescued]" if n.key() in rescued_keys else ""
        LOG(f"   {ms:>6.1f}ms  {n.protocol.value:<6} {n.name[:48]}{suffix}{mark}")


def _exit_no_nodes(nodes_out: Path, summary_out: Path,
                   stats: Dict[str, Any], t_start: float) -> None:
                                                                         

                                                                       
                                                                        
                                                                      

                                                                         
                                                                       
                                                         
       
    age = ""
    if nodes_out.exists():


        age = f" (age {(time.time() - nodes_out.stat().st_mtime)/86400:.1f}d)"
    LOG(f"[out] 0 working nodes - previous list kept{age}: {nodes_out}")
    duration = time.time() - t_start
    _log_funnel(stats, 0)
    export_summary([], stats, summary_out, duration)
    LOG(f"[out] summary -> {summary_out}")
    LOG(f"[done] duration {duration:.1f}s")
    clear_state()
