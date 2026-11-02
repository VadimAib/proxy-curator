                                       
   
from ._common import (_SHADOWTLS_PLUGIN, _as_int, _attach_shadowtls, _join_list,
                      _truthy, normalize_wg_key)
from .serialize import node_to_uri
from ..models import Node, Protocol, Security, Transport
from typing import Any, Dict, List, Optional
import yaml


_CLASH_TYPES: Dict[str, Protocol] = {
    "vless": Protocol.VLESS, "vmess": Protocol.VMESS, "trojan": Protocol.TROJAN,
    "ss": Protocol.SHADOWSOCKS, "shadowsocks": Protocol.SHADOWSOCKS,
    "hysteria2": Protocol.HYSTERIA2, "hysteria": Protocol.HYSTERIA2,
    "tuic": Protocol.TUIC, "wireguard": Protocol.WIREGUARD,
}


def _clash_transport(extra: Dict[str, Any], p: Dict[str, Any]) -> Transport:
                                                                                 
    net = str(p.get("network") or "").lower()
    if net == "ws":
        opts = p.get("ws-opts") or {}
        if isinstance(opts, dict):
            if opts.get("path"):
                extra["path"] = str(opts["path"])
            headers = opts.get("headers") or {}
            if isinstance(headers, dict) and headers.get("Host"):
                extra["host"] = str(headers["Host"])
        return Transport.WS
    if net == "grpc":
        opts = p.get("grpc-opts") or {}
        if isinstance(opts, dict) and opts.get("grpc-service-name"):
            extra["serviceName"] = str(opts["grpc-service-name"])
        return Transport.GRPC
    if net in ("h2", "http"):
        opts = p.get("h2-opts") or {}
        if isinstance(opts, dict):
            if opts.get("path"):
                extra["path"] = str(opts["path"])
            hosts = opts.get("host")
            if isinstance(hosts, list) and hosts:
                extra["host"] = str(hosts[0])
        return Transport.HTTP
    if net == "httpupgrade":
        opts = p.get("http-upgrade-opts") or {}
        if isinstance(opts, dict) and opts.get("path"):
            extra["path"] = str(opts["path"])
        return Transport.HTTPUPGRADE
    return Transport.TCP


def _clash_proxy(p: Dict[str, Any]) -> Optional[Node]:
                                                                     
    if not isinstance(p, dict):
        return None
    proto = _CLASH_TYPES.get(str(p.get("type", "")).lower())
    if proto is None:
        return None
    host = str(p.get("server") or "")
    port = _as_int(p.get("port"))
    if not host or port <= 0:
        return None

    extra: Dict[str, Any] = {}
    security = Security.TLS if _truthy(p.get("tls")) else Security.NONE
    if proto in (Protocol.HYSTERIA2, Protocol.TUIC):
        security = Security.TLS

    reality = p.get("reality-opts") or {}
    if isinstance(reality, dict) and reality:
        security = Security.REALITY
        extra["pbk"] = str(reality.get("public-key") or "")
        extra["sid"] = str(reality.get("short-id") or "")
    sni = p.get("servername") or p.get("sni")
    if sni:
        extra["sni"] = str(sni)
    alpn = _join_list(p.get("alpn"))
    if alpn:
        extra["alpn"] = alpn
    if p.get("client-fingerprint"):
        extra["fp"] = str(p["client-fingerprint"])
    if _truthy(p.get("skip-cert-verify")):
        extra["insecure"] = "1"

    transport = _clash_transport(extra, p)

    if proto == Protocol.VLESS:
        extra["__userinfo"] = str(p.get("uuid") or "")
        extra["flow"] = str(p.get("flow") or "")
        if p.get("packet-encoding"):
            extra["packetEncoding"] = str(p["packet-encoding"])
    elif proto == Protocol.VMESS:
        extra["id"] = str(p.get("uuid") or "")
        extra["aid"] = str(_as_int(p.get("alterId")))
        extra["scy"] = str(p.get("cipher") or "auto")
        extra["net"] = transport.value
        extra["tls"] = "tls" if security != Security.NONE else ""
    elif proto == Protocol.TROJAN:
        extra["__userinfo"] = str(p.get("password") or "")
    elif proto == Protocol.SHADOWSOCKS:
        extra["method"] = str(p.get("cipher") or "")
        extra["password"] = str(p.get("password") or "")
        if str(p.get("plugin") or "").lower().startswith(_SHADOWTLS_PLUGIN):
            opts = p.get("plugin-opts") or {}
            parts = ([f"{k}={v}" for k, v in sorted(opts.items())]
                     if isinstance(opts, dict) else [])
            _attach_shadowtls(extra, ";".join([_SHADOWTLS_PLUGIN] + parts))


    elif proto == Protocol.HYSTERIA2:
        extra["password"] = str(p.get("password") or "")
        if p.get("obfs"):
            extra["obfs"] = str(p["obfs"])
        if p.get("obfs-password"):
            extra["obfs-password"] = str(p["obfs-password"])
        extra["up"] = _join_list(p.get("up"))
        extra["down"] = _join_list(p.get("down"))
    elif proto == Protocol.TUIC:
        extra["uuid"] = str(p.get("uuid") or "")
        extra["password"] = str(p.get("password") or "")
        extra["congestion_control"] = str(p.get("congestion-controller") or "")
        extra["udp_relay_mode"] = str(p.get("udp-relay-mode") or "")
    elif proto == Protocol.WIREGUARD:
        extra["private_key"] = normalize_wg_key(p.get("private-key"))
        extra["public_key"] = normalize_wg_key(p.get("public-key"))
        extra["preshared_key"] = normalize_wg_key(p.get("pre-shared-key"))
        extra["address"] = _join_list(p.get("ip") or p.get("ipv6"))
        extra["mtu"] = _join_list(p.get("mtu"))
        extra["allowed_ips"] = _join_list(p.get("allowed-ips"))
        extra["reserved"] = _join_list(p.get("reserved"))
        security, transport = Security.NONE, Transport.UDP

    if proto in (Protocol.HYSTERIA2, Protocol.TUIC):
        transport = Transport.QUIC

    node = Node(proto, "", str(p.get("name") or ""), host, port, security,
                transport, extra)
    node.raw = node_to_uri(node)
    return node


def parse_clash_config(data: Any) -> List[Node]:
                                                                     

                                                                                
       
    if isinstance(data, (str, bytes)):
        try:
            data = yaml.safe_load(data)
        except Exception as e:
            raise ValueError(f"clash: invalid YAML: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("clash: root is not a mapping")
    proxies = data.get("proxies")
    if not isinstance(proxies, list):
        raise ValueError("clash: 'proxies:' section missing")

    nodes: List[Node] = []
    for p in proxies:
        try:
            n = _clash_proxy(p)
        except Exception:
            n = None
        if n:
            nodes.append(n)
    return nodes
