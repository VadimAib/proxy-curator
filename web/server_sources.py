                                                                                                              
from __future__ import annotations

import re
import shutil
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = ROOT / "sources.txt"
SOURCES_PREV = SOURCES_PATH.with_name(SOURCES_PATH.name + ".prev")




_sources_lock = threading.Lock()









import re as _re_sources

class SourcesError(ValueError):
                                                                            

                                                                           
                                                                              
                                            
       

    def __init__(self, msg: str, code: str = "", detail: str = "") -> None:
        super().__init__(msg)
        self.code = code
        self.detail = detail


def _sources_error_body(e: SourcesError) -> dict:
                                                                                                                    
    body: dict = {"error": str(e)}
    if e.code:
        body["code"] = e.code
    if e.detail:
        body["detail"] = e.detail
    return body


def _classify_source(line: str) -> str:
                                                                                
    s = line.strip()
    if s.startswith(("https://github.com/", "http://github.com/")):
        return "github"
    if s.startswith(("http://", "https://")):
        return "raw"
    if "/" in s and " " not in s and s[0].isalpha():
        return "slug"
    return "unknown"


def _validate_source_line(line: str) -> None:
                                                                                                                            
    s = line.strip()
    if not s or s.startswith("#"):
        return
    typ = _classify_source(s)
    if typ in ("raw", "github", "slug"):
        return
    raise SourcesError(
        f"invalid source: {s[:80]!r} (expected URL or GitHub slug)",
        code="invalid", detail=s[:80],
    )


def parse_sources_text(text: str) -> dict:
                                               

                                               
                                                                   
            
                                        
                                                                    
                                                                    
                                    
       
    URL_DIS = _re_sources.compile(r"^(https?://[^\s]+)$")
    DIV = _re_sources.compile(r"^#\s*===\s*(.*?)\s*===\s*$")
    sections: list = []
    cur_title = ""
    pending_comment = ""

    def _ensure_section():
        if not sections:
            sections.append({"title": cur_title, "items": []})
        return sections[-1]["items"]

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        dm = DIV.match(stripped)
        if dm:
            cur_title = dm.group(1)
            sections.append({"title": cur_title, "items": []})


            continue

        if stripped.startswith("#"):
            body = stripped.lstrip("#").strip()
            um = URL_DIS.match(body)
            if um:
                url = um.group(1)
                _validate_source_line(url)
                _ensure_section().append({
                    "url": url, "enabled": False,
                    "comment": pending_comment,
                    "type": _classify_source(url),
                })
                pending_comment = ""
            else:
                pending_comment += ("\n" if pending_comment else "") + body
            continue

        _validate_source_line(stripped)
        _ensure_section().append({
            "url": stripped, "enabled": True,
            "comment": pending_comment,
            "type": _classify_source(stripped),
        })
        pending_comment = ""

    if not sections:
        sections.append({"title": "", "items": []})


    if pending_comment and sections:
        last_items = sections[-1].get("items", [])
        if last_items:
            last_items[-1]["comment"] = (
                (last_items[-1].get("comment") or "") + "\n" + pending_comment
            ).strip()
    return {"sections": sections}


def serialize_sources_text(data: dict) -> str:
                                                                      
                                                                                                                    
    lines: list = []
    for sec in data.get("sections", []):
        items = sec.get("items", [])
        if not items:
            continue
        if sec.get("title"):
            lines.append("")
            lines.append(f"# === {sec['title']} ===")
        for item in sec.get("items", []):
            url = (item.get("url") or "").strip()
            comment = (item.get("comment") or "").strip()
            if not url:
                continue
            if comment:
                for cline in comment.splitlines():
                    lines.append(f"# {cline}")
            lines.append(url if item.get("enabled", True) else f"# {url}")
            lines.append("")
    return "\n".join(lines).strip("\n") + "\n"


def load_sources_data() -> dict:
                                                                                                     
    with _sources_lock:
        try:
            text = SOURCES_PATH.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
    return parse_sources_text(text)


def save_sources_data(data: dict) -> None:
                                                                              
    with _sources_lock:
        seen: set[str] = set()
        for sec in data.get("sections", []):
            for item in sec.get("items", []):
                url = (item.get("url") or "").strip()
                if not url:
                    continue
                _validate_source_line(url)
                if url in seen:
                    raise SourcesError(
                        f"duplicate source: {url}", code="duplicate", detail=url,
                    )
                seen.add(url)

                item["enabled"] = bool(item.get("enabled", True))
        new_text = serialize_sources_text(data)
        if SOURCES_PATH.exists():
            try:
                shutil.copy2(SOURCES_PATH, SOURCES_PREV)
            except OSError:
                pass
        tmp = SOURCES_PATH.with_name(SOURCES_PATH.name + ".tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_text)
        tmp.replace(SOURCES_PATH)


def restore_sources_text() -> str:
                                                                                            
    if not SOURCES_PREV.exists():
        raise SourcesError("no previous version to restore", code="no_backup")
    new_text = SOURCES_PREV.read_text(encoding="utf-8")
    tmp = SOURCES_PATH.with_name(SOURCES_PATH.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_text)
    tmp.replace(SOURCES_PATH)
    return new_text
