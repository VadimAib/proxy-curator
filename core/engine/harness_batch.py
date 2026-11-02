                                                     

                                                                       

                                                                         
                                                                             
                                                                
                                      

                                                                             
                                                                             
                
   

import os
import shutil
import time
from typing import Iterator, List, Optional, Tuple

from .harness_process import ProcessMixin
from ..config import TestUrlConfig
from .httptest import http_test
from ..log import DEBUG, dlog
from ..models import Node
from ..utils import first_line

class BatchMixin(ProcessMixin):

                                                                                                                                  

    def run_batch_test(
        self,
        nodes: List[Node],
        ports: List[int],
        binary_path: str,
        timeout: float,
        connectivity_urls: List[TestUrlConfig],
        bypass_urls: List[TestUrlConfig],
        critical_urls: List[TestUrlConfig],
        critical_timeout: Optional[float] = None,
        connectivity_timeout: Optional[float] = None,
        bypass_timeout: Optional[float] = None,
        critical_mode: str = "all",
        connectivity_only: bool = False,
    ) -> Iterator[Tuple[Node, int, Optional[float], Optional[str]]]:
                                                  

                                                                         
                                                                      
                                                             
           
        if len(nodes) != len(ports):
            raise ValueError("run_batch_test: nodes and ports must be equal length")
        if connectivity_only:
            bypass_urls, critical_urls = [], []

        config_path = self.generate_batch_config(nodes, ports)
        proc = None
        try:
            t0 = time.time()
            proc = self._spawn(config_path, binary_path)


            t0 = time.time()
            port_open = self._wait_ports(proc, ports)

            if not port_open:
                err = self._stop_process(proc, ports[0] if ports else None)
                proc = None
                dlog(f"{self.__class__.__name__} batch config: {config_path}")
                reason = self._trim_err(err or "engine_failed_to_start")
                for node, port in zip(nodes, ports):
                    yield node, port, None, reason
                return


            for i, (node, port) in enumerate(zip(nodes, ports)):
                if proc.poll() is not None:
                    for n, p in zip(nodes[i:], ports[i:]):
                        yield n, p, None, "engine_crashed_mid_batch"
                    break

                if DEBUG and len(nodes) > 10 and i > 0 and i % 10 == 0:
                    dlog(f"[{self.__class__.__name__}] batch progress: {i}/{len(nodes)} ports tested")

                t0 = time.time()
                err = http_test(
                    port, connectivity_urls, bypass_urls, critical_urls, timeout,
                    critical_timeout, connectivity_timeout, bypass_timeout, critical_mode
                )
                ms = (time.time() - t0) * 1000 if err is None else None

                yield node, port, ms, err

        except Exception as e:
            dlog(f"{self.__class__.__name__} batch config: {config_path}")
            err_msg = self._trim_err(first_line(e))
            for n, p in zip(nodes, ports):
                yield n, p, None, err_msg
        finally:
            if proc:
                self._stop_process(proc, ports[0] if ports else None)
            try:
                if config_path.is_dir():
                    shutil.rmtree(config_path, ignore_errors=True)
                else:
                    os.unlink(config_path)
            except Exception:
                pass
