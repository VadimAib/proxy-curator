                                                                             

                                                                            
                                                                         
                                                                            
   
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .archive import MERGE_REFRESH_FILES, archive_run_artifacts
from .config import Config, OutputConfig
from .exporters import (copy_to_clipboard, export_nodes, export_summary,
                            export_working_nodes_json, nodes_text)
from .log import LOG
from .models import Node
from .output_quality import apply_quality_gate
from .parsers import parse_node
from .paths import ROOT, rp


def _load_node_list(path: Path) -> List[Node]:
                                                                                                                                         
    if not path.exists():
        return []
    nodes = []
    for line in path.read_text("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        n = parse_node(line)
        if n:
            nodes.append(n)
    return nodes


def _load_ms_map(json_path: Path) -> Dict[Tuple[str, str, int, str, str], float]:
                                                                                  

                                                                        
                                                           
                                                                       
                                                                
                                                                      
                                                                         
                                                         

                                  
                                                                     
                                                                         
                                                             
                                                                     
                                                                          
                                                                  
                                                             
       
    if not json_path.exists():
        return {}
    try:
        items = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        LOG(f"[merge] WARNING: {json_path} unreadable ({e}), ms=0 for fresh")
        return {}
    if not isinstance(items, list):
        return {}
    out: Dict[Tuple[str, str, int, str, str], float] = {}
    ambiguous: Set[Tuple[str, str, int, str, str]] = set()
    for it in items:
        if not isinstance(it, dict):
            continue
        key: Optional[Tuple[str, str, int, str, str]] = None
        n = parse_node(it["raw"]) if it.get("raw") else None
        if n:
            key = (n.protocol.value, n.host, n.port, n.name, n.ck())
        else:
            proto, host, port, name = (it.get("protocol"), it.get("host"),
                                        it.get("port"), it.get("name"))
            if not proto or not host or not port:
                continue
            try:
                port = int(port)
            except (TypeError, ValueError):
                continue
            key = (str(proto), str(host), port, str(name or ""),
                   str(it.get("ck") or ""))
        if key is None:
            continue
        try:
            ms = float(it.get("ms") or 0.0)
        except (TypeError, ValueError):
            ms = 0.0
        if key in out and out[key] != ms:
            if not key[4]:

                ambiguous.add(key)

            continue
        out[key] = ms
    for bad_key in ambiguous:
        out.pop(bad_key, None)
    return out


def _load_json(path: Path) -> Optional[Dict]:
                                                                                                                       
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        LOG(f"[merge] WARNING: {path.name} unreadable ({e}), ignored")
        return None
    return data if isinstance(data, dict) else None


def _load_summary_ms(summary_path: Path) -> Dict[Tuple[str, str, int, str, str], float]:
                                                                                        

                                                                       
                                                                   
                                                       
                                                                
                                       
                                                               

                                                                         
                                                                    
                                                                       
               
       
    data = _load_json(summary_path)
    working = (data or {}).get("working")
    if not isinstance(working, list):
        return {}
    out: Dict[Tuple[str, str, int, str, str], float] = {}
    ambiguous: Set[Tuple[str, str, int, str, str]] = set()
    for it in working:
        if not isinstance(it, dict):
            continue
        host = it.get("host")




        proto = it.get("protocol") or it.get("proto")
        if not host or not proto:
            continue
        try:
            port = int(it.get("port") or 0)
            ms = float(it.get("ms") or 0.0)
        except (TypeError, ValueError):
            continue
        stamp = (str(proto), str(host), port, str(it.get("name") or ""),
                 str(it.get("ck") or ""))
        if stamp in out and out[stamp] != ms:
            if not stamp[4]:

                ambiguous.add(stamp)

            continue
        out[stamp] = ms
    for bad_stamp in ambiguous:
        out.pop(bad_stamp, None)
    return out


def _merge_stats(prev_stats: Dict, fresh_stats: Dict) -> Dict:
                                                          

                                                                
                                                                     
                                                                        
                                                                            
                                        

                                                                                   
                                                                          
                                               
       
    merged = dict(fresh_stats)
    for field in ("speedtest", "speedtest_quick"):
        prev_val = prev_stats.get(field)
        if isinstance(prev_val, dict):
            merged[field] = {**prev_val, **(fresh_stats.get(field) or {})}
    prev_rescued = prev_stats.get("rescued")
    if isinstance(prev_rescued, list):
        seen = set(fresh_stats.get("rescued") or [])
        merged["rescued"] = list(prev_rescued) + [k for k in seen]
    return merged


def merge_working_lists(config_path: Optional[Path] = None) -> int:
                                                                                 

                                                                             
                                                                               
                                                                               
                                                                       
                                                                                
                                                                              
                                                       
       
    cfg_file = config_path or (ROOT / "config.yaml")
    if not cfg_file.exists():
        LOG(f"ERROR: {cfg_file} not found")
        return 1
    cfg = Config.load(cfg_file)
    out_path = rp(cfg.output.working_nodes)
    prev_path = out_path.parent / (out_path.stem + ".prev.txt")
    json_path = out_path.with_name(out_path.stem + ".json")
    summary_path = rp(cfg.output.summary)

    fresh = _load_node_list(out_path)
    prev = _load_node_list(prev_path)

    seen = set()
    merged: List[Node] = []
    for n in fresh + prev:
        k = n.key()
        if k not in seen:
            seen.add(k)
            merged.append(n)







    stats: Optional[Dict] = None
    if summary_path.exists():
        stats = _load_json(summary_path)
    else:
        LOG(f"[merge] WARNING: {summary_path} not found, skipping summary update")

    net = ""
    pairs: List[Tuple[Node, float]] = [(n, 0.0) for n in merged]
    if stats is not None:
        try:


            net = str(stats.get("run_network") or "")
            prev_stats = _load_json(summary_path.with_name("summary.prev.json"))
            if prev_stats:
                stats = _merge_stats(prev_stats, stats)











            prev_ms_map = _load_ms_map(
                json_path.with_name("working_nodes.prev.json"))
            fresh_ms_map = _load_ms_map(json_path)
            prev_stamp_ms = _load_summary_ms(
                summary_path.with_name("summary.prev.json"))
            fresh_stamp_ms = _load_summary_ms(summary_path)

            def _ms_of(n: Node) -> float:
                key = (n.protocol.value, n.host, n.port, n.name, n.ck())
                legacy_key = (n.protocol.value, n.host, n.port, n.name, "")
                for m in (fresh_ms_map, prev_ms_map,
                          fresh_stamp_ms, prev_stamp_ms):
                    v = m.get(key) or m.get(legacy_key)
                    if v:
                        return v
                return 0.0

            pairs = [(n, _ms_of(n)) for n in merged]




            pairs = apply_quality_gate(pairs, stats, cfg.output)
        except Exception as e:
            LOG(f"[merge] WARNING: latency/quality gate failed ({e}); "
                f"falling back to ms=0 for all nodes")
            pairs = [(n, 0.0) for n in merged]

    export_nodes(pairs, out_path)
    LOG(f"[merge] {len(fresh)} fresh + {len(prev)} prev = "
        f"{len(merged)} unique -> {len(pairs)} after quality gate -> {out_path}")


    if cfg.output.clip_to_clipboard and pairs:
        copy_to_clipboard(nodes_text(pairs))

    if stats is None:
        return 0

    try:
        no_ms = sum(1 for _, ms in pairs if ms <= 0.0)



        summary_max = getattr(cfg.output, "summary_max_nodes",
                              OutputConfig.summary_max_nodes)
        capped = pairs[:summary_max] if summary_max > 0 else pairs



        export_working_nodes_json(pairs, stats, json_path)
        LOG(f"[merge] {len(pairs)} nodes -> {json_path}")




        duration = float(stats.get("duration_sec") or 0.0)
        stats["merged"] = True
        export_summary(capped, stats, summary_path, duration)
        LOG(f"[merge] summary updated ({len(capped)} nodes) -> {summary_path}")







        if net:
            archive_run_artifacts(out_path.parent, net,
                                  files=MERGE_REFRESH_FILES)
        if no_ms:
            LOG(f"[merge] NOTE: {no_ms}/{len(pairs)} nodes without latency "
                f"(no non-zero ms in JSON or summary working[])")
    except Exception as e:
        LOG(f"[merge] WARNING: failed to update summary.json: {e}")

    return 0
