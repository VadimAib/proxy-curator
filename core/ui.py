                                                             

                                                      

                                                                          
                                                                      
                                                                          
                                                 
                                                                             
                                       

                                                                 
                                                                      
                                                                      
                                                                       
                                                                        
                                                           

                                                                        
                                                                     
                                                                     
                                    
   
import threading
import time

from .log import CONSOLE, LOG


def _progress(line: str, interactive: bool = False) -> None:
                                                                                  

                                                                         
                                                                    
                                                                             
                                                                     
                                                                                 
                                                                 

                                                                           
                                                                         
                

                                                                            
                                                                          
                                                                        
                     

                                                                       
                                                                       
                                                                        
                                                                         
                                                                  
                                                                 
       
    LOG(line, console=not interactive)


def fmt_dur(sec: float) -> str:
                                                                                                 
    sec = int(max(0, sec))
    if sec < 60:
        return f"{sec}s"
    m, s = divmod(sec, 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m"


def fmt_bytes(n: float) -> str:
                                                    

                                                                           
                                                                        
                             
       
    n = float(max(0.0, n))
    if n < 1024:
        return f"{int(n)} B"
    for unit in ("KB", "MB", "GB"):
        n /= 1024.0
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}"
    return f"{n:.1f} GB"


class ProgressBar:
                                                                                

                                                                            
                                                                      
                                                                  

                                                                     
                                                                        
                                            
                                                                           
                                                                       
                                                            
                                                                     
                                                                          
                                                                           
                                                                        
                                                                        
                                                                        
       



    LOG_STEPS_MAX = 50

    def __init__(self, total: int, label: str, log_progress: bool = False,
                 unit: str = "", show_ok: bool = True):
        self.total = max(total, 1)
        self.label = label
        self.unit = unit
        self.show_ok = show_ok
        self.done = 0
        self.ok = 0
        self.start = time.time()
        self._lock = threading.Lock()
        self._log_progress = log_progress
        self._last_logged = 0

    def begin(self) -> None:
                                                                                

                                                                              
                                                                    
                                                           

                                                                             
                                                                      
                                                                    
                                                                          
                                                                              
                                                                               
                                                     
           
        with self._lock:
            self._render()
            if self._log_progress:
                _progress(self._render_line(), CONSOLE.interactive)

    def update(self, ok: bool = False) -> None:
        with self._lock:
            self.done += 1
            if ok:
                self.ok += 1











            over_total = self.done > self.total
            should_log = self._log_progress and not over_total and (
                self.done == 1
                or self.done == self.total
                or self.done - self._last_logged >= self._log_step()
            )
            if should_log:
                self._last_logged = self.done
            self._render()
            if should_log:
                _progress(self._render_line(), CONSOLE.interactive)

    def _log_step(self) -> int:
                                                                              

                                                                             
                                                                           
                                                                            
                                                                         
                                                                          
                                                                          
                             
           
        return max(1, -(-self.total // self.LOG_STEPS_MAX))

    def add_total(self, n: int) -> None:
        with self._lock:
            self.total += n

    def set_total(self, n: int) -> None:
                                                                 

                                                                            
                                                                      
                                                                    
                                                                  
           
        with self._lock:
            self.total = max(n, 1)

    def _render(self) -> None:
        line = self._render_line()
        CONSOLE.bar(line)

    def _render_line(self) -> str:
        done, total = self.done, self.total
        elapsed = time.time() - self.start
        rate = done / elapsed if elapsed > 0 else 0
        eta = (total - done) / rate if rate > 0 else 0
        pct = min(100, done * 100 // total)
        bar_len = 24
        filled = bar_len * done // total
        bar = "#" * filled + "." * (bar_len - filled)


        counted = f"{done}/{total}" + (f" {self.unit}" if self.unit else "")



        ok = f" ok={self.ok}" if self.show_ok else ""
        return f"[{self.label}] [{bar}] {pct:>3}% {counted}{ok} " \
               f"elapsed={fmt_dur(elapsed)} ETA={fmt_dur(eta)}"

    def finish(self) -> None:
        with self._lock:
            self._render()
            CONSOLE.bar_clear()
            if self._log_progress:
                _progress(self._render_line(), CONSOLE.interactive)


class ByteBar:
                                                          

                                                                            
                                                                     
                                                                        
                                                              

                                                                          
                                                 
       

    BAR_LEN = 24


    LOG_STEP_PCT = 10

    def __init__(self, total: int, label: str, log_progress: bool = False):
        self.total = max(int(total or 0), 0)
        self.label = label
        self.done = 0
        self.start = time.time()
        self._lock = threading.Lock()
        self._log_progress = log_progress
        self._last_logged_pct = 0
        self._logged_unknown = False

    def add(self, n: int) -> None:
                                                                                                                                
        if n <= 0:
            return
        with self._lock:
            self.done += n
            self._render()
            if self._log_progress and self._step_crossed():
                _progress(self._render_line(), CONSOLE.interactive)

    def _step_crossed(self) -> bool:
                                                             

                                                                             
                                                                 
                                                                        
                              
           
        if not self.total:

            if self._logged_unknown:
                return False
            self._logged_unknown = True
            return True
        pct = self._pct()
        if (pct // self.LOG_STEP_PCT) <= (self._last_logged_pct
                                          // self.LOG_STEP_PCT):
            return False
        self._last_logged_pct = pct
        return True

    def _pct(self) -> int:
        if not self.total:
            return 0
        return min(100, self.done * 100 // self.total)

    def set_total(self, n: int) -> None:
                                                                  

                                                                           
                                                                          
                                                                         
                                           
           
        with self._lock:
            self.total = max(int(n or 0), 0)

    def _render(self) -> None:
        CONSOLE.bar(self._render_line())

    def _render_line(self) -> str:
        elapsed = time.time() - self.start
        rate = self.done / elapsed if elapsed > 0 else 0.0
        if not self.total:
            track = "?" * self.BAR_LEN
            return (f"[{self.label}] [{track}] {fmt_bytes(self.done)} "
                    f"{fmt_bytes(rate)}/s elapsed={fmt_dur(elapsed)}")
        pct = self._pct()
        filled = min(self.BAR_LEN, self.BAR_LEN * self.done // self.total)
        bar = "#" * filled + "." * (self.BAR_LEN - filled)
        eta = (self.total - self.done) / rate if rate > 0 else 0.0
        return (f"[{self.label}] [{bar}] {pct:>3}% "
                f"{fmt_bytes(self.done)}/{fmt_bytes(self.total)} "
                f"{fmt_bytes(rate)}/s elapsed={fmt_dur(elapsed)} "
                f"ETA={fmt_dur(eta)}")

    def finish(self) -> None:
                                                                           
                                                                     
        with self._lock:
            CONSOLE.bar(self._render_line())
            CONSOLE.bar_clear()
            if self._log_progress:
                _progress(self._render_line(), CONSOLE.interactive)
