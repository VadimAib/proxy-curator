# Proxy Curator

A pipeline that collects, filters and **actually tests** free VPN nodes from public
GitHub aggregators. The result is a set of working nodes, each verified through its
own tunnel against services that are blocked on your network.

> **The mandatory check (stage 3) is on: `www.instagram.com`.** A node has to open
> this address through its own tunnel; if it does not, it goes to RESCUE and is
> dropped only when its quick measurement is below the threshold. To switch the
> stage off entirely: `critical_urls: []` in `config.yaml`.

> **Blocklists differ by country and by network, so the mandatory list is yours to
> set.** The same service is blocked in one country, throttled in another and open in
> a third; a provider may block Telegram, Instagram, Facebook, YouTube or a local
> news site. The address shipped in `critical_urls` is the one this project measured
> — replace it with the addresses that matter where you live. The stage treats every
> address the same way: opened through the node's tunnel, or not.

> **Telegram is not in the mandatory list.** `web.telegram.org` resolves to
> `149.154.167.99`, which does not answer on TCP; kept in the list, it cut
> `hysteria2` nodes as `critical_failed:telegram` while their channel was alive —
> a false drop. To bring it back, add the address to `critical_urls` in
> `config.yaml` — the entry already there shows the format.

> **The stage is protected against false drops.** Before the
> DELAY phase, `critical_canary()` checks every mandatory address **directly from the
> host** (no proxy, no cores) and removes the unreachable one for that run —
> otherwise a site that is down globally would drop *all* nodes. An address removed
> from the host is re-checked through the tunnels of the first nodes: if at least one
> node opens it, the address comes back into play. After selection the log prints
> `[critical] audit: ok=… failed=… unchecked=…` — this is a metric of the output
> composition in `summary.json`, not a filter: rescued nodes are not cut. With an
> empty list every check stays silent.

**An empty blocklist in `filters` is not a leftover.** All four keys are read by the
code: `blacklist_domains` (substring in the domain, PARSE phase), `name_blacklist`
(substring in the node name), `country_blacklist` (exit country code, looked up from
the node's **external IP** — empty in the shipped template, so nothing is filtered
until you name the countries you want to avoid) and `protocol_blacklist` (protocol
code — the persistent form of `--only`). An empty list disables the filter
entirely and without any network requests; the shipped template leaves all four
empty, and the **Docs** tab shows the format of every key.

**Exit country, not the label.** The country tag inside a node name belongs to someone
else (the feed author writes it); in a sample of 18 nodes with a readable tag, 5
**lied**: they promised `🇨🇦 CA` while the exit was in `DE` and `GB`. The real
country is determined by a request **through the node's own tunnel** and written to
`working[].exit_country`. If the service is unreachable, nodes are **not** dropped
(fail-open) and the failure is visible in `summary.json`.

**Multi-core architecture:** Xray · sing-box. The protocol unambiguously determines
the testing core.

---

## Requirements

- **Windows 10 or 11.** The program is Windows-only: the launcher is a `.bat` file,
  the testing cores are `.exe` binaries, and the console and process handling is
  Win32.
- **No installation and no administrator rights.** Unpack the archive to any folder
  and run `run_curate.bat`. The folder can be moved or copied to another disk — the
  paths in `config.yaml` are relative.
- **Python 3.12+ is optional.** If `run_curate.bat` does not find a suitable Python,
  it downloads an embeddable 3.12.8 into the `py\` folder (no admin rights, no
  registry, no PATH) and installs PyYAML there.
- **Internet on the first launch.** The cores are downloaded then: `xray.exe` is
  about 33 MB, `sing-box.exe` about 76 MB — roughly 110 MB in total. If system
  Python is missing, the embeddable one is downloaded too.
- **VPN/TUN off during a run.** A TUN client replaces DNS with fake-IP and distorts
  the measurements — see the note at the end of Quick start.

## Quick start

**Get the program.** Take the archive from the **Releases** page of this repository
and unpack it anywhere — there is nothing to install. If Windows warns about a file
from the internet, allow it: the archive holds no binaries, only scripts and text, and
the cores are downloaded later by the program itself.

```batch
cd /d "<path to the project>"

run_curate.bat                     :: default: web UI — the browser opens by itself
                                   :: at http://127.0.0.1:8765
                                   :: (dashboard, Start/Stop, log, config.yaml)
run_curate.bat --report            :: full run in the console (IMPORTANT: no VPN)
run_curate.bat --selftest          :: sanity check of both cores
run_curate.bat --ping-only         :: TCP/QUIC probes only (phase 4), no cores needed
run_curate.bat --tcping-only       :: quick triage: PING + CONNECTIVITY + DIAGNOSIS,
                                   :: without delay/speedtest (cores DO start!)
run_curate.bat --only vless,trojan :: protocol filter
```

> 📌 **Running without arguments leads to the web UI** (browser + dashboard). The
> console pipeline starts only with an explicit flag (`--report`, `--selftest`, ...).
> `NO_UI=1` before launch restores the old console behaviour without arguments.

> **Important:** a full run (`--report`) is started **manually only, without a VPN**.

> ⚠️ **The project is not installed through `pip`.** The metadata in
> `pyproject.toml` is correct, but it is used as a declaration (dependency, Python
> version, entry points for editors), not as installation instructions. Launch from
> the root: `python curate.py <flags>` or `run_curate.bat <flags>`.

> ✅ **Publishing to a gist is manual only.** `run_curate.bat` does not call
> `upload_to_gist.py` — neither after a regular run nor after a service one. The
> cloud subscription is updated with the **"Publish to gist"** button on the
> "Share" tab or by running the script directly. That way an experimental run does
> not reach subscribers: a secret gist is not private, anyone with the link can read
> it.

> 🟥 **`--tcping-only` does not touch the subscription.** It stops
> selection at phase 5 (CONNECTIVITY PRE-FILTER) and **does not** go through DELAY,
> the canary or the speed measurement. The result is written separately to
> `working_nodes.tcping.txt` and `summary.tcping.json`, and the `working_nodes.txt`
> subscription stays untouched.

> ✅ **`--ping-only` is the one honestly named "TCP/QUIC probes only".** Phase 4
> runs and that is it: no cores are started at all.
> The result is in `output/working_nodes.ping.txt` and `output/summary.ping.json`.

> ⚠️ Before **any** run, turn off VPN/TUN — a TUN client replaces DNS with fake-IP
> and distorts the results. Check: `python -c "import socket;
> print(socket.gethostbyname('api.github.com'))"` — it must return a real address, not
> `198.18.x.x`.

---

## Documentation

| File | What is inside |
|------|----------------|
| `README.md` | This file: quick start, dependencies, layout |
| **Docs** tab in the web UI | The full documentation inside the application: quick start, every setting, run results, troubleshooting, a reference of `config.yaml`, of the CLI flags and of the log — with search across articles. It opens in the browser together with the program (`http://127.0.0.1:8765` → **Docs** tab); every settings field has a "?" icon linking to the relevant article |
| `LICENSE` | License (MIT) |

---

## Dependencies

```text
pyyaml>=6.0
```

Both declarations (`pyyaml>=6.0` and `requires-python = ">=3.12"`) live in
`pyproject.toml` — that is the only place where they are declared. A system Python,
if you use one, needs `pip install pyyaml`; the embedded one gets PyYAML on install
(see Requirements).

The core binaries live **inside the project** — the `bin\` folder next to `core\`:

- **Xray** — `bin\xray.exe`
- **sing-box** — `bin\sing-box.exe`

Paths in `config.yaml` are **relative** (`bin/xray.exe`): `rp()` resolves them from
the project root (`core/paths.py`). That is why the project folder can be copied to
any disk without touching the code or the config.

> If an antivirus deleted or blocked the core binaries (`bin\xray.exe`,
> `bin\sing-box.exe`) — see
> [If your antivirus removes the cores](#if-your-antivirus-removes-the-cores) below:
> how to add the `bin\` folder to the exclusions and restore the cores.

### Cores update themselves

On every launch of `run_curate.bat` — **before** scanning — new Xray and sing-box
builds are checked. If a newer version exists, an `[Y/n]` question is printed; without
consent the file in `bin\` is not touched. A downgrade never happens — see below.

```batch
set "NO_UPDATE=1"  :: skip the update check entirely
set "UPDATE_YES=1" :: update without asking (scheduler, launch from another .bat)
```

By hand:

```bash
python tools/update_cores.py --check-only    # only show what is new
python tools/update_cores.py --force         # reinstall the same release (repair)
python tools/update_cores.py --yes           # without asking
```

**No downgrades:** `releases/latest` returns a version *older* than the installed one
for both cores, so only a strictly newer build is installed. The archive is verified
against the official checksum (sing-box does not publish one — there the binary is
started and its version is checked), and the previous one stays next to it as
`bin\*.exe.bak`.

### If your antivirus removes the cores

Windows Defender and third-party antiviruses regularly delete `bin\xray.exe` or
`bin\sing-box.exe` right after `run_curate.bat` has downloaded them, naming them
`Trojan:Win32/CryptInject`, `Trojan:Win32/Sabsik.FL!ml`,
`HEUR:Trojan.Win32.Generic` or the like. These are **false positives**. Both cores
are official open-source projects: [Xray](https://github.com/XTLS/Xray-core)
(Apache-2.0) and [sing-box](https://github.com/SagerNet/sing-box) (GPL-3.0). The
signature reacts to what a proxy does by nature — it opens connections and tunnels
traffic, exactly like a trojan does — and it cannot tell "a proxy for getting around
a block" from "a proxy for stealing data".

The binary is not modified on the way in: `tools/update_cores.py` takes it from the
official GitHub release and verifies it against the published checksum (sing-box
publishes none — there the binary is started and its version read). The program
itself contains no third-party code beyond these cores.

**What to do — an exclusion for the `bin\` folder:**

- **Windows Defender:** Virus & threat protection → Manage settings → Exclusions →
  Add or remove exclusions → Folder → pick the `bin\` folder of the program.
- **Third-party antiviruses:** add `bin\` to the exclusions / trusted zones.
- Do **not** turn the antivirus off entirely — a folder exclusion is enough.

If a core was already taken: add the exclusion, then launch `run_curate.bat` again
(or `python tools/update_cores.py --force`) — the missing file is downloaded again,
and the previous build stays next to it as `bin\*.exe.bak`.

---

## Project layout

```
proxy-curator\
├── README.md              ← this file
├── LICENSE                ← MIT
├── config.yaml            ← pipeline configuration
├── sources.txt            ← sources (subscription URLs)
├── run_curate.bat         ← launch wrapper
├── curate.py              ← Entry Point: CLI, logging, exit codes
├── upload_to_gist.py      ← manual publishing of the subscription to a GitHub gist
├── pyproject.toml         ← declaration of dependencies and of the Python version
├── .gitattributes         ← line endings as built (`.bat` stays CRLF)
├── .gitignore
├── core\                  ← the pipeline core (47 top-level modules, see below)
│   ├── pipeline.py        ← orchestrator: run_pipeline() + resume logic
│   ├── pipeline_env.py    ← phases 1–2: SOURCES + FRESHNESS (resolve, cache, HEAD)
│   ├── pipeline_funnel.py ← funnel: counters, max_nodes, top-N, per-endpoint
│   ├── pipeline_perfeed.py← per-feed processing inside PARSE
│   ├── pipeline_export.py ← EXPORT + replace/append/keep + summary
│   ├── pipeline_log.py    ← log formatting (fmt_dur, ProgressBar wrappers)
│   ├── pipeline_modes.py  ← run modes: Auto/Full/Light + flags
│   ├── pipeline_ping.py   ← phase 4 PING (TCP/QUIC)
│   ├── pipeline_resume.py ← resume logic (checkpoint, skip_to_phase)
│   ├── pipeline_tune.py   ← auto-tune after the run
│   ├── merge.py           ← merge_working_lists: the --merge Append mode
│   ├── state.py           ← PipelineState: data typing between phases
│   ├── resume.py          ← restore/checkpoint of the state
│   ├── archive.py         ← archiving/removal of old files (output/, logs/, cache/)
│   ├── feed_cache.py      ← feed cache (24 h TTL, keys of the current sources only)
│   ├── nodes_cache.py     ← cache of working nodes between runs
│   ├── sources_cache.py   ← sources cache
│   ├── sources_fetch.py   ← feed download (HTTP/JSON GitHub API)
│   ├── sources_github.py  ← parsing of GitHub raw / JSON API
│   ├── cores.py           ← core auto-update facade: plan — cores_plan.py,
│   │                          applying — cores_apply.py, console — cores_cli.py
│   ├── cores_apply.py     ← download, verify .dgst, replace the binary, roll back
│   ├── cores_cache.py     ← cache of core binaries
│   ├── cores_cli.py       ← console: the "update?" question, return code
│   ├── cores_fetch.py     ← core download + checksum verification
│   ├── cores_plan.py      ← update plan: what is newer, what is on disk
│   ├── cores_specs.py     ← core specifications/versions
│   ├── cores_version.py   ← parsing of version strings
│   ├── speed_profile.py   ← detection channel profile (full/light/unknown)
│   ├── stress_advice.py   ← A/B advice, verdicts on load
│   ├── stress_tests.py    ← stress measurement facade: dispatcher + re-exports;
│   │                          the measurements themselves — stress_cpu.py /
│   │                          stress_net.py / stress_disk.py, shared — stress_common.py
│   ├── tune_plan.py       ← auto-tune plan (metric → config value)
│   ├── trusted_nodes.py   ← trusted node list (DELAY bypass)
│   ├── working_lists.py   ← working_nodes.* replace/append/keep + backup_previous
│   ├── retest.py          ← re-test of selected nodes (UI button, /api/nodes/test)
│   ├── utils.py           ← shared helpers (parse_float, sleep, retry)
│   ├── exporters.py       ← writing artifacts, clipboard — on a flag only
│   ├── output_quality.py  ← output composition check after SPEEDTEST (speed
│   │                          threshold, protocol diversity)
│   ├── filters.py         ← policy_check, deduplicate
│   ├── config.py / models.py / log.py / ui.py / paths.py
│   ├── parsers\           ← URI / Clash-YAML / sing-box / TG / WireGuard / serialize
│   ├── phases\            ← extracted phases (19 modules: fetch, fetch_one, parse,
│   │                          probe, connectivity, connectivity_recheck, critical,
│   │                          critical_tunnel, diagnose, delay, delay_rounds,
│   │                          geo_after_gate, geo_record, geofilter, speedtest,
│   │                          speedtest_measure, speedtest_instrument,
│   │                          speedtest_channel, strategy_dedup)
│   ├── net\               ← NetworkMonitor, tcping / udping, diag, geoip,
│   │                        geo_cache, netlabel, netmon, netutil (8 modules)
│   └── engine\            ← cores: Xray, sing-box, winjob (Job Object);
│                              harness* (5 submodules), selftest, httptest,
│                              batch, ports, engines (14 modules)
├── tools\                 ← helper scripts (run by hand; to_clash is also used by sharing)
│   ├── bootstrap_python.py ← unpacking of embedded Python + PyYAML
│   ├── update_cores.py    ← core update (--check-only / --force / --yes)
│   └── to_clash.py        ← working_nodes.txt → Clash/Mihomo YAML
├── web\                   ← UI server (http.server, standard library only)
│   ├── server.py          ← HTTP API + SSE for the live log (facade; modules — web/server_*.py)
│   ├── _progress_parser.py← progress-bar line parser: is_progress_bar_line,
│   │                        update_progress_from_line (for /api/progress)
│   ├── qrcode.js          ← vendored QR generator (MIT) for the "Share" tab
│   ├── guide.js           ← help module: article rendering, tree, search, anchors
│   ├── logs.js            ← "Logs" tab module: file list, reading, cleanup
│   ├── guide\guide.json   ← content of the "Docs" tab (EN + RU)
│   └── index.html         ← dashboard, console, nodes, settings, share, help
├── bin\                   ← cores: appear on the first launch (tools/update_cores.py)
├── py\                    ← embedded Python: appears on the first launch if no system 3.12+ is present
├── output\                ← artifacts (working_nodes.txt, working_nodes.json, summary.json)
├── logs\                  ← run logs
├── cache\                 ← feed cache (24 h TTL, keys of the current sources only)
└── temp\                  ← temporary files, resume checkpoint
```

> The folders `bin\`, `py\`, `output\`, `logs\`, `cache\`, `temp\` are created on the
> first launch: the cores and the embedded Python are downloaded automatically, and
> the artifacts appear after a run.

> **Note:** `curate.py` is the Entry Point: CLI (`argparse`), log initialisation and
> exit codes only; it calls `core.pipeline.run_pipeline(args)`. All pipeline business
> logic lives in `core/`.

---

## Web UI

Launch: `run_curate.bat` without arguments (the default) or explicitly `--ui` → the
browser opens by itself at http://127.0.0.1:8765

- **Dashboard** — funnel statistics from `summary.json`, core state, Auto/Full/Light profiles, Start/Stop buttons
- The tabs follow **the user's path**: run → result → nodes → share; then settings, then the reference and the archive.
- **Console** — the run's stdout in real time (SSE stream, monospace `<pre>`)
- **Last scan** — the funnel of the last run: how many nodes reached each stage
- **Nodes** — the list of working nodes after a run
- **Share** — hand the node list to devices in the same network (phone/PC) or publish it to the cloud: QR code, LAN subscription links (URI / base64 / Clash) and manual publishing to a GitHub gist
- **Settings** — editing `config.yaml` through the browser
- **Sources** — the feed list (`sources.txt`): add, disable, rename a category
- **Docs** — built-in documentation: quick start, every setting, run results, troubleshooting, a reference of `config.yaml`/flags/log, search across articles. Every settings field has a "?" icon that opens the relevant article
- **Logs** — log files of previous runs: list, read, delete (one file, or all run logs older than 14 days — archived run artifacts stay), open the log folder

**How to close the program.** The **"Exit"** button in the panel stops the run and the
server itself and shows the "Program stopped" placeholder; the console window can be
closed after that. Alternatives: Ctrl+C in the console window, or simply **closing the
console window** — the whole process tree is killed by a Job Object
(`core/net/winjob.py`). ⚠️ Closing the **browser tab does NOT stop the program** — the
server keeps listening on the port and an active run continues (the tab is only a
client).

The server is strictly `127.0.0.1` and uses only the Python standard library (no new
dependencies).

**Sharing over Wi-Fi.** The button on the "Share" tab starts a separate read-only
server on `0.0.0.0` (port 8766, overridable with `UI_SHARE_PORT`) and shows a QR code
and three links to the current `working_nodes.txt`: the URI list (v2rayNG/v2rayN), the
base64 subscription and the Clash/Mihomo YAML. Access is granted by a secret token in
the link; anyone in your network with the link sees the nodes, so turn sharing off
when it is not needed (it also stops on "Exit"). It can be started right away:
`run_curate.bat --share`.

**Cloud subscription (GitHub gist).** The second block of the "Share" tab publishes
`working_nodes.txt` and the Clash YAML to a **secret** gist — so the subscription
works from any device, not only from the home network. Publishing is manual only: a
run never uploads anything by itself. The token needs the `gist` scope; it can be
entered in the browser field (it lives in the tab's memory and is never written to
disk) or set in the `GITHUB_TOKEN` environment variable before launch. The links are
updated after every publication. A secret gist is **not private**, only
non-indexable: anyone with the link sees the nodes. If the Clash YAML could not be
built, the old Clash file is removed from the gist and the local Clash link is
cleared — better to hand out no Clash subscription at all than the previous run's.
Direct launch: `python upload_to_gist.py` (token — in the env).

---

## License

Distributed under the [MIT](LICENSE) license.

The core binaries (Xray, sing-box) are under their own licenses (Apache-2.0 and
GPL-3.0 respectively).
