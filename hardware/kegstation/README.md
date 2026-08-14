# KegStation — Sallaup Electronics

Part of the **Sallaup KegSense** keg-monitoring system, made by
**Sallaup Electronics**.

**KegStation** is the central unit: reads all 5 KegSensor modules over
the wired in-keezer hub connection, streams each keg's brew name +
weight down the KegDisplay chain (see
[`../kegdisplay/`](../kegdisplay/)) so each tap's own OLED can show its
own keg directly, and hosts a web dashboard mirroring the same
information remotely.

This is a planning doc — no hardware or software has been built yet.
Captures decisions made so far so they aren't lost before implementation
starts (see `hardware/kegsensor/wiring.md` and `hardware/keghub/README.md`
for the equivalent docs that preceded the KegSensor module).

## Decisions so far

- **Platform**: Raspberry Pi 4, 5, or Zero 2 W — any of these have
  built-in Wi-Fi + Bluetooth, so no wireless add-on hardware is needed.
- **Connectivity**: reads the 5× KegSensor modules over the wired hub
  connection (shared SCK + 5× DT + power, see
  `hardware/kegsensor/wiring.md` and `hardware/keghub/README.md`) —
  direct to the Pi's GPIO header, 3.3V logic throughout, no level
  shifters needed. No Wi-Fi/radio inside the keezer itself (unchanged
  from the original hub design constraint) — KegStation sits outside the
  keezer, so its own Wi-Fi is unrelated to that constraint.
- **Wi-Fi provisioning**: [Comitup](https://davesteele.github.io/comitup/)
  — Pi broadcasts a captive-portal setup network (SSID `KegStation-Setup`)
  on first boot / when no known network is available, works from any
  phone's browser via the OS-level captive-portal mechanism (no app
  needed, no Web Bluetooth iOS limitation). Chosen over BLE provisioning,
  which has no mature ready-made tool on Linux/Raspberry Pi.
  - **Branding**: Comitup's setup pages (`comitup_web/templates/` —
    `index.html`/`connect.html`/`confirm.html` + `css`/`js`/`images`) are
    plain by default (no existing logo to fight against), but the
    template path is hardcoded in `comitupweb.py`
    (`/usr/share/comitup/templates`, confirmed by reading the source —
    no config/env override exists). Branding means overwriting those
    installed files with our own after installing the `comitup` package,
    as part of KegStation's own setup script — and re-applying that after
    any future `comitup` package upgrade, since there's no supported way
    to point it at a separate custom template directory.
- **Software updates**: git-based. KegStation's code lives in a git repo
  on the Pi; updating is `git pull` + restart the service, rollback is
  checking out a previous tag. Deliberately not a fleet OTA framework
  (Mender, balena) — this is one device, not a fleet.
  - **Trigger**: manual button in the web dashboard (an admin
    action that runs the pull + restart on demand) — not automatic on a
    schedule, so an update never lands unannounced (e.g. mid-party), and
    not SSH-only, so it doesn't require terminal access for routine use.
- **KegSensor-interfacing layer: C.** The HX711 protocol needs precise
  clock-pulse timing to bit-bang correctly (shared SCK + 5× DT, per
  `hardware/kegsensor/wiring.md`) — C gives predictable low-level GPIO control
  that's harder to guarantee in a higher-level language. This is scoped
  specifically to the hardware-interfacing piece, not necessarily the
  rest of KegStation's software (dashboard, etc. — still open, below).
  - **Interface to the rest of the system**: a small daemon, written in
    C, that reads all 5 kegs on a fixed interval and writes current
    readings to a local JSON/text file. Whatever ends up driving the
    OLED and web dashboard just reads that file — simplest possible
    hand-off, easy to debug by hand (`cat` the file), no IPC to build or
    maintain. Chosen over a Unix socket/local IPC (more real-time, more
    moving parts) and over having the C program also drive the OLED/
    dashboard directly (would remove the option to pick a different,
    easier language for that higher-level part later).
  - **GPIO library**: not yet chosen, but worth flagging now — `pigpio`
    (the traditional choice for precise bit-banged timing on a Pi) does
    not support the Raspberry Pi 5's GPIO chip (RP1); if a Pi 5 is in play,
    `lgpio` (pigpio's suggested successor) or direct `libgpiod` should be
    used instead. Decide this once the Pi model (below) is locked in.
- **Tare/weight calibration: CLI-first.** A small companion program
  (`kegcal`) run on the Pi itself (SSH or a plugged-in keyboard), not a
  dashboard UI — the dashboard doesn't exist yet, and whenever it does it
  can shell out to the same commands rather than needing its own
  calibration logic.
  - `kegcal tare <keg>` — reads that keg's *current* raw ADC value (from
    the daemon's readings file) and stores it as the tare reference.
  - `kegcal setfull <keg> <grams>` — same, but stores it as the "full"
    reference point at a known weight in grams. That known weight can be
    either the actual full keg's spec weight (so the reference doubles as
    the "how much is left" baseline) or a separate known calibration
    mass — the tool works the same either way, this only affects what
    number you type in.
  - Calibration values live in a separate config file (e.g.
    `calibration.json`), which the daemon just re-reads on its normal
    cycle — no signaling/IPC needed for `kegcal` to take effect.
  - The daemon's readings file includes both the raw ADC count and the
    calibrated weight (once calibration exists) per keg, since `kegcal`
    needs to read the live raw value to know what to record.
  - **Not yet built** — see below.
- **Per-tap detail now lives entirely at the tap, not at KegStation.**
  Each tap has its own OLED (driven by its own Trinket M0 — see
  [`../kegdisplay/README.md`](../kegdisplay/README.md)) that shows that
  keg's brew name + weight directly, all the time. This superseded an
  earlier button + resistor-ladder + KegStation-touchscreen scheme (see
  git history) once each tap got a real display back — no button to
  read, no ADC needed at KegStation for this purpose.
  - **Wiring run this still creates**: KegStation sits outside the
    keezer (see System overview in the root README), but taps are
    mounted at the keezer itself, so a physical run out to each tap is
    still needed regardless of what's at the far end — a wired
    connection either way (consistent with the no-WiFi-in-the-keezer
    rule, which is about radios, not wired signals).
  - **KegStation's job for this chain**: stream each keg's current brew
    name + weight down the KegDisplay daisy chain in tap order (see the
    chain-addressing scheme in KegDisplay's own README) — not yet
    implemented, see Still Open.
- **KegStation's own display and the calibration front-end are open
  again** — the 4-5" touchscreen plan was chosen specifically to show
  per-tap detail on request *and* double as a calibration UI; now that
  per-tap detail lives on each tap's own OLED, the touchscreen only has
  the calibration reason left, which may not be enough to justify it on
  its own vs. reverting to the original CLI-first (`kegcal`) plan or a
  web-only calibration page. See Still Open — deliberately not
  re-decided yet rather than carrying the touchscreen forward on a
  reason that no longer fully applies.

## Still open

- **All of the above C daemon / `kegcal` work is design-only, not yet
  implemented.** Deliberately holding off writing the code until a
  physical Raspberry Pi + HX711 setup exists to test against, rather than
  writing GPIO-bit-banging code that can only be verified once real
  hardware shows up — the risk of subtle timing/wiring bugs surviving
  unnoticed in untestable code isn't worth it here (same reasoning as
  everything else in this project: validate against something real
  before calling it done, not just "it compiles").

- Software language/stack for everything *other* than the KegSensor
  interfacing daemon (Python is the natural fit for the Pi's OLED/web
  library support, but not yet committed to) — the daemon just needs to
  read a file, so it can be written in anything.
- Which Pi model specifically (4 / 5 / Zero 2 W) — affects the GPIO
  library choice for the C daemon (see above).
- Whether to build a small interface PCB (breaking out the hub's RJ45
  connection and the KegDisplay chain's UART-ish GPIO pins to the Pi's
  header) or wire it directly on a protoboard/HAT — these are native Pi
  GPIO peripherals, no special adapter needed, unlike the original
  RS-485 design's USB-RS485 requirement.
- **KegStation's own KegDisplay-chain code**: the piece that reads the
  daemon's readings file and streams it down the chain in tap order —
  not yet written (see [`../kegdisplay/README.md`](../kegdisplay/README.md)
  for the chain protocol's own still-open details).
- **Whether KegStation needs a display of its own at all now** — the
  4-5" touchscreen's main reason (showing per-tap detail on request) is
  gone now that each tap has its own OLED; only the calibration-UI
  reason is left. Options: keep the touchscreen anyway (still a nice
  standalone calibration UI), revert to the original CLI-first `kegcal`
  plan, or build a web-only calibration page. Not re-decided yet.
- Web dashboard framework, exact GPIO pin mapping for the shared-SCK +
  5×DT KegSensor scheme, and the on-disk format/path for the readings
  file the C daemon writes.
- Physical enclosure for KegStation itself (separate from the KegSensor
  case already built) — depends on the touchscreen decision above.
