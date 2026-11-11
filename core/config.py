                               
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import TYPE_CHECKING, List, Type, TypeVar, Union
import yaml
from .net.netmon import NetworkMonitor
from .net.netutil import validate_ipv6_mode
from .models import Protocol

if TYPE_CHECKING:






    from _typeshed import DataclassInstance





T = TypeVar('T', bound='DataclassInstance')






NETWORK_PROBE_INTERVAL_MIN = 0.5
NETWORK_PROBE_INTERVAL_MAX = 5.0

def _load_dc(cls: Type[T], data: dict | None) -> T:
                                                                   

                                                                            
                                                                            
                                                              
       
    if data is None:
        data = {}
    known = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in known})


def _load_speedtest(data: dict | None) -> "SpeedTestConfig":
                                                                              
                                                                     
                                                           
       
    if data is None:
        data = {}
    flat: dict = {}
    for key in ("enabled", "url", "retries", "workers", "quick_enabled",
                "quick_min_mbps", "quick_drop_failed", "rescue_enabled",
                "rescue_min_mbps", "full_max_measure"):
        if key in data:
            flat[key] = data[key]

    light = data.get("light") or {}
    full = data.get("full") or {}
    quick = data.get("quick") or {}
    if isinstance(light, dict):
        if "bytes" in light:
            flat["light_bytes"] = light["bytes"]
        if "timeout" in light:
            flat["light_timeout"] = light["timeout"]
    if isinstance(full, dict):
        if "bytes" in full:
            flat["full_bytes"] = full["bytes"]
        if "timeout" in full:
            flat["full_timeout"] = full["timeout"]


    if isinstance(quick, dict):
        for src, dst in (("enabled", "quick_enabled"),
                         ("bytes", "quick_bytes"),
                         ("timeout", "quick_timeout"),
                         ("workers", "quick_workers"),
                         ("retries", "quick_retries")):
            if src in quick:
                flat[dst] = quick[src]

    for src, dst in (("light_bytes", "light_bytes"),
                     ("light_timeout", "light_timeout"),
                     ("full_bytes", "full_bytes"),
                     ("full_timeout", "full_timeout"),
                     ("quick_bytes", "quick_bytes"),
                     ("quick_timeout", "quick_timeout"),
                     ("quick_workers", "quick_workers"),
                     ("quick_retries", "quick_retries")):
        if src in data:
            flat[dst] = data[src]
    return _load_dc(SpeedTestConfig, flat)


@dataclass
class XrayConfig:
    path: str
    use_xhttp_name: bool = False
    enabled: bool = True

@dataclass
class UiConfig:
                                                                                                              
    port: int = 8765

@dataclass
class SingBoxConfig:
                                                                                                   
    path: str = "bin/sing-box.exe"
    enabled: bool = True


@dataclass
class FetchingConfig:
    sources_file: str
    max_links: int
    max_age_days: int
    workers: int
    timeout: int



    feed_cache_enabled: bool = True
    feed_cache_ttl_hours: float = 24.0


@dataclass
class TcpingConfig:
    timeout: float
    workers: int
    prefer_ipv4: bool = True
    max_addrs: int = 3









    probe_retries: int = 2



    retry_timeout: float = 1.5


@dataclass
class UdpingConfig:
                                                                                           
    timeout: float = 3.0
    workers: int = 256
    prefer_ipv4: bool = True
    max_addrs: int = 3
    attempts: int = 2
    probe_size: int = 1200
    max_consecutive_timeouts: int = 0



@dataclass
class TestingConfig:
    timeout: float
    port_pool_size: int
    max_tcp_latency: int



    max_tcp_latency_soft: int = 2000
    workers: int = 24
    critical_timeout: float = 12.0



    connectivity_timeout: float = 6.0



    connectivity_prefilter_timeout: float = 3.0



    diagnose_timeout: float = 2.0



    diagnose_workers: int = 32



    geoip_timeout: float = 3.0
    bypass_timeout: float = 8.0
    max_e2e_latency_ms: int = 0
    critical_mode: str = "all"
    ipv6_mode: str = "auto"









    network_probe_interval: float = 3.0



    connectivity_workers: int = 24
    connectivity_batch_size: int = 15
    batch_size: int = 15





    batch_workers: int = 4




    batch_stagger_ms: int = 200





    recheck_pause_sec: float = 0.0



    dead_nodes_cache_enabled: bool = True
    dead_nodes_ttl_hours: float = 24.0





    trusted_nodes_enabled: bool = True
    trusted_nodes_ttl_hours: float = 1.0

    def __post_init__(self):
                                                                                      
                                                                   
                                                                     
                                                                        
                                                                       
                                             
           
        bsm = self.batch_stagger_ms
        if isinstance(bsm, bool) or not isinstance(bsm, int) or bsm < 0:
            raise ValueError(
                f"config: testing.batch_stagger_ms={bsm!r} invalid "
                f"(expected integer >= 0 ms; 0 = simultaneous start)"
            )
        rps = self.recheck_pause_sec
        if isinstance(rps, bool) or not isinstance(rps, (int, float)) or rps < 0:
            raise ValueError(
                f"config: testing.recheck_pause_sec={rps!r} invalid "
                f"(expected number >= 0 s; 0 = retry disabled)"
            )
        mts = self.max_tcp_latency_soft
        mtl = self.max_tcp_latency
        if isinstance(mts, bool) or not isinstance(mts, int) or mts < 0:
            raise ValueError(
                f"config: testing.max_tcp_latency_soft={mts!r} invalid "
                f"(expected integer >= 0 ms; 0 = soft filter disabled)"
            )
        if mtl > 0 and mts > 0 and mts >= mtl:
            raise ValueError(
                f"config: testing.max_tcp_latency_soft={mts!r} must be < "
                f"max_tcp_latency={mtl!r} when both are set"
            )


@dataclass
class SpeedTestConfig:
                                                                           

                                                                           
                                                                        
                                                                         
                                                                       

                                                                      
                                                                    
                                                                     

                                                                              
                                                                               
                                                              
       
    enabled: bool = True
    url: str = "https://speed.cloudflare.com/__down?bytes="
    light_bytes: int = 1_000_000
    light_timeout: float = 5.0
    full_bytes: int = 3_000_000
    full_timeout: float = 10.0
    retries: int = 1


    workers: int = 8


    quick_enabled: bool = True
    quick_bytes: int = 250_000
    quick_timeout: float = 3.0
    quick_workers: int = 10
    quick_retries: int = 1
    quick_min_mbps: float = 0.0
    quick_drop_failed: bool = True


    rescue_enabled: bool = True
    rescue_min_mbps: float = 5.0






    full_max_measure: int = 300


@dataclass
class FiltersConfig:
    only_standard_ports: bool
    blacklist_domains: List[str]
    standard_ports: List[int]
    name_blacklist: List[str]










    protocol_blacklist: List[str] = field(default_factory=list)





    country_blacklist: List[str] = field(default_factory=list)
















    country_paranoid: Union[bool, str] = False




    country_adaptive_min_confidence: float = 0.8




    aggressive_dedup: bool = False




    strategy_dedup: bool = True


    geo_cache_enabled: bool = True
    geo_cache_ttl_hours: float = 168.0


@dataclass
class TestUrlConfig:
    url: str
    ok_statuses: List[int]
    name: str = ""


@dataclass
class OutputConfig:
    working_nodes: str
    summary: str
    log_dir: str
    cache_dir: str
    max_nodes: int = 0
    max_nodes_per_endpoint: int = 0
    summary_max_nodes: int = 0





    clip_to_clipboard: bool = False







    min_speed_mbps: float = 1.0
    max_latency_ms: int = 3000




    quality_gate_min_keep: int = 10


@dataclass
class Config:
    xray: XrayConfig
    fetching: FetchingConfig
    tcping: TcpingConfig
    testing: TestingConfig
    filters: FiltersConfig
    connectivity_urls: List[TestUrlConfig]
    bypass_urls: List[TestUrlConfig]
    output: OutputConfig
    critical_urls: List[TestUrlConfig] = field(default_factory=list)
    udping: UdpingConfig = field(default_factory=UdpingConfig)
    singbox: SingBoxConfig = field(default_factory=SingBoxConfig)
    speedtest: SpeedTestConfig = field(default_factory=SpeedTestConfig)
    ui: UiConfig = field(default_factory=UiConfig)

    @classmethod
    def load(cls, path: Path) -> 'Config':
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        cfg = cls(
            xray=_load_dc(XrayConfig, data.get('xray')),
            fetching=_load_dc(FetchingConfig, data.get('fetching')),
            tcping=_load_dc(TcpingConfig, data.get('tcping')),
            testing=_load_dc(TestingConfig, data.get('testing')),
            filters=_load_dc(FiltersConfig, data.get('filters')),
            connectivity_urls=[_load_dc(TestUrlConfig, u)
                               for u in data.get('connectivity_urls', [])],
            bypass_urls=[_load_dc(TestUrlConfig, u)
                         for u in data.get('bypass_urls', [])],
            critical_urls=[_load_dc(TestUrlConfig, u)
                           for u in data.get('critical_urls', [])],
            output=_load_dc(OutputConfig, data.get('output')),
            udping=_load_dc(UdpingConfig, data.get('udping')),
            singbox=_load_dc(SingBoxConfig, data.get('singbox')),
            speedtest=_load_speedtest(data.get('speedtest')),
            ui=_load_dc(UiConfig, data.get('ui')),
        )

        ui_port = cfg.ui.port
        if isinstance(ui_port, bool) or not isinstance(ui_port, int) \
                or not (1 <= ui_port <= 65535):
            raise ValueError(
                f"config: ui.port={ui_port!r} invalid (expected int 1..65535)"
            )


        cfg.testing.ipv6_mode = validate_ipv6_mode(cfg.testing.ipv6_mode)




        npi = cfg.testing.network_probe_interval
        if (isinstance(npi, bool) or not isinstance(npi, (int, float))
                or not (NETWORK_PROBE_INTERVAL_MIN
                        <= float(npi) <= NETWORK_PROBE_INTERVAL_MAX)):
            raise ValueError(
                f"config: testing.network_probe_interval={npi!r} invalid "
                f"(expected {NETWORK_PROBE_INTERVAL_MIN} <= value <= "
                f"{NETWORK_PROBE_INTERVAL_MAX} sec: outage detection window = "
                f"interval × {NetworkMonitor.FAIL_THRESHOLD})"





            )


        mct = cfg.udping.max_consecutive_timeouts
        if isinstance(mct, bool) or not isinstance(mct, int) or mct < 0:
            raise ValueError(
                f"config: udping.max_consecutive_timeouts={mct!r} invalid "
                f"(expected int >= 0, 0 = disabled)"
            )



        cp = cfg.filters.country_paranoid
        if not isinstance(cp, bool) and cp != "adaptive":
            raise ValueError(
                f"config: filters.country_paranoid={cp!r} invalid "
                f"(expected bool or \"adaptive\")"
            )



        if cp == "adaptive":
            amc = cfg.filters.country_adaptive_min_confidence
            if (isinstance(amc, bool) or not isinstance(amc, (int, float))
                    or not (0.0 <= float(amc) <= 1.0)):
                raise ValueError(
                    f"config: filters.country_adaptive_min_confidence="
                    f"{amc!r} invalid (expected 0.0 <= value <= 1.0)"
                )






        known_protos = {p.value for p in Protocol}
        pbl = cfg.filters.protocol_blacklist
        for entry in pbl:
            if (not isinstance(entry, str)
                    or entry.strip().lower() not in known_protos):
                raise ValueError(
                    f"config: filters.protocol_blacklist={entry!r} invalid "
                    f"(expected a protocol code from {sorted(known_protos)})"
                )
        cfg.filters.protocol_blacklist = [e.strip().lower() for e in pbl]





        for key in ("batch_size", "connectivity_batch_size"):
            val = getattr(cfg.testing, key)
            if isinstance(val, bool) or not isinstance(val, int) or val < 1:
                raise ValueError(
                    f"config: testing.{key}={val!r} invalid "
                    f"(expected integer >= 1: the value splits nodes into "
                    f"batches, 0 crashes the phase, a negative one silently "
                    f"drops nodes)"
                )






        cw = cfg.testing.connectivity_workers
        if isinstance(cw, bool) or not isinstance(cw, int) or cw < 1:
            raise ValueError(
                f"config: testing.connectivity_workers={cw!r} invalid "
                f"(expected integer >= 1)"
            )
        pool = cfg.testing.port_pool_size
        if isinstance(pool, bool) or not isinstance(pool, int) or pool < 1:
            raise ValueError(
                f"config: testing.port_pool_size={pool!r} invalid "
                f"(expected integer >= 1)"
            )
        cap = pool // (2 * cw)
        if cfg.testing.connectivity_batch_size > cap:
            raise ValueError(
                f"config: testing.connectivity_batch_size="
                f"{cfg.testing.connectivity_batch_size!r} invalid "
                f"(expected <= {cap} = port_pool_size {pool} // (2 × "
                f"connectivity_workers {cw})): {cw} batches run at once, "
                f"and with batch >= pool no free ports remain — PortPool "
                f"waits 5 s per port. Raise port_pool_size or lower the batch"
            )









        bw = cfg.testing.batch_workers
        if isinstance(bw, bool) or not isinstance(bw, int) or bw < 1:
            raise ValueError(
                f"config: testing.batch_workers={bw!r} invalid "
                f"(expected integer >= 1; 1 = engine batches run sequentially)"
            )
        need = 2 * bw * cfg.testing.batch_size
        if need > pool // 2:
            raise ValueError(
                f"config: testing.batch_workers={bw!r} invalid: peak "
                f"2 engines × {bw} batches × {cfg.testing.batch_size} ports = "
                f"{need} ports, but half the pool ({pool // 2}) — PortPool "
                f"waits 5 s per port. Lower batch_workers/batch_size "
                f"or raise port_pool_size"
            )


        st = cfg.speedtest
        for num_name in ("light_bytes", "full_bytes"):
            val = getattr(st, num_name)
            if isinstance(val, bool) or not isinstance(val, int) or val <= 0:
                raise ValueError(
                    f"config: speedtest.{num_name}={val!r} invalid "
                    f"(expected int > 0)"
                )
        for num_name in ("light_timeout", "full_timeout"):
            val = float(getattr(st, num_name))
            if val <= 0:
                raise ValueError(
                    f"config: speedtest.{num_name}={val!r} invalid "
                    f"(expected > 0)"
                )
        if (isinstance(st.retries, bool) or not isinstance(st.retries, int)
                or st.retries < 0):
            raise ValueError(
                f"config: speedtest.retries={st.retries!r} invalid "
                f"(expected int >= 0)"
            )
        if (isinstance(st.workers, bool) or not isinstance(st.workers, int)
                or st.workers < 1):
            raise ValueError(
                f"config: speedtest.workers={st.workers!r} invalid "
                f"(expected int >= 1)"
            )

        if (isinstance(st.full_max_measure, bool)
                or not isinstance(st.full_max_measure, int)
                or st.full_max_measure < 0):
            raise ValueError(
                f"config: speedtest.full_max_measure="
                f"{st.full_max_measure!r} invalid (expected int >= 0)"
            )


        for num_name in ("quick_bytes",):
            val = getattr(st, num_name)
            if isinstance(val, bool) or not isinstance(val, int) or val <= 0:
                raise ValueError(
                    f"config: speedtest.{num_name}={val!r} invalid "
                    f"(expected int > 0)"
                )
        if float(st.quick_timeout) <= 0:
            raise ValueError(
                f"config: speedtest.quick_timeout={st.quick_timeout!r} "
                f"invalid (expected > 0)"
            )
        for num_name in ("quick_workers", "quick_retries"):
            val = getattr(st, num_name)
            if isinstance(val, bool) or not isinstance(val, int) or val < (
                    1 if num_name == "quick_workers" else 0):
                raise ValueError(
                    f"config: speedtest.{num_name}={val!r} invalid "
                    f"(expected int >= "
                    f"{1 if num_name == 'quick_workers' else 0})"
                )
        for num_name in ("quick_min_mbps", "rescue_min_mbps"):
            val = float(getattr(st, num_name))
            if val < 0:
                raise ValueError(
                    f"config: speedtest.{num_name}={val!r} invalid "
                    f"(expected >= 0)"
                )


        fttl = cfg.fetching.feed_cache_ttl_hours
        if (isinstance(fttl, bool) or not isinstance(fttl, (int, float))
                or fttl < 0):
            raise ValueError(
                f"config: fetching.feed_cache_ttl_hours={fttl!r} invalid "
                f"(expected number >= 0, 0 = TTL check disabled)"
            )



        msm = cfg.output.min_speed_mbps
        if (isinstance(msm, bool) or not isinstance(msm, (int, float))
                or msm < 0):
            raise ValueError(
                f"config: output.min_speed_mbps={msm!r} invalid "
                f"(expected number >= 0, 0 = gate disabled)"
            )
        mlm = cfg.output.max_latency_ms
        if isinstance(mlm, bool) or not isinstance(mlm, int) or mlm < 0:
            raise ValueError(
                f"config: output.max_latency_ms={mlm!r} invalid "
                f"(expected integer >= 0, 0 = gate disabled)"
            )
        qgk = cfg.output.quality_gate_min_keep
        if isinstance(qgk, bool) or not isinstance(qgk, int) or qgk < 0:
            raise ValueError(
                f"config: output.quality_gate_min_keep={qgk!r} invalid "
                f"(expected integer >= 0, 0 = safety valve disabled)"
            )
        return cfg
