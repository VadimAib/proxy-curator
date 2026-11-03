                                                                               

                                                                   
                                                                    
             

           
                                                                           
                                                                
                                                                               
                                                                 
                                        
                                                                             
                                                                              
                                                                           
                                   
                                                                           
                                                                    
                                                                          
   
import base64
import json
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from datetime import datetime

from .log import LOG
from .models import Node, Protocol
from .utils import first_line, write_text_atomic




CLIP_TIMEOUT = 5.0




CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def nodes_text(nodes: Iterable[Tuple[Node, float]]) -> str:
                                                                       

                                                               
                                                                         
                                                  
       
    return "\n".join(n.raw for n, _ in nodes)


def copy_to_clipboard(text: str) -> bool:
                                                           

                                                                      
                                                                      
                                                                       
                                                                

                                                                          
                                                                       
                                                        
       
    if not text:
        return False
    try:
        subprocess.run(
            ["clip"], input=text.encode("utf-8"),
            timeout=CLIP_TIMEOUT, check=True,
            creationflags=CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        LOG(f"[out] WARNING: clipboard copy timed out after {CLIP_TIMEOUT}s")
        return False
    except Exception as e:
        LOG(f"[out] WARNING: clipboard copy failed: {first_line(e)}")
        return False
    LOG(f"[out] clipboard: {len(text)} chars copied")
    return True


def export_nodes(nodes: List[Tuple[Node, float]], output_path: Path) -> None:
                                                                               

                                                                     
                                                          

                                                                       
                                                                         
                                                                     
                                                       
       
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plain = nodes_text(nodes)


    write_text_atomic(output_path, plain + ("\n" if plain else ""))
    if plain:
        b64_path = output_path.with_name(output_path.stem + "_b64.txt")
        write_text_atomic(b64_path,
                          base64.b64encode(plain.encode("utf-8")).decode())


def _speed_fields(n: Node, stats: Dict) -> Dict:
                                                                         

                                                                        
                                                                  
                                                                         
                                                                     

                                                                             
                                                                     
                                                                       
                                                                     
                                                                    
                                              

                                                                       
                                                            
                          
       
    extra: Dict = {}
    hit = (stats.get("speedtest") or {}).get(n.key())
    if isinstance(hit, dict) and "mbps" in hit:
        extra["speed_mbps"] = hit["mbps"]
    q = (stats.get("speedtest_quick") or {}).get(n.key())
    if isinstance(q, dict) and "mbps" in q:
        extra["speed_quick_mbps"] = q["mbps"]
    if n.key() in (stats.get("rescued") or []):
        extra["rescued"] = True



    code = (stats.get("geo") or {}).get(n.key())
    if code:
        extra["exit_country"] = code
    net = stats.get("run_network")
    if net:
        extra["net"] = str(net)
    if n.protocol == Protocol.MTPROTO:



        extra["secret_unverified"] = True
    extra.update(_tls_fields(n))
    return extra





_TLS_FIELDS = ("security", "sni", "alpn", "fp", "flow", "insecure")


def _tls_fields(n: Node) -> Dict:
                                                                               

                                                                              
                                                                        
                                                                          
                                                           

                                                                      
                                                    
       
    out: Dict = {}
    sec = getattr(n.security, "value", None)
    if sec and sec != "none":
        out["security"] = sec
    for key in _TLS_FIELDS[1:]:
        val = n.extra.get(key)
        if val in (None, "", []):
            continue
        out[key] = val
    return out


def export_working_nodes_json(nodes: List[Tuple[Node, float]], stats: Dict,
                               json_path: Path) -> None:
                                                                         

                                                              
                                                                   
                                                                        
                                                                  

                                                                
                                                                          
                                                                          
                                                                        
                                                                         
                                            
       
    items = []
    for n, ms in nodes:
        entry = {
            "protocol": n.protocol.value,
            "host": n.host,
            "port": n.port,
            "name": n.name,
            "ck": n.ck(),
            "ms": round(ms, 2),
        }
        entry.update(_speed_fields(n, stats))
        items.append(entry)


    write_text_atomic(json_path,
                      json.dumps(items, ensure_ascii=False,
                                 separators=(",", ":")))


def export_summary(nodes: List[Tuple[Node, float]], stats: Dict,
                   summary_path: Path, duration: float) -> None:
    working_list = []
    for n, ms in nodes:
        entry = {
            "protocol": n.protocol.value,
            "name": n.name,
            "host": n.host,
            "port": n.port,



            "ck": n.ck(),
            "ms": round(ms, 2),
        }
        entry.update(_speed_fields(n, stats))
        working_list.append(entry)

    stats.update({
        "finished": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "duration_sec": round(duration, 1),
        "working": working_list,
    })
    write_text_atomic(summary_path,
                      json.dumps(stats, ensure_ascii=False,
                                 separators=(",", ":")))