                                                          

                                                                        
                                                                                
                                                                
   
import socket
from typing import List



VALID_IPV6_MODES = ("auto", "force", "off")





ERR_NO_IPV4 = "no-ipv4 (ipv6 skipped)"


def validate_ipv6_mode(value: str) -> str:
                                                                                                              
    mode = str(value or "").strip().lower()
    if mode not in VALID_IPV6_MODES:
        raise ValueError(
            f"config: testing.ipv6_mode={value!r} invalid "
            f"(valid: {', '.join(VALID_IPV6_MODES)})"
        )
    return mode


def filter_addrs(addrs: list, ipv6_mode: str, ipv6_ok: bool) -> List:
                                                             

                               
                                                    
                                                                         
       
    if ipv6_mode == "off":
        return [a for a in addrs if a[0] == socket.AF_INET]
    if ipv6_mode == "auto" and not ipv6_ok:
        return [a for a in addrs if a[0] == socket.AF_INET]
    return addrs
