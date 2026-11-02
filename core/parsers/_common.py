                                                                    
                                                             
   
from ..models import Security, Transport
from typing import Any, Dict, Optional, Tuple
from urllib.parse import unquote
import base64


def _b64_decode(data: str) -> str:
                                                                             

                                                                         
                                                                        
                                                                          
                                                                        
                                                                       
                
       
    flat = data.replace('\n', '').replace('\r', '').strip()
    for decoder in (base64.b64decode, base64.urlsafe_b64decode):
        for pad in ('', '=', '=='):
            try:
                return decoder((flat + pad).encode()).decode('utf-8')
            except Exception:
                continue
    raise ValueError(f"Cannot decode base64: {data[:50]}")


def _split_host_port(s: str) -> Tuple[Optional[str], Optional[int]]:
                                                                                      

                                                                       
                                                                          
                                                
       
    s = s.strip()
    if not s:
        return None, None
    try:
        if s.startswith('['):
            if ']:' not in s:
                return None, None
            host, port_s = s[1:].split(']:', 1)
        else:
            if ':' not in s:
                return None, None
            host, port_s = s.rsplit(':', 1)
        port = int(port_s)
        if not host or port <= 0 or port > 65535:
            return None, None
        return host, port
    except Exception:
        return None, None


def _parse_uri_components(rest: str) -> Tuple[str, Optional[str], Optional[int], str, str, str]:
       
                                                  
                                                                        
       

    fragment = ""
    if "#" in rest:
        rest, fragment = rest.split("#", 1)


    query_string = ""
    if "?" in rest:
        rest, query_string = rest.split("?", 1)


    url_path = ""
    if "/" in rest:
        rest, url_path = rest.split("/", 1)


    userinfo = ""
    if "@" in rest:
        userinfo, rest = rest.rsplit("@", 1)


    host, port = _split_host_port(rest)

    return userinfo, host, port, query_string, fragment, url_path


_TRANSPORT_ALIASES = {
    "h2": "http", "http2": "http",
    "gun": "grpc", "grpcgun": "grpc",
    "mkcp": "kcp", "raw": "tcp",
    "tcp": "tcp", "ws": "ws", "websocket": "ws",
    "grpc": "grpc", "http": "http",
    "httpupgrade": "httpupgrade",
    "quic": "quic", "udp": "udp",
    "splithttp": "xhttp", "xhttp": "xhttp",
}


def _transport(val: str) -> Optional[Transport]:
                                                                                  

                                                                          
                                                                           
                                                                    
                     
       
    v = (val or "tcp").strip().lower()
    canonical = _TRANSPORT_ALIASES.get(v, v)
    try:
        return Transport(canonical)
    except ValueError:
        return None


def _security(val: str) -> Optional[Security]:
                                          

                                                                             
                                                                          
                                                                        
                                           
       
    v = (val or "none").strip().lower()
    try:
        return Security(v)
    except ValueError:
        return None


def _params_to_dict(params: dict) -> dict:
                                                                                                                          
    return {k: (v[0] if len(v) == 1 else v) for k, v in params.items()}


def _truthy(val: Any) -> bool:
                                                        

                                                                            
                                                                             
                                                                 
       
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _as_int(val: Any, default: int = 0) -> int:
                                                          

                                                                            
                                                     
       
    try:
        return int(str(val).strip())
    except Exception:
        return default


_SHADOWTLS_PLUGIN = "shadow-tls"


def _shadowtls_opts(opts: str) -> Dict[str, str]:
                                                                                       
    out: Dict[str, str] = {}
    for part in str(opts or "").split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip().lower()] = v.strip()
    return out


def _attach_shadowtls(extra: Dict[str, Any], plugin: str) -> None:
                                                                                                                 
    opts = plugin.split(";", 1)[1] if ";" in plugin else ""
    o = _shadowtls_opts(opts)
    extra["plugin"] = plugin
    extra["shadow_tls"] = {
        "host": o.get("host", ""),
        "password": o.get("password", ""),
        "version": o.get("version", ""),
    }


def _join_list(val: Any) -> str:
                                                            

                                                                          
                                                                              
                                                                     
                                                          
       
    if isinstance(val, list):
        return ",".join(str(v) for v in val if v not in (None, ""))
    return "" if val in (None, "") else str(val)







WG_KEY_BYTES = 32


def normalize_wg_key(raw: Any) -> str:
                                                             

                                                                              
                                     

                                                                     
                                                                          
                                                              
                                                                      
                                                       
                                                                    

                                                                  
                                    

                                                                       
                                                                      
                                                                    
                                                                     
                                                                    
                                                                    
                        
       
    key = unquote(str(raw or "").strip()).replace(" ", "+").strip()
    if key and len(key) % 4 != 0:
        key += "=" * (-len(key) % 4)
    return key


def wg_key_decode_error(key: str) -> str:
                                                                            

                                                                        
                                                                          
                                                         

                                                                      
                                                                          
                                
       
    try:
        decoded = base64.b64decode(key, validate=True)
    except Exception:
        return "base64"
    if len(decoded) != WG_KEY_BYTES:
        return f"len={len(decoded)}"
    return ""
