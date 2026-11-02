#!/usr/bin/env python3
                                                                    

                                                                                  
                                                                       
                                                              
   



import argparse
import sys
import traceback
from typing import List, Optional

import core.log as logmod
from core.log import LOG
from core.merge import merge_working_lists
from core.pipeline import run_pipeline
from core.retest import run_retest
from core.working_lists import apply_mode, backup_previous

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Proxy Curator")
    ap.add_argument("--log-file", default=None, help="append log to file")
    ap.add_argument("--merge", action="store_true",
                    help="merge working_nodes.txt with working_nodes.prev.txt and exit")
    ap.add_argument("--backup-working", action="store_true",
                    help="copy output artifacts to *.prev.* and exit "
                         "(internal, used by run_curate.bat)")
    ap.add_argument("--apply-mode", choices=("replace", "append", "keep", "none"),
                    default=None,
                    help="apply the working-nodes decision after a run and exit "
                         "(internal, used by run_curate.bat and web/server.py)")
    ap.add_argument("--report", action="store_true", help="verbose/debug")
    ap.add_argument("--selftest", action="store_true",
                    help="sanity-check harness (xray + sing-box) and exit")
    ap.add_argument("--tcping-only", action="store_true",
                    help="fast cut without engine delay/speedtest: runs PING "
                         "+ CONNECTIVITY + DIAGNOSIS (kernels ARE started), "
                         "writes working_nodes.tcping.txt")
    ap.add_argument("--ping-only", action="store_true",
                    help="TCP/QUIC probes only (phase 4), no kernels at all, "
                         "writes working_nodes.ping.txt")
    ap.add_argument("--only", default="",
                    help="comma-separated protocols, e.g. vless,trojan")
    ap.add_argument("--retest", default="", metavar="FILE",
                    help="re-measure the nodes listed by ck in FILE right now "
                         "(one ck per line) and write fresh metrics into "
                         "working_nodes.json; feed and outputs are not touched")
    ap.add_argument("--speed-profile", default="auto",
                    choices=("auto", "full", "light"),
                    help="speed-test profile: auto-detect (default), "
                         "'full' (3MB/10s), light (1MB/5s). 'full'/'light' "
                         "override auto-detection (ROADMAP #12)")
    ap.add_argument("--auto-tune", action="store_true",
                    help="opt-in: adapt speed-test parameters (workers, "
                         "batch, payload, timeout) to the measured RTT/"
                         "jitter of the local channel instead of fixed "
                         "profile values. Complements --speed-profile: it never "
                         "disables the profile or the fingerprint cache, it "
                         "only refines the parameters around them")
    return ap

def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    args = build_parser().parse_args(argv)

    args.argv = argv




    logmod.init(args.log_file, args.report)

    try:
        if args.backup_working:
            copied = backup_previous()
            LOG(f"[stage] backup: {copied} file(s) copied to *.prev.*")
            return 0
        if args.apply_mode is not None:
            note, status = apply_mode(args.apply_mode)
            LOG(note)
            if status == "restored":
                return 2
            if status == "failed":
                return 3
            return 0
        if args.merge:
            return merge_working_lists()
        if args.retest:




            return run_retest(args)
        return run_pipeline(args)
    except KeyboardInterrupt:
        LOG("[!] interrupted")
        return 130
    except Exception:
        LOG("[!] exception:")
        for line in traceback.format_exc().splitlines():
            LOG("    " + line)
        return 1
    finally:
        LOG.close()


if __name__ == "__main__":
    sys.exit(main())
