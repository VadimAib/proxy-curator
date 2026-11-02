                                                                    

                                                                        
                                                                               
                                                                              
                                                                     
                                                                     
   
from typing import Any, Dict, List, Tuple

from ..config import Config
from ..log import LOG
from ..models import Node, QUIC_PROTOCOLS
from ..net.netmon import NetworkMonitor, detect_ipv6_support, wait_internet
from ..net.netutil import validate_ipv6_mode
from ..state import PipelineState
from ..net.tcping import ping_nodes
from ..ui import ProgressBar


def tcping_phase(state: PipelineState, cfg: Config,
                  monitor: NetworkMonitor) -> None:
                                                               

                                                                     
                                                                         
                                             
       
    nodes = state.nodes
    stats = state.stats

    quic_n = sum(1 for n in nodes if n.protocol in QUIC_PROTOCOLS)
    udp_cfg = getattr(cfg, "udping", None)
    udp_timeout = udp_cfg.timeout if udp_cfg else cfg.tcping.timeout

    ipv6_mode = validate_ipv6_mode(getattr(cfg.testing, "ipv6_mode", "auto"))
    ipv6_ok = True
    if ipv6_mode == "auto":
        ipv6_ok = detect_ipv6_support()
    LOG(f"[ping] testing {len(nodes)} nodes "
        f"({len({(n.host.lower(), n.port) for n in nodes})} endpoints, "
        f"tcp={len(nodes) - quic_n} quic={quic_n}, "
        f"workers={cfg.tcping.workers}, "
        f"timeout={cfg.tcping.timeout}s/udp {udp_timeout}s)")
    if ipv6_mode == "force":
        LOG(f"[tcping] IPv6 mode: force → trying IPv6 addrs")
    elif ipv6_mode == "off":
        LOG(f"[tcping] IPv6 mode: off → skipping IPv6 addrs")
    else:
        LOG(f"[tcping] IPv6 mode: auto, detected support: {ipv6_ok} → "
            f"{'using IPv6 addrs' if ipv6_ok else 'skipping IPv6 addrs'}")

    if monitor.is_down:
        LOG("[net] WARNING: no direct internet, waiting for recovery...")
        wait_internet(monitor)
        if monitor.is_down:
            LOG("[net] still down after wait cap — starting tcping anyway.")
        else:
            LOG("[net] OK: connection restored, starting tcping.")

    ep_count = _progress_budget(nodes)


    bar = ProgressBar(ep_count, "ping", log_progress=True, unit="endpoints")

    alive_all: List[Tuple[Node, float]] = []
    tcp_drops_all: Dict[str, int] = {}
    dead_all: List[Tuple[Node, str]] = []
    remaining = list(nodes)
    attempt = 0
    retries_left: Dict[str, int] = {}
    MAX_NET_RETRIES = 2
    transient = ("unreachable network", "network is unreachable",
                 "10051", "[errno 11002]", "getaddrinfo failed")
    permanent = ("[errno 11001]", "udp refused")

    def _retryable(err: str) -> bool:
        low = err.lower()
        if any(p in low for p in permanent):
            return False
        return any(t in low for t in transient)

    while remaining:
        if monitor.is_down:
            LOG("[net] WARNING: connection lost during tcping, waiting...")
            wait_internet(monitor)
            if monitor.is_down:
                LOG(f"[net] still down after wait cap — continuing with "
                    f"{len(remaining)} node(s) in queue")
            else:
                LOG(f"[net] OK: connection restored, {len(remaining)} node(s) "
                    f"in queue")
        udp_kwargs: Dict[str, Any] = {}
        if udp_cfg is not None:
            udp_kwargs = {
                "udp_timeout": udp_cfg.timeout,
                "udp_workers": udp_cfg.workers,
                "udp_attempts": udp_cfg.attempts,
                "udp_probe_size": udp_cfg.probe_size,
                "udp_max_consecutive_timeouts": getattr(
                    udp_cfg, "max_consecutive_timeouts", 5),
            }
        alive, tcp_drops, dead = ping_nodes(
            [(n, None) for n in remaining], cfg.tcping.timeout, cfg.tcping.workers,
            prefer_ipv4=cfg.tcping.prefer_ipv4,
            max_addrs=cfg.tcping.max_addrs,
            progress_cb=lambda ok: bar.update(ok), retry_cb=bar.add_total,
            probe_retries=cfg.tcping.probe_retries,
            retry_timeout=cfg.tcping.retry_timeout,
            ipv6_mode=ipv6_mode, ipv6_ok=ipv6_ok,
            **udp_kwargs)
        alive_all.extend(alive)
        dead_all.extend(dead)
        for k, v in tcp_drops.items():
            tcp_drops_all[k] = tcp_drops_all.get(k, 0) + v
        if monitor.is_down:
            next_remaining = [n for n, _ in dead]
        else:
            next_remaining = []
            for n, err in dead:
                if not _retryable(err):
                    continue
                left = retries_left.get(n.raw, MAX_NET_RETRIES)
                if left > 0:
                    retries_left[n.raw] = left - 1
                    next_remaining.append(n)
        if next_remaining:
            attempt += 1
            LOG(f"[net] tcping retry {attempt}: {len(next_remaining)} nodes to retry")
            bar.add_total(_progress_budget(next_remaining))
            remaining = next_remaining
        else:
            remaining = []

    bar.finish()
    LOG(f"[tcping] {len(alive_all)} alive")
    for e, c in sorted(tcp_drops_all.items(), key=lambda x: -x[1])[:5]:
        LOG(f"         -{c:<6} {e}")

    quic_alive = sum(1 for n, _ in alive_all if n.protocol in QUIC_PROTOCOLS)
    quic_dead = [(n, err) for n, err in dead_all
                 if n.protocol in QUIC_PROTOCOLS]
    quic_timeout = sum(1 for _, err in quic_dead if err == "timeout")
    quic_blocked = sum(1 for _, err in quic_dead if err == "udp-blocked")
    quic_total = quic_alive + len(quic_dead)
    LOG(f"[ping] QUIC nodes: {quic_alive} alive, "
        f"{quic_timeout} timeout, {quic_blocked} udp-blocked")
    if quic_total > 0 and quic_blocked > quic_total // 2:
        LOG(f"[ping] WARNING: UDP appears to be blocked by router/ISP "
            f"({quic_blocked}/{quic_total} QUIC nodes untestable). "
            f"Hysteria2/TUIC nodes will not work on this network.")
    stats.update({"tcping_alive": len(alive_all), "tcping_drops": tcp_drops_all})















    probed_ms = [m for _, m in alive_all if m > 0]
    if probed_ms:
        avg_ms = sum(probed_ms) / len(probed_ms)
        spread_ms = max(probed_ms) - min(probed_ms) if len(probed_ms) > 1 else 0.0
        stats["ping"] = {"avg_ms": round(avg_ms, 2),
                         "spread_ms": round(spread_ms, 2),
                         "count": len(probed_ms)}
    state.alive = alive_all




    for n, _ in alive_all:
        state.bump_feed(n.extra.get("src"), "tcping_alive")









    ratio_warn, min_sample = 0.35, 200
    tcp_total = sum(1 for n in nodes if n.protocol not in QUIC_PROTOCOLS)
    tcp_alive = sum(1 for n, _ in alive_all if n.protocol not in QUIC_PROTOCOLS)
    if tcp_total >= min_sample and tcp_alive / tcp_total > ratio_warn:
        LOG(f"[ping] WARNING: TCP-alive {tcp_alive}/{tcp_total} "
            f"({tcp_alive / tcp_total:.0%}) — ratio above the typical one for "
            f"free nodes. Looks like a transparent carrier/network proxy: "
            f"connect() completes on a middlebox rather than the node, so this "
            f"figure is inflated and conversion to working nodes is "
            f"understated. Later phases will filter out the false alive — this "
            f"is network diagnostics, not selection.")


def _progress_budget(nodes) -> int:
                                                                            

                                                                              
                                                                         
                                                                                          
                                                                               
                                                                             
                                                                         
                                                           

                                                           
       
    tcp = {(n.host.lower(), n.port) for n in nodes
           if n.protocol not in QUIC_PROTOCOLS}
    quic = {(n.host.lower(), n.port) for n in nodes
            if n.protocol in QUIC_PROTOCOLS}
    return len(tcp) + len(quic)
