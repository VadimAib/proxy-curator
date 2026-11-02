                                                     

                                                                       

                                                       

                                                                              
                                                                            
                                                                             
         
                                                                      
                                                                             
                                                                                  
                                                                             

                                                         
                                                               
                                                                         
                                                 
                                                                    
   


import contextlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple
from ..config import TestUrlConfig
from .httptest import http_test
from ..log import dlog
from ..models import Node
from ..utils import first_line
from .harness_config import ConfigMixin
from .harness_process import ProcessMixin


class RunMixin(ProcessMixin, ConfigMixin):

                                                                                            

    @contextlib.contextmanager
    def probe_session(self, node: Node, binary_path: str,
                      local_port: int) -> Iterator[subprocess.Popen]:
                                                                     

                                                                              
                                                                              
                                                                         
                                                                               
                                                                               
                                                       
                                                             
                                  

                 
                                                                             
                                                      
                                                                             
                                                           
                                                                              
                                                                       
                                                               
                                                                               
                                                   

                                                                       
                                
           
        config_path = self.generate_config(node, local_port)
        proc: Optional[subprocess.Popen] = None
        try:
            proc = self._spawn(config_path, binary_path)
            if not self._wait_port(proc, local_port):
                self._stop_process(proc, None)
                proc = None
                dlog(f"{self.__class__.__name__} config: {config_path}")
                raise RuntimeError("engine_failed_to_start")
            yield proc
        finally:
            if proc is not None:
                self._stop_process(proc, None)


            try:
                if config_path.is_dir():
                    shutil.rmtree(config_path, ignore_errors=True)
                else:
                    os.unlink(config_path)
            except Exception:
                pass

    def run_test(
        self,
        node_or_cfg: Node | Dict | Path,
        binary_path: str,
        local_port: int,
        timeout: float,
        connectivity_urls: List[TestUrlConfig],
        bypass_urls: List[TestUrlConfig],
        critical_urls: List[TestUrlConfig],
        critical_timeout: Optional[float] = None,
        connectivity_timeout: Optional[float] = None,
        bypass_timeout: Optional[float] = None,
        critical_mode: str = "all",
    ) -> Tuple[Optional[float], Optional[str], Dict]:
                                                                                

                                                                          
                                                                             

                                                                         
                                                                        
                                    

                                                                             
                                                                                       
                                                                              
                                                                         
                                                                              
           
        timings: Dict[str, float] = {}
        if isinstance(node_or_cfg, Node):
            config_path = self.generate_config(node_or_cfg, local_port)
        elif isinstance(node_or_cfg, Path):
            config_path = node_or_cfg
        else:
            fd, path = self._mkstemp(f"{self.__class__.__name__.lower()}_")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(node_or_cfg, f)
            config_path = Path(path)
        proc = None
        try:
            t0 = time.time()
            proc = self._spawn(config_path, binary_path)
            timings["spawn"] = (time.time() - t0) * 1000

            t0 = time.time()
            port_open = self._wait_port(proc, local_port)
            timings["wait_port"] = (time.time() - t0) * 1000

            if not port_open:
                err = self._stop_process(proc, local_port)
                proc = None
                dlog(f"{self.__class__.__name__} config: {config_path}")
                return None, self._trim_err(err or "engine_failed_to_start"), timings

            t0 = time.time()
            test_err = http_test(
                local_port, connectivity_urls, bypass_urls, critical_urls, timeout,
                critical_timeout, connectivity_timeout, bypass_timeout, critical_mode
            )
            timings["http"] = (time.time() - t0) * 1000

            if test_err is None:
                return timings["http"], None, timings

            err = self._stop_process(proc, local_port)
            proc = None
            if err:
                test_err = f"{test_err} | {err}"
            dlog(f"{self.__class__.__name__} config: {config_path}")
            return None, test_err[:400], timings

        except Exception as e:
            dlog(f"{self.__class__.__name__} config: {config_path}")
            return None, self._trim_err(first_line(e)), timings
        finally:
            if proc:
                self._stop_process(proc, local_port)


            try:
                if config_path.is_dir():
                    shutil.rmtree(config_path, ignore_errors=True)
                else:
                    os.unlink(config_path)
            except Exception:
                pass
