                                                            

                                                                     
                                                             
                                                                        
                                                                
                                                                  

                                                            
                                                                           
                                                                            
                                             
   
from typing import List, Tuple

from ..config import Config
from ..filters import geo_lookup_enabled
from ..net.geoip import GeoState, format_summary, keep_or_drop
from ..log import LOG
from ..models import Node

def _geo_confidence_ratio(geo: GeoState) -> float:
                                                                                

                                                                      
                                                                         
                                                                        
                                                                        
       
    asked = geo.breaker.asked
    return (geo.breaker.answered / asked) if asked else 0.0


def unknown_country_dropped(cfg: Config, confidence_ratio: float) -> bool:
                                                                    

                                                                          
                                                                          
                                                                            
                                                                     
                                 
       
    mode = getattr(cfg.filters, "country_paranoid", False)
    if mode == "adaptive":
        min_conf = float(getattr(cfg.filters,
                                 "country_adaptive_min_confidence", 0.8))
        return confidence_ratio >= min_conf
    return bool(mode)


def _drop_by_exit_country(final: List[Tuple[Node, float]],
                          geo: GeoState, cfg: Config
                          ) -> List[Tuple[Node, float]]:
                                                                    

                                                                        
                                                                         
                                                                       
                                                                       
                                                                  
                                                                
                                                                         
                                                                        
                                                                         

                                                        
                                                                 
                                                                       
                                                 
                                                                    
                                                              
                                                                     
                                                                    
                                                                          
                                                          
       
    blacklist = list(getattr(cfg.filters, "country_blacklist", []) or [])


    if not geo_lookup_enabled(cfg.filters):
        return final
    mode = getattr(cfg.filters, "country_paranoid", False)

    by_key = {n.key(): code for (n, _) in final
              if (code := geo.countries.get(n.key()))}
    keep_keys, dropped = keep_or_drop(by_key, blacklist)

    adaptive = (mode == "adaptive")




    min_conf = float(getattr(cfg.filters,
                             "country_adaptive_min_confidence", 0.8))


    drop_unknown = unknown_country_dropped(cfg, _geo_confidence_ratio(geo))



    geo.unknown_action = "dropped" if drop_unknown else "kept"
    if not drop_unknown and not dropped:
        return final
    drop_set = {key for key, _ in dropped}
    if drop_unknown:

        kept = [(n, ms) for n, ms in final if n.key() in set(keep_keys)]
        unknown_dropped = len(final) - len(by_key)
        if adaptive:
            LOG(f"[geo] adaptive exit country: {len(kept)}/{len(final)} kept, "
                f"{len(drop_set)} blacklisted, {unknown_dropped} unknown "
                f"(fail-closed, confidence={_geo_confidence_ratio(geo):.2f} "
                f">= {min_conf:.2f}) by {format_summary(by_key)}")
        else:
            LOG(f"[geo] paranoid exit country: {len(kept)}/{len(final)} kept, "
                f"{len(drop_set)} blacklisted, {unknown_dropped} unknown "
                f"(fail-closed) by {format_summary(by_key)}")
    else:
        kept = [(n, ms) for n, ms in final if n.key() not in drop_set]
        LOG(f"[geo] exit country: {len(kept)}/{len(final)} kept, "
            f"{len(drop_set)} dropped by {format_summary(by_key)}")
    for key, code in dropped[:8]:
        node = next((n for n, _ in final if n.key() == key), None)
        LOG(f"[geo]   dropped {code}: "
            f"{(node.name if node else key)[:48]}")
    return kept
