                                                       

                                                                       

                                                                        
                                                                         
                                                                         
                                                                         
                                                                    

                                  
                                                                            
                                                                         
                                                             
                                                                    
                                                                             
                                                                                
   

import re
import socket
import subprocess
import time
from pathlib import Path
from typing import List, Optional

from .harness_config import HarnessABC
from ..log import dlog
from ..utils import first_line
from .winjob import assign_to_job




CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)



class ProcessMixin(HarnessABC):

                                                                                                   

    def _spawn(self, config_path: Path,
               binary_path: str) -> subprocess.Popen:
                                                              

                                                                    
                                                                               
                                                                                     
                                                                        
                                                                             
           
        proc = subprocess.Popen(
            [binary_path] + self.get_cli_args(config_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW,
        )
        assign_to_job(proc)
        return proc

    def _wait_port(self, proc: subprocess.Popen, port: int,
                   connect_timeout: float = 0.1) -> bool:
                                                                       

                                                                            
                                                                         
                                                                                
                                                    
           
        for _ in range(40):
            if proc.poll() is not None:
                break
            try:
                with socket.create_connection(("127.0.0.1", port),
                                              timeout=connect_timeout):
                    return True
            except Exception:
                time.sleep(0.05)
        return False

    def _wait_ports(self, proc: subprocess.Popen, ports: List[int]) -> bool:
                                                                            

                                                                   
                                                                           
                                                      
           
        for _ in range(40):
            if proc.poll() is not None:
                break
            if any(self._try_connect("127.0.0.1", p) for p in ports):
                return True
            time.sleep(0.05)
        return False

    def _stop_process(
        self,
        proc: subprocess.Popen,
        used_port: Optional[int] = None,
    ) -> str:
                                                                                                                                                          
        if not proc:
            return ""

        if proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                try:
                    proc.wait(timeout=1.0)
                except Exception as e:
                    dlog(f"kill+wait failed: {first_line(e)}")
            except Exception as e:
                dlog(f"stop_process({type(proc).__name__}) failed: {first_line(e)}")

        err_msg = ""
        try:
            out, err = proc.communicate(timeout=1.0)
            out_str = (out or b"").decode("utf-8", "replace").strip()
            err_str = (err or b"").decode("utf-8", "replace").strip()
            status = self.parse_logs(out_str, err_str)
            if not status.success and status.message:
                err_msg = status.message
        except Exception as e:


            dlog(f"communicate/parse_logs failed: {first_line(e)}")
















        if used_port and self.port_pool:
            try:
                self.port_pool.release_port(used_port)
            except Exception as e:
                dlog(f"release_port({used_port}) on stop: {first_line(e)}")
        return err_msg

    def _trim_err(self, s: str) -> str:
        if not s:
            return ""
        s = re.sub(r'^(?:Failed to start:\s*)?main:\sfailed to load config files:\s[.?]\s>\s*', '', s).strip()
        s = re.sub(r'(?:infra/conf:\s*)+', '', s).strip()
        return s[:400]

    @staticmethod
    def _try_connect(host: str, port: int, timeout: float = 0.05) -> bool:
                                                                                      
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            return False
