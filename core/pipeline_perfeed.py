                                                                

                                                                                                                   
                                                                 
                                                                   
                                                                            
                                                 
                                                                   
                         
   
from typing import Dict, List, Tuple

from .log import LOG
from .models import Node




_ZERO_YIELD_MIN = 200


_PER_FEED_KEYS = ("links", "config_nodes", "survive", "tcping_alive",
                  "working")


def build_per_feed(feed_stats: Dict[str, Dict[str, int]],
                   final: List[Tuple[Node, float]]) -> Dict[str, Dict[str, int]]:
                                                                          

                                                       
                                                                        
                                                                   
                                                                 
                                                                   
                                                                  

                                                                  
                                                                   
                                                       
       
    per_feed: Dict[str, Dict[str, int]] = {
        url: dict(counts) for url, counts in feed_stats.items()}
    for n, _ in final:
        src = (getattr(n, "extra", None) or {}).get("src")
        if src:
            row = per_feed.setdefault(src, {})
            row["working"] = row.get("working", 0) + 1
    for row in per_feed.values():
        for key in _PER_FEED_KEYS:
            row.setdefault(key, 0)
    return dict(sorted(per_feed.items(),
                       key=lambda kv: (-kv[1].get("links", 0), kv[0])))


def _log_per_feed(per_feed: Dict[str, Dict[str, int]]) -> None:
                                                                      

                                                                       
                                                                     
                                                                       
                                                                   
                          
       
    if not per_feed:
        return
    with_out = sum(1 for r in per_feed.values() if r.get("working"))
    zero = [url for url, r in per_feed.items()
            if r.get("links", 0) + r.get("config_nodes", 0) >= _ZERO_YIELD_MIN
            and not r.get("working")]
    note = (f"; zero-yield (>= {_ZERO_YIELD_MIN} links): {len(zero)}"
            if zero else "")
    LOG(f"[per_feed] {len(per_feed)} feeds, {with_out} with working nodes"
        + note)
    for url in zero[:10]:
        r = per_feed[url]
        LOG(f"[per_feed]   zero-yield {r['links']} uri + "
            f"{r['config_nodes']} config -> survive {r['survive']}, "
            f"alive {r['tcping_alive']}: {url}")
