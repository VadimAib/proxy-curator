                                               

                                                                        
                                                                               
                                                                              
                                                                   
                                                                    

                                                                               
                                                                        
                       

                                                                       
                                                                        
                                                                    
                                                              
                                                               

                                                                                                                                                                                                                                                  
   
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

from ..feed_cache import (FEED_CACHE_FILE, FeedCacheContext,
                          load_feed_cache, prune_feed_cache,
                          save_feed_cache)
from ..log import LOG
from ..models import Node
from ..sources_fetch import FORMAT_URI, Subscription
from .fetch_one import _CACHE_NOTES, _fetch_one_feed, _sub_summary
from ..state import PipelineState



_PERMANENT_FETCH_CODES = frozenset({401, 403, 404, 410})


def _is_permanent_fetch_error(exc: BaseException) -> bool:
                                                             

                                                                           
                                                                        
                                                                        
                                                                 
                                                    
       
    code = getattr(exc, "code", None)
    return code in _PERMANENT_FETCH_CODES


def fetch_and_sample_links(state: PipelineState, urls: List[str], max_links: int,
                           workers: int, report: bool, timeout: int = 30,
                           feed_cache: Optional[FeedCacheContext] = None
                           ) -> None:
                                                                         

                      
                                                                  
                                                                    
                                                          
                                   
                                                               
                                                              
                                                                         
                                                           
                                  
                                                                         
                                                                   
                                                                  
                                    
                                                                 
                                                                
                                                                    
                                                                 
                        

                                                                     
                                                                   
                                                                       
       
    LOG(f"[fetch] fetching {len(urls)} files...")
    cache = (load_feed_cache(feed_cache.cache_dir / FEED_CACHE_FILE)
             if feed_cache is not None else None)
    subs: List[Tuple[Subscription, str]] = []
    failed: List[str] = []
    permanent_failures = 0
    cache_hits = 0
    hash_hits = 0

    def _log_sub(sub: Subscription, url: str, note: str = "") -> None:
        tag = "" if sub.fmt == FORMAT_URI else f"  [{sub.fmt}]"
        LOG(f"[fetch] {_sub_summary(sub):>8}  {url.rsplit('/', 1)[-1]}{tag}{note}",
            console=report)

    def _submit(ex: "ThreadPoolExecutor", targets: List[str]) -> Dict:
        return {ex.submit(_fetch_one_feed, u, timeout, cache, feed_cache): u
                for u in targets}

    def _count(note: str) -> None:
        nonlocal cache_hits, hash_hits
        if note == "feed-cache":
            cache_hits += 1
        elif note == "hash-cache":
            hash_hits += 1

    with ThreadPoolExecutor(workers) as ex:
        futs = _submit(ex, urls)
        for f in as_completed(futs):
            u = futs[f]
            try:
                sub, note = f.result()
                _count(note)
                subs.append((sub, u))
                _log_sub(sub, u, _CACHE_NOTES.get(note, ""))
            except Exception as e:
                if _is_permanent_fetch_error(e):




                    permanent_failures += 1
                    LOG(f"[fetch] FAIL {u.rsplit('/', 1)[-1]}: {e} "
                        f"(not retrying: server response)")
                    continue
                LOG(f"[fetch] FAIL {u.rsplit('/', 1)[-1]}: {e} (retrying once)")
                failed.append(u)

    if failed:
        time.sleep(2)
        with ThreadPoolExecutor(min(workers, len(failed))) as ex:
            futs = _submit(ex, failed)
            for f in as_completed(futs):
                u = futs[f]
                try:
                    sub, note = f.result()
                    _count(note)
                    subs.append((sub, u))
                    _log_sub(sub, u, _CACHE_NOTES.get(note, "") + " (retry ok)")
                except Exception as e:
                    LOG(f"[fetch] FAIL {u.rsplit('/', 1)[-1]}: {e} (after retry)")

    all_links: List[str] = []
    link_source: Dict[str, str] = {}
    config_nodes: List[Node] = []
    samples: List[str] = []
    fmt_counts: Dict[str, int] = {}
    seen = set()
    for sub, u in subs:
        fmt_counts[sub.fmt] = fmt_counts.get(sub.fmt, 0) + 1
        for l in sub.links:
            if l not in seen:
                seen.add(l)
                all_links.append(l)




                link_source[l] = u
                state.bump_feed(u, "links")
        if sub.nodes:


            for node in sub.nodes:
                node.extra["src"] = u
            config_nodes.extend(sub.nodes)
            state.bump_feed(u, "config_nodes", len(sub.nodes))
        if sub.error:
            samples.append(f"[{sub.error}] {sub.sample}")

    total = len(all_links)
    if max_links and max_links > 0 and total > max_links:
        LOG(f"[fetch] WARNING: {total} links exceeds max_links={max_links}, truncating")
        all_links = all_links[:max_links]
    formats = ", ".join(f"{k}:{v}" for k, v in sorted(fmt_counts.items()))
    LOG(f"[fetch] {total} unique links + {len(config_nodes)} config nodes "
        f"({formats})")
    if samples:
        LOG(f"[fetch] {len(samples)} subscription(s) failed to parse")
    state.links = all_links
    state.config_nodes = config_nodes
    state.samples = samples
    state.link_source = link_source
    state.stats.update({
        "links_total": total, "links_unique": len(all_links),
        "config_nodes": len(config_nodes), "subscriptions": fmt_counts,
        "fetch_errors": len(failed),
        "fetch_errors_permanent": permanent_failures,
        "feed_cache_hits": cache_hits,
        "feed_cache_hash_hits": hash_hits,
    })
    if cache is not None and feed_cache is not None:


        pruned = prune_feed_cache(cache, urls, feed_cache.ttl_hours)
        save_feed_cache(feed_cache.cache_dir / FEED_CACHE_FILE, pruned)
        LOG(f"[fetch] feed cache: {cache_hits} served, {hash_hits} "
            f"content-unchanged, {len(pruned)} entries kept", console=report)
