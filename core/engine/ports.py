                                                                                     
import socket
import threading
import time
from typing import List


class PortPool:
    def __init__(self, size: int = 30):
        self.size = size
        self._ports: List[int] = []
        self._available: List[int] = []
        self._in_use: set = set()
        self._lock = threading.Lock()
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._ports = [self._get_free_port() for _ in range(self.size)]
        self._available = list(self._ports)
        self._in_use = set()
        self._initialized = True

    def _get_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def _is_free(self, port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return True
        except OSError:
            return False

    def get_port(self) -> int:
        if not self._initialized:
            self.initialize()


        deadline = time.time() + 5.0
        while time.time() < deadline:
            with self._lock:

                checked = 0
                while self._available and checked < len(self._ports):
                    port = self._available.pop(0)
                    checked += 1
                    if port in self._in_use:


                        self._available.append(port)
                        continue
                    if self._is_free(port):
                        self._in_use.add(port)
                        return port









                    self._available.append(port)


            time.sleep(0.05)


        port = self._get_free_port()
        with self._lock:
            self._ports.append(port)
            self._in_use.add(port)
        return port

    def release_port(self, port: int) -> None:
        with self._lock:
            if port in self._in_use:
                self._in_use.discard(port)
                if port in self._ports and port not in self._available:
                    self._available.append(port)



_shared_pool: PortPool | None = None
_shared_pool_lock = threading.Lock()


def get_shared_pool(size: int = 30) -> PortPool:
                                                               

                                                                    
                                                                 
       
    global _shared_pool
    if _shared_pool is not None:
        return _shared_pool
    with _shared_pool_lock:
        if _shared_pool is not None:
            return _shared_pool
        pool = PortPool(size)
        pool.initialize()
        _shared_pool = pool
        return pool