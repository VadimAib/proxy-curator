                                                                     

                                                                         
                                                                            
                                                                       
                                

                                                                   
                                                                     
                                                                   
                     
   
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import Config
from .feed_cache import FeedCacheContext, feed_cache_context
from .engine.harness import sweep_stale_configs
from .log import LOG
from .net.netlabel import (_network_fingerprint, log_run_network,
                           resolve_run_network)
from .net.netmon import get_local_ip, measure_local_link
from .paths import ROOT, rp



from .pipeline_tune import _apply_profile_override, _auto_tune
from .engine.selftest import get_kernel_version
from .sources_cache import (cached_url_count, filter_by_age,
                           resolve_file_dates)
from .sources_github import resolve_sources






_INPUT_DROP_RATIO = 0.6


def _resolve_sources_phase(sources_file: Path, token: str, stats: Dict,
                           cache_dir: Path) -> Optional[List[str]]:
    if not sources_file.exists():
        LOG(f"ERROR: {sources_file} not found")
        return None
    raw_sources = [l.strip() for l in sources_file.read_text("utf-8").splitlines()
                   if l.strip() and not l.strip().startswith("#")]
    if not raw_sources:
        LOG(f"ERROR: {sources_file} is empty")
        return None
    source_errors: List[Dict[str, str]] = []
    urls = resolve_sources(raw_sources, True, token, source_errors)
    LOG(f"[sources] resolved {len(urls)} file URL(s)")
    if source_errors:




        stats["source_errors"] = source_errors
        stats["sources_failed"] = len(source_errors)
        LOG(f"[sources] {len(source_errors)} source(s) failed to resolve")
    prev = cached_url_count(cache_dir / "file_dates.json")
    if prev:
        stats["files_resolved_prev"] = prev
        if len(urls) < prev * _INPUT_DROP_RATIO:
            LOG(f"[sources] WARNING: resolved {len(urls)} file URL(s), "
                f"previous run had {prev} ({len(urls) * 100 // prev}%) — "
                f"check sources.txt and api.github.com reachability")
    stats["files_resolved"] = len(urls)
    return urls


def _freshness_phase(urls: List[str], cfg: Config, cache_dir: Path,
                     args, stats: Dict) -> Tuple[List[str], Optional[FeedCacheContext]]:
    LOG(f"[dates] checking freshness (max {cfg.fetching.max_age_days} days)...")
    dates = resolve_file_dates(urls, cache_dir / "file_dates.json",
                              ttl_days=7, workers=cfg.fetching.workers)
    urls, skipped = filter_by_age(urls, dates, cfg.fetching.max_age_days, args.report)
    LOG(f"[dates] {len(urls)} fresh, {len(skipped)} skipped")
    stats["files_fetched"] = len(urls)
    return urls, feed_cache_context(
        cache_dir, dates, cfg.fetching.feed_cache_enabled,
        cfg.fetching.feed_cache_ttl_hours)


def _prepare_env(cfg: Config, argv: List[str],
                 args: Any = None) -> Dict[str, Any]:
                                                                                

                                                                           
                                                                        
                                        

                                                                                   
                                                                       
                                                                         
                                                                        
                                                 
       
    xray_path = rp(cfg.xray.path)
    singbox_path = rp(cfg.singbox.path) if getattr(cfg.singbox, "path", "") else None
    sources_file = rp(cfg.fetching.sources_file)
    out_path = rp(cfg.output.working_nodes)
    summary_path = rp(cfg.output.summary)
    cache_dir = rp(cfg.output.cache_dir)
    log_dir = rp(cfg.output.log_dir)

    for d in (out_path.parent, cache_dir, log_dir, ROOT / "temp"):
        d.mkdir(parents=True, exist_ok=True)

    LOG("=" * 72)
    LOG(f"[{datetime.now():%H:%M:%S}] Proxy Curator")
    LOG(f"[env] root: {ROOT}")
    if xray_path.exists():
        LOG(f"[env] xray: {xray_path} (OK)")
        LOG(f"[env] xray version: {get_kernel_version(xray_path)}")
    else:
        LOG(f"[env] xray: {xray_path} (NOT FOUND)")
    if singbox_path is None:
        LOG("[env] singbox: not set (singbox.path in config.yaml)")
    elif singbox_path.exists():
        LOG(f"[env] singbox: {singbox_path} (OK)")
        LOG(f"[env] singbox version: {get_kernel_version(singbox_path)}")
    else:
        LOG(f"[env] singbox: {singbox_path} (NOT FOUND)")
    LOG(f"[env] args: {' '.join(argv)}")
    LOG("=" * 72)








    stale = sweep_stale_configs([ROOT / "temp"])
    if stale:
        LOG(f"[env] removed orphaned engine configs: {len(stale)}")

    local_ip = get_local_ip()
    stats: Dict[str, Any] = {
        "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "xray": str(xray_path),
        "singbox": str(singbox_path or ""),
        "args": list(argv),





        "run_network": "",







        "local_ip": local_ip,
        "network_fingerprint": _network_fingerprint(local_ip),





        "local_link": None,
    }



    if args is not None:
        _apply_profile_override(args, stats)
    stats["run_network"] = resolve_run_network(stats)




    if getattr(args, "auto_tune", False):
        link = stats.get("local_link")
        if not (isinstance(link, (list, tuple)) and len(link) == 2):
            try:
                measured = measure_local_link()
            except Exception:
                measured = None
            if measured is not None:
                link = [round(float(measured[0]), 1),
                        round(float(measured[1]), 1)]
                stats["local_link"] = link
        if isinstance(link, (list, tuple)) and len(link) == 2:
            try:
                stats["auto_tune"] = _auto_tune(float(link[0]),
                                                float(link[1]))
            except (TypeError, ValueError):
                pass
    log_run_network(stats)
    return {
        "xray_path": xray_path, "singbox_path": singbox_path,
        "sources_file": sources_file, "out_path": out_path,
        "summary_path": summary_path, "cache_dir": cache_dir,
        "stats": stats,
    }

