                                                                     

                                                                 
                                                                                                           
import base64
import re
from dataclasses import dataclass, field
from typing import List
from urllib.request import Request, urlopen
from .models import Node
from .parsers import parse_config_text
from .utils import first_line

FORMAT_JSON = "json"


FORMAT_YAML = "yaml"


FORMAT_URI = "uri"


FORMAT_UNKNOWN = "unknown"



_YAML_SECTION_RE = re.compile(r"^[ \t]*(proxies|proxy-groups)[ \t]*:", re.I | re.M)


_URI_LINE_RE = re.compile(r"^[a-z][a-z0-9+.\-]*://", re.I)





UA = {"User-Agent": "v2rayN/7.x"}




def http_get(url: str, timeout: int = 30) -> bytes:
    with urlopen(Request(url, headers=UA), timeout=timeout) as r:
        return r.read()




def _b64_any(data: bytes) -> bytes:
    flat = b"".join(data.split())
    last_err = None
    for fn in (base64.b64decode, base64.urlsafe_b64decode):
        for pad in (b"", b"=", b"=="):
            try:
                return fn(flat + pad)
            except Exception as e:
                last_err = e
    raise ValueError(f"not base64: {last_err}")





def detect_content_format(text: str) -> str:
                                                                             

                       
                                                                  
                                                                 
                                                               
       
    if not text:
        return FORMAT_UNKNOWN
    if text.lstrip("\ufeff \t\r\n").startswith("{"):
        return FORMAT_JSON
    if _YAML_SECTION_RE.search(text):
        return FORMAT_YAML
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "//")):
            continue
        if _URI_LINE_RE.match(line):
            return FORMAT_URI
    return FORMAT_UNKNOWN




def decode_payload(data: bytes) -> str:
                                                                                                
    text = data.decode("utf-8", "replace")
    if detect_content_format(text) != FORMAT_UNKNOWN:
        return text
    try:
        decoded = _b64_any(data).decode("utf-8")
    except Exception:
        return text
    return decoded if detect_content_format(decoded) != FORMAT_UNKNOWN else text




def extract_uri_links(text: str) -> List[str]:
                                                                                                           
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line and "://" in line and not line.startswith(("#", "//")):
            out.append(line)
    return out




@dataclass
class Subscription:
                                                                                            
    url: str = ""
    fmt: str = FORMAT_UNKNOWN
    nodes: List[Node] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    error: str = ""
    sample: str = ""




def parse_subscription(text: str, url: str = "") -> Subscription:
                                                                                                  
    fmt = detect_content_format(text)
    sub = Subscription(url=url, fmt=fmt)

    if fmt == FORMAT_URI:
        sub.links = extract_uri_links(text)
    elif fmt in (FORMAT_JSON, FORMAT_YAML):
        try:
            sub.nodes = parse_config_text(text, fmt)
        except Exception as e:
            sub.error = f"{fmt}: {first_line(e, 140)}"
            sub.sample = " ".join(text.split())[:160]
    else:
        sub.error = "unknown: not URI list / sing-box JSON / Clash YAML"
        sub.sample = " ".join(text.split())[:160]
    return sub




def fetch_subscription(url: str, timeout: int = 30) -> Subscription:
                                                                                                                                      
    sub = parse_subscription(decode_payload(http_get(url, timeout=timeout)), url)
    if sub.error:
        tail = url.rsplit("/", 1)[-1][:40]
        sub.error = f"{sub.error} <{tail}>"
    return sub

