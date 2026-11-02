                                                            
                                               
   
from ._common import normalize_wg_key
from urllib.parse import quote
from ..models import Node, Protocol, Security
from ..utils import first
from typing import Any, Dict
import base64
import json


def _hostport(host: str, port: int) -> str:
                                                                                   
    return f"[{host}]:{port}" if ":" in host else f"{host}:{port}"


def _frag(name: str) -> str:
    return f"#{quote(name, safe='')}" if name else ""


def _qs(params: Dict[str, Any]) -> str:
                                                                                                          
    items = []
    for k, v in sorted(params.items()):
        if k.startswith("_") or v is None or v == "":
            continue
        if isinstance(v, (dict, list)):
            continue
        items.append(f"{quote(str(k), safe='')}={quote(str(v), safe='')}")
    return "&".join(items)


def _q(params: Dict[str, Any]) -> str:
    qs = _qs(params)
    return f"?{qs}" if qs else ""


def _uri_params(n: Node) -> Dict[str, Any]:
                                                                                                  
    params = {k: v for k, v in n.extra.items()
              if not k.startswith("_") and k not in ("__userinfo", "__source")}
    params.setdefault("security", n.security.value)
    params.setdefault("type", n.transport.value)
    return params


def node_to_uri(n: Node) -> str:
                                                                             

                                                                        
                                                                       
                                                                     
       
    name = n.name or ""

    if n.protocol == Protocol.VLESS:
        uid = first(n.extra, "__userinfo") or first(n.extra, "id")
        return (f"vless://{uid}@{_hostport(n.host, n.port)}"
                f"{_q(_uri_params(n))}{_frag(name)}")

    if n.protocol == Protocol.VMESS:
        e = n.extra
        blob = {
            "v": "2", "ps": name, "add": n.host, "port": str(n.port),
            "id": first(e, "id") or first(e, "__userinfo"),
            "aid": first(e, "aid", "0"), "scy": first(e, "scy", "auto"),
            "net": first(e, "net") or n.transport.value,
            "type": first(e, "headerType", "none"),
            "host": first(e, "host"), "path": first(e, "path"),
            "tls": "tls" if n.security != Security.NONE else "",
            "sni": first(e, "sni") or first(e, "servername"),
            "alpn": first(e, "alpn"), "fp": first(e, "fp"),
        }
        payload = base64.b64encode(json.dumps(
            {k: v for k, v in blob.items() if v},
            ensure_ascii=False).encode("utf-8")).decode()
        return f"vmess://{payload}"

    if n.protocol == Protocol.TROJAN:
        pwd = first(n.extra, "__userinfo") or first(n.extra, "password")
        return (f"trojan://{quote(pwd, safe='')}@{_hostport(n.host, n.port)}"
                f"{_q(_uri_params(n))}{_frag(name)}")

    if n.protocol == Protocol.SHADOWSOCKS:
        method = first(n.extra, "method")
        pwd = first(n.extra, "password")
        userinfo = base64.b64encode(f"{method}:{pwd}".encode()).decode().rstrip("=")
        plugin = first(n.extra, "plugin")
        path = f"/?plugin={quote(plugin, safe='')}" if plugin else ""
        return f"ss://{userinfo}@{_hostport(n.host, n.port)}{path}{_frag(name)}"

    if n.protocol == Protocol.HYSTERIA2:
        params = _uri_params(n)
        pwd = quote(str(params.pop("password", "")), safe='')
        return (f"hysteria2://{pwd}@{_hostport(n.host, n.port)}"
                f"{_q(params)}{_frag(name)}")

    if n.protocol == Protocol.TUIC:
        params = _uri_params(n)
        uid = quote(str(params.pop("uuid", "")), safe='')
        pwd = quote(str(params.pop("password", "")), safe='')
        userinfo = f"{uid}:{pwd}" if pwd else uid
        return (f"tuic://{userinfo}@{_hostport(n.host, n.port)}"
                f"{_q(params)}{_frag(name)}")

    if n.protocol == Protocol.ANYTLS:



        params = _uri_params(n)
        pwd = quote(str(params.pop("password", "")), safe='')
        return (f"anytls://{pwd}@{_hostport(n.host, n.port)}"
                f"{_q(params)}{_frag(name)}")

    if n.protocol == Protocol.MTPROTO:





        return f"{n.raw}{_frag(name)}"

    if n.protocol == Protocol.WIREGUARD:
        params = _uri_params(n)


        priv = quote(normalize_wg_key(params.pop("private_key", "")), safe='')
        for k in ("publickey", "public_key", "preshared_key"):
            v = params.get(k)
            if isinstance(v, str) and v:
                params[k] = normalize_wg_key(v)
        return (f"wg://{priv}@{_hostport(n.host, n.port)}"
                f"{_q(params)}{_frag(name)}")

    return n.raw
