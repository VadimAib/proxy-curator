                                                                       

                                                                        
                                                                              
                                                                     
                                                                      
                                                     

                                                                             
                                                                           
   
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ..engine.engines import ENGINES, engine_name_for, split_nodes
from ..filters import (deduplicate, filter_countries, filter_domains,
                       filter_names, filter_ports, policy_check)
from ..log import LOG
from ..models import Node
from ..parsers import parse_node
from ..state import PipelineState


def _sanitize_key(key: str) -> str:
    return "".join(c for c in key if c.isprintable() and ord(c) < 128).strip()


def _apply_policy(n: Node, filters_cfg, only_protos: Optional[set]) -> Tuple[bool, str]:
                                                                                                           
    ok, why = policy_check(n, filters_cfg)
    if ok and only_protos and n.protocol.value not in only_protos:
        ok, why = False, f"--only excluded {n.protocol.value}"
    return ok, why


def parse_and_filter_nodes(state: PipelineState, filters_cfg: Any,
                           only_protos: Optional[Set[str]],
                           unparseable_path: Path
                           ) -> None:
                                                                          

                      
                                                                         
                                                                         
                                                                      
                                                                     
                                                                

                                                                             
                                                                           
                                                                
                                            

                                                                     
                                                                         
                                              
       
    nodes: List[Node] = []
    drops: Dict[str, int] = {}
    SAMPLE_SIZE = 20






    CONFIG_SAMPLE_CAP = 3
    extra_nodes = state.config_nodes
    extra_samples = state.samples
    unparseable_sample: List[str] = list(extra_samples or [])[:CONFIG_SAMPLE_CAP]
    if extra_nodes:
        LOG(f"[policy] {len(extra_nodes)} pre-parsed nodes from configs")




    state.source_nodes = list(extra_nodes)





    for n in extra_nodes or []:
        ok, why = _apply_policy(n, filters_cfg, only_protos)
        if ok:
            nodes.append(n)
        else:
            key = _sanitize_key(why[:60])
            drops[key] = drops.get(key, 0) + 1

    for l in state.links:
        n = parse_node(l)
        if not n or not n.host or not n.port:
            if "://" in l:
                scheme = l.split("://", 1)[0].lower().strip()
            else:
                scheme = "no_scheme"
            if scheme in ("vless", "vmess", "trojan", "ss", "hysteria2", "hy2",
                          "tuic", "wg", "wireguard",



                          "anytls", "tg"):
                reason = f"parse_error_{scheme}"
            else:
                reason = f"unsupported_scheme_{scheme[:20]}"
            key = _sanitize_key(reason)
            drops[key] = drops.get(key, 0) + 1
            if len(unparseable_sample) < SAMPLE_SIZE:
                unparseable_sample.append(l)
            continue




        src = state.link_source.get(l)
        if src:
            n.extra["src"] = src
        ok, why = _apply_policy(n, filters_cfg, only_protos)
        if not ok:
            key = _sanitize_key(why[:60])
            drops[key] = drops.get(key, 0) + 1
            continue
        state.source_nodes.append(n)
        nodes.append(n)

    aggressive = getattr(filters_cfg, "aggressive_dedup", False)
    before = len(nodes)
    nodes = deduplicate(nodes, aggressive=aggressive)
    LOG(f"[policy] dedup ({'aggressive' if aggressive else 'normal'}): {before} -> {len(nodes)}")
    LOG(f"[policy] {len(nodes)} survive policy")
    for w, c in sorted(drops.items(), key=lambda x: -x[1])[:12]:
        LOG(f"         -{c:<6} {w}")

    if unparseable_sample:
        unparseable_path.parent.mkdir(parents=True, exist_ok=True)
        with open(unparseable_path, "w", encoding="utf-8") as f:
            f.write("\n".join(unparseable_sample) + "\n")
        LOG(f"[policy] unparseable sample ({len(unparseable_sample)}) -> {unparseable_path}")

    before = len(nodes)
    nodes = filter_names(nodes, filters_cfg.name_blacklist)
    LOG(f"[filter] name blacklist: {before} -> {len(nodes)}")
    before = len(nodes)
    nodes = filter_countries(nodes, filters_cfg.country_blacklist)
    if before != len(nodes):
        LOG(f"[filter] country blacklist: {before} -> {len(nodes)}")




    before = len(nodes)
    nodes = filter_domains(nodes, filters_cfg.blacklist_domains)
    if before != len(nodes):
        drops["blacklisted_domain"] = before - len(nodes)
        LOG(f"[filter] domain blacklist: {before} -> {len(nodes)}")
    if filters_cfg.only_standard_ports:
        before = len(nodes)
        nodes = filter_ports(nodes, filters_cfg.standard_ports)
        if before != len(nodes):
            drops["non_standard_port"] = before - len(nodes)
            LOG(f"[filter] standard ports: {before} -> {len(nodes)}")
    state.nodes = nodes
    state.policy_drops = drops
    state.stats["policy_survive"] = len(nodes)
    state.stats["policy_drops"] = drops



    for n in nodes:
        state.bump_feed(n.extra.get("src"), "survive")


def routing_phase(nodes: List[Node], stats: Dict) -> Dict[str, List[Node]]:
                                                                                                          
    groups = split_nodes(nodes)
    LOG("[route] engines: " + ", ".join(
        f"{p.value}->{c.ENGINE_NAME}" for p, c in ENGINES.items()))
    LOG("[route] " + (", ".join(f"{k}:{len(v)}" for k, v in groups.items())
                      or "no nodes with a known engine"))
    stats["routes"] = {k: len(v) for k, v in groups.items()}
    stats["routes_no_engine"] = sum(1 for n in nodes if not engine_name_for(n))
    return groups
