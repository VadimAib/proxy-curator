                                                                              

                                                                     
                                                                                  
                                                                                     
                                                                           
                                                                  
                                                                 
   

import ipaddress
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

from .harness import BaseEngine, EngineStatus
from ..log import DEBUG
from ..models import Node
from .ports import PortPool
from ..utils import first
from .xray_fp import REALITY_FINGERPRINTS, _resolve_fingerprint

VALID_ALPN = {"h2", "http/1.1", "h3"}

VALID_FLOWS = {"xtls-rprx-vision"}

VALID_VMESS_SCY = {"aes-128-gcm", "chacha20-poly1305", "auto", "none", "zero"}

VALID_PACKET_ENCODING = {"packet", "xudp"}







REALITY_NETWORKS = frozenset({"tcp", "grpc", "xhttp", "splithttp"})


_BANNER_LINES = (
    "penetrates everything",
    "a unified platform for anti-censorship",
    "xray",
    "reading config",
    "v2ray",
)


_ERR_PREFIX_RE = re.compile(
    r'^(?:Failed to start:\s*)?main:\sfailed to load config files:\s[.?]\s>\s*'
)

_INFRA_RE = re.compile(r'(?:infra/conf:\s*)+')



def _is_ip(s: str) -> bool:
    try:
        ipaddress.ip_address(s.strip("[]"))
        return True
    except Exception:
        return False



def _clean_hostname(val: str, fallback: str = "") -> str:
    v = (val or "").strip()
    if "://" in v:
        v = v.split("://", 1)[1]
    v = v.split("#", 1)[0].split("/", 1)[0]
    v = v.split("?", 1)[0].split(",", 1)[0].strip().strip(".")
    return v or fallback



def _clean_path(val: str) -> str:
    v = (val or "").strip().split("#", 1)[0].strip()
    if not v:
        return "/"
    if not v.startswith("/"):
        v = "/" + v
    return v.replace(" ", "%20")



def _clean_alpn(val: str) -> List[str]:
    toks = [t.strip() for t in (val or "").replace("|", ",").split(",")]
    out, seen = [], set()
    for t in toks:
        if t in VALID_ALPN and t not in seen:
            seen.add(t)
            out.append(t)
    return out



class XrayEngine(BaseEngine):
                                                                      

    ENGINE_NAME = "xray"

    def __init__(self, port_pool: PortPool, use_xhttp_name: bool = False):
        super().__init__(port_pool)
        self.use_xhttp_name = use_xhttp_name

    def generate_config(self, node: Node, local_port: int) -> Path:
        cfg = self._make_dict(node, local_port)
        fd, path = self._mkstemp("xray_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        return Path(path)

    def generate_batch_config(self, nodes: List[Node], ports: List[int]) -> Path:
                                                                                                                                   
        if len(nodes) != len(ports):
            raise ValueError("generate_batch_config: nodes and ports length mismatch")
        inbounds = []
        outbounds = []
        for i, (node, _port) in enumerate(zip(nodes, ports)):
            ob = self._make_dict(node, 0)["outbounds"][0]
            ob["tag"] = f"ob-{i}"
            outbounds.append(ob)
            inbounds.append({
                "listen": "127.0.0.1",
                "port": _port,
                "protocol": "http",
                "settings": {"timeout": 5},
                "tag": f"ib-{i}",
            })




        rules = []
        for i in range(len(nodes)):
            rules.append({
                "network": "tcp,udp",
                "inboundTag": [f"ib-{i}"],
                "outboundTag": f"ob-{i}",
            })

        rules.append({"network": "tcp,udp", "outboundTag": "direct"})
        cfg = {
            "log": {"loglevel": "none"},
            "inbounds": inbounds,
            "outbounds": outbounds + [{"protocol": "freedom", "tag": "direct"}],
            "routing": {"rules": rules},
        }
        fd, path = self._mkstemp("xray_batch_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        return Path(path)

    def get_cli_args(self, config_path: Path) -> List[str]:
        return ["-config", str(config_path)]

    def parse_logs(self, stdout: str, stderr: str) -> EngineStatus:
        lines_out = stdout.strip().splitlines()
        lines_err = stderr.strip().splitlines()

        if not DEBUG:
            lines_out = self._filter_lines(lines_out)
            lines_err = self._filter_lines(lines_err)

        if lines_err:
            err_msg = " | ".join(lines_err[-2:])
        elif lines_out:
            err_msg = lines_out[-1]
        else:
            err_msg = ""

        if err_msg:
            err_msg = _ERR_PREFIX_RE.sub('', err_msg).strip()
            err_msg = _INFRA_RE.sub('', err_msg).strip()
            return EngineStatus(success=False, message=err_msg[:400])
        return EngineStatus(success=True)

    @classmethod
    def from_config(cls, port_pool: PortPool, kernel_cfg) -> 'XrayEngine':
                                                                          
        return cls(port_pool, use_xhttp_name=bool(
            getattr(kernel_cfg, "use_xhttp_name", False)))

    def _filter_lines(self, lines: List[str]) -> List[str]:
        out = []
        for line in lines:
            low = line.lower()
            if any(b in low for b in _BANNER_LINES):
                continue
            if "[warning]" in line or "[info]" in line:
                continue
            if "is deprecated" in low:
                continue
            if line.strip():
                out.append(line.strip())
        return out

    def _stream(self, n: Node) -> Tuple[str, str]:
                                                                      

                                                                        
                                                                          
           
        net = n.transport.value.lower()
        if net in ("h2", "http2"):
            net = "http"
        elif net in ("gun", "grpcgun"):
            net = "grpc"
        elif net in ("xhttp", "splithttp"):
            net = "xhttp" if self.use_xhttp_name else "splithttp"

        sec = n.security.value.lower() or "none"
        if sec == "reality" and net not in REALITY_NETWORKS:








            net = "tcp"
        return net, sec

    def _sni(self, n: Node, sni_raw: str) -> str:
                                                                                            
        return _clean_hostname(sni_raw, n.host if not _is_ip(n.host) else "")

    def _tls(self, n: Node, stream: Dict, sec: str, sni: str, cget) -> None:
                                                                            

                                                                           
                                              
           
        net = stream["network"]
        if sec == "tls":






            tls: Dict = {"insecure": True}
            if sni:
                tls["serverName"] = sni
            fp = cget("fp", "")
            if fp:
                tls["fingerprint"] = _resolve_fingerprint(fp)
            alpn_raw = cget("alpn", "")
            if alpn_raw and net in ("tcp", "grpc", "http"):
                tls["alpn"] = _clean_alpn(alpn_raw)
            stream["tlsSettings"] = tls
        elif sec == "reality":



            fp = _resolve_fingerprint(cget("fp", ""),
                                      allowed=REALITY_FINGERPRINTS)
            stream["realitySettings"] = {
                "serverName": sni or n.host,
                "publicKey": cget("pbk", "").strip(),
                "shortId": cget("sid", "").strip(),
                "fingerprint": fp,
            }

    def _transport(self, stream: Dict, net: str, cget, vhost: str) -> None:
                                                                                         
        if net == "ws":
            ws: Dict = {"path": _clean_path(cget("path", "/"))}
            if vhost:
                ws["headers"] = {"Host": vhost}
            stream["wsSettings"] = ws
        elif net == "grpc":
            sn = (cget("serviceName", "") or cget("path", ""))
            sn = sn.split("#", 1)[0].strip().lstrip("/")
            stream["grpcSettings"] = {"serviceName": sn or "grpc"}
        elif net == "http":
            hs: Dict = {"path": _clean_path(cget("path", "/"))}
            if vhost:
                hs["host"] = [vhost]
            stream["httpSettings"] = hs
        elif net == "httpupgrade":
            hu = {"path": _clean_path(cget("path", "/"))}
            if vhost:
                hu["host"] = vhost
            stream["httpupgradeSettings"] = hu
        elif net in ("splithttp", "xhttp"):
            sh = {"path": _clean_path(cget("path", "/"))}
            if vhost:
                sh["host"] = vhost
            mode = cget("mode", "")
            if mode:
                sh["mode"] = mode
            stream["xhttpSettings" if net == "xhttp" else "splithttpSettings"] = sh
        elif net == "kcp":
            stream["kcpSettings"] = {}
        elif net == "quic":
            stream["quicSettings"] = {}

    def _vhost(self, cget, sni_raw: str) -> str:
                                                                         

                                                                         
           
        host_raw = cget("host", "")
        vhost = _clean_hostname(host_raw, "")
        if not vhost and not host_raw:
            cand = _clean_hostname(sni_raw, "")
            if cand and not _is_ip(cand):
                vhost = cand
        return vhost

    def _vless(self, ob: Dict, n: Node, net: str, cget,
               stream: Dict) -> None:
                                                              

                                                                  
                                                                        
                                                            
           
        uid = cget("__userinfo", "")
        if not uid:
            uid = n.raw.split("://", 1)[1].split("@", 1)[0]
        user = {"id": uid.strip(), "encryption": "none"}
        flow = cget("flow", "").strip()
        if flow in VALID_FLOWS and net == "tcp":
            user["flow"] = flow
        settings = {"vnext": [{"address": n.host, "port": n.port, "users": [user]}]}
        pe = cget("packetEncoding", "").lower()
        if pe in VALID_PACKET_ENCODING:
            settings["packetEncoding"] = pe
        ob["settings"] = settings
        ob["streamSettings"] = stream

    def _make_dict(self, n: Node, local_port: int) -> Dict:
                                                                                            
        net, sec = self._stream(n)
        stream = {"network": net, "security": sec}

        def cget(key: str, default: str = "") -> str:
            return first(n.extra, key, default)

        sni_raw = cget("sni", "") or cget("servername", "")
        sni = self._sni(n, sni_raw)
        self._tls(n, stream, sec, sni, cget)
        self._transport(stream, net, cget, self._vhost(cget, sni_raw))

        proto = "shadowsocks" if n.protocol.value == "ss" else n.protocol.value
        ob = {"protocol": proto, "settings": {}}

        if n.protocol.value == "vless":
            self._vless(ob, n, net, cget, stream)
        else:
            self._outbound_settings(ob, n, cget, stream)

        return {
            "log": {"loglevel": "none"},
            "inbounds": [{
                "listen": "127.0.0.1",
                "port": local_port,
                "protocol": "http",
                "settings": {"timeout": 5},
            }],
            "outbounds": [ob, {"protocol": "freedom", "tag": "direct"}],
        }

    def _outbound_settings(self, ob: Dict, n: Node, cget,
                           stream: Dict) -> None:
                                                                           

                                                                             
                                                          
           
        if n.protocol.value == "trojan":
            pwd = cget("__userinfo", "")
            if not pwd:
                pwd = n.raw.split("://", 1)[1].split("@", 1)[0]
            ob["settings"] = {"servers": [{"address": n.host, "port": n.port, "password": pwd.strip()}]}
            ob["streamSettings"] = stream
        elif n.protocol.value == "vmess":
            try:
                aid = max(0, int(cget("aid", "0") or 0))
            except Exception:
                aid = 0
            scy = cget("scy", "auto").lower()
            if scy not in VALID_VMESS_SCY:
                scy = "auto"
            settings = {
                "vnext": [{
                    "address": n.host,
                    "port": n.port,
                    "users": [{"id": cget("id", "").strip(), "alterId": aid, "security": scy}],
                }]
            }
            pe = cget("packetEncoding", "").lower()
            if pe in VALID_PACKET_ENCODING:
                settings["packetEncoding"] = pe
            ob["settings"] = settings
            ob["streamSettings"] = stream
        elif n.protocol.value == "ss":
            ob["settings"] = {
                "servers": [{
                    "address": n.host,
                    "port": n.port,
                    "method": cget("method", ""),
                    "password": cget("password", ""),
                }]
            }

