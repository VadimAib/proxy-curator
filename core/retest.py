                                                                             

                                                                        
                                                                      
                                                                         
                                                       
                       

                 

                                                                         
                                                            
                                                                             
                                                                          
                                                                    
             
                                                                             
                                                                             
                                                             
                                                                           
                                                                       
                                                                         
                                                                    
                                                                            
                                             
                                                                           
                                                                   
                                           

                                                                    
                                                                           
   
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Tuple

from .config import Config
from .engine.engines import EngineRuntime, build_engines
from .engine.ports import PortPool, get_shared_pool
from .log import LOG
from .models import Node
from .net.netmon import NetworkMonitor
from .parsers import parse_node
from .paths import ROOT, rp
from .phases.connectivity import connectivity_phase
from .phases.delay import delay_phase
from .phases.geo_after_gate import record_countries
from .phases.speedtest import (rescue_phase, speedtest_phase,
                               speedtest_quick_phase)
from .speed_profile import normalize_speed_profile
from .state import PipelineState
from .ui import ProgressBar

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_NOTHING = 2




_METRIC_KEYS = ("speed_mbps", "speed_quick_mbps", "exit_country", "rescued")



_PHASE_NUM = 0
_PHASE_TOTAL = 6



def read_cks(path: Path) -> List[str]:
                                                                             

                                                                       
                                                                     
                                                       
       
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        LOG(f"[retest] cannot read selection {path.name}: {exc}")
        return []
    out: List[str] = []
    for line in text.splitlines():
        ck = line.strip()
        if not ck or ck.startswith("#"):
            continue
        if ck not in out:
            out.append(ck)
    return out


def _load_records(json_path: Path) -> list:
                                                                    

                                                                         
                                                   
       
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        LOG(f"[retest] cannot read {json_path.name}: {exc}")
        return []
    if not isinstance(data, list):
        LOG(f"[retest] {json_path.name}: expected a list of records")
        return []
    return data


def select_nodes(txt_path: Path, json_path: Path,
                 cks: List[str]) -> List[Tuple[Node, float]]:
                                                                         

                                                                        
                                                                          
                                          
       
    wanted = set(cks)
    if not wanted:
        return []
    records = _load_records(json_path)
    if not records:
        return []
    try:
        text = txt_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        LOG(f"[retest] cannot read {txt_path.name}: {exc}")
        return []
    raws = [line.strip() for line in text.splitlines() if line.strip()]

    selected: List[Tuple[Node, float]] = []
    skipped = 0
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue
        ck = record.get("ck")
        if not isinstance(ck, str) or ck not in wanted:
            continue
        if index >= len(raws):
            skipped += 1
            continue
        node = parse_node(raws[index])
        if node is None or node.ck() != ck:
            skipped += 1
            continue
        ms = record.get("ms")
        selected.append((node, float(ms) if isinstance(ms, (int, float)) else 0.0))
    if skipped:
        LOG(f"[retest] {skipped} selected record(s) skipped: "
            "working_nodes.txt and working_nodes.json are out of sync")
    return selected



def _default_paths(cfg: Config) -> Tuple[Path, Path]:
                                                                                                        
    txt_path = rp(cfg.output.working_nodes)
    return txt_path, txt_path.with_name(txt_path.stem + ".json")


def _open_env(cfg: Config) -> Tuple[NetworkMonitor, PortPool,
                                    Dict[str, EngineRuntime]]:
                                                                                                                          
    monitor = NetworkMonitor(interval=cfg.testing.network_probe_interval)
    monitor.start()
    workers = getattr(cfg.testing, "workers", 40)
    pool_size = max(cfg.testing.port_pool_size, workers * 3)
    port_pool = get_shared_pool(pool_size)
    return monitor, port_pool, build_engines(port_pool, cfg, rp)


def _measure(selection: List[Tuple[Node, float]], cfg: Config, args,
             stats: Dict) -> List[Tuple[Node, float]]:
                                                                                 

                                                                     
                                                                           

                                                                               
                                                                            
                                                                       
       
    monitor, port_pool, engines = _open_env(cfg)
    state = PipelineState(stats=stats, alive=list(selection),
                          save_checkpoint=False)

    delay_args = SimpleNamespace(tcping_only=False,
                                 report=bool(getattr(args, "report", False)))
    try:
        def _emit_header(name: str, executed: bool) -> None:
                                                                    
                                                                 
                                                                             
                                                                        
                                                                 

                                                                        
                                                                     
                                                                               
               
            global _PHASE_NUM
            global _PHASE_TOTAL
            _PHASE_NUM += 1
            total = _PHASE_TOTAL
            executed_tag = "" if executed else "  [skipped]"
            LOG(f"=== PHASE {_PHASE_NUM}/{_PHASE_TOTAL}: {name}{executed_tag} ===")

        def _close_phase(state_: PipelineState, name: str) -> None:
                                                                        
                                                              
                                                                         
                                
               
            LOG(f"--- PHASE {name} closed ---")



        bar = ProgressBar(len(selection), "conn", log_progress=True, unit="nodes")
        _emit_header("CONNECTIVITY", True)
        connectivity_phase(state, engines, cfg, port_pool, bar=bar)
        quick_exec = bool(state.alive)
        _emit_header("SPEEDTEST-QUICK", quick_exec)
        if quick_exec:
            speedtest_quick_phase(state, engines, cfg, port_pool)
        _close_phase(state, "SPEEDTEST-QUICK")

        _emit_header("DELAY", True)
        delay_phase(state, engines, cfg, delay_args, monitor, port_pool)
        _close_phase(state, "DELAY")

        _emit_header("RESCUE", True)
        rescue_phase(state, cfg)
        _close_phase(state, "RESCUE")

        speed_exec = bool(state.final)
        _emit_header("SPEEDTEST", speed_exec)
        if speed_exec:
            speedtest_phase(state, engines, cfg, port_pool)
        _close_phase(state, "SPEEDTEST")



        geo_exec = bool(state.final)
        _emit_header("GEO", geo_exec)
        if geo_exec:
            record_countries(state, engines, cfg)
        _close_phase(state, "GEO")
    finally:
        monitor.stop()
    return list(state.final)



def _merge_measured(record: Dict, node_key: str, geo: Dict, speed: Dict,
                    quick: Dict, rescued: set) -> None:
                                                                     

                                                                      
                                                                         
       
    hit = speed.get(node_key)
    if isinstance(hit, dict) and "mbps" in hit:
        record["speed_mbps"] = hit["mbps"]
    hit_quick = quick.get(node_key)
    if isinstance(hit_quick, dict) and "mbps" in hit_quick:
        record["speed_quick_mbps"] = hit_quick["mbps"]
    code = geo.get(node_key)
    if code:
        record["exit_country"] = code
    if node_key in rescued:
        record["rescued"] = True
    else:
        record.pop("rescued", None)


def merge_results(json_path: Path, selection: List[Tuple[Node, float]],
                  final: List[Tuple[Node, float]], stats: Dict) -> Tuple[int, int]:
                                                                  

                                                                            
                                                                            
                                                                  
       
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{json_path.name}: expected a list of records")

    keys = {node.ck(): node.key() for node, _ in selection}
    final_ms = {node.ck(): float(ms) for node, ms in final}
    geo = stats.get("geo") or {}
    speed = stats.get("speedtest") or {}
    quick = stats.get("speedtest_quick") or {}
    rescued = set(stats.get("rescued") or [])

    alive = dead = 0
    for record in data:
        if not isinstance(record, dict):
            continue
        ck = record.get("ck")
        if not isinstance(ck, str) or ck not in keys:
            continue
        if ck in final_ms:
            alive += 1
            record["ms"] = round(final_ms[ck], 2)
            _merge_measured(record, keys[ck], geo, speed, quick, rescued)
        else:
            dead += 1
            record["ms"] = 0
            for key in _METRIC_KEYS:
                record.pop(key, None)

    tmp = json_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    tmp.replace(json_path)
    return alive, dead



def run_retest(args) -> int:
                                                                                                           
    config_path = ROOT / "config.yaml"
    if not config_path.exists():
        LOG(f"ERROR: {config_path} not found")
        return EXIT_ERROR
    cfg = Config.load(config_path)
    txt_path, json_path = _default_paths(cfg)

    cks = read_cks(Path(args.retest))
    if not cks:
        LOG("[retest] nothing to measure: selection is empty")
        return EXIT_NOTHING
    selection = select_nodes(txt_path, json_path, cks)
    if not selection:
        LOG("[retest] none of the selected nodes found in working_nodes.json "
            "(the list changed since the selection was made?)")
        return EXIT_NOTHING

    LOG(f"[retest] measuring {len(selection)} selected node(s) now")
    stats: Dict = {}



    profile = normalize_speed_profile(getattr(args, "speed_profile", None) or "auto")
    if profile and profile != "auto":
        stats["profile_override"] = profile
    final = _measure(selection, cfg, args, stats)
    try:
        alive, dead = merge_results(json_path, selection, final, stats)
    except (OSError, ValueError) as exc:
        LOG(f"[retest] cannot write {json_path.name}: {exc}")
        return EXIT_ERROR
    LOG(f"[retest] done: {alive} alive, {dead} dead -> {json_path.name} "
        "(working_nodes.txt and summary.json untouched)")
    return EXIT_OK
