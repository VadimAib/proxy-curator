                                                                                                                  
from __future__ import annotations

import json
import os
import shutil
import tempfile
import yaml
from core.config import Config
from core.paths import ROOT, rp
from pathlib import Path
CONFIG_PATH = ROOT / "config.yaml"
CONFIG_PREV = CONFIG_PATH.with_name(CONFIG_PATH.name + ".prev")






_DEFAULT_NODES = "output/working_nodes.txt"
_DEFAULT_SUMMARY = "output/summary.json"


def artifact_paths() -> dict[str, Path]:
                                                                        

                                                                         
                                                                             
                                                                             
                                                                         

                                                                   
                                                                        
                                         

                                                                               
                                                              
                                       
       
    nodes_rel = _DEFAULT_NODES
    summary_rel = _DEFAULT_SUMMARY
    try:
        cfg = Config.load(CONFIG_PATH)
        nodes_rel = cfg.output.working_nodes or nodes_rel
        summary_rel = cfg.output.summary or summary_rel
    except Exception:
        pass
    nodes = Path(rp(nodes_rel))
    return {
        "nodes": nodes,
        "nodes_json": nodes.with_name(nodes.stem + ".json"),
        "summary": Path(rp(summary_rel)),
        "dir": nodes.parent,
    }


def _read_summary() -> dict | None:
                                                                  

                                                           
                                                                
                                                                  
                      
       
    try:
        path = rp(Config.load(CONFIG_PATH).output.summary)
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except Exception:
        return None







class ConfigError(ValueError):
    pass                                                                                                     


def validate_config_text(text: str) -> None:
                                                                     

                                                                              
                                                                        
                                                                            
                                                          
       
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML parse error: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError("top level of config.yaml must be a mapping")
    fd, name = tempfile.mkstemp(suffix=".yaml", dir=str(CONFIG_PATH.parent))
    try:



        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        Config.load(Path(name))
    except Exception as e:
        raise ConfigError(f"{type(e).__name__}: {e}") from e
    finally:
        try:
            os.unlink(name)
        except OSError:
            pass


def save_config_text(text: str) -> None:
                                                                          

                                                                        
                                                                           
                                                                   
       
    validate_config_text(text)
    if CONFIG_PATH.exists():
        try:
            shutil.copy2(CONFIG_PATH, CONFIG_PREV)
        except OSError:
            pass
    fd, name = tempfile.mkstemp(suffix=".yaml", dir=str(CONFIG_PATH.parent))
    try:




        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(name, CONFIG_PATH)
    except OSError:
        try:
            os.unlink(name)
        except OSError:
            pass
        raise


def restore_config_text() -> str:
                                                                          

                                                                           
                                                                            
                                                                          
                           
       
    if not CONFIG_PREV.exists():
        raise ConfigError("nothing to restore (no previous config)")
    text = CONFIG_PREV.read_text(encoding="utf-8")
    save_config_text(text)
    return text



