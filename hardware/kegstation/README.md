# KegStation — Sallaup Electronics

Part of the **Sallaup KegSense** keg-monitoring system, made by
**Sallaup Electronics**.

**KegStation** is the central unit: reads all 5 KegSensor modules over
the wired in-keezer hub connection, drives a small OLED at each keg's
own tap (weight + brew name, right where you're pouring from — not one
shared display listing all kegs), and hosts a web dashboard mirroring
the same information remotely.

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
- **One OLED per keg, mounted at/over that keg's own tap** — not one
  shared display listing all 5 kegs. Each shows just its own keg's brew
  name + weight/% remaining, right where you're actually pouring from.
  - **New wiring run this creates**: KegStation sits outside the keezer
    (see System overview in the root README), but taps are mounted at
    the keezer itself — so unlike a single-shared-display plan, each
    display now needs its own wired run out to its tap. Still a wired
    connection (consistent with the no-WiFi-in-the-keezer rule, which is
    about radios, not wired signals) but a physical run that didn't need
    to exist before this decision.
  - **Why not just 5 bare I2C OLEDs**: cheap small OLEDs (SSD1306 etc.)
    ship at a fixed I2C address (usually 0x3C) — putting 5 on one bus
    directly doesn't work, at most 2 could coexist by address alone.
    Ruled out an I2C multiplexer (TCA9548A) and SPI (needs its own
    chip-select line per display off the Pi) in favor of the design
    below, which solves both the addressing problem *and* the long
    cable run problem in one move.

- **KegDisplay: a combined Arduino Nano + OLED board, one per keg,
  daisy-chained over RS-485.** Each tap gets its own small board (Nano +
  OLED on one PCB, OLED wired directly to its own Nano over short local
  I2C traces — no cable, no connector for that link) rather than a bare
  OLED talking straight to the Pi.
  - **Why this solves the addressing problem**: an OLED driver chip's
    I2C address is fixed in hardware, but a microcontroller's address
    (or, here, its node address on the RS-485 line) is just a value set
    in its own firmware — freely chosen, no collision between the 5
    KegDisplay boards even though every OLED behind them answers to the
    same fixed address locally.
  - **Why RS-485, not I2C, for the run back to KegStation**: I2C's
    open-drain bus has a real capacitance/distance budget that gets
    tight over long or multi-drop cable runs; RS-485 is a differential
    signaling standard built specifically for long, noisy, multi-drop
    runs (the same class of problem as industrial sensor networks).
    Each KegDisplay gets a cheap transceiver chip (e.g. MAX485); the Pi
    needs a USB-to-RS485 adapter or HAT.
  - **Connectors**: two RS-485 connectors per KegDisplay board (IN/OUT),
    wired in parallel so boards daisy-chain tap to tap — one cable
    hopping from KegStation to keg 1 to keg 2 ... to keg 5, instead of 5
    separate home-run cables. RS-485 actively prefers this topology
    (star wiring causes reflections); a bare OLED wouldn't have this
    connector pattern, only the Nano side does.
  - **Termination**: a 120Ω resistor at each *end* of the chain
    (KegStation end and the last KegDisplay) — not at the intermediate
    boards — to prevent signal reflections. Cheap insurance even on a
    short, slow bus.
  - **Addressing/protocol on the RS-485 line**: not yet decided between
    Modbus RTU (established, off-the-shelf protocol for exactly this
    "poll device N over a shared line" pattern, with existing Arduino
    libraries) or a small custom protocol.
  - **Power**: distributed down the *same* 4-wire daisy-chain cable as
    the RS-485 signal (A, B, GND, +V) — RS-485 itself doesn't carry
    power (unlike PoE), but nothing stops running power on separate
    conductors in the same cable, so no separate power supply is needed
    at each KegDisplay. The chain as a whole still needs its own supply,
    separate from the Pi's own 5V one — voltage not locked in (12V is a
    reasonable default, cheap and widely available, with a small local
    regulator on each KegDisplay stepping down to what the Nano/OLED
    need — higher distribution voltage means lower current for the same
    power, which means less voltage drop over distance) but the actual
    number depends on real cable length and total current draw, neither
    measured yet.
  - **Consequence for calibration UI**: weakens (doesn't rule out) the
    keypad+OLED idea below, since there's no longer one central OLED at
    KegStation to pair a keypad with — see Still Open.
  - **Not yet built or prototyped** — this whole design came out of
    conversation, not a physical test yet. Same "verify against real
    hardware before calling it done" standard as everything else here.

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
  connection + a USB-to-RS485 adapter/HAT to the Pi's GPIO header) or
  wire it directly on a protoboard/HAT.
- **KegDisplay specifics (see above)**: Modbus RTU vs. a custom protocol
  for RS-485 node addressing; the actual RS-485-chain power supply
  voltage (12V assumed for now, pending real cable-length/current
  numbers) and each board's local regulator; specific OLED model/size
  and Nano variant; the physical mounting method at/over each tap; and
  the physical cable path from KegStation out to keg 1 (then daisy-
  chained on from there, so only that first leg needs separate scoping).
- Web dashboard framework, exact GPIO pin mapping for the shared-SCK +
  5×DT KegSensor scheme, and the on-disk format/path for the readings
  file the C daemon writes.
- Physical enclosure for KegStation itself (separate from the KegSensor
  case already built).
- **Calibration front-end: keypad+OLED vs. web page vs. both — not yet
  decided, and the per-tap OLED decision above weakens the keypad+OLED
  case specifically**: that idea assumed one central OLED at KegStation
  itself to pair a keypad with; now that the OLEDs are out at each tap
  instead, there's no obvious display left at KegStation to use for it
  (short of adding a 6th, KegStation-only OLED just for this, which
  hasn't been proposed). Both are still viable on top of the same
  `kegcal` CLI commands (see above), so this doesn't block building the
  daemon/CLI itself. The trade-off raised so far: a physical keypad + a
  local OLED means calibration works fully standalone, with no phone or
  network needed — arguably in the spirit of KegStation being a
  self-contained unit, not dependent on Wi-Fi/a browser for its core
  job. A web page is less hardware to build (reuses the same "small
  local web server + form" pattern already used for the Comitup Wi-Fi
  setup page) but means calibration requires a working network and a
  phone/laptop in hand. Was leaning toward keypad+OLED as the real
  interface with a web page as a later convenience layer; the per-tap
  OLED decision makes that lean weaker (extra hardware just for this
  now, rather than reusing something already there) but doesn't rule it
  out — still not committed either way.
