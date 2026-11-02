                                                             

                                                                       

                                                                             
                                                                      
                                                                           
                                                                            
                                                                       
                                                                     
                                                                 
                                                                         
                       

                                                         
                                                                                        
                                                         
                                                               
                                                                           
                                                    
   

import abc
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from ..models import Node
from .ports import PortPool




@dataclass
class EngineStatus:
    success: bool
    message: str = ""




class HarnessABC(abc.ABC):

                                                                                                                    





    port_pool: PortPool
    temp_dir: Path

    @abc.abstractmethod
    def generate_config(self, node: Node, local_port: int) -> Path:
                                                                                                                                          
        ...

    @abc.abstractmethod
    def generate_batch_config(self, nodes: List[Node], ports: List[int]) -> Path:
                                                                                                                            
        ...

    @abc.abstractmethod
    def get_cli_args(self, config_path: Path) -> List[str]:
                                                                                                              
        ...

    @abc.abstractmethod
    def parse_logs(self, stdout: str, stderr: str) -> EngineStatus:
                                                                                                                                 
        ...



class ConfigMixin(HarnessABC):

                                                                     

    def _mkstemp(self, prefix: str) -> Tuple[int, str]:
                                                              

                                                                         
                                                                        
                                                               

                                                                        
                                                                    
                                                                       
                                                                       
                                                                         

                                                                         
                                                                           
                                                                       
                                                               

                                                                            
                                                                   
                                                           
           
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        return tempfile.mkstemp(suffix=".json", prefix=prefix,
                                dir=str(self.temp_dir))
