                                                            

                                                                               
                                                                         
                                                                        

                                                                           
                                              
                                                                                    
                                                            
                                                                           
                                                                                   

                                                                                       
                                                                         
                                                            

                                                                
                                                                     
                                                           
                                                                 
                                                           
                                                                          
                                                                    
                                                               

                                                                
                          
                                                                          
                                                                       
   

import abc
import time
from pathlib import Path
from typing import List, Optional

from .harness_batch import BatchMixin
from .harness_config import ConfigMixin
from .harness_config import EngineStatus
from .harness_process import CREATE_NO_WINDOW
from .harness_run import RunMixin
from ..log import dlog
from ..paths import ROOT
from .ports import PortPool
from ..utils import first_line






ENGINE_CONFIG_PREFIXES = ("xray_", "singbox_")




STALE_CONFIG_AGE_SEC = 24 * 3600


def sweep_stale_configs(dirs: List[Path],
                        max_age_sec: int = STALE_CONFIG_AGE_SEC
                        ) -> List[str]:
                                                                            

                                                                           
                                                                         
                                                                       
                                                                      
                                                 

                                                                       
                                                                           
                                                                      
                                                                      
                                                 

                                                                           
                                                                   
       
    removed: List[str] = []
    cutoff = time.time() - max_age_sec
    for directory in dirs:
        try:
            entries = list(Path(directory).iterdir())
        except OSError:

            continue
        for entry in entries:
            if not entry.name.startswith(ENGINE_CONFIG_PREFIXES):
                continue
            try:
                if entry.stat().st_mtime >= cutoff:
                    continue
                entry.unlink()
            except OSError as e:
                dlog(f"sweep_stale_configs: {entry} not removed "
                     f"({first_line(e)})")
                continue
            removed.append(str(entry))
    return removed





class BaseEngine(RunMixin, BatchMixin, ConfigMixin, abc.ABC):

                                                      

                                                                     
                                                                          
                                                                  
                                                                     
                                             

                                                                            
                                                                           
                                                                        
                                                                         
                                                                        
                                                                         
   

    ENGINE_NAME: str = "engine"

    def __init__(self, port_pool: PortPool, temp_dir: Optional[Path] = None):
        self.port_pool = port_pool





        self.temp_dir = temp_dir or (ROOT / "temp")

    @classmethod
    def from_config(cls, port_pool: PortPool, kernel_cfg) -> 'BaseEngine':
                                                               

                                                                           
                                                                        
                                                               
           
        return cls(port_pool)
