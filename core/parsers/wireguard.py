                                                        

                                                        
                                   
   
from ._common import (_b64_decode, _params_to_dict, _split_host_port,
                      normalize_wg_key)
from urllib.parse import parse_qs, unquote
from ..models import Node, Protocol, Security, Transport
from ..utils import first
from typing import Any, Dict, Optional
import re


_WG_INI_RE = re.compile(r"\[interface\]|privatekey|endpoint", re.I)


def _b64_or_none(data: str) -> Optional[str]:
                                                                                                              
    if not data:
        return None
    if "=" not in data and len(data) < 16:
        return None
    try:
        return _b64_decode(data)
    except Exception:
        return None


def _wg_ini_values(text: str) -> Dict[str, str]:
                                                                                              
    vals: Dict[str, str] = {}
    section = ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line.strip("[]").strip().lower()
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            vals[f"{section}.{k.strip().lower()}"] = v.strip()
    return vals









WG_KEEPALIVE_KEYS = ("keepalive", "persistentkeepalive",
                     "persistent_keepalive", "persistent-keepalive")


def _normalize_wg_keepalive(extra: Dict[str, Any]) -> None:
                                                                       

                                                                  
                                                                 
                                                                           
                                                                 
       
    for key in WG_KEEPALIVE_KEYS:
        val = first(extra, key)
        if not val:
            continue



        if val.isdigit() and 0 < int(val) <= 65535:
            extra["keepalive"] = str(int(val))
            break
        for stale in WG_KEEPALIVE_KEYS:
            extra.pop(stale, None)


def parse_wireguard(url: str, scheme: str, rest: str) -> Optional[Node]:
                                                                

                                                                          
                                                                                 
                                                                 
       
    name = ""
    if "#" in rest:
        rest, name = rest.split("#", 1)
        name = unquote(name)

    query_string = ""
    if "?" in rest:
        rest, query_string = rest.split("?", 1)
    params = _params_to_dict(parse_qs(query_string))

    userinfo, host, port = "", None, None
    ini_text = ""
    if "@" in rest:
        userinfo, hostport = rest.rsplit("@", 1)
        host, port = _split_host_port(hostport)
        if host is None:
            return None
        userinfo = unquote(userinfo)
        candidate = _b64_or_none(userinfo)
        if candidate and _WG_INI_RE.search(candidate):
            ini_text, userinfo = candidate, ""
    else:
        decoded = _b64_or_none(unquote(rest))
        if decoded and _WG_INI_RE.search(decoded):
            ini_text = decoded
        else:
            host, port = _split_host_port(unquote(rest))
            if host is None:
                return None

    extra: Dict[str, Any] = dict(params)
    if ini_text:
        vals = _wg_ini_values(ini_text)
        endpoint = vals.get("peer.endpoint", "")
        e_host, e_port = _split_host_port(endpoint) if endpoint else (None, None)
        if host is None and e_host:
            host, port = e_host, e_port
        extra.update({
            "private_key": normalize_wg_key(vals.get("interface.privatekey", "")),
            "public_key": normalize_wg_key(vals.get("peer.publickey", "")),
            "preshared_key": normalize_wg_key(vals.get("peer.presharedkey", "")),
            "address": vals.get("interface.address", ""),
            "dns": vals.get("interface.dns", ""),
            "mtu": vals.get("interface.mtu", ""),
            "allowed_ips": vals.get("peer.allowedips", ""),
        })

        keepalive = vals.get("interface.persistentkeepalive", "")
        if keepalive:
            extra["keepalive"] = keepalive
        _normalize_wg_keepalive(extra)
    else:
        extra["private_key"] = normalize_wg_key(userinfo)


        extra["public_key"] = normalize_wg_key(
            first(params, "publickey")
            or first(params, "public_key")
            or first(params, "peer"))
        extra["address"] = first(params, "address") or first(params, "ip")
        extra["mtu"] = first(params, "mtu")






        _normalize_wg_keepalive(extra)

    if host is None or port is None or not first(extra, "public_key"):
        return None

    return Node(
        protocol=Protocol.WIREGUARD, raw=url, name=name,
        host=host, port=port, security=Security.NONE, transport=Transport.UDP,
        extra=extra,
    )
