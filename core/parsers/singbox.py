                                   
   
from ._common import (_SHADOWTLS_PLUGIN, _as_int, _attach_shadowtls, _join_list,
                      _transport, normalize_wg_key)
from .serialize import node_to_uri
from ..models import Node, Protocol, Security, Transport
from ..utils import first
from typing import Any, Dict, List, Optional
import json


_SINGBOX_TYPES: Dict[str, Protocol] = {
    "vless": Protocol.VLESS, "vmess": Protocol.VMESS, "trojan": Protocol.TROJAN,
    "shadowsocks": Protocol.SHADOWSOCKS, "hysteria2": Protocol.HYSTERIA2,
    "tuic": Protocol.TUIC, "wireguard": Protocol.WIREGUARD,
}


def _singbox_tls(extra: Dict[str, Any], tls: Any) -> Security:
                                                                                   
    if not isinstance(tls, dict):
        return Security.NONE
    reality = tls.get("reality") or {}
    if isinstance(reality, dict) and reality.get("enabled"):
        security = Security.REALITY
        extra["pbk"] = str(reality.get("public_key") or "")
        extra["sid"] = str(reality.get("short_id") or "")
    elif tls.get("enabled"):
        security = Security.TLS
    else:
        security = Security.NONE
    if tls.get("server_name"):
        extra["sni"] = str(tls["server_name"])
    alpn = _join_list(tls.get("alpn"))
    if alpn:
        extra["alpn"] = alpn
    utls = tls.get("utls") or {}
    if isinstance(utls, dict) and utls.get("fingerprint"):
        extra["fp"] = str(utls["fingerprint"])
    return security


def _singbox_transport(extra: Dict[str, Any], tr: Any) -> Transport:
                                                                                    
    if not isinstance(tr, dict) or not tr.get("type"):
        return Transport.TCP
    t = str(tr["type"]).lower()
    transport = _transport(t)
    if transport is None:
        raise ValueError(f"unsupported transport: {t}")
    if t == "ws":
        if tr.get("path"):
            extra["path"] = str(tr["path"])
        host = (tr.get("headers") or {}).get("Host")
        if host:
            extra["host"] = str(host)
    elif t == "grpc":
        if tr.get("service_name"):
            extra["serviceName"] = str(tr["service_name"])
    elif t in ("http", "httpupgrade"):
        if tr.get("path"):
            extra["path"] = str(tr["path"])
        hosts = tr.get("host") or (tr.get("headers") or {}).get("Host")
        if isinstance(hosts, list) and hosts:
            extra["host"] = str(hosts[0])
        elif isinstance(hosts, str) and hosts:
            extra["host"] = hosts
    return transport


def _singbox_outbound(ob: Dict[str, Any], by_tag: Dict[str, Any],
                      depth: int = 0) -> Optional[Node]:
                                                                                                                   
    if not isinstance(ob, dict):
        return None
    otype = str(ob.get("type", "")).lower()

    if otype == "shadowtls":

        detour = by_tag.get(str(ob.get("detour", ""))) if depth < 2 else None
        inner = _singbox_outbound(detour, by_tag, depth + 1) if detour else None
        if inner is None:
            return None
        plugin = (f"{_SHADOWTLS_PLUGIN};version={ob.get('version', '')}"
                  f";password={ob.get('password', '')}")
        _attach_shadowtls(inner.extra, plugin)
        if ob.get("server"):
            inner.host = str(ob["server"])
        if _as_int(ob.get("server_port")):
            inner.port = _as_int(ob["server_port"])
        if inner.security == Security.NONE:
            inner.security = Security.TLS
        inner.raw = node_to_uri(inner)
        return inner

    proto = _SINGBOX_TYPES.get(otype)
    if proto is None:
        return None

    host = str(ob.get("server") or "")
    port = _as_int(ob.get("server_port"))
    extra: Dict[str, Any] = {}

    peers = ob.get("peers")
    if proto == Protocol.WIREGUARD and isinstance(peers, list) and peers:
        peer = peers[0] if isinstance(peers[0], dict) else {}
        host = host or str(peer.get("address") or "")
        port = port or _as_int(peer.get("port"))
        extra["public_key"] = normalize_wg_key(peer.get("public_key"))
        extra["preshared_key"] = normalize_wg_key(peer.get("pre_shared_key"))
        extra["allowed_ips"] = _join_list(peer.get("allowed_ips"))

    if not host or port <= 0:
        return None

    security = _singbox_tls(extra, ob.get("tls"))
    transport = _singbox_transport(extra, ob.get("transport"))

    if proto == Protocol.VLESS:
        extra["__userinfo"] = first(ob, "uuid")
        extra["flow"] = first(ob, "flow")
        extra["packetEncoding"] = first(ob, "packet_encoding")
    elif proto == Protocol.VMESS:
        extra["id"] = first(ob, "uuid")
        extra["scy"] = first(ob, "security") or "auto"
        extra["aid"] = first(ob, "alter_id", "0")
        extra["net"] = transport.value
        extra["packetEncoding"] = first(ob, "packet_encoding")
        extra["tls"] = "tls" if security != Security.NONE else ""
    elif proto == Protocol.TROJAN:
        extra["__userinfo"] = first(ob, "password")
    elif proto == Protocol.SHADOWSOCKS:
        extra["method"] = first(ob, "method")
        extra["password"] = first(ob, "password")
        plugin = first(ob, "plugin")
        if plugin:
            if plugin.lower().startswith(_SHADOWTLS_PLUGIN):
                _attach_shadowtls(extra, f"{plugin};{ob.get('plugin_opts', '')}")
            else:
                extra["plugin"] = plugin
    elif proto == Protocol.HYSTERIA2:
        extra["password"] = first(ob, "password")
        obfs = ob.get("obfs")
        if isinstance(obfs, dict):
            extra["obfs"] = str(obfs.get("type") or "")
            extra["obfs-password"] = str(obfs.get("password") or "")
        extra["up"] = first(ob, "up_mbps")
        extra["down"] = first(ob, "down_mbps")
    elif proto == Protocol.TUIC:
        extra["uuid"] = first(ob, "uuid")
        extra["password"] = first(ob, "password")
        extra["congestion_control"] = first(ob, "congestion_control")
    elif proto == Protocol.WIREGUARD:
        extra["private_key"] = normalize_wg_key(first(ob, "private_key"))
        extra["address"] = _join_list(ob.get("address") or ob.get("local_address"))
        extra["mtu"] = first(ob, "mtu")
        extra["reserved"] = _join_list(ob.get("reserved"))
        extra["public_key"] = normalize_wg_key(
            first(extra, "public_key") or first(ob, "peer_public_key"))

    if proto in (Protocol.HYSTERIA2, Protocol.TUIC):
        transport = Transport.QUIC
        if security == Security.NONE:
            security = Security.TLS
    elif proto == Protocol.WIREGUARD:
        transport, security = Transport.UDP, Security.NONE

    node = Node(proto, "", first(ob, "tag"), host, port, security,
                transport, extra)
    node.raw = node_to_uri(node)
    return node


def parse_singbox_config(data: Any) -> List[Node]:
                                                                            

                                                                    
                                                                             
                                                                       
                                                                                
                                                                          
                                                                          
       
    if isinstance(data, (str, bytes)):
        try:
            data = json.loads(data)
        except Exception as e:
            raise ValueError(f"sing-box: invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("sing-box: root is not an object")
    outbounds = data.get("outbounds")
    if not isinstance(outbounds, list):
        raise ValueError("sing-box: 'outbounds' list missing")

    by_tag = {str(o.get("tag")): o for o in outbounds
              if isinstance(o, dict) and o.get("tag")}


    inner_tags = {str(o.get("detour")) for o in outbounds
                  if isinstance(o, dict) and o.get("detour")}
    nodes: List[Node] = []
    for ob in outbounds:
        if isinstance(ob, dict) and str(ob.get("tag") or "") in inner_tags:
            continue
        try:
            n = _singbox_outbound(ob, by_tag)
        except Exception:
            n = None
        if n:
            nodes.append(n)
    return nodes
