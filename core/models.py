                                
from dataclasses import dataclass, field
from typing import Dict, Any
from enum import Enum
from hashlib import sha1
from urllib.parse import parse_qs

class Protocol(str, Enum):
    VLESS = "vless"
    VMESS = "vmess"
    TROJAN = "trojan"
    SHADOWSOCKS = "ss"
    HYSTERIA2 = "hysteria2"
    TUIC = "tuic"
    WIREGUARD = "wireguard"




    ANYTLS = "anytls"






    MTPROTO = "mtproto"

class Security(str, Enum):
    NONE = "none"
    TLS = "tls"
    REALITY = "reality"

class Transport(str, Enum):
    TCP = "tcp"
    WS = "ws"
    GRPC = "grpc"
    HTTP = "http"
    HTTPUPGRADE = "httpupgrade"
    XHTTP = "xhttp"
    SPLITHHTTP = "splithttp"
    KCP = "kcp"
    QUIC = "quic"
    UDP = "udp"



QUIC_PROTOCOLS = frozenset({Protocol.HYSTERIA2, Protocol.TUIC})






REALITY_TRANSPORTS = frozenset({
    Transport.TCP, Transport.GRPC, Transport.XHTTP,
})

def _canonical_raw(raw: str) -> str:
                                                                                                    
    base = raw.split("#", 1)[0]
    if "?" not in base:
        return base
    left, query = base.split("?", 1)
    try:
        q = parse_qs(query)
        parts = [f"{k}={q[k][0]}" for k in sorted(q) if q[k]]
        return left + "?" + "&".join(parts) if parts else left
    except Exception:
        return base

@dataclass
class Node:
    protocol: Protocol
    raw: str
    name: str
    host: str
    port: int
    security: Security
    transport: Transport
    extra: Dict[str, Any] = field(default_factory=dict)

    def key(self) -> str:
                                                  
        
                                                                                   
                                                                                
                                                                 
           
        if self.protocol == Protocol.VMESS:
            e = self.extra
            return "|".join([
                "vmess", self.host, str(self.port),
                e.get("net", ""), e.get("tls", ""), e.get("id", ""),
                e.get("path", ""), e.get("host", ""), e.get("sni", ""),
            ])
        return f"{self.protocol.value}|{_canonical_raw(self.raw)}"

    def dedup_key(self) -> str:
                                                                             

                                                                          
                                                                           
                                                                        
                                                                      

                                                                     
                                                                           
                                                                                   
           
        if self.protocol == Protocol.VMESS:
            cred = self.extra.get("id", "")
        elif self.protocol in (Protocol.VLESS, Protocol.TROJAN):

            cred = self.extra.get("__userinfo", "") or self.extra.get("password", "")
        elif self.protocol == Protocol.SHADOWSOCKS:
            cred = self.extra.get("password", "")
        elif self.protocol == Protocol.WIREGUARD:
            cred = self.extra.get("public_key", "")
        elif self.protocol in (Protocol.HYSTERIA2, Protocol.TUIC):
            cred = self.extra.get("password", "") or self.extra.get("uuid", "")
        elif self.protocol == Protocol.ANYTLS:

            cred = self.extra.get("password", "")
        elif self.protocol == Protocol.MTPROTO:



            cred = self.extra.get("secret", "")
        else:
            cred = ""
        return f"{self.protocol.value}|{self.host}|{self.port}|{cred}"

    def ck(self) -> str:
                                                                            

                                                                   
                                                                   
                                                                     
                                                                     
                                                                        
                                                                  
                                                                       
                                                                          
                                        
           
        return sha1(self.key().encode("utf-8")).hexdigest()[:16]