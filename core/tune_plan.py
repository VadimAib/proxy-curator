                                                                               

                                                                          
                                                                                
                                                                                 
                                                                               
                                                                               
                                                  

                                                                     
                                                                              
                           

                                                                   
                                                                              
                                                                            
                                                                        
                                                                            
                                                                        
                                                                       
                                                                            
                                                        

                                                                          
                                                                          
                                                                           
                                                     

                                                                       
                                                                             
                                                              

                                                                
                                                                         
                                                                           
                                                                         
                                            

                                                                                
                                                                           
                                                                       
                                                                            
                                                                        
                                           
   
from typing import Any, Dict, List, Optional



SAFE_FLIGHT_BYTES = 24_000_000


LIGHT_BYTES = 1_000_000
FULL_BYTES = 3_000_000


LIGHT_TIMEOUT_FLOOR = 5.0
FULL_TIMEOUT_FLOOR = 10.0


TIMEOUT_MARGIN = 3.0






SLOW_MBPS = 20.0






from .net.netmon import detect_channel_profile
from .phases.speedtest_instrument import timeout_for_budget, transfer_deadline
from .speed_profile import speed_profile_for_channel


def recommend_profile(mbps: Optional[float], rtt_ms: Optional[float],
                      jitter_ms: Optional[float]) -> str:
                                                                                 

                                                                            
                                                                    
                                                                            
                                                                             
                                                                             

                                                                   
                                                                         
                                                                      
                                                                      
                                                                         
                                                                        
                                                                         
                                                                         
                                         
       
    if mbps is None:
        return "unknown"
    if mbps < SLOW_MBPS:
        return "light"
    if rtt_ms is None or jitter_ms is None:

        return "full"
    try:
        channel = detect_channel_profile(float(rtt_ms), float(jitter_ms))
    except (TypeError, ValueError):
        return "unknown"

    return speed_profile_for_channel(channel)


def plan_internet_tune(
    *,
    mbps: Optional[float],
    rtt_ms: Optional[float],
    jitter_ms: Optional[float],
    current: Dict[str, Any],
) -> List[Dict[str, Any]]:
                                                                     

                                                                           
                                                                           
                                                                 

                                                                         
                                                                      
                                                                             
                                        

                                                                        
                                                                           
                                                                              
                                                                        
                                                                            
                                                                               
                                                
       
    if mbps is None or mbps <= 0:
        return []
    profile = recommend_profile(mbps, rtt_ms, jitter_ms)
    bytes_ = LIGHT_BYTES if profile == "light" else FULL_BYTES
    floor = LIGHT_TIMEOUT_FLOOR if profile == "light" else FULL_TIMEOUT_FLOOR

    key = profile

    proposals: List[Dict[str, Any]] = []

    def add(path: str, value: Any, reason: Dict[str, Any]) -> None:
        if current.get(path) != value:
            proposals.append({"path": path, "value": value, "reason": reason})

    add(f"speedtest.{key}_bytes", bytes_,
        {"code": "tier", "args": {"tier": profile, "mb": bytes_ // 1_000_000}})




    seconds = bytes_ * 8.0 / (mbps * 1_000_000.0)
    needed = seconds * TIMEOUT_MARGIN
    cur_timeout = float(current.get(f"speedtest.{key}_timeout") or 0.0)
    budget = transfer_deadline(cur_timeout) if cur_timeout > 0 else 0.0
    if budget < needed:
        value = max(floor, timeout_for_budget(needed))
        add(f"speedtest.{key}_timeout", value, {"code": "timeout", "args": {
            "tier": profile,
            "mb": round(bytes_ / 1_000_000.0, 2),
            "seconds": round(seconds, 1),
            "timeout": cur_timeout,
            "budget": round(budget, 1) if budget > 0 else 0.0,
            "needed": round(needed, 1),
            "margin": TIMEOUT_MARGIN,
            "value": value,
            "suggested_budget": round(transfer_deadline(value), 1),
        }})





    workers_cap = max(1, SAFE_FLIGHT_BYTES // FULL_BYTES)
    cur_workers = current.get("speedtest.workers")
    if isinstance(cur_workers, int) and cur_workers > workers_cap:
        add("speedtest.workers", workers_cap,
            {"code": "workers_cap", "args": {
                "cur": cur_workers,
                "per": FULL_BYTES // 1_000_000,
                "flight": cur_workers * (FULL_BYTES // 1_000_000),
                "budget": SAFE_FLIGHT_BYTES // 1_000_000}})

    return proposals











_RUN_TIERS = (("speedtest", None), ("speedtest_quick", "quick"))


TIER_BYTES = {"light": LIGHT_BYTES, "full": FULL_BYTES, "quick": 250_000}
TIER_TIMEOUT_FLOOR = {
    "light": LIGHT_TIMEOUT_FLOOR, "full": FULL_TIMEOUT_FLOOR, "quick": 3.0,
}




TIMEOUT_TIGHT_RATIO = 0.7


def _percentile(sorted_values: List[float], q: float) -> float:
                                                                                                                                    
    if not sorted_values:
        return 0.0
    idx = int(round((len(sorted_values) - 1) * q))
    idx = max(0, min(len(sorted_values) - 1, idx))
    return float(sorted_values[idx])


def _tier_stats(samples: Any) -> Optional[Dict[str, float]]:
                                                                 

                                                                         
                                                                       
                                                                      
                                                  
       
    if not isinstance(samples, dict):
        return None
    values = sorted(
        float(v["mbps"]) for v in samples.values()
        if isinstance(v, dict) and isinstance(v.get("mbps"), (int, float))
        and float(v["mbps"]) > 0
    )
    if not values:
        return None
    return {
        "count": len(values),
        "p10": round(_percentile(values, 0.10), 2),
        "median": round(_percentile(values, 0.50), 2),
        "p90": round(_percentile(values, 0.90), 2),
    }


def _top_reason(reasons: Any) -> str:
                                                                                                                                    
    if not isinstance(reasons, dict) or not reasons:
        return ""
    try:
        return str(max(reasons.items(), key=lambda kv: kv[1])[0])
    except (TypeError, ValueError):
        return ""


def plan_from_run(
    *,
    run: Optional[Dict[str, Any]],
    current: Dict[str, Any],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
                                                                    

                                                                           
                                                                             
                                                          

                                                                              
                                                                          
                                                                       
                                                                             
                              

                                                            
                                                                          
                                                                               
                   
       
    proposals: List[Dict[str, Any]] = []
    notes: List[Dict[str, Any]] = []
    if not isinstance(run, dict) or not run:
        return proposals, [{"code": "run_missing"}]

    duration_sec = run.get("duration_sec")
    notes.append({"code": "run_summary", "args": {
        "started": str(run.get("started") or ""),
        "minutes": round(float(duration_sec) / 60.0) if isinstance(
            duration_sec, (int, float)) else None,
        "links_total": int(run.get("links_total") or 0),



        "config_nodes": int(run.get("config_nodes") or 0),
    }})

    for samples_key, fixed_tier in _RUN_TIERS:
        stats = _tier_stats(run.get(samples_key))
        if not stats:
            continue
        if fixed_tier is None:
            measured_with = str(run.get("speedtest_profile")
                                or run.get("speedtest_network") or "full")
            tier = "light" if measured_with == "light" else "full"
        else:
            tier = fixed_tier
        timeout_key = f"speedtest.{tier}_timeout"
        bytes_key = f"speedtest.{tier}_bytes"
        bytes_ = int(current.get(bytes_key) or TIER_BYTES[tier])
        floor = TIER_TIMEOUT_FLOOR[tier]
        timeout = float(current.get(timeout_key) or 0.0)
        seconds = bytes_ * 8.0 / (stats["p10"] * 1_000_000.0)





        budget = transfer_deadline(timeout) if timeout else 0.0
        notes.append({"code": "run_tier", "args": {
            "tier": tier,
            "count": stats["count"],
            "p10": stats["p10"],
            "median": stats["median"],
            "p90": stats["p90"],


            "mb": round(bytes_ / 1_000_000.0, 2),
            "seconds": round(seconds, 1),
            "timeout": timeout,
            "budget": round(budget, 1),
            "ratio": round(seconds / budget, 2) if budget else None,
            "tight": bool(budget) and seconds > budget * TIMEOUT_TIGHT_RATIO,
        }})
        if budget and seconds > budget:
            suggested = max(floor, timeout_for_budget(seconds * TIMEOUT_MARGIN))
            proposals.append({
                "path": timeout_key,
                "value": suggested,
                "reason": {"code": "run_timeout", "args": {
                    "tier": tier,
                    "seconds": round(seconds, 1),
                    "timeout": timeout,
                    "budget": round(budget, 1),
                    "margin": TIMEOUT_MARGIN,



                    "value": suggested,
                    "suggested_budget": round(transfer_deadline(suggested), 1),
                }},
            })


    quick_tested = run.get("speedtest_quick_tested")
    if isinstance(quick_tested, int) and quick_tested > 0:
        dropped = int(run.get("speedtest_quick_dropped") or 0)
        notes.append({"code": "run_drops", "args": {
            "tier": "quick",
            "tested": quick_tested,
            "ok": int(run.get("speedtest_quick_ok") or 0),
            "dropped": dropped,
            "pct": round(dropped * 100.0 / quick_tested),
            "reason": _top_reason(run.get("speedtest_quick_drop_reasons")),
        }})


    cap = current.get("speedtest.full_max_measure")
    speedtest = run.get("speedtest")
    measured = len(speedtest) if isinstance(speedtest, dict) else 0
    skipped = run.get("speedtest_full_skipped")
    if isinstance(cap, int):
        notes.append({"code": "run_cap", "args": {
            "cap": cap,
            "measured": measured,
            "skipped": int(skipped) if isinstance(skipped, int) else 0,





            "hit": (int(skipped) > 0) if isinstance(skipped, int) else measured >= cap,
        }})
    fail_reasons = run.get("speedtest_fail_reasons")
    if isinstance(fail_reasons, dict) and fail_reasons:
        notes.append({"code": "run_failures", "args": {
            "tier": "full",
            "failed": sum(int(n) for n in fail_reasons.values()
                          if isinstance(n, int)),
            "reason": _top_reason(fail_reasons),
        }})

    return proposals, notes
