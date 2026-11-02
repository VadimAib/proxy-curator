                                                                                                                                         
from __future__ import annotations

import secrets
from urllib.parse import urlsplit






_UI_API_TOKEN = secrets.token_hex(16)



def _origin_allowed(origin: str | None, referer: str | None, expected: str) -> bool:
                                                           

                                                                       
                                                             

                                                                        
                                                                
                                                                  
                                             
       
    for value in (origin, referer):
        if not value:
            continue
        if value.rstrip("/") == expected:
            return True
        parsed = urlsplit(value)
        if f"{parsed.scheme}://{parsed.netloc}" == expected:
            return True
    return False


def _token_valid(token: str | None) -> bool:
                                                            
    if not token:
        return False
    return secrets.compare_digest(token, _UI_API_TOKEN)




_DESTRUCTIVE_ROUTES = frozenset({"/api/logs/delete"})
