                                                              
                 
   
from .uri import (parse_anytls, parse_hysteria2, parse_shadowsocks,
                 parse_trojan, parse_tuic, parse_vless,
                 parse_vmess)
from .tg_proxy import parse_tg_proxy
from .wireguard import parse_wireguard
from .singbox import parse_singbox_config
from .clash import parse_clash_config
from ..models import Node
from typing import List, Optional


def parse_config_text(text: str, fmt: str) -> List[Node]:
                                                              

                                                                 
                                                          
       
    if fmt == "json":
        return parse_singbox_config(text)
    if fmt == "yaml":
        return parse_clash_config(text)
    raise ValueError(f"unsupported config format: {fmt}")


def parse_node(url: str) -> Optional[Node]:
    url = url.strip()
    if not url or "://" not in url:
        return None







    url = url.replace("&amp;", "&")

    try:
        scheme, rest = url.split("://", 1)
        scheme = scheme.lower()

        if scheme in ("hy2", "hysteria2"):
            return parse_hysteria2(url, scheme, rest)
        if scheme == "tuic":
            return parse_tuic(url, rest)
        if scheme == "anytls":


            return parse_anytls(url, rest)
        if scheme in ("wg", "wireguard"):
            return parse_wireguard(url, scheme, rest)
        if scheme == "tg":



            return parse_tg_proxy(url, rest)
        if scheme == "https" and rest.lower().startswith("t.me/"):


            return parse_tg_proxy(url, rest)

        if scheme == "vless":
            return parse_vless(url, scheme, rest)
        elif scheme == "vmess":
            return parse_vmess(url, rest)
        elif scheme == "trojan":
            return parse_trojan(url, rest)
        elif scheme == "ss":
            return parse_shadowsocks(url, rest)

        return None
    except Exception:
        return None
