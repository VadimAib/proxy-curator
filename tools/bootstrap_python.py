#!/usr/bin/env python3
                                                                        

                                                                          
                                                                              
                                                                     
                                                                              
                                                   

                                                                              
                                                                        
                                                                        

                          
                                                                        
                                                                         
                                                                          
                                  
                                                                          
                                                                          
                                                                       
                                           

       
                                                                              
                                                                            
                                                                        

                                                                         
                                                                         
   
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import sysconfig
import urllib.request
import zipfile
from pathlib import Path







sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.log as logmod

DEFAULT_PYYAML_VERSION = "6.0.2"
PYPI_JSON_URL = "https://pypi.org/pypi/PyYAML/{version}/json"
HTTP_TIMEOUT_S = 30
PTH_SITE_PACKAGES = r"Lib\site-packages"





PTH_PROJECT_ROOT = ".."


class BootstrapError(RuntimeError):
    pass                                                                                                                        







def _pth_file(py_dir: Path) -> Path | None:
                                                                                                      
    matches = sorted(py_dir.glob("python*._pth"))
    return matches[0] if matches else None


def _pth_site_enabled(text: str) -> bool:
                                                                                      
    for line in text.splitlines():
        if line.strip().replace(" ", "").lower() == "importsite":
            return True
    return False


def ensure_site(py_dir: Path) -> bool:
                                                             

                                                                           
                                                                            
                 
       
    pth = _pth_file(py_dir)
    if pth is None:
        raise BootstrapError(
            f"no pythonXY._pth in {py_dir} (not an embeddable Python?)")
    lines = pth.read_text(encoding="utf-8").splitlines()

    def _has_path(entry: str) -> bool:
        return any(line.strip().replace("/", "\\").lower() == entry.lower()
                   for line in lines)

    has_sp = _has_path(PTH_SITE_PACKAGES)
    has_root = _has_path(PTH_PROJECT_ROOT)
    out: list[str] = []
    for line in lines:
        compact = line.strip().replace(" ", "").lower()
        if compact == "#importsite":
            out.append("import site")
        else:
            out.append(line)


    has_site = _pth_site_enabled("\n".join(out))
    changed = False
    for present, entry in ((has_site, "import site"),
                           (has_sp, PTH_SITE_PACKAGES),
                           (has_root, PTH_PROJECT_ROOT)):
        if not present:
            out.append(entry)
            changed = True
    if changed:
        pth.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed







def site_packages(py_dir: Path) -> Path:
    return py_dir / "Lib" / "site-packages"


def _wheel_tag() -> tuple[str, str]:
                                                                            
    v = sys.version_info
    abi = f"cp{v.major}{v.minor}"
    plat = sysconfig.get_platform().replace("-", "_").replace(".", "_")
    return abi, plat


def select_wheel(urls: list[dict], abi: str, plat: str) -> dict | None:
                                                                                                             
    for entry in urls:
        name = entry.get("filename", "")
        if name.endswith(".whl") and abi in name and plat in name:
            return entry
    return None


def _http_bytes(url: str) -> bytes:
                                                                                                                              
    with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT_S) as resp:
        return resp.read()


def _fetch_urls(version: str) -> list[dict]:
                                                                                      
    meta = json.loads(_http_bytes(PYPI_JSON_URL.format(version=version)).decode("utf-8"))
    return list(meta.get("urls", []))


def install_pyyaml(py_dir: Path, version: str, urls: list[dict] | None = None) -> Path:
                                                                     

                                                                         
                                
       
    site = site_packages(py_dir)
    site.mkdir(parents=True, exist_ok=True)
    abi, plat = _wheel_tag()
    files = urls if urls is not None else _fetch_urls(version)
    wheel = select_wheel(files, abi, plat)
    if wheel is None:
        raise BootstrapError(
            f"PyYAML {version}: no wheel for {abi}/{plat} on PyPI")
    data = _http_bytes(wheel["url"])
    expected = (wheel.get("digests") or {}).get("sha256", "")
    actual = hashlib.sha256(data).hexdigest()
    if expected and actual != expected:


        raise BootstrapError(
            f"PyYAML {version}: sha256 mismatch (PyPI {expected[:12]}…, "
            f"file {actual[:12]}…)")
    tmp = py_dir / "_pyyaml_tmp.whl"
    tmp.write_bytes(data)
    try:
        with zipfile.ZipFile(tmp) as zf:
            for member in zf.namelist():
                top = member.split("/")[0]
                if member.startswith("yaml/") or top.startswith("_yaml"):
                    zf.extract(member, site)
    finally:
        tmp.unlink(missing_ok=True)
    return site


def is_ready(py_dir: Path) -> bool:
                                                                                                             
    pth = _pth_file(py_dir)
    if pth is None or not _pth_site_enabled(pth.read_text(encoding="utf-8")):
        return False
    return (site_packages(py_dir) / "yaml" / "__init__.py").is_file()


def _pyyaml_version() -> str:
    return os.environ.get("PYYAML_VERSION", "").strip() or DEFAULT_PYYAML_VERSION







def main(argv: list[str] | None = None) -> int:
    logmod.init()
    ap = argparse.ArgumentParser(
        description="Bootstrap the embeddable runtime (site + PyYAML into py\\\\)")
    ap.add_argument("--py-dir", required=True,
                    help="embeddable Python directory (contains python.exe)")
    ap.add_argument("--version", default=None,
                    help=f"PyYAML version (default {DEFAULT_PYYAML_VERSION} "
                         "or env PYYAML_VERSION)")
    ap.add_argument("--check", action="store_true",
                    help="only check readiness, change nothing")
    ap.add_argument("--force", action="store_true",
                    help="reinstall PyYAML even if already installed")
    args = ap.parse_args(argv)

    py_dir = Path(args.py_dir)
    version = args.version or _pyyaml_version()
    try:
        if not (py_dir / "python.exe").is_file():
            raise BootstrapError(f"missing {py_dir / 'python.exe'}")
        if args.check:
            ok = is_ready(py_dir)
            logmod.LOG(f"[bootstrap] runtime {'ready' if ok else 'NOT ready'}: "
                       f"{py_dir}")
            return 0 if ok else 1
        if is_ready(py_dir) and not args.force:
            logmod.LOG(f"[bootstrap] runtime already ready: {py_dir}")
            return 0
        if ensure_site(py_dir):
            logmod.LOG("[bootstrap] _pth: enabled import site and "
                       "Lib\\site-packages")
        site = install_pyyaml(py_dir, version)
        logmod.LOG(f"[bootstrap] PyYAML {version} installed into {site}")
        return 0
    except BootstrapError as e:
        logmod.LOG(f"[bootstrap] ERROR: {e}")
        return 1
    except Exception as e:
        logmod.LOG(f"[bootstrap] ERROR: {e!r}")
        return 1
    finally:
        logmod.LOG.close()


if __name__ == "__main__":
    raise SystemExit(main())
