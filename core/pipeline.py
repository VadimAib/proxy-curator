                                                                     

                                                                           
                                                                       
        

                                                                                 
                                                                 
                                                                                
                                                                      
                                                                            
                                                                 
                                                                        
                                                               
                                                 
                                                 

                                                     
                                                                           
                                                                          
                                      

                                                                            
                                                                             
                                                               
                                                                

              
                                                            
                                                                 
                                                 
                                                              
                                             
                                                         
                                                                           
                                                        
                                                   
                                                                 
                                                                  
                                                                             
                                                                               
                                                                               
                                                                        
                                                                         
                                                                      
                                                                     
                                                                     
                                                     
                                                     
                                                                                 

                                                                            
                                                                                  
                                                                             
                     
   
import os
import time
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    import argparse

from .config import Config, OutputConfig
from .archive import archive_run_artifacts
from .engine.engines import build_engines
from .exporters import export_summary
from .log import LOG
from .net.netmon import NetworkMonitor
from .nodes_cache import record_conn_drops
from .output_quality import apply_latency_prefilter, apply_quality_gate
from .paths import ROOT, rp
from .phases.connectivity import connectivity_phase
from .phases.critical import critical_audit
from .phases.delay import delay_phase
from .phases.diagnose import diagnosis_phase
from .phases.fetch import fetch_and_sample_links
from .phases.geo_after_gate import geo_after_gate_phase
from .phases.parse import routing_phase, parse_and_filter_nodes
from .phases.speedtest import (rescue_phase, speedtest_phase,
                                speedtest_quick_phase)
from .phases.strategy_dedup import strategy_dedup_phase
from .pipeline_env import (_freshness_phase,
                           _prepare_env,
                           _resolve_sources_phase)
from .pipeline_export import (_exit_no_nodes, _export_phase, _rank_final,
                              _stop_after_ping, export_nodes,
                              export_working_nodes_json, resolve_output_paths)
from .pipeline_funnel import _log_funnel
from .pipeline_log import (_log_engines, _log_out_count,
                           _log_route_by_engine, _stop_note)
from .pipeline_modes import _read_modes
from .pipeline_perfeed import _log_per_feed, build_per_feed
from .pipeline_ping import run_ping_block
from .pipeline_resume import _restore_resume
from .pipeline_tune import _apply_auto_tune
from .engine.ports import get_shared_pool
from .resume import clear_state, load_state
from .engine.selftest import run_selftest
from .state import PipelineState
from .trusted_nodes import apply_trusted_bypass
from .ui import ProgressBar


def run_pipeline(args: "argparse.Namespace") -> int:
                                                                   

                                                                        
                                    

                                                                          
                                                               
                                                                            
                               
       
    t_start = time.time()
    argv = getattr(args, "argv", [])

    config_path = ROOT / "config.yaml"
    if not config_path.exists():
        LOG(f"ERROR: {config_path} not found")
        return 1
    cfg = Config.load(config_path)

    env = _prepare_env(cfg, argv, args)
    xray_path, singbox_path = env["xray_path"], env["singbox_path"]
    sources_file, out_path = env["sources_file"], env["out_path"]
    summary_path, cache_dir = env["summary_path"], env["cache_dir"]
    stats: Dict[str, Any] = env["stats"]


    if getattr(args, "auto_tune", False):
        _apply_auto_tune(cfg, stats)

    tcping_only, ping_only = _read_modes(args)


    nodes_out, summary_out = resolve_output_paths(out_path, summary_path,
                                                  tcping_only, ping_only)

    token = os.environ.get("GITHUB_TOKEN", "")






    if args.selftest:
        if not xray_path.exists():
            LOG("ERROR: xray not found")
            return 1
        pool = get_shared_pool(4)
        return 0 if run_selftest(xray_path, pool, cfg, singbox_path) else 1





    monitor = NetworkMonitor(interval=cfg.testing.network_probe_interval)
    monitor.start()
    workers = getattr(cfg.testing, 'workers', 40)
    pool_size = max(cfg.testing.port_pool_size, workers * 3)
    port_pool = get_shared_pool(pool_size)

    engines = build_engines(port_pool, cfg, rp)
    _log_engines(engines, stats)


    state = PipelineState(stats=stats, resume_data=load_state())
    skip_to_phase, initial_nodes = _restore_resume(state)

    LOG("")
    LOG("=== PHASE 1/11: SOURCES ==="
        + ("  [skipped: resume]" if skip_to_phase else ""))
    if not skip_to_phase:
        urls = _resolve_sources_phase(sources_file, token, stats, cache_dir)
        if urls is None:
            return 1

        LOG("")
        LOG("=== PHASE 2/11: FRESHNESS + FETCH ===")
        urls, feed_cache = _freshness_phase(urls, cfg, cache_dir, args, stats)

        fetch_and_sample_links(
            state, urls, cfg.fetching.max_links, cfg.fetching.workers,
            args.report, cfg.fetching.timeout, feed_cache)

        LOG("")
        LOG("=== PHASE 3/11: PARSE + POLICY ===")
        only_protos = ({p.strip().lower() for p in args.only.split(",")
                        if p.strip()} or None)
        unparseable_path = out_path.parent / "unparseable_sample.txt"
        parse_and_filter_nodes(
            state, cfg.filters, only_protos, unparseable_path)
    else:
        state.nodes = initial_nodes
        LOG("")
        LOG("=== PHASE 2/11: FRESHNESS + FETCH ===  [skipped: resume]")
        LOG("")
        LOG("=== PHASE 3/11: PARSE + POLICY ===  [skipped: resume]")
    routing_phase(state.nodes if state.nodes else [n for n, _ in state.alive],
                   stats)

    LOG("")
    LOG("=== PHASE 4/11: PING (TCP + QUIC) ==="
        + ("  [skipped: resume]" if skip_to_phase == "delay" else ""))
    if skip_to_phase != "delay":



        run_ping_block(state, cfg, cache_dir, monitor)


    stop_note = _stop_note(ping_only, skip_to_phase)

    LOG("")
    LOG("=== PHASE 5/11: CONNECTIVITY PRE-FILTER ===" + stop_note)
    if ping_only:
        LOG("[conn] skipped (--ping-only: TCP/QUIC probes, engines not started)")
    elif skip_to_phase != "delay":






        trusted_alive, state.alive = apply_trusted_bypass(
            state.alive, out_path, cfg)
        conn_bar = ProgressBar(len(state.alive), "conn", log_progress=True,
                               unit="nodes")
        connectivity_phase(state, engines, cfg, port_pool, bar=conn_bar)
        if trusted_alive:
            state.alive.extend(trusted_alive)
            LOG(f"[trusted] {len(trusted_alive)} nodes skipped the pre-filter")
        if not state.alive:
            LOG("[conn] all nodes dropped by connectivity pre-filter")


        if cfg.testing.dead_nodes_cache_enabled and state.conn_drops:
            remembered = record_conn_drops(
                cache_dir, state.conn_drops, cfg.testing.dead_nodes_ttl_hours,
                state.stats.get("network_fingerprint"),
                state.source_nodes)
            LOG(f"[dead-cache] {remembered} node(s) remembered for next run")
    else:





        LOG(f"[resume] pre-filter skipped: {len(state.alive)} candidates, "
            f"{len(state.final)} already OK")

    LOG("")





    LOG("=== PHASE 6/11: DIAGNOSIS (server probe of dropped nodes) ==="
        + stop_note)
    if skip_to_phase != "delay" and not ping_only:
        diagnosis_phase(state, cfg, out_path.parent / "diag_tls_ok.txt")

    LOG("")
    LOG("=== PHASE 7/11: SPEEDTEST-QUICK (all candidates) ===" + stop_note)



    if skip_to_phase == "delay":
        LOG("[speedtest] quick tier skipped (resume: candidates already measured)")
    elif ping_only:
        LOG("[speedtest] quick tier skipped (--ping-only: engines not started)")
    elif tcping_only:

        LOG("[speedtest] quick tier skipped (--tcping-only)")
    else:
        speedtest_quick_phase(state, engines, cfg, port_pool)
        if not state.alive:
            LOG("[speedtest] all candidates dropped by quick tier")
        strategy_dedup_phase(state, cfg)

    LOG("")
    LOG("=== PHASE 8/11: DELAY TESTS (Xray + sing-box) ===" + stop_note)
    try:
        if ping_only:
            LOG("[delay] skipped (--ping-only)")
        else:
            delay_phase(state, engines, cfg, args, monitor, port_pool)
    finally:
        monitor.stop()
    final = state.final

    LOG("")
    LOG("=== PHASE 9/11: RESCUE (soft drops with fast channel) ===" + stop_note)
    if ping_only:
        LOG("[rescue] skipped (--ping-only)")
    elif tcping_only:
        LOG("[rescue] skipped (--tcping-only)")
    else:
        rescue_phase(state, cfg)
        final = state.final




    if ping_only and skip_to_phase != "delay":
        final = _stop_after_ping(state)
    final = _rank_final(final, cfg.output)
    state.final = final
    if final:
        _log_route_by_engine(stats)





    per_feed = build_per_feed(state.feed_stats, final)
    if per_feed:
        stats["per_feed"] = per_feed
        _log_per_feed(per_feed)

    if not final:
        _exit_no_nodes(out_path, nodes_out, summary_out, stats, t_start)



        archive_run_artifacts(out_path.parent, str(stats.get("run_network")))
        return 3

    _log_out_count(final, stats, ping_only, tcping_only)

    LOG("")
    LOG("=== PHASE 10/11: SPEEDTEST (adaptive throughput) ===" + stop_note)


    if ping_only:
        LOG("[speedtest] skipped (--ping-only)")
    elif tcping_only:
        LOG("[speedtest] skipped (--tcping-only)")
    else:




        state.final = apply_latency_prefilter(state.final, stats, cfg.output)
        if not state.final:
            LOG("[quality] prefilter removed every node — nothing to measure")
            _exit_no_nodes(out_path, nodes_out, summary_out, stats, t_start)
            archive_run_artifacts(out_path.parent, str(stats.get("run_network")))
            return 3
        speedtest_phase(state, engines, cfg, port_pool)





        final = apply_quality_gate(state.final, stats, cfg.output)
        state.final = final




        geo_after_gate_phase(state, engines, cfg)
        final = state.final
        if not final:
            LOG("[geo] country filter removed every node — nothing to export")
            _exit_no_nodes(out_path, nodes_out, summary_out, stats, t_start)
            archive_run_artifacts(out_path.parent,
                                  str(stats.get("run_network")))
            return 3

    critical_audit(state, stats)
    _export_phase(final, stats, cfg, nodes_out, summary_out, tcping_only, ping_only)

    duration = time.time() - t_start


    summary_max = getattr(cfg.output, "summary_max_nodes",
                          OutputConfig.summary_max_nodes)
    _log_funnel(stats, len(final))
    export_summary(final[:summary_max] if summary_max > 0 else final,
                   stats, summary_out, duration)
    LOG(f"[out] summary -> {summary_out}")


    archive_run_artifacts(out_path.parent, str(stats.get("run_network")))
    LOG(f"[done] duration {duration:.1f}s")

    clear_state()
    return 0
