# Proxy Curator

**Proxy Curator is for people who use free VPN nodes from public repositories and
want to automate the scanning of thousands of them.** You point it at the sources you
already use; it downloads the node lists, throws away dead, duplicated and
irrelevant entries, and then does the part that decides whether a node is usable at
all: it starts a real tunnel for that node (Xray or sing-box) and checks that the
tunnel opens the addresses that are blocked on **your** network. What survives is
written out as a subscription your client can import — v2rayNG, v2rayN, Clash /
Mihomo.

A node that answers a TCP probe is not a working node. Public lists are full of
addresses that are alive on the outside and useless on the inside: the server is up
but the credentials are dead, the tunnel opens but the blocked site does not load,
the same server appears ten times under different names. Proxy Curator measures each
candidate through its own tunnel, so the output is a list of nodes that actually
carry traffic where you live — not a list of reachable IP addresses.

No single blocklist fits everyone: the same service is blocked in one country,
throttled in another and open in a third, and providers block different things. The
addresses a node has to open are therefore **yours to set** — see
[Settings to look at first](#settings-to-look-at-first). The project ships one
measured example, and it is meant to be replaced.

## What you get

- `output/working_nodes.txt` — the subscription: one URI per line (`vless://`,
  `vmess://`, `trojan://`, `ss://`, `hysteria2://`, `tuic://`, `anytls://`).
  Import it into v2rayNG, v2rayN or any client that accepts a URI list.
- `output/working_nodes.json` — the same nodes with metrics: latency, speed, quick
  measurement, real exit country, protocol, and whether the node was rescued.
- `output/summary.json` — the funnel of the last run: how many nodes entered each
  stage and why the rest were dropped. This is the file to read when "there are too
  few nodes".
- A Clash / Mihomo YAML, a QR code and LAN links are one click away on the **Share**
  tab, as is an optional upload to a GitHub gist.

## Requirements

- **Windows 10 or 11.** The launcher is a `.bat` file, the testing cores are `.exe`
  binaries, and process handling is Win32.
- **No installation, no administrator rights.** Unpack the archive into any folder
  and run `run_curate.bat`. The folder can be moved or copied to another disk: the
  paths in `config.yaml` are relative.
- **Python 3.12+ is optional.** If `run_curate.bat` finds no suitable Python, it
  downloads an embeddable 3.12.8 into the `py\` folder and installs PyYAML there —
  no registry, no PATH.
- **VPN/TUN off during a run.** A TUN client replaces DNS with a fake IP
  (`198.18.x.x`) and distorts every measurement — see the note in Quick start.

## Quick start

**1. Get the program.** Open the
[Releases page](https://github.com/VadimAib/proxy-curator/releases/latest), download
the newest release as **Source code (zip)** and unpack it anywhere — there is nothing
to install. Windows may warn about a file from the internet: the archive holds
scripts and text only — the cores are a separate download inside the program.

**2. Add your sources — one link is enough.** A source is a URL that returns a list
of nodes. In the **Sources** tab press **Add source**, paste the link and **Save** —
the list is used on the next run. The same thing by hand in `sources.txt`: one URL
per line, `#` starts a comment.

```text
# my subscriptions
https://example.com/sub.txt
https://raw.githubusercontent.com/someone/nodes/main/all.txt
```

What the link may point to, starting from the usual case:

1. **A link to a file where the profiles are stored** — plain text, one node link
   per line: `vless://…`, `vmess://…`, `trojan://…`, `ss://…`, `hysteria2://…`,
   `tuic://…`, `anytls://…`. This covers most public lists and subscription
   endpoints. Use the **direct** address of the file, not the browser page that
   displays it.
2. **A base64 subscription** — the same list encoded, the way many services hand it
   out; the program decodes it itself, no conversion needed.
3. **A Clash / Mihomo YAML** — a file with a `proxies:` section.
4. **A sing-box JSON** — a config that starts with `{`.
5. **A GitHub page link** — `github.com/owner/repo/blob/branch/file` for one file,
   or the short form `owner/repo/branch/file`. It works, but it is slower and hits
   GitHub's rate limit — a raw link from case 1 is preferable.
6. **A folder on GitHub** — point at a directory and every `.txt` file directly
   inside it becomes a source. Handy when a repository keeps each protocol in its
   own file:

   ```text
   https://github.com/someone/nodes/tree/main/configs
   someone/nodes/main/configs
   ```

   Both lines mean the same folder; the files in it are listed through the GitHub
   API. Only that one folder is read — subfolders are not walked, and files without
   the `.txt` extension are skipped. If the folder holds `all.txt` or
   `all_configs_sub.txt`, only that file is taken, since it already unions the rest.
   For a single file a raw link from case 1 is still faster.

The shipped `sources.txt` is empty on purpose: which public lists to trust is your
call, and a feed that is dead today should not be baked into the program. Sources
are applied on the next run; a source that fails to download is named in the log and
counted in `summary.json` → `fetch_errors`, and the rest of the run continues.

**3. Start it.** In the project folder:

```batch
run_curate.bat
```

Without arguments it opens the web UI at `http://127.0.0.1:8765` (the browser opens
by itself). The console pipeline starts only with an explicit flag
(`--report`, `--selftest`, …); `NO_UI=1` before launch forces the console path.

The cores are not installed yet: in the toolbar of the page there is one button per
core (`xray`, `singbox`) with a red dot. Click both — the first download is about
110 MB — and wait for the dots to turn green before the first run.

**4. Turn the VPN off before the first measurement** — including TUN clients such as
Hiddify or Tailscale. A run goes out through your real connection; a TUN client
hijacks DNS and the results stop meaning anything. The check needs no extra software:

```batch
nslookup api.github.com
```

The `Address:` line must show a real address. If it shows `198.18.x.x`, a TUN client
is still running — turn it off and check again.

> **The program brings its own Python.** If `run_curate.bat` found no Python 3.12+ on
> your system, it downloads one into the `py\` folder — and from the project folder
> you can use it for anything, including this check:
>
> ```batch
> py\python.exe -c "import socket; print(socket.gethostbyname('api.github.com'))"
> py\python.exe curate.py --ping-only   :: the pipeline without the .bat wrapper
> ```
>
> `py\` appears after the first launch. Nothing is installed into Windows: no
> registry entries, no PATH changes, the folder can be deleted at any time. For
> normal runs keep using `run_curate.bat` — it starts the UI, keeps the run log and,
> in the console path, checks the cores and asks about the working-nodes mode.

**5. Set your mandatory addresses, then press Run** — see the next section.

**6. Take the result.** `output/working_nodes.txt` is the subscription; the same
list, with metrics and the **Test selected** button, is on the **Nodes** tab, and the
**Share** tab turns it into a QR code, a LAN link or a gist.

> ⏳ **The first run takes a while, and that is the point.** Every candidate is
> actually opened and traffic is pushed through it, so tens of thousands of nodes
> mean tens of minutes — far more than a ping sweep, and that is why the resulting
> list works. The **Console** tab shows the current phase and the progress; a run can
> be stopped at any time and the previous subscription stays untouched. If your
> connection drops mid-run, the next launch continues from the checkpoint instead of
> starting over.

> ⚠️ A full run is a manual action, without a VPN. The program is not installed
> through `pip`: `pyproject.toml` is a declaration of dependencies and the Python
> version, not installation instructions. Launch from the project root:
> `run_curate.bat <flags>` (or `py\python.exe curate.py <flags>`).

## Settings to look at first

Everything below lives in `config.yaml` — edited by hand or in the **Settings** tab,
where every field has a "?" icon that opens the relevant article of the built-in
documentation. Five things decide what your subscription looks like:

| Setting | What it decides | What to do |
|---|---|---|
| `critical_urls` | **The mandatory addresses.** A node has to open every one of them through its own tunnel or it is dropped. This is the strictest filter in the project and the reason the output works where you live. | Replace the shipped `https://www.instagram.com/` with the addresses blocked on your provider/country. `[]` disables the stage entirely. |
| `filters.country_blacklist` | Exit countries you do **not** want. The country is looked up from the node's external IP through its own tunnel, not from the name in the list. | Empty in the shipped template — nothing is filtered until you name the countries you want to avoid. |
| `output.min_speed_mbps`, `output.max_latency_ms` | The final quality gate applied after the speed measurement. A node below the thresholds does not enter the subscription even if it is alive. | Defaults are `5` Mbps and `3000` ms. Raise the speed for streaming, lower it for a slow mobile link. If the thresholds cut everything, the gate keeps the best `quality_gate_min_keep` (10) nodes instead of handing you an empty list. |
| Measure size — **Auto / Full / Light** on the dashboard, or `--speed-profile` | How much traffic a measurement spends: `light` = 1 MB per node, `full` = 3 MB, `auto` picks from the detected channel. The payloads live in `speedtest.light` / `speedtest.full`. | `Light` on mobile or metered connections, `Full` on a fast home link. The profile does not change which nodes are kept — only how precisely they are ranked. |
| `output.max_nodes` | How many nodes the subscription may contain (`0` = all). | A short list is easier to keep on a phone; `0` keeps everything that passed. |

Two more things worth knowing before you judge the output:

- **The country in a node name is written by whoever published the list.** In the
  project's own sample, 5 of 18 labelled nodes lied: they promised `🇨🇦 CA` and
  exited in `DE` or `GB`. The real country comes from the node's external IP and is
  stored in `working[].exit_country`. If the geo service cannot answer, the node is
  **not** dropped (fail-open) and the failure is counted in `summary.json`.
- **The mandatory stage is protected against false drops.** Before the DELAY phase a
  canary checks each `critical_urls` address straight from your host, without any
  proxy, and removes the unreachable one for that run — otherwise a site that is
  down globally would drop *all* nodes. An address removed by the canary is
  re-checked through the first nodes' tunnels and comes back if at least one node
  opens it. After selection the log prints `[critical] audit: ok=… failed=…
  unchecked=…`; that is a metric of the output composition, not a filter.

> `filters.blacklist_domains`, `filters.name_blacklist` and
> `filters.protocol_blacklist` are cheap cuts applied before any traffic is spent
> (dead domains, junk node names, protocols you never use). The shipped template
> leaves the first two empty and blocks `mtproto` only. An empty list disables the
> filter completely, with no network requests.

## Using the web UI

`run_curate.bat` with no arguments opens `http://127.0.0.1:8765`. The page follows the
user's path — run it, read the result, look at the nodes, share them; then settings,
reference, archive:

- **The top bar** — **Run** / **Stop**, the progress bar with the current stage, the
  measure size (Auto / Full / Light), the working-nodes mode (replace / append /
  keep), the cores and **Exit**.
- **Console** — the run's output live (the finished run is not replayed here; open
  **Logs** for that).
- **Last Scan** — the funnel of `summary.json`: how many links were collected, how
  many nodes reached each stage and why the rest were dropped, plus the network and
  the cores of that run.
- **Nodes** — the working nodes with metrics; **Test selected** re-measures the
  selected ones right now without a new full run; selected nodes can also be deleted.
- **Share** — hand the list to another device on your Wi-Fi (QR code, URI / base64 /
  Clash links over a read-only LAN server), or publish it to a GitHub gist so the
  subscription works from anywhere.
- **Settings** — `config.yaml` in the browser, with validation and rollback to the
  previous version.
- **Sources** — `sources.txt`: add a link with a note and a category, switch sources
  on and off, remove them; categories can be renamed or deleted.
- **Docs** — the built-in documentation: quick start, every setting, run results,
  troubleshooting, a reference of `config.yaml`, of the CLI flags and of the log,
  with search across articles.
- **Logs** — files of previous runs: read, delete one or all older than 14 days,
  open the folder.

**How to close the program.** The **Exit** button stops the run and the server and
shows a "Program stopped" placeholder; then the console window can be closed.
Ctrl+C in the console window, or simply closing it, also kills the whole process
tree. ⚠️ Closing the **browser tab does not stop the program** — the server keeps
listening and an active run continues.

**Sharing over Wi-Fi** starts a separate read-only server on `0.0.0.0` (port 8766,
override with `UI_SHARE_PORT`) and shows a QR code and three links to the current
`working_nodes.txt`: the URI list, the base64 subscription and the Clash/Mihomo YAML.
Access is granted by a secret token in the link; turn sharing off when it is not
needed (it also stops on Exit). It can be started immediately:
`run_curate.bat --share`.

**Cloud subscription (GitHub gist)** publishes `working_nodes.txt` and the Clash YAML
to a **secret** gist, so the subscription works from any device. Publishing is
manual only — a run never uploads anything by itself, because an experimental run
should not reach subscribers. A secret gist is **not private**, only
non-indexable: anyone with the link sees the nodes. The token needs the `gist`
scope; enter it in the browser field (it lives in the tab's memory and is never
written to disk) or set `GITHUB_TOKEN` before launch.

The UI server is strictly `127.0.0.1` and uses only the Python standard library.
If port 8765 is busy, change `ui.port` in `config.yaml` or set `UI_PORT`.

## Command line

```batch
run_curate.bat                     :: web UI (the default), browser opens by itself
run_curate.bat --report            :: full run in the console (VPN must be off!)
run_curate.bat --selftest          :: sanity check of both cores
run_curate.bat --ping-only         :: TCP/QUIC probes only (phase 4), no cores started
run_curate.bat --tcping-only       :: quick triage: PING + CONNECTIVITY + DIAGNOSIS,
                                   :: no DELAY/speedtest (the cores DO start)
run_curate.bat --only vless,trojan :: protocol filter
run_curate.bat --speed-profile light :: 1 MB per node instead of 3 MB
run_curate.bat --share             :: UI plus the LAN share server
```

`--tcping-only` does not touch the subscription: it stops before DELAY and the
mandatory stage, and writes `working_nodes.tcping.txt` / `summary.tcping.json`.
`--ping-only` writes `working_nodes.ping.txt` / `summary.ping.json`. The full run
writes `working_nodes.*` and `summary.json`.

## Files and folders

```
proxy-curator\
├── run_curate.bat     ← launch: UI by default, console with a flag
├── config.yaml        ← every setting (edited by hand or in the UI)
├── sources.txt        ← your feed URLs, one per line
├── curate.py          ← the console entry point
├── core\  tools\  web\  ← the program itself
├── bin\               ← cores: downloaded from the toolbar on the first launch
├── py\                ← embeddable Python: only if no system 3.12+ exists
├── output\            ← working_nodes.txt / .json, summary.json
├── logs\              ← run logs
├── cache\             ← feed cache (24 h) and geo cache
└── temp\              ← resume checkpoint and temporary files
```

The folders from `bin\` down are created on the first launch. `output\` is the only
place your results live; `logs\` keeps the history of runs.

## Keeping the cores up to date

The nodes are tested through two engines — Xray and sing-box — and each is a separate
executable in `bin\`. The toolbar has one button per core, with a status dot:

- **green** — the installed build is current, nothing to do;
- **yellow** — a newer build is published, click the button to download it;
- **red or grey** — the core is missing (this is where the very first launch starts)
  or does not respond — click the button to download it.

While a download runs the dot pulses and shows the percent; clicking the same button
again cancels it. The version check runs by itself and answers from a local cache,
but a download only ever happens on your click — and a downgrade never happens:
only a strictly newer build is installed, the archive is verified against the
official checksum (sing-box publishes none — there the binary is started and its
version read), and the previous build stays next to the new one as `bin\*.exe.bak`.

The first download is about 33 MB for `xray.exe` and 76 MB for `sing-box.exe`.

> **Download both cores before the first run.** There is nothing to test the nodes
> through until they are in place, so **Run** refuses to start and names the missing
> cores — the same for **Self test**. Click the core buttons, wait for the green dots
> and press **Run** again.

The console pipeline (`run_curate.bat --report`, `--selftest`, …) runs the same
check before the scan and asks `[Y/n]` in the console window:

```batch
set "NO_UPDATE=1"  :: skip the update check entirely
set "UPDATE_YES=1" :: update without asking (scheduler, launch from another .bat)
```

## If your antivirus removes the cores

Windows Defender and third-party antiviruses regularly delete `bin\xray.exe` or
`bin\sing-box.exe` right after they are downloaded, naming them
`Trojan:Win32/CryptInject`, `Trojan:Win32/Sabsik.FL!ml`,
`HEUR:Trojan.Win32.Generic` or the like. These are **false positives**. Both cores
are official open-source projects: [Xray](https://github.com/XTLS/Xray-core)
(Apache-2.0) and [sing-box](https://github.com/SagerNet/sing-box) (GPL-3.0). The
signature reacts to what a proxy does by nature — it opens connections and tunnels
traffic, exactly like a trojan does — and it cannot tell "a proxy for getting around
a block" from "a proxy for stealing data". The binaries are not modified on the way
in: they come from the official GitHub releases and are verified against the
published checksum.

**What to do — add an exclusion for the `bin\` folder:**

- **Windows Defender:** Virus & threat protection → Manage settings → Exclusions →
  Add or remove exclusions → Folder → pick the `bin\` folder of the program.
- **Third-party antiviruses:** add `bin\` to the exclusions / trusted zones.
- Do **not** turn the antivirus off entirely — a folder exclusion is enough.

If a core was already taken: add the exclusion and download that core again from the
toolbar (its dot is red) — the missing file is fetched again.

## Documentation

The full documentation is built into the program: **Docs** tab →
`http://127.0.0.1:8765`. It covers quick start, every setting, how to read the run
results, troubleshooting, a reference of `config.yaml`, of the CLI flags and of the
log, and it is searchable.

This README is the short version for a first launch. The `docs\` folder in the
source repository is developer material — design decisions, measurements, history —
and is not part of the release archive.

## License

Distributed under the [MIT](LICENSE) license.

The core binaries (Xray, sing-box) are under their own licenses (Apache-2.0 and
GPL-3.0 respectively).
