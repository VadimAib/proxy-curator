                           
import re
import ipaddress
from typing import Dict, List, Tuple, Set
from .models import (Node, Protocol, Security, Transport, QUIC_PROTOCOLS,
                     REALITY_TRANSPORTS)
from .config import FiltersConfig
from .utils import first

TESTABLE_PROTOCOLS = {Protocol.VLESS, Protocol.VMESS, Protocol.TROJAN,
                      Protocol.SHADOWSOCKS, Protocol.HYSTERIA2, Protocol.TUIC,

                      Protocol.ANYTLS,





                      Protocol.MTPROTO}







SUPPORTED_TRANSPORTS = {
    Transport.TCP, Transport.WS, Transport.GRPC,
    Transport.HTTP, Transport.HTTPUPGRADE, Transport.XHTTP,
    Transport.SPLITHHTTP, Transport.KCP, Transport.QUIC
}

UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I
)


def geo_lookup_enabled(filters: FiltersConfig) -> bool:
                                                                

                                                                            
                                                                       
                                                                          
        

                                         
                                                         
                                                                              
                                                         

                                                                 
       
    if list(getattr(filters, "country_blacklist", None) or []):
        return True
    return bool(getattr(filters, "country_paranoid", False))

def policy_check(n: Node, filters: FiltersConfig) -> Tuple[bool, str]:





    bl = filters.protocol_blacklist
    if bl and n.protocol.value in {p.strip().lower() for p in bl if p.strip()}:
        return False, f"blacklisted proto {n.protocol.value}"

    if n.protocol not in TESTABLE_PROTOCOLS:
        return False, f"untestable proto {n.protocol.value}"

    if n.transport not in SUPPORTED_TRANSPORTS:
        return False, f"unsupported transport {n.transport.value}"
    if n.extra.get("shadow_tls"):


        return False, f"shadowtls+no-engine {n.protocol.value}"

    if n.protocol in QUIC_PROTOCOLS:
        if n.transport != Transport.QUIC:
            return False, f"{n.protocol.value}+non-QUIC-transport"
        if n.protocol == Protocol.TUIC and not first(n.extra, "uuid"):
            return False, "TUIC+no-uuid"
        if n.protocol == Protocol.HYSTERIA2:
            if not first(n.extra, "password"):
                return False, "Hysteria2+no-auth"
            if first(n.extra, "obfs") and not first(n.extra, "obfs-password"):







                return False, "Hysteria2+obfs-no-password"
        return True, ""

    if n.security == Security.REALITY:
        if n.protocol != Protocol.VLESS:
            return False, f"Reality+{n.protocol.value}"





        if n.transport not in REALITY_TRANSPORTS:
            return False, f"Reality+unsupported-{n.transport.value}"
        pbk = first(n.extra, "pbk")
        if not pbk or len(pbk) < 20:
            return False, "Reality+invalid-pbk"











    if n.protocol in (Protocol.VLESS, Protocol.VMESS):
        uid = first(n.extra, "__userinfo" if n.protocol == Protocol.VLESS else "id")
        if not uid:
            uid = n.raw.split("://", 1)[1].split("@", 1)[0]
        if not uid:
            return False, f"{n.protocol.value}+no-uuid"
        if not UUID_RE.match(uid):
            return False, f"{n.protocol.value}+invalid-uuid"

    if n.protocol == Protocol.VLESS:
        if n.security == Security.NONE:
            try:
                ipaddress.ip_address(n.host)
                return False, "VLESS+noTLS+IP"
            except ValueError:
                return False, "VLESS+noTLS+domain"

    elif n.protocol == Protocol.TROJAN:
        pwd = first(n.extra, "__userinfo") or n.raw.split("://", 1)[1].split("@", 1)[0]
        if not pwd:
            return False, "Trojan+no-password"
        if n.security == Security.NONE:
            return False, "Trojan+noTLS"

    elif n.protocol == Protocol.ANYTLS:



        if not first(n.extra, "password"):
            return False, "anytls+no-password"

    elif n.protocol == Protocol.MTPROTO:




        if not first(n.extra, "secret"):
            return False, "mtproto+no-secret"

    elif n.protocol == Protocol.SHADOWSOCKS:
        method = first(n.extra, "method")
        pwd = first(n.extra, "password")
        if not method or not pwd:
            return False, "SS+no-credentials"
        valid_methods = {
            "aes-128-gcm", "aes-256-gcm", "chacha20-ietf-poly1305",
            "2022-blake3-aes-128-gcm", "2022-blake3-aes-256-gcm",
            "2022-blake3-chacha20-poly1305",
        }
        if method.lower() not in valid_methods:
            return False, f"SS+invalid-method-{method}"

    return True, ""

def filter_domains(nodes: List[Node], blacklist: List[str]) -> List[Node]:
                                                                   

                                                                          
                                                                     
                                                                          
       
    bl = [d.strip().lower() for d in blacklist if d and d.strip()]
    if not bl:
        return list(nodes)
    return [n for n in nodes
            if not any(d in (n.host or "").lower() for d in bl)]


def filter_ports(nodes: List[Node], ports: List[int]) -> List[Node]:
                                                                               

                                                                       
                                                                        
       
    allowed = set(ports)
    return [n for n in nodes if n.port in allowed]

def filter_names(nodes: List[Node], blacklist: List[str]) -> List[Node]:
                                                                  

                                                                        
                                                 
       
    bl = [p.strip() for p in blacklist if p.strip()]
    return [n for n in nodes if not any(p in n.name for p in bl)]





_FLAG_BASE = 0x1F1E6


def _flag_emoji(code: str) -> str:
                                                                           

                                                                       
                                                                    
                                                                       
                                                                 
                             
       
    if len(code) != 2 or not code.isalpha() or not code.isascii():
        return ""
    return "".join(chr(_FLAG_BASE + ord(ch.upper()) - ord("A"))
                   for ch in code)


def _country_patterns(code: str) -> List["re.Pattern[str]"]:
                                                                  

                                                                 
                                                                         
                                                                       
                                                                  
       
    up = code.strip().upper()
    if not up or not up.isascii() or not up.isalpha():
        return []

    return [re.compile(rf"(?<![A-Za-z]){re.escape(up)}(?![A-Za-z])", re.I)]











FULL_NAMES: Dict[str, List[str]] = {
    "RU": ["РОССИЯ", "РФ", "РУССИЯ", "РУСС", "RUSSIA", "RUSS",
           "Moscow", "МОСКВА", "SPb", "Saint Petersburg", "Kazan",
           "Samara", "Novosibirsk", "Nizhny Novgorod", "Krasnodar"],
    "DE": ["DEUTSCHLAND", "GERMANY", "ГЕРМАНИЯ", "БЕРЛИН", "МЮНХЕН",
           "Berlin", "Munich"],
    "NL": ["НИДЕРЛАНДЫ", "ХОЛЛАНДИЯ", "HOLLAND", "AMSTERDAM", "ROTTERDAM"],
    "US": ["UNITED STATES", "USA", "UNITED STATES OF AMERICA", "AMERICA",
           "NEW YORK", "LOS ANGELES", "CHICAGO"],
    "PL": ["POLSKA", "ПОЛЬША", "WARSZAWA", "ВАРШАВА", "KRAKOW", "WROCLAW"],
}




DOMAIN_PATTERNS: Dict[str, List[str]] = {
    "RU": [".ru", ".su", ".рф", ".ру"],
    "DE": [".de"],
    "NL": [".nl"],
    "US": [".us"],
    "PL": [".pl"],
}


def _token_pattern(token: str) -> "re.Pattern[str]":
                                                       

                                                                   
                                                                  
                                                                        
                                                              
       
    if token.startswith("."):
        inner = token[1:]
        return re.compile(rf"(?<=\.){re.escape(inner)}(?![\w])", re.I)
    return re.compile(rf"(?<!\w){re.escape(token)}(?!\w)", re.I)


def filter_countries(nodes: List[Node], blacklist: List[str]) -> List[Node]:
                                                           

                                                                            
                                                                       
                                                                  

                                                                     
                                                                         
                                  

                                                                        
                                                       
       
    codes = [c for c in (x.strip() for x in blacklist) if c]
    if not codes:
        return list(nodes)
    flags = {f for f in (_flag_emoji(c) for c in codes) if f}
    patterns = [p for c in codes for p in _country_patterns(c)]
    extra = []
    for c in codes:
        cu = c.upper()
        info = FULL_NAMES.get(cu)
        if info:
            extra.extend(_token_pattern(t) for t in info)
        domains = DOMAIN_PATTERNS.get(cu)
        if domains:
            extra.extend(_token_pattern(t) for t in domains)
    if not flags and not patterns and not extra:
        return list(nodes)

    kept = []
    for n in nodes:
        name = n.name or ""
        if (any(f in name for f in flags)
                or any(p.search(name) for p in patterns)
                or any(p.search(name) for p in extra)):
            continue
        kept.append(n)
    return kept

def deduplicate(nodes: List[Node], aggressive: bool = False) -> List[Node]:
                                               

                                                                              
                                                                           
                                                                            
                                    

                                                                
                                                                             
                                                                          
                          
       
    seen: Set[str] = set()
    result = []
    for n in nodes:
        key = n.dedup_key() if aggressive else n.key()
        if key not in seen:
            seen.add(key)
            result.append(n)
    return result