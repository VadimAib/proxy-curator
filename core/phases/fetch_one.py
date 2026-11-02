                                                  

                                                                                                            
                                                                       
                                                             
                                                                    
                                       
   
from typing import Any, Dict, Optional, Tuple

from ..feed_cache import (FeedCacheContext, cached_subscription,
                          cache_parsed_nodes, entry_fresh,
                          feed_content_hash, lm_unchanged_since)
from ..sources_fetch import (Subscription, decode_payload,
                             fetch_subscription, http_get,
                             parse_subscription)


_CACHE_NOTES: Dict[str, str] = {"feed-cache": " (feed cache)",
                                "hash-cache": " (content unchanged)"}


def _sub_summary(sub: Subscription) -> str:
                                                                              
    if sub.links:
        return f"{len(sub.links)} uri"
    if sub.nodes:
        return f"{len(sub.nodes)} nodes"
    return "empty"


def _fetch_one_feed(url: str, timeout: int,
                    cache: Optional[Dict[str, Dict[str, Any]]],
                    ctx: Optional[FeedCacheContext]) -> Tuple[Subscription, str]:
                                                                    

                                                                      
                                                                         
                                                                       
                          

                                                                                  
                                                                         
                                 
       
    if ctx is None or cache is None:
        return fetch_subscription(url, timeout), ""
    entry = cache.get(url)
    if (entry is not None and entry_fresh(entry, ctx.ttl_hours)
            and lm_unchanged_since(entry, ctx.lm_dates.get(url))):
        return cached_subscription(url, entry), "feed-cache"
    text = decode_payload(http_get(url, timeout))
    content_hash = feed_content_hash(text)
    if entry is not None and entry.get("content_hash") == content_hash:
        sub = cached_subscription(url, entry)
        cache_parsed_nodes(cache, url, content_hash, sub)
        return sub, "hash-cache"
    sub = parse_subscription(text, url)
    if not sub.error:
        cache_parsed_nodes(cache, url, content_hash, sub)
    return sub, ""
