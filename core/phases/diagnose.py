                                                                                     

                                                                             

                                                                             
                                                                           
                                                                          
                                                                          
                                                                            
                                                    

                                                                             
                                                                          
                                                                         

                               

                                                                        
                                                                        
                                                        
                                                                                  

                                                                     
                                                                       
                                                      
                                          
   
from collections import Counter
from pathlib import Path
from typing import List, Optional, Tuple

from ..config import Config
from ..net.diag import ALIVE_VERDICTS, diagnose, endpoint_of
from ..log import LOG
from ..models import Node
from ..state import PipelineState
from ..ui import ProgressBar
from ..utils import first_line




_NET_FAIL = "no_connectivity"



_Dropped = List[Tuple[Node, str]]


def _diag_workers(cfg: Config) -> int:
                                                                           

                                                                          
                                                                       
                                  
       
    return getattr(cfg.testing, "diagnose_workers", 0) or \
        cfg.testing.connectivity_workers


def _diag_bar() -> ProgressBar:
                            

                                                                       
                                                                           
                                                   

                                                                             
                                                                    
                                                                                 
                                                                       
                                

                                                                            
       
    return ProgressBar(0, "diag", log_progress=True, unit="endpoints",
                       show_ok=False)


def _net_fail_nodes(dropped: _Dropped) -> List[Node]:
                                                                                                          
    return [node for node, reason in dropped if reason == _NET_FAIL]


def _write_tls_ok_corpus(corpus_path: Path, nodes: List[Node]) -> int:
                                                                     

                                                                               
                                                                         
                                                                             
                                                       

                                                                            
                                                                            
                                                                           
                

                                                                    
                                        
       
    lines = sorted({n.raw for n in nodes if n.raw})
    if not lines:
        return 0
    try:
        corpus_path.parent.mkdir(parents=True, exist_ok=True)
        with open(corpus_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except OSError as e:
        LOG(f"[diag] tls-ok corpus NOT written to {corpus_path}: {e}")
        return 0
    LOG(f"[diag] tls-ok corpus ({len(lines)}) -> {corpus_path}")
    return len(lines)


def diagnosis_phase(state: PipelineState, cfg: Config, corpus_path: Path,
                    bar: Optional[ProgressBar] = None) -> None:
                                                                             

                                                                    
                                                                            
                                                                        

                                                                
                                                                       
                                                                          

                                                                          
                                                                        
                               
       
    timeout = getattr(cfg.testing, "diagnose_timeout", 0.0)
    if timeout <= 0:
        LOG("[diag] skipped (diagnose_timeout: 0)")
        return
    dropped: _Dropped = list(state.conn_drops.values())
    dead_guess = _net_fail_nodes(dropped)
    if not dead_guess:
        LOG("[diag] skipped (nothing to probe as no_connectivity: "
            + (", ".join(f"{r}={c}" for r, c in
                         Counter(r for _, r in dropped).most_common(3))
               or "no drops at all") + ")")
        return
    workers = _diag_workers(cfg)
    LOG(f"[diag] direct server probe of {len(dead_guess)} node(s) dropped as "
        f"{_NET_FAIL}: TCP connect + TLS ClientHello, timeout={timeout}s, "
        f"workers={workers}")
    try:
        report = diagnose(dead_guess, timeout, workers,
                          bar=bar if bar is not None else _diag_bar())
    except Exception as e:
        LOG(f"[diag] skipped: {first_line(e)}")
        return





    report["dropped"] = len(dead_guess)
    state.stats["connectivity_diagnosis"] = report
    counts = report["counts"]
    LOG(f"[diag] verdict: {report['nodes']} nodes, "
        f"{report['endpoints']} endpoints -> "
        + ", ".join(f"{k}={v}" for k, v in sorted(counts.items(),
                                                  key=lambda x: -x[1])))
    if report["alive"]:
        LOG(f"[diag] {report['alive']} server(s) alive but unusable "
            f"(protocol/credentials), {report['dead']} dead")


    alive_endpoints = {
        (row[0], row[1], row[2]) for row in report["verdicts"]
        if row[3] in ALIVE_VERDICTS
    }
    corpus = [n for n in dead_guess if endpoint_of(n) in alive_endpoints]
    _write_tls_ok_corpus(corpus_path, corpus)