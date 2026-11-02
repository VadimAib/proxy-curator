#!/usr/bin/env python3
                                                                                 

                                                                           
                                                                             
                                                                           

       
                                                                         
                                                                              
                                                                            
                                                                             

                                                                               
                                                                            
                                                           
   
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path







sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import core.log as logmod
from core.config import Config
from core.cores import update_cores
from core.paths import rp

CONFIG = "config.yaml"


def main() -> int:




    logmod.init()
    ap = argparse.ArgumentParser(description="Update Xray / sing-box cores")
    ap.add_argument("--log-file", default=None, help="append log to file")
    ap.add_argument("--check-only", action="store_true",
                    help="only show what is new, download nothing")
    ap.add_argument("--force", action="store_true",
                    help="reinstall the current release (binary repair)")
    ap.add_argument("--yes", action="store_true",
                    help="update without asking (non-interactive run)")
    args = ap.parse_args()
    if args.log_file:
        logmod.init(args.log_file)
    try:
        cfg = Config.load(rp(CONFIG))


        assume_yes = args.yes or bool(os.environ.get("UPDATE_YES", "").strip())
        return update_cores(cfg, assume_yes=assume_yes,
                            check_only=args.check_only, force=args.force)
    except Exception as e:
        logmod.LOG(f"[cores] failed to start: {e}")
        return 1
    finally:
        logmod.LOG.close()


if __name__ == "__main__":
    raise SystemExit(main())
