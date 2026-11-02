                                                                      
                                                                         
                                         
   
from ._common import (_attach_shadowtls, _b64_decode, _params_to_dict,
                      _parse_uri_components, _security, _split_host_port,
                      _transport, _truthy, _SHADOWTLS_PLUGIN)
from urllib.parse import parse_qs, unquote
from ..models import Node, Protocol, Security, Transport
from ..utils import first
from typing import Any, Dict, Optional
import json


def parse_vless(url: str, scheme: str, rest: str) -> Optional[Node]:
    userinfo, host, port, query_string, name, url_path = _parse_uri_components(rest)





    if not userinfo or host is None or port is None:
        return None

    name = unquote(name)
    params = parse_qs(query_string)

    security = _security(first(params, "security", "none"))
    if security is None:
        return None

    transport = _transport(first(params, "type", "tcp"))
    if transport is None:
        return None

    extra = _params_to_dict(params)
    extra["__userinfo"] = userinfo

    if url_path and "path" not in extra:
        extra["path"] = "/" + url_path

    return Node(
        protocol=Protocol.VLESS, raw=url, name=name,
        host=host, port=port, security=security, transport=transport,
        extra=extra,
    )


def parse_vmess(url: str, rest: str) -> Optional[Node]:
    try:
        j = json.loads(_b64_decode(rest))
    except Exception:
        return None

    if not isinstance(j, dict):
        return None

    host = str(j.get("add", "")).strip()
    try:
        port = int(j.get("port", 0))
    except Exception:
        port = 0

    if not host or port <= 0:
        return None

    tls_raw = j.get("tls", "")
    security = Security.TLS if (
        (isinstance(tls_raw, bool) and tls_raw) or
        str(tls_raw).lower() in ("tls", "true", "1")
    ) else Security.NONE

    transport = _transport(j.get("net", "tcp"))
    if transport is None:
        return None

    return Node(
        protocol=Protocol.VMESS, raw=url, name=str(j.get("ps", "")),
        host=host, port=port, security=security, transport=transport,
        extra={k: str(v) for k, v in j.items() if v is not None},
    )


def parse_trojan(url: str, rest: str) -> Optional[Node]:
    userinfo, host, port, query_string, name, url_path = _parse_uri_components(rest)

    if not userinfo or host is None or port is None:
        return None

    name = unquote(name)
    params = parse_qs(query_string)

    security = _security(first(params, "security", "tls"))
    if security is None or security == Security.NONE:
        security = Security.TLS

    transport = _transport(first(params, "type", "tcp"))
    if transport is None:
        return None

    extra = _params_to_dict(params)
    extra["__userinfo"] = userinfo

    if url_path and "path" not in extra:
        extra["path"] = "/" + url_path

    return Node(
        protocol=Protocol.TROJAN, raw=url, name=name,
        host=host, port=port, security=security, transport=transport,
        extra=extra,
    )


def parse_shadowsocks(url: str, rest: str) -> Optional[Node]:
       
                             
                                                                       
                                                           
       
    name = ""
    if "#" in rest:
        rest, name = rest.split("#", 1)
        name = unquote(name)

    query_string = ""
    if "?" in rest:
        rest, query_string = rest.split("?", 1)
    params = _params_to_dict(parse_qs(query_string))

    if "@" in rest:
        userinfo_b64, hostport = rest.rsplit("@", 1)






        if ":" in userinfo_b64:
            userinfo = unquote(userinfo_b64)
        else:
            try:
                userinfo = _b64_decode(userinfo_b64)
            except Exception:
                return None



        host, port = _split_host_port(hostport.split("/", 1)[0])
        if host is None or port is None:
            return None

        if ":" not in userinfo:
            return None
        method, pwd = userinfo.split(":", 1)
    else:
        try:
            dec = _b64_decode(rest)
        except Exception:
            return None

        if "@" not in dec:
            return None
        userinfo, hostport = dec.rsplit("@", 1)

        host, port = _split_host_port(hostport.split("/", 1)[0])
        if host is None or port is None:
            return None

        if ":" not in userinfo:
            return None
        method, pwd = userinfo.split(":", 1)

    extra: Dict[str, Any] = {"method": method, "password": pwd}

    plugin = first(params, "plugin")
    if plugin:
        if plugin.lower().startswith(_SHADOWTLS_PLUGIN):
            _attach_shadowtls(extra, plugin)
        else:
            extra["plugin"] = plugin

    return Node(
        protocol=Protocol.SHADOWSOCKS, raw=url, name=name,
        host=host, port=port, security=Security.NONE,
        transport=Transport.TCP,
        extra=extra,
    )


def parse_anytls(url: str, rest: str) -> Optional[Node]:
                                                                            

                                                                       
                                                                          
                                                                          
                     

                                                      
                                                                             
                                                  
       
    userinfo, host, port, query_string, name, _ = _parse_uri_components(rest)
    if host is None or port is None:
        return None

    password = unquote(userinfo)
    if not password:
        return None

    params = _params_to_dict(parse_qs(query_string))
    extra: Dict[str, Any] = dict(params)
    extra["password"] = password
    extra["sni"] = first(params, "sni") or first(params, "peer")
    extra["insecure"] = "1" if _truthy(
        first(params, "insecure") or first(params, "allowinsecure")
        or first(params, "allow_insecure")) else ""

    security = _security(first(params, "security", "tls"))
    if security is None or security == Security.NONE:



        security = Security.TLS

    return Node(
        protocol=Protocol.ANYTLS, raw=url, name=unquote(name),
        host=host, port=port, security=security, transport=Transport.TCP,
        extra=extra,
    )


def parse_hysteria2(url: str, scheme: str, rest: str) -> Optional[Node]:
                                                                              

                                                                           
       
    userinfo, host, port, query_string, name, _ = _parse_uri_components(rest)
    if host is None or port is None:
        return None

    password = unquote(userinfo)
    if not password:
        return None

    params = _params_to_dict(parse_qs(query_string))
    extra: Dict[str, Any] = dict(params)
    extra["password"] = password
    extra["sni"] = first(params, "sni") or first(params, "peer")
    extra["insecure"] = "1" if _truthy(
        first(params, "insecure") or first(params, "allowinsecure")
        or first(params, "allow_insecure")) else ""
    obfs_pwd = first(params, "obfs-password") or first(params, "obfs_password")
    if obfs_pwd:
        extra["obfs-password"] = obfs_pwd

    return Node(
        protocol=Protocol.HYSTERIA2, raw=url, name=unquote(name),
        host=host, port=port, security=Security.TLS, transport=Transport.QUIC,
        extra=extra,
    )


def parse_tuic(url: str, rest: str) -> Optional[Node]:
                                                                                          
    userinfo, host, port, query_string, name, _ = _parse_uri_components(rest)
    if host is None or port is None or not userinfo:
        return None

    params = _params_to_dict(parse_qs(query_string))
    userinfo = unquote(userinfo)
    if ":" in userinfo:
        uuid, password = userinfo.split(":", 1)
    else:
        uuid, password = userinfo, first(params, "password")

    if not uuid:
        return None

    extra: Dict[str, Any] = dict(params)
    extra["uuid"] = uuid
    extra["password"] = password
    extra["sni"] = first(params, "sni") or first(params, "peer")

    return Node(
        protocol=Protocol.TUIC, raw=url, name=unquote(name),
        host=host, port=port, security=Security.TLS, transport=Transport.QUIC,
        extra=extra,
    )

