                                                                          

                                                                          
                                                                          
                                                                         
                                               
   
import os
import sys
import time
import shutil
import threading
import ctypes
from ctypes import wintypes


_k32 = getattr(ctypes, "windll", None)
if _k32 is not None:
    try:
        _k32.GetStdHandle.argtypes = [wintypes.DWORD]
        _k32.GetStdHandle.restype = wintypes.HANDLE
        _k32.WriteConsoleW.argtypes = [
            wintypes.HANDLE, wintypes.LPCWSTR, wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID,
        ]
        _k32.WriteConsoleW.restype = wintypes.BOOL
    except Exception:
        _k32 = None

_STD_OUTPUT_HANDLE = wintypes.DWORD(0xFFFFFFF5)
_CONSOLE_W_OK = _k32 is not None


def _console_w_enabled() -> bool:
                                                                                                          
    global _CONSOLE_W_OK
    if not _CONSOLE_W_OK:
        return False
    try:
        if not sys.stdout.isatty():
            _CONSOLE_W_OK = False
    except Exception:
        _CONSOLE_W_OK = False
    return _CONSOLE_W_OK


def _force_console_font(face: str = "Consolas", size: int = 14) -> None:
                                                                      
                                                                                                             
    try:
        class _CONSOLE_FONT_INFOEX(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("nFont", ctypes.c_ulong),
                ("dwFontSizeX", ctypes.c_short),
                ("dwFontSizeY", ctypes.c_short),
                ("FontFamily", ctypes.c_uint),
                ("FontWeight", ctypes.c_uint),
                ("FaceName", ctypes.c_wchar * 32),
            ]

        k32 = ctypes.windll.kernel32
        k32.GetStdHandle.restype = wintypes.HANDLE
        k32.GetCurrentConsoleFontEx.argtypes = [
            wintypes.HANDLE, wintypes.BOOL,
            ctypes.POINTER(_CONSOLE_FONT_INFOEX)]
        k32.SetCurrentConsoleFontEx.argtypes = [
            wintypes.HANDLE, wintypes.BOOL,
            ctypes.POINTER(_CONSOLE_FONT_INFOEX)]

        h = k32.GetStdHandle(wintypes.DWORD(0xFFFFFFF5))
        if not h:
            return
        info = _CONSOLE_FONT_INFOEX()
        info.cbSize = ctypes.sizeof(info)
        if not k32.GetCurrentConsoleFontEx(h, False, ctypes.byref(info)):
            return
        info.dwFontSizeX = 0
        info.dwFontSizeY = size
        info.FontFamily = 0x36
        info.FontWeight = 400
        info.FaceName = face
        k32.SetCurrentConsoleFontEx(h, False, ctypes.byref(info))
    except Exception:
        pass


def _write_console_w(text: str) -> bool:
                                                                                                       




    if not text or _k32 is None or not _console_w_enabled():
        return False
    try:
        h = _k32.GetStdHandle(_STD_OUTPUT_HANDLE)
        if not h:
            return False
        written = wintypes.DWORD(0)
        return bool(_k32.WriteConsoleW(h, text, len(text),
                                       ctypes.byref(written), None))
    except Exception:
        return False


def _force_utf8_console() -> None:
                                                                     
                                                                                                        
    try:
        k32 = ctypes.windll.kernel32
        k32.SetConsoleOutputCP(65001)
        k32.SetConsoleCP(65001)
    except Exception:
        pass
    for s in (sys.stdout, sys.stderr):




        reconfigure = getattr(s, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace",
                        line_buffering=True)
        except Exception:
            pass
    _force_console_font()

def _write_bytes(data: bytes) -> None:
                                                                                                                       
    text = data.decode("utf-8", "replace")
    if _write_console_w(text):
        return
    buf = getattr(sys.stdout, "buffer", None)
    if buf is not None:
        try:
            buf.write(data)
            buf.flush()
            return
        except Exception:
            pass
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except Exception:
        pass


class Console:
                                                                                                                             

    def __init__(self):
        self._lock = threading.Lock()
        self._bar = 0
        self._tty = bool(getattr(sys.stdout, "isatty", lambda: False)()) or os.environ.get("CURATE_FORCE_TTY") == "1"

    @property
    def interactive(self) -> bool:
                                                                             

                                                                    
                                                                            
                                                                        
                                                            
                                 
           
        return self._tty

    @staticmethod
    def _width() -> int:
        try:
            return max(40, shutil.get_terminal_size((100, 24)).columns - 1)
        except Exception:
            return 99

    def _erase(self):
        if self._bar:
            _write_bytes(("\r" + " " * self._bar + "\r").encode("utf-8"))
            self._bar = 0

    def line(self, msg=""):
        with self._lock:
            self._erase()
            _write_bytes((str(msg) + "\n").encode("utf-8"))

    def bar(self, text):
        if not self._tty:
            return
        with self._lock:
            self._erase()
            text = text[:self._width()]
            _write_bytes(text.encode("utf-8"))
            self._bar = len(text)

    def bar_clear(self):
        with self._lock:
            self._erase()


CONSOLE = Console()


class Logger:
    def __init__(self):
        self.fh = None


        self._lock = threading.Lock()

    def open(self, path):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            self.fh = open(path, "a", encoding="utf-8", newline="\n")
        except OSError as e:
            CONSOLE.line(f"[log] cannot open {path}: {e}")

    def __call__(self, msg="", console=True):
        line = str(msg)
        with self._lock:
            if console:
                CONSOLE.line(line)
            if self.fh:
                try:
                    self.fh.write(f"{time.strftime('%H:%M:%S')} {line}\n")
                    self.fh.flush()
                except Exception:
                    pass

    def close(self):
        if self.fh:
            try:
                self.fh.close()
            except Exception:
                pass
            self.fh = None


LOG = Logger()
DEBUG = False


def dlog(msg):
    if DEBUG:
        LOG(f"      [debug] {msg}", console=False)


def init(path=None, debug=False):
    global DEBUG
    _force_utf8_console()
    if path:
        LOG.open(path)
    DEBUG = debug