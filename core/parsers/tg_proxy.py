                                                                            

                                                                                                                   
                                                                      
                                                                        
                                                                   
                                                                      
   
from urllib.parse import parse_qs, quote, unquote

from ..models import Node, Protocol, Security, Transport
from ..utils import first
from ._common import _params_to_dict
from typing import Optional


def parse_tg_proxy(url: str, rest: str) -> Optional[Node]:
                                                                                       

                                                                       
                                                                  
                                                                          
                                                                      
                                                                           
                                                          

                                                                      
                                                                     
                                                                     
                                                                
       
    path, _, query = rest.partition("?")
    host_path = path.lower().strip("/")
    if host_path not in ("proxy", "t.me/proxy"):
        return None


    query, _, frag = query.partition("#")
    params = _params_to_dict(parse_qs(query))


    server = first(params, "server").rstrip(".")
    if not server:
        return None
    port_raw = first(params, "port")
    if not port_raw:
        port = 443
    else:
        try:
            port = int(port_raw)
        except ValueError:
            return None
        if not 1 <= port <= 65535:
            return None
    secret = first(params, "secret")
    qs = f"server={quote(server, safe='')}&port={port}"
    if secret:
        qs += f"&secret={quote(secret, safe='')}"
    return Node(
        protocol=Protocol.MTPROTO, raw=f"https://t.me/proxy?{qs}",
        name=unquote(frag), host=server, port=port, security=Security.TLS,
        transport=Transport.TCP, extra={"secret": secret},
    )
