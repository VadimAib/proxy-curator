                                                                                   

                                                                                                                 
                                                                   
                                                                   
                                                                       
                                                                      
                          
   
from typing import Any, Dict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

from .config import Config
from .log import LOG
from .net.netmon import detect_channel_profile
from .speed_profile import normalize_speed_profile, speed_profile_for_channel


def _apply_profile_override(args: "argparse.Namespace",
                            stats: Dict[str, Any]) -> None:
                                                        

                                                                             
                                                   
       
    raw = getattr(args, "speed_profile", None) or "auto"
    profile = normalize_speed_profile(raw)


    if profile is None or profile == "auto":
        return
    stats["profile_override"] = profile
    LOG(f"[env] speedtest profile: {profile} (owner override, "
        f"auto-detect bypassed)")


def _auto_tune(rtt_ms: float, jitter_ms: float) -> Dict[str, Any]:
                                                                         

                                                                 
                                                                   
                                                        

                                                                    
                       
                     
                          
                               
       
    overrides: Dict[str, Any] = {}


    if jitter_ms < 5.0:
        overrides["workers"] = min(32, max(1, int(8 * 2)))
    elif jitter_ms > 30.0:
        overrides["workers"] = max(1, int(8 // 2))
    else:
        overrides["workers"] = 8


    if rtt_ms > 150.0:
        overrides["batch"] = max(1, int(32 // 2))
    elif rtt_ms < 30.0:
        overrides["batch"] = min(64, int(32 * 2))
    else:
        overrides["batch"] = 32


    if jitter_ms < 10.0 and rtt_ms < 50.0:
        overrides["payload_mb"] = min(20, int(10 * 2))
    elif jitter_ms > 50.0:
        overrides["payload_mb"] = max(1, int(10 // 2))
    else:
        overrides["payload_mb"] = 10


    overrides["timeout_s"] = 5.0 + (rtt_ms / 1000.0) + (jitter_ms / 1000.0)

    return overrides


def _apply_auto_tune(cfg: Config, stats: Dict[str, Any]) -> None:
                                                                          

                                                                            
                                                                          
                                                                        
                                                     
                                                                       
                                                                           
                                                                             
                                                                         
       
    overrides = stats.get("auto_tune")
    if not isinstance(overrides, dict):
        return
    speed_cfg = getattr(cfg, "speedtest", None)
    test_cfg = getattr(cfg, "testing", None)


    workers = overrides.get("workers")
    if speed_cfg is not None and isinstance(workers, int):
        speed_cfg.workers = max(1, min(32, workers))


    batch = overrides.get("batch")
    if test_cfg is not None and isinstance(batch, int):
        test_cfg.batch_size = max(1, min(64, batch))





    override = normalize_speed_profile(stats.get("profile_override")) or ""
    link = stats.get("local_link")
    detected = "unknown"
    if isinstance(link, (list, tuple)) and len(link) == 2:
        try:
            detected = detect_channel_profile(float(link[0]), float(link[1]))
        except (TypeError, ValueError):
            detected = "unknown"
    if override in ("full", "light"):
        profile = override
    else:
        profile = speed_profile_for_channel(detected)

    payload_mb = overrides.get("payload_mb")
    timeout_s = overrides.get("timeout_s")
    if speed_cfg is not None:
        bytes_attr = "light_bytes" if profile == "light" else "full_bytes"
        timeout_attr = ("light_timeout" if profile == "light"
                        else "full_timeout")
        if isinstance(payload_mb, (int, float)):
            mb = int(round(max(1.0, min(20.0, float(payload_mb)))))
            setattr(speed_cfg, bytes_attr, mb * 1_000_000)
        if isinstance(timeout_s, (int, float)):
            setattr(speed_cfg, timeout_attr, max(0.0, float(timeout_s)))

    LOG(f"[env] auto-tune applied: profile={profile}, "
        f"workers={getattr(speed_cfg, 'workers', None)}, "
        f"batch={getattr(test_cfg, 'batch_size', None)}, "
        f"payload_mb={overrides.get('payload_mb')}, "
        f"timeout_s={overrides.get('timeout_s')}")
