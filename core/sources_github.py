                                                                          

                                                                    
                                                                       
                                                                      
                              

                                                                
                                                                      
                                                             
                                                  
import json
import socket
import time
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from .log import LOG, dlog
from .utils import first_line
from .sources_fetch import UA





_API_RETRIES = 2


_API_RETRY_SLEEP = 2.0





_API_RETRY_AFTER_MAX = 60.0


PREFER_UNION = {"all_configs_sub.txt", "all.txt"}




def _retry_after_seconds(err: HTTPError, fallback: float) -> float:
                                                                      

                                                                        
                                                         
                                                                           
                                  
       
    hdr = getattr(err, "headers", None)
    if hdr is not None:
        raw = hdr.get("Retry-After")
        if raw:
            try:
                return min(max(float(str(raw).strip()), 0.0),
                           _API_RETRY_AFTER_MAX)
            except ValueError:
                pass
        reset = hdr.get("X-RateLimit-Reset")
        if reset:
            try:
                return min(max(float(str(reset).strip()) - time.time(), 0.0),
                           _API_RETRY_AFTER_MAX)
            except ValueError:
                pass
    return min(fallback, _API_RETRY_AFTER_MAX)




def github_folder_raw_urls(api_slug: str, prefer_union: bool = True,
                           token: str = "") -> List[str]:
       
                            
                
                              
                            
                                                   
       
    api_slug = api_slug.strip('/')
    parts = api_slug.split('/')

    if len(parts) < 2:
        raise ValueError(f"invalid API slug: {api_slug}")

    owner, repo = parts[0], parts[1]
    rest = parts[2:]

    branch = None
    path = ""

    if rest and rest[0] == "contents":

        path = "/".join(rest[1:])
    elif len(rest) >= 1:

        branch = rest[0]
        path = "/".join(rest[1:])

    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    if branch:
        api_url += f"?ref={branch}"

    headers = {**UA, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"










    last_err: Optional[Exception] = None
    entries = None
    for attempt in range(_API_RETRIES + 1):
        try:
            with urlopen(Request(api_url, headers=headers), timeout=30) as r:
                entries = json.load(r)
            break
        except HTTPError as e:
            if e.code == 401 and headers.pop("Authorization", None):






                LOG("[sources] github api 401 — token rejected, retrying "
                    "without it")
                continue
            if e.code not in (403, 429) or attempt >= _API_RETRIES:
                raise

            wait = _retry_after_seconds(e, _API_RETRY_SLEEP * (attempt + 1))
            LOG(f"[sources] github api {e.code} rate-limit, retry in "
                f"{wait:.0f}s ({attempt + 1}/{_API_RETRIES})")
            time.sleep(wait)
        except (URLError, socket.timeout, OSError) as e:
            last_err = e
            if attempt < _API_RETRIES:
                time.sleep(_API_RETRY_SLEEP * (attempt + 1))
    if entries is None:
        raise last_err if last_err else RuntimeError("github api: empty response")

    if isinstance(entries, dict):

        if entries.get("type") == "file":
            return [entries.get("download_url") or
                    entries["html_url"].replace("/blob/", "/raw/")]
        raise RuntimeError(entries.get("message", "unexpected"))


    files = [e for e in entries
             if e.get("type") == "file" and e["name"].lower().endswith(".txt")]

    if prefer_union:
        hit = {e["name"].lower() for e in files} & PREFER_UNION
        if hit:
            files = [e for e in files if e["name"].lower() in hit]

    return [e.get("download_url") or e["html_url"].replace("/blob/", "/raw/")
            for e in files if e.get("download_url") or e.get("html_url")]




def resolve_sources(raw_sources: List[str], prefer_union: bool = True,
                    token: str = "",
                    errors: Optional[List[Dict[str, str]]] = None) -> List[str]:
       
                                                              
                 
                             
                                                          
                                                                                       

                                                                           
                                                                         
                                                                            
                                                                    
                                                                      
       
    out, seen = [], set()

    for src in raw_sources:
        src = src.strip()
        if not src or src.startswith("#"):
            continue


        if src.startswith(("https://github.com/", "http://github.com/")):
            try:
                parts = src.split("github.com/")[1].split("/")
                if len(parts) >= 4 and parts[2] in ("blob", "raw"):
                    user, repo, _, branch = parts[0], parts[1], parts[2], parts[3]
                    path = "/".join(parts[4:]) if len(parts) > 4 else ""
                    raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}"
                    if raw_url not in seen:
                        seen.add(raw_url)
                        out.append(raw_url)
                    continue
                elif len(parts) >= 4 and parts[2] == "tree":

                    user, repo, branch = parts[0], parts[1], parts[3]
                    path = "/".join(parts[4:]) if len(parts) > 4 else ""
                    src = f"{user}/{repo}/{branch}/{path}" if path else f"{user}/{repo}/{branch}"

            except Exception as e:

                dlog(f"parse github url {src[:60]}: {first_line(e)}")


        parsed = urlparse(src)
        if parsed.scheme in ("http", "https"):
            if src not in seen:
                seen.add(src)
                out.append(src)
            continue


        if "/" in src and " " not in src and not src.startswith("/"):
            try:
                for u in github_folder_raw_urls(src, prefer_union, token):
                    if u not in seen:
                        seen.add(u)
                        out.append(u)
            except Exception as e:
                LOG(f"[sources] FAIL {src}: {e}")
                if errors is not None:
                    errors.append({"source": src,
                                   "error": first_line(e) or type(e).__name__})

    return out

