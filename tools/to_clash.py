#!/usr/bin/env python3
                                                              

                                                                                 
                                                                         
                                                         
                                                               

                                                                                
                                                                      
                                                                   

                                                                            

                                                                                      
                                                                                   

                                  
                                                                        
                                           
                                                                                  
                                                                           
                                                                  

                                                                          
   
import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml







sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.models import Node, Protocol, Security
from core.parsers import parse_node
from core.paths import ROOT

NODES_FILE = ROOT / "output" / "working_nodes.txt"


OUT_FILE = ROOT / "output" / "working_nodes.yaml"


SKIP_TRANSPORTS = frozenset({"kcp"})


def _warn(msg: str) -> None:
    print(f"[to_clash] WARNING: {msg}", file=sys.stderr)


def _first(node: Node, key: str, default: str = "") -> str:
    val = node.extra.get(key, default)
    return val if isinstance(val, str) else default


def _list_opt(node: Node, key: str) -> List[str]:
                                                                                            
    raw = _first(node, key)
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def _unique_name(name: str, seen: Dict[str, int]) -> str:
                                                                                                                    
    if name not in seen:
        seen[name] = 1
        return name
    seen[name] += 1
    return f"{name} #{seen[name]}"


def _truthy(val: Any) -> bool:
                                                        

                                                                              
                                                                        
                                                                    
                                               

                                                                         
                                                                          
                                                                  
       
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _transport(node: Node, p: Dict[str, Any]) -> None:
                                                                                                 
    net = node.transport.value
    if net == "splithttp":
        net = "xhttp"
    if net in ("tcp", "udp", "quic"):
        return
    p["network"] = net
    path = _first(node, "path")
    host = _first(node, "host")
    if net == "ws":
        opts: Dict[str, Any] = {}
        if path:
            opts["path"] = path
        if host:
            opts["headers"] = {"Host": host}
        if opts:
            p["ws-opts"] = opts
    elif net == "grpc":
        opts = {}
        svc = _first(node, "serviceName")
        if svc:
            opts["grpc-service-name"] = svc
        if opts:
            p["grpc-opts"] = opts
    elif net in ("http", "h2"):
        opts = {}
        if path:
            opts["path"] = path
        if host:
            opts["host"] = [host]
        if opts:
            p["h2-opts"] = opts
    elif net == "xhttp":
        opts = {}
        if path:
            opts["path"] = path
        if host:
            opts["host"] = host
        if opts:
            p["xhttp-opts"] = opts


def _tls_common(node: Node, p: Dict[str, Any]) -> None:
                                                                                          
    sec = node.security.value
    if sec == Security.REALITY.value:
        p["tls"] = True
        reality: Dict[str, Any] = {}
        pbk = _first(node, "pbk")
        sid = _first(node, "sid")
        if pbk:
            reality["public-key"] = pbk
        if sid:
            reality["short-id"] = sid
        if reality:
            p["reality-opts"] = reality
    elif sec == Security.TLS.value:
        p["tls"] = True
    else:
        return

    sni = _first(node, "sni")
    if sni:
        p["servername"] = sni
    alpn = _list_opt(node, "alpn")
    if alpn:
        p["alpn"] = alpn


    fp = _first(node, "fp")
    if fp:
        p["client-fingerprint"] = fp
    if _truthy(node.extra.get("insecure")):
        p["skip-cert-verify"] = True


def _proxy(node: Node, name: str) -> Dict[str, Any]:
    p: Dict[str, Any] = {"name": name, "type": node.protocol.value,
                         "server": node.host, "port": node.port}
    proto = node.protocol

    if proto == Protocol.VLESS:
        p["uuid"] = _first(node, "__userinfo")
        flow = _first(node, "flow")
        if flow:
            p["flow"] = flow
        if _first(node, "packetEncoding"):
            p["packet-encoding"] = _first(node, "packetEncoding")
    elif proto == Protocol.VMESS:
        p["uuid"] = _first(node, "id")
        p["alterId"] = int(_first(node, "aid") or 0)
        p["cipher"] = _first(node, "scy", "auto")
    elif proto == Protocol.TROJAN:
        p["password"] = _first(node, "__userinfo")
    elif proto == Protocol.SHADOWSOCKS:
        p["cipher"] = _first(node, "method")
        p["password"] = _first(node, "password")
    elif proto == Protocol.HYSTERIA2:
        p["password"] = _first(node, "password")
        obfs = _first(node, "obfs")
        if obfs:
            p["obfs"] = obfs
        obfs_pw = _first(node, "obfs-password")
        if obfs_pw:
            p["obfs-password"] = obfs_pw
    elif proto == Protocol.TUIC:
        p["uuid"] = _first(node, "uuid")
        p["password"] = _first(node, "password")
    else:
        raise ValueError(f"unsupported protocol: {proto.value}")

    _tls_common(node, p)
    _transport(node, p)
    return p


def build(nodes: List[Node]) -> Tuple[List[Dict[str, Any]], List[str]]:
                                                                                                           
    proxies: List[Dict[str, Any]] = []
    dropped: List[str] = []
    seen: Dict[str, int] = {}
    for node in nodes:
        if node.transport.value in SKIP_TRANSPORTS:
            dropped.append(f"{node.name} (transport={node.transport.value} "
                           f"not in mihomo)")
            continue
        try:
            fallback = f"{node.protocol.value}-{node.host}-{node.port}"
            p = _proxy(node, _unique_name(node.name or fallback, seen))
        except ValueError as e:
            dropped.append(f"{node.name} ({e})")
            continue
        proxies.append(p)
    return proxies, dropped


def config(proxies: List[Dict[str, Any]]) -> Dict[str, Any]:
                                                                                                                                        
    names = [p["name"] for p in proxies]
    return {
        "mixed-port": 7890,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "info",
        "proxies": proxies,
        "proxy-groups": [
            {"name": "PROXY", "type": "select", "proxies": names},


            {"name": "AUTO", "type": "url-test", "proxies": names,
             "url": "https://www.gstatic.com/generate_204",
             "interval": 300, "tolerance": 50},
        ],
        "rules": [
            "GEOIP,CN,DIRECT",
            "MATCH,PROXY",
        ],
    }


def render(text: str) -> str:
                                     

                                                                            
                                                                      
                                                                  

                                                                           
                                                                               
       
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    nodes: List[Node] = []
    for ln in lines:
        node = parse_node(ln)
        if node is None:
            _warn(f"link not parsed, skipped: {ln[:80]}")
            continue
        nodes.append(node)

    proxies, dropped = build(nodes)
    for d in dropped:
        _warn(f"node skipped: {d}")
    if not proxies:
        raise ValueError("no nodes — the Clash config would be empty")

    return yaml.safe_dump(config(proxies), allow_unicode=True, sort_keys=False,
                          default_flow_style=False, width=4096)


def main() -> int:
    ap = argparse.ArgumentParser(description="working_nodes.txt → Clash-Mihomo YAML")
    ap.add_argument("--input", default=str(NODES_FILE))
    ap.add_argument("--output", default=str(OUT_FILE))
    ap.add_argument("--print-config-only", action="store_true",
                    help="print YAML to stdout, do not write a file")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"[to_clash] ERROR: {src} not found. Run run_curate.bat first.", file=sys.stderr)
        return 1

    raw = src.read_text(encoding="utf-8")
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    try:
        text = render(raw)
    except ValueError as e:
        print(f"[to_clash] ERROR: {e}", file=sys.stderr)
        return 1

    dst = Path(args.output)
    if args.print_config_only:
        sys.stdout.write(text)
        target = "stdout"
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")
        target = str(dst)




    n_proxies = len(yaml.safe_load(text).get("proxies", []))
    print(f"[to_clash] {n_proxies} proxy/proxies -> {target}")
    print(f"[to_clash] input lines: {len(lines)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
