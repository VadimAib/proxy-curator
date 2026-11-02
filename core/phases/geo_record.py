                                                             

                                                                                                              
                                                           
                                                                
                                                                     
                                                                   
                                                              
                              
   
from typing import Dict

from ..log import LOG
from ..net.geoip import GEO_URL, GeoState, format_summary
from .geofilter import _geo_confidence_ratio


def _record_geo(stats: Dict, geo: GeoState) -> None:
                                                                                

                                                                       
                                                                       
                                                  

                                                                      
                                                                          
                                                                         
                                                                     
                                                                        
                                                                   
                                     

                                                                
                                                                      
                                                   

                                                                    
                                                                   
                                                                        
                                                                        
           
       
    breaker = geo.breaker
    stats["geo_asked"] = breaker.asked
    stats["geo_answered"] = breaker.answered


    stats["geo_failure_ratio"] = round(breaker.failure_ratio(), 3)








    identified = len(geo.countries)
    answered = breaker.answered
    asked = breaker.asked
    checked = int((stats.get("geo_gate") or {}).get("checked") or 0)
    if checked:
        total = max(checked, identified)
    else:


        total = identified + max(asked - answered, 0)
    unknown = max(total - identified, 0)
    stats["geo_confidence"] = {
        "identified": identified,
        "unknown": unknown,
        "total": total,


        "ratio": round(answered / asked, 3) if asked else 0.0,
    }


    stats["geo_breaker_state"] = ("open" if breaker.is_open else
                                   "unstable" if breaker.failure_ratio() > 0
                                   else "closed")
    if breaker.is_open:
        stats["geo_disabled"] = True




        partial = (f"country filter applied only to {identified} "
                   f"identified node(s); " if identified else
                   "filter could not be applied — no countries obtained; ")





        action = getattr(geo, "unknown_action", None)
        if action == "dropped":
            unknown_part = ("unknown nodes dropped (fail-closed: high "
                            "confidence outweighed an open breaker); ")
        else:
            unknown_part = "unknown nodes kept as is (fail-open); "
        LOG(f"[geo] SERVICE UNAVAILABLE: {partial}{unknown_part}"
            f"checked {breaker.asked} node(s), responses "
            f"{breaker.answered} (confidence {_geo_confidence_ratio(geo):.2f}). "
            f"Check availability of "
            f"{GEO_URL.split('?')[0]} or remove country_blacklist.")
    if not geo.countries:
        return
    stats["geo"] = dict(geo.countries)
    LOG(f"[geo] exit countries: {format_summary(geo.countries)}")
