from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


_WINDOWS_AMD64 = "windows-amd64"

@dataclass(frozen=True)
class CoreSpec:
                                                                                                                         

    name: str
    repo: str
    asset: str
    binary: str
    digest: str = ""
    version_args: Tuple[str, ...] = ("version",)






CORE_SPECS: Tuple[CoreSpec, ...] = (
    CoreSpec(name="xray", repo="XTLS/Xray-core",
             asset="Xray-windows-64.zip", binary="xray.exe",
             digest="Xray-windows-64.zip.dgst"),
    CoreSpec(name="singbox", repo="SagerNet/sing-box",
             asset=f"sing-box-{{version}}-{_WINDOWS_AMD64}.zip",
             binary="sing-box.exe"),
)


@dataclass
class CorePlan:
                                                                                                                               

    name: str
    binary: Path
    label: str
    tag: str
    version: str
    asset: str
    url: str
    digest_url: str
    size: int


def spec_for(name: str) -> CoreSpec:
                                                                                         
    for spec in CORE_SPECS:
        if spec.name == name:
            return spec
    raise KeyError(f"unknown core: {name}")
