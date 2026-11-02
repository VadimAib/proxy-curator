from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
import zipfile
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple
from urllib.request import Request, urlopen

from .cores_specs import CoreSpec
from .log import LOG
from .ui import ByteBar


API_RELEASES = "https://api.github.com/repos/{repo}/releases?per_page={per_page}"
DOWNLOAD_URL = "https://github.com/{repo}/releases/download/{tag}/{asset}"





API_TIMEOUT = 15
DOWNLOAD_TIMEOUT = 60
DOWNLOAD_DEADLINE = 600
CHUNK = 256 * 1024
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
API_PER_PAGE = 5

_UA = "proxy-curator (core updater)"
_SHA256_RE = re.compile(r"SHA2-256=\s*([0-9a-fA-F]{64})")


class Cancelled(Exception):
                                                                                                 

    pass



def _api_headers() -> Dict[str, str]:
                                                                                                  
    headers = {"User-Agent": _UA, "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch(url: str, timeout: int) -> bytes:
    with urlopen(Request(url, headers=_api_headers()), timeout=timeout) as r:
        return r.read()


def latest_release(repo: str, per_page: int = API_PER_PAGE) -> Tuple[str, Dict[str, int]]:
                                                                    

                                                                                
                                                                            
                                                                
       
    raw = json.loads(_fetch(API_RELEASES.format(repo=repo, per_page=per_page),
                            API_TIMEOUT).decode("utf-8", "replace"))
    for release in raw:
        if release.get("draft"):
            continue
        tag = str(release.get("tag_name") or "")
        if not tag:
            continue
        sizes = {str(a.get("name")): int(a.get("size") or 0)
                 for a in release.get("assets", [])}
        return tag, sizes
    raise ValueError(f"{repo}: response has no non-draft release")


def digest_from_dgst(text: str) -> str:
                                                                                
    m = _SHA256_RE.search(text or "")
    if not m:
        raise ValueError("no SHA2-256 line in .dgst")
    return m.group(1).lower()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def _download(url: str, dest: Path, size_hint: int = 0,
              label: str = "", *, progress: Optional[Callable[[int, int],
              None]] = None, cancel: Optional[Callable[[], bool]] = None
              ) -> None:
                                                                      

                                                                           
                                                                       
                                                                    

                                                                    
                                                                          
                                                                           
                                                                      
                                                                          
              

                                                                         
                                                                            
                                               
       
    deadline = time.monotonic() + DOWNLOAD_DEADLINE
    written = 0
    bar = ByteBar(size_hint, label or dest.name, log_progress=True)
    try:
        with urlopen(Request(url, headers={"User-Agent": _UA}),
                     timeout=DOWNLOAD_TIMEOUT) as r, open(dest, "wb") as fh:
            if not bar.total:
                bar.set_total(_content_length(r))
            while True:
                if cancel is not None and cancel():
                    raise Cancelled(label or dest.name)
                if time.monotonic() > deadline:
                    raise TimeoutError(f"download exceeded {DOWNLOAD_DEADLINE}s")
                chunk = r.read(CHUNK)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_ARCHIVE_BYTES:
                    raise ValueError(f"response larger than "
                                     f"{MAX_ARCHIVE_BYTES} bytes")
                fh.write(chunk)
                bar.add(len(chunk))
                if progress is not None:
                    progress(written, bar.total or size_hint or 0)
    finally:
        bar.finish()
    if written == 0:
        raise ValueError("server returned an empty response")
    if size_hint and written != size_hint:
        LOG(f"[cores] WARNING: archive size {written} bytes, "
            f"GitHub reported {size_hint}")


def _content_length(response) -> int:
                                                                                                          
    try:
        return max(int(response.headers.get("Content-Length") or 0), 0)
    except (AttributeError, TypeError, ValueError):
        return 0



def _extract_binary(archive: Path, spec: CoreSpec, dest_dir: Path) -> Path:
                                                                              

                                                                            
                                                                              
                                                                               
                                     
       
    with zipfile.ZipFile(archive) as z:
        names = [n for n in z.namelist()
                 if n.rsplit("/", 1)[-1].lower() == spec.binary.lower()]
        if len(names) != 1:
            raise ValueError(
                f"{spec.binary} in archive: found {len(names)}, expected 1")
        out = dest_dir / spec.binary
        with z.open(names[0]) as src, open(out, "wb") as fh:
            shutil.copyfileobj(src, fh)
    return out
