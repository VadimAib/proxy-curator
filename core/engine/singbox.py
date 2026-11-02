                                                          

                                                                                    
                                                                       
              
   
import json
import os
import re
from pathlib import Path
from typing import Dict, List

from .harness import BaseEngine, EngineStatus
from ..models import Node
from .ports import PortPool
from ..utils import first


_VALID_CC = {"cubic", "new_reno", "bbr"}
_VALID_UDP_RELAY = {"native", "quic"}


def _mbps(val: str) -> int:
                                                                              
    m = re.match(r"\s*(\d+)", str(val or ""))
    return int(m.group(1)) if m else 0


class SingBoxEngine(BaseEngine):
                                                                                                    

    ENGINE_NAME = "singbox"

    def __init__(self, port_pool: PortPool):
        super().__init__(port_pool)

    def generate_config(self, node: Node, local_port: int) -> Path:
        cfg = self._make_dict(node, local_port)
        fd, path = self._mkstemp("singbox_")
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
                "type": "http",
                "tag": f"ib-{i}",
                "listen": "127.0.0.1",
                "listen_port": _port,
            })







        cfg = {
            "log": {"level": "error"},
            "inbounds": inbounds,
            "outbounds": outbounds,
            "route": {"rules": [
                {"inbound": [f"ib-{i}"], "action": "route", "outbound": f"ob-{i}"}
                for i in range(len(nodes))
            ]},
        }
        fd, path = self._mkstemp("singbox_batch_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        return Path(path)

    def get_cli_args(self, config_path: Path) -> List[str]:
        return ["run", "-c", str(config_path)]

    def parse_logs(self, stdout: str, stderr: str) -> EngineStatus:



        _ERR_RE = re.compile(r'^(ERROR|FATAL)\[', re.IGNORECASE)


        for line in reversed(stdout.strip().splitlines()):
            if _ERR_RE.match(line.strip()):
                return EngineStatus(success=False, message=line.strip()[:400])


        for line in reversed(stderr.strip().splitlines()):
            stripped = line.strip()
            if stripped and _ERR_RE.match(stripped):
                return EngineStatus(success=False, message=stripped[:400])

        return EngineStatus(success=True)

    def _make_dict(self, n: Node, local_port: int) -> Dict:
                                                                      

                                                                                 
                                                                         
                                                                       
           
        cfg: Dict = {
            "log": {"level": "error"},
            "inbounds": [
                {
                    "type": "http",
                    "tag": "http-in",
                    "listen": "127.0.0.1",
                    "listen_port": local_port,
                }
            ],
            "outbounds": [],
        }

        tls = {
            "enabled": True,
            "server_name": first(n.extra, "sni", n.host),
            "insecure": True,
            "alpn": ["h3"],
        }

        if n.protocol.value == "hysteria2":
            ob: Dict = {
                "type": "hysteria2",
                "tag": "proxy",
                "server": n.host,
                "server_port": n.port,
                "password": first(n.extra, "password", ""),
                "tls": tls,
                "up_mbps": _mbps(first(n.extra, "up")),
                "down_mbps": _mbps(first(n.extra, "down")),
            }
            obfs_type = first(n.extra, "obfs")
            obfs_pwd = first(n.extra, "obfs-password")
            if obfs_type and obfs_pwd:




                ob["obfs"] = {"type": obfs_type, "password": obfs_pwd}
            cfg["outbounds"].append(ob)
        if n.protocol.value == "anytls":




            ob = {
                "type": "anytls",
                "tag": "proxy",
                "server": n.host,
                "server_port": n.port,
                "password": first(n.extra, "password", ""),
                "tls": {
                    "enabled": True,
                    "server_name": first(n.extra, "sni", n.host),
                    "insecure": True,
                },
            }
            cfg["outbounds"].append(ob)
        elif n.protocol.value == "tuic":
            ob = {
                "type": "tuic",
                "tag": "proxy",
                "server": n.host,
                "server_port": n.port,
                "uuid": first(n.extra, "uuid", ""),
                "password": first(n.extra, "password", ""),
                "tls": tls,
            }
            cc = first(n.extra, "congestion_control")
            if cc in _VALID_CC:
                ob["congestion_control"] = cc
            urm = first(n.extra, "udp_relay_mode")
            if urm in _VALID_UDP_RELAY:
                ob["udp_relay_mode"] = urm
            cfg["outbounds"].append(ob)

        return cfg



