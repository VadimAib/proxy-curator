                                                       

                                      
                                                                                   
                                                                                

                                                                          
                                                                      
                                                                                
                    

                                                                         
                                                                 

                                                                           
                                                                   
                                                                    
                                                                             
                                                                     
   
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Type

from .harness import BaseEngine
from ..log import LOG
from ..models import Node, Protocol
from .ports import PortPool
from .singbox import SingBoxEngine
from .xray import XrayEngine


ENGINES: Dict[Protocol, Type[BaseEngine]] = {
    Protocol.VLESS: XrayEngine,
    Protocol.VMESS: XrayEngine,
    Protocol.TROJAN: XrayEngine,
    Protocol.SHADOWSOCKS: XrayEngine,
    Protocol.HYSTERIA2: SingBoxEngine,
    Protocol.TUIC: SingBoxEngine,


    Protocol.ANYTLS: SingBoxEngine,
}


@dataclass
class EngineRuntime:
                                                                                               
    name: str
    engine: BaseEngine
    binary: Optional[Path] = None
    enabled: bool = True

    def available(self) -> bool:
        return bool(self.enabled and self.binary and self.binary.exists())


def engine_name_for(node: Node) -> str:
                                                                                                     
    cls = ENGINES.get(node.protocol)
    return cls.ENGINE_NAME if cls else ""


def split_nodes(nodes: List[Node]) -> Dict[str, List[Node]]:
                                                                                                                            
    groups: Dict[str, List[Node]] = {}
    for n in nodes:
        cls = ENGINES.get(n.protocol)
        if cls is None:
            continue
        groups.setdefault(cls.ENGINE_NAME, []).append(n)
    return groups


def build_engines(port_pool: PortPool, cfg,
                  resolve: Optional[Callable[[str], Path]] = None
                  ) -> Dict[str, EngineRuntime]:
                                                                       

                                                                                   
                                                                     
                                                                     
       
    res: Callable[[str], Path] = resolve or (lambda p: Path(p))
    specs = (
        (XrayEngine, getattr(cfg, "xray", None)),
        (SingBoxEngine, getattr(cfg, "singbox", None)),
    )
    out: Dict[str, EngineRuntime] = {}
    for cls, kernel_cfg in specs:
        if kernel_cfg is None:
            continue
        raw = str(getattr(kernel_cfg, "path", "") or "")
        rt = EngineRuntime(
            name=cls.ENGINE_NAME,
            engine=cls.from_config(port_pool, kernel_cfg),
            binary=res(raw) if raw else None,
            enabled=bool(getattr(kernel_cfg, "enabled", True)),
        )
        out[rt.name] = rt
        if not rt.enabled:
            LOG(f"[engines] {rt.name}: disabled in config.yaml")
        elif not rt.available():
            LOG(f"[engines] {rt.name}: binary not found ({rt.binary})")
    return out
