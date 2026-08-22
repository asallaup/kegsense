# KegStation — Sallaup Electronics

Part of the **Sallaup KegSense** keg-monitoring system, made by
**Sallaup Electronics**.

**KegStation** is the central unit: reads all 5 KegSensor modules over
the wired in-keezer hub connection, drives each tap's WS2812 fill-bar
LEDs directly (see [`../kegdisplay/`](../kegdisplay/) — no per-tap
MCU, KegStation lights however many LEDs correspond to that keg's
remaining %), and hosts a web dashboard mirroring the same information
remotely. Brew-name display is a separate concern, handled (if built)
by the experimental [`../kegtag/`](../kegtag/) add-on and its own hub,
not by KegStation streaming text down the LED chain.

This is a planning doc — no hardware or software has been built yet.
Captures decisions made so far so they aren't lost before implementation
starts (see `hardware/kegsensor/wiring.md` and `hardware/keghub/README.md`
for the equivalent docs that preceded the KegSensor module).

## Decisions so far

- **Platform: Raspberry Pi Zero 2 W, settled — not Pi 4, Pi 5, or a
  larger board.** Originally Pi 4, picked over Zero 2 W solely because
  the (now-dropped, see Touchscreen/display below) Touch Display 2
  needed a DSI connector the Zero series doesn't have — once the display
  requirement changed to a button-driven I2C OLED, that blocker went
  away and Zero 2 W became the smallest/cheapest board that still meets
  every other requirement. Still ruled out vs. Pi 5 for the same reasons
  as before: power budget (Pi 5 draws roughly double idle power and
  wants a 27W supply, inflating the shared-PSU sizing above for headroom
  this project's workload doesn't need) and GPIO library maturity
  (`pigpio`, the battle-tested choice for the HX711's precise bit-banged
  timing, does not support Pi 5's RP1 GPIO chip at all). Zero 2 W's
  SoC (RP3A0) uses the same classic GPIO peripheral family as Pi 3/4,
  not Pi 5's RP1, so `pigpio` and the whole KegSensor-interfacing scheme
  below carry over unchanged. Has built-in Wi-Fi (2.4GHz only, unlike Pi
  4's dual-band — irrelevant here, Comitup's captive portal works fine
  over 2.4GHz) + Bluetooth 4.2/BLE (also unused by KegStation itself),
  so still no wireless add-on hardware needed. Fixed at 512MB RAM (no
  variants) — expected to be plenty given the now-lighter workload (no
  browser/desktop GUI, just the C daemon, the button/OLED interface, and
  a modest web dashboard), though with less margin than the Pi 4 RAM
  options would have had.
- **Connectivity**: reads the 5× KegSensor modules over the wired hub
  connection (shared SCK + 5× DT + power, see
  `hardware/kegsensor/wiring.md` and `hardware/keghub/README.md`) —
  direct to the Pi's GPIO header, 3.3V logic throughout, no level
  shifters needed. No Wi-Fi/radio inside the keezer itself (unchanged
  from the original hub design constraint) — KegStation sits outside the
  keezer, so its own Wi-Fi is unrelated to that constraint.
  - **Bench/debug connector, settled: a 6th, dedicated DT channel — not
    shared with any of the 5 production kegs.** A second RJ14 (6P4C)
    jack, same connector type as KegSensor's own J7, mounted directly on
    KegStation, for plugging in and testing a spare KegSensor without
    touching KegHub or any deployed keg. Shares the common SCK/3.3V/GND
    rails (safe — those are shared across all kegs anyway) but gets its
    **own dedicated DT GPIO pin**, deliberately not reusing one of the 5
    production DT lines: sharing a DT line would mean two HX711 modules
    could end up driving the same GPIO simultaneously if a real keg is
    plugged into KegHub at the same time as a test sensor here — a real
    electrical bus-contention risk, not just a software mixup. One extra
    GPIO pin is cheap on Zero 2 W's 40-pin header (no touchscreen, and
    discrete buttons instead of a component-heavy nav switch, both free
    up pins), so paying that cost to remove a real correctness risk is
    worth it. The daemon reads this 6th channel too, but keeps it out of
    the normal 5-keg dashboard/fill-bar logic — surfaced only through a
    separate bench-test view, not mixed into live readings.
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
    KegDisplay LED chain and web dashboard just reads that file —
    simplest possible hand-off, easy to debug by hand (`cat` the file),
    no IPC to build or maintain. Chosen over a Unix socket/local IPC
    (more real-time, more moving parts) and over having the C program
    also drive the LED chain/dashboard directly (would remove the
    option to pick a different, easier language for that higher-level
    part later).
  - **GPIO library: `pigpio`.** The traditional, most battle-tested
    choice for the HX711's precise bit-banged clock timing — viable now
    that Pi 4 is settled (below), unlike on Pi 5 where it doesn't
    support the RP1 GPIO chip at all.
  - **Disconnected-cable detection: a per-keg DT timeout watchdog,
    settled.** The RJ14 wiring has no spare conductor for a dedicated
    presence-detect signal (all 4 — GND/VCC/SCK/DT — are already used),
    so detection is inferred from HX711 protocol behavior instead: each
    keg's DT line should pulse low on every new conversion (~100ms or
    ~12.5ms depending on the HX711's rate setting). If a keg's DT line
    produces no valid ready-pulse within 2-3× that interval, the daemon
    marks that keg as **not responding** rather than reporting a stale
    or garbage weight. The DT input needs an internal or external
    pull-up so "disconnected" reads as a consistent, predictable HIGH
    instead of noisy floating, making the timeout check reliable
    instead of racy. Surfaced as a distinct per-keg status in the
    readings file (not folded into the weight/percentage fields) — see
    Display + input below for how it's shown on-unit, and note
    KegDisplay's per-tap fill bar shouldn't just show 0% for this case
    either, since that reads as "keg is empty" rather than "sensor
    isn't talking" (still open, see KegDisplay's own README).
- **Tare/weight calibration: must work fully standalone at the unit
  itself — no web browser and no external device (phone/laptop/SSH)
  required.** This is a hard requirement, not a convenience preference,
  so the on-unit button + OLED interface (below) is the primary
  calibration interface. A `kegcal` CLI program still exists underneath
  as the actual implementation (and an SSH-accessible fallback for
  development/debugging) — the button/OLED UI shells out to the same
  commands rather than duplicating calibration logic, same relationship
  originally planned between `kegcal` and a future dashboard, just with
  the button/OLED interface as the primary caller instead of the web
  dashboard.
  - `kegcal tare <keg>` — reads that keg's *current* raw ADC value (from
    the daemon's readings file) and stores it as the tare reference.
  - `kegcal setfull <keg> <grams>` — same, but stores it as the "full"
    reference point at a known weight in grams. That known weight can be
    either the actual full keg's spec weight (so the reference doubles as
    the "how much is left" baseline) or a separate known calibration
    mass — the tool works the same either way, this only affects what
    number you type in.
  - **On-unit UI note**: the button/nav-switch interface offers Set Full
    as a **preset selection** (e.g. 5/10/15/20kg), not free numeric
    entry — implementing the "actual full keg's spec weight" option
    above via list-selection rather than typing a number, consistent
    with every other step in the flow being a scroll-and-select action
    (see Display + input above). The presets must be the *real* spec
    weight (liquid + keg tare) of whatever keg sizes are actually in
    use, not round numbers — an inaccurate preset introduces a
    systematic error across every future reading for that keg, since
    it directly anchors the calibration math. `kegcal setfull` itself
    is unaffected — it still just takes a gram value; only the on-unit
    UI constrains which values are offered.
  - **On-unit calibration wizard, designed**: tare and setfull are one
    continuous guided flow, not two separate manual actions, with a
    confirmation prompt gating each raw-ADC read so a mistimed press
    can't bake in a bad calibration point:
    1. Select **Tare** from the keg's menu (nav switch)
    2. Prompt: "Place empty keg on scale, then confirm" — user places
       it, presses select
    3. System reads the current raw ADC → internally calls
       `kegcal tare <keg>`, stores it as the 0% reference
    4. Prompt: select a known full weight (the preset list above)
    5. Prompt: "Place [selected weight] on scale, then confirm" — user
       places the full keg (or a calibration mass matching that
       weight), presses select
    6. System reads the current raw ADC → internally calls
       `kegcal setfull <keg> <grams>` with the chosen preset value
    7. Both calibration points now stored — the daemon can compute
       that keg's tare↔full linear scale from here on
    - **A Back/cancel option at every confirmation prompt** — lets the
      user back out if the keg isn't actually placed right or the
      wrong preset got selected, rather than being forced through to a
      bad read.
  - Calibration values live in a separate config file (e.g.
    `calibration.json`), which the daemon just re-reads on its normal
    cycle — no signaling/IPC needed for `kegcal` to take effect.
  - The daemon's readings file includes both the raw ADC count and the
    calibrated weight (once calibration exists) per keg, since `kegcal`
    needs to read the live raw value to know what to record.
  - **Not yet built** — see below.
- **Per-tap indicator is just an LED fill level now, no per-tap
  detail/MCU at all.** Each tap's WS2812 bar (see
  [`../kegdisplay/README.md`](../kegdisplay/README.md)) is lit directly
  by KegStation over the shared chain — no brew name, no numeric
  weight, no OLED, no per-tap microcontroller. This superseded both the
  earlier button + resistor-ladder + KegStation-touchscreen scheme and
  the later ATtiny1614+OLED-per-tap scheme (see git history and
  KegDisplay's own revision note) — no button/detail hardware to read
  at any tap.
  - **Wiring run this still creates**: KegStation sits outside the
    keezer (see System overview in the root README), but taps are
    mounted at the keezer itself, so a physical run out to each tap is
    still needed regardless of what's at the far end — a wired
    connection either way (consistent with the no-WiFi-in-the-keezer
    rule, which is about radios, not wired signals).
  - **KegStation's job for this chain**: light however many LEDs
    correspond to each keg's remaining % as a bottom-up fill bar, in
    tap order down the KegDisplay daisy chain (see the chain-position
    addressing scheme in KegDisplay's own README) — not yet
    implemented, see Still Open.
- **Power: one shared 5V supply, star-wired — not drawn through the
  Pi's own GPIO pin/trace.** A single 5V PSU, sized for worst-case total
  draw (Pi + KegSensor bus + KegDisplay LEDs), feeds two separate direct
  wire runs: one straight to the Pi (its own 5V input), one straight to
  the KegDisplay chain's power input — neither run passes through the
  other. The actual hard requirement was never "two physical supplies,"
  it was "LED current must never pass through the Pi's own GPIO 5V
  pin/trace" (see Why below) — one adequately-sized PSU with star wiring
  satisfies that just as well as two separate PSUs would, with less
  hardware.
  - **Why the Pi can't just pass LED current through**: WS2812 LEDs draw
    up to ~60mA each at full white (20mA × 3 channels). ~18-26 LEDs/tap
    × 5 taps ≈ 130 LEDs total → up to ~7.8A (~39W) worst case,
    realistically a few amps even at moderate brightness — more than the
    Pi's GPIO 5V pin/trace is rated to pass through, regardless of what
    supplies it. Standard WS2812 practice regardless of platform: the
    LED chain's power connects directly to its supply, not routed
    through the controller board.
  - **Tradeoff accepted by sharing one PSU**: an LED-side short/
    overcurrent event could brown out the whole shared supply, taking
    the Pi (touchscreen/calibration/reset) down with it — two
    independent PSUs would isolate that risk, one shared PSU does not.
    Accepted here in favor of one fewer component.
  - **PSU model: Mean Well GST60A05-P1J (5V, 6A, 30W), settled — paired
    with a mandatory software brightness/current cap.** Theoretical
    worst case (130 LEDs × 60mA full-white + Pi's ~1.5A) is ~9.3A, well
    past this unit's 6A rating — Mean Well's built-in overload
    protection fails safe (hiccup-mode shutdown) rather than
    dangerously, but a trip still browns out the Pi along with the
    LEDs (see Tradeoff above), so the LED-driving code (see Still Open)
    **must** cap total simultaneous current with margin under 6A —
    e.g. single-channel color instead of white, and/or an explicit
    brightness ceiling — not just assume typical usage stays low.
    Picked over the 10A Mean Well LRS-50-5 alternative (which needs no
    software cap) for its smaller size (125×50×31.5mm captive-cable
    wall-wart vs. 128×97×38mm screw-terminal box) and simpler
    plug-and-play wiring (captive DC cable + standard IEC C14 cord,
    vs. terminating both AC and DC leads by hand).
  - **Physical implementation: a plain fixed 5V DC power brick
    (the GST60A05 above), not a USB-C PD charger.** A generic
    USB-C PD wall charger's default/fallback output (before any
    negotiation) is typically just 5V at a modest current (often 3A) —
    getting more current specifically *at* 5V, rather than the charger
    bumping voltage up instead, needs either a PD-trigger chip
    negotiating for it or a charger that happens to default that way,
    neither guaranteed. A plain fixed-5V brick sidesteps that entirely:
    no negotiation, current rating is just whatever the brick is rated
    for. Its 5V/GND wires go into a small **non-negotiating USB-C
    breakout board** (just exposes VBUS/GND pads with basic CC
    pull-down resistors, no PD chip) mounted as the single external
    power-entry connector on the KegStation enclosure — the Pi's own
    onboard USB-C port stays unused/hidden inside the case. From the
    breakout's pads, two star-wired runs go out: one to the **Pi's GPIO
    5V pin** (bypassing its onboard USB-C port), one straight to **J1's
    5V/GND** for the LED chain — same star topology as before, just with
    a concrete connector at the wall-facing end instead of bare PSU
    leads.
  - **Considered and rejected: an internal 220V AC→5V DC module** (e.g.
    Mean Well RS-25-5), with just a mains cord entering the enclosure
    instead of an external DC brick. Rejected because it brings mains
    voltage inside a custom DIY enclosure — a different safety class
    than a certified external wall-wart, needing its own fusing,
    creepage/clearance, and an isolated compartment to get right, none
    of which is worth taking on for a one-off hobby build vs. buying an
    already UL/CE-certified external supply.
  - **Also considered and declined: a panel-mount IEC C14 inlet on the
    enclosure with the PSU module mounted inside it** (safer than the
    fully-DIY version above, since both the inlet — typically bundled
    with its own fuse holder/switch — and the PSU module itself would
    still be pre-certified parts). Declined anyway to keep it simple:
    the external brick stays external, KegStation's only power connector
    is the low-voltage USB-C breakout.
  - See `power_wiring_diagram.png` (`generate_power_wiring_diagram.py`)
    for the star-topology layout: the Pi and the KegDisplay chain each
    run their own wire straight back to the shared PSU. The PSU's 5V/GND
    and the Pi's DATA line stay separate conductors electrically but
    physically converge at J1 (KegDisplay's existing 3-pin JST-PH
    chain-in connector) into one cable for the run out to tap 1 —
    bundling into one physical cable is fine, it's only the electrical
    source of each conductor that has to stay separate.
- **One external-to-the-Pi component needed: a logic-level shifter IC
  on the KegDisplay DATA line.** KegHub/KegSensor need none (3.3V logic
  throughout, see Connectivity above) — but KegDisplay's WS2812 strip is
  a 5V logic part, expecting a DATA-high signal above roughly 0.7×VDD ≈
  3.5V, and the Pi's GPIO only outputs 3.3V. That's marginal enough
  (a well-known flaky case for Pi+WS2812 projects, especially at the
  *first* LED — every LED after that regenerates the signal at its own
  full 5V output) that a small one-chip level shifter (e.g. 74AHCT125 or
  74HCT14) belongs between the Pi's DATA GPIO pin and J1's DIN. One
  small IC, only needed at that single connection point, powered off the
  same shared 5V rail. **Not yet added to the BOM/wiring** — see the
  updated `power_wiring_diagram.png`.
- **PIR motion sensor for occupancy-based LED power saving: HC-SR501,
  settled.** The KegDisplay chain doesn't need to stay lit when nobody's
  in the room — running all 5 taps' LEDs continuously is the dominant
  chunk of the power budget the GST60A05 (above) is already sized close
  to the edge of. The HC-SR501 (~$1-2, 3-pin VCC/GND/OUT) wired to one
  Pi GPIO pin detects room entry; its digital output is already
  3.3V-logic level, so — unlike the WS2812 DATA line — **no level
  shifter needed** for this one. Another small external-to-the-Pi
  component, but a simple, well-supported one.
  - **Behavior**: motion resets an inactivity timer in the LED-driving
    code; while the timer's running, the chain shows the normal
    fill-bar; on timeout with no further motion, the chain **dims to a
    low brightness** (settled — not a full blank), cutting most but not
    all of the LED power draw while keeping a faint always-visible
    fill-level readable at a glance, then returns to normal brightness
    on the next motion event.
  - **Mounting location: on the KegStation enclosure itself, settled.**
    No remote sensor needed — KegStation already sits in the same room
    as the keezer (see System overview in the root README), so a PIR
    mounted on its own case covers room-entry detection without a
    separate wired/wireless sensor unit.
  - **Inactivity timeout: user-configurable, settled** — not a
    hardcoded constant. Lives in the same config file the daemon
    already re-reads on its normal cycle (alongside `calibration.json`,
    see Tare/weight calibration above), so it's adjustable without a
    code change or restart-losing edit — a sensible default ships, but
    the actual duration is a setting, not a fixed value baked into the
    LED-driving code.
  - **Dimmed brightness level: 15% of normal, settled** — low end of
    the tradeoff (favors power savings over glance-readability from
    across the room), still configurable like the timeout above rather
    than hardcoded, 15% is just the shipped default.
  - **Not yet decided**: the default timeout duration.
- **Two distinct reset mechanisms: soft reset via power cycling (no
  dedicated button), factory reset via a dedicated physical button.**
  - **Soft reset = power off/on.** Just reboots the Pi/services, no data
    touched (WiFi creds, calibration all survive) — no dedicated button
    needed, a power switch (or just unplugging) already does this.
  - **Factory reset = a recessed pinhole button** (needs a pin/paperclip
    to press, like a router's reset — not something bumped by accident),
    wired to a GPIO the daemon watches. Held ~5-10s: clears WiFi
    credentials (falls back to Comitup's setup portal) and wipes
    `calibration.json`. Deliberately a physical button, not a
    software menu item — has to work even if the display UI or
    software is hung/misconfigured, which is exactly the case a factory
    reset needs to recover from.
- **Display + input: a 4.0" color IPS TFT (ILI9488, 480×320, "No Touch"
  variant) plus physical navigation buttons, not a touchscreen.**
  Superseded an intermediate plan (2.42" monochrome I2C OLED, see git
  history) — chosen over that OLED specifically for future headroom:
  a 480×320 color panel leaves real room to grow the on-unit UI later
  (WiFi signal bars, brew name, per-keg level graphs, multiple fields
  at once) without another hardware swap, which the OLED's 128×64
  monochrome canvas couldn't accommodate gracefully. Both options were
  chosen over the official Raspberry Pi Touch Display 2 (5", SC1975,
  ~$40/€53) to cut cost — that touchscreen was the single largest line
  item in KegStation's BOM, and dropping it also unblocked the Platform
  change to Zero 2 W above (the Touch Display 2's DSI requirement was
  the only thing ruling Zero 2 W out). Buttons still satisfy the
  standalone-calibration hard requirement below just as well as a
  touchscreen — the touchscreen was originally picked for being the
  *simplest* single-component option ("no separate buttons/encoder to
  wire up"), not because buttons don't work.
  - **"No Touch" variant, deliberately** — a touch variant exists on the
    same listing, but adding touch back would partly undo the reason
    the Touch Display 2 was dropped, and the design already commits to
    buttons for input.
  - **Interface: SPI** (~8 pins without touch: VCC, GND, CS, RESET, DC,
    SDI/MOSI, SCK, LED backlight) — more GPIO than the OLED option's 2
    pins (SDA/SCL) would have used, but Zero 2 W's 40-pin header still
    has plenty of room alongside the navigation buttons, PIR sensor, and
    factory-reset button.
  - **UI approach: a lightweight embedded graphics library** (e.g.
    LVGL-style), not a browser/desktop stack — keeps the richer color UI
    well within Zero 2 W's 512MB RAM, same conclusion as the OLED plan
    reached, just confirmed explicitly for the bigger screen too.
  - **Driver note**: at least one buyer of this exact listing received
    an ILI9484-branded chip instead of the advertised ILI9488 ("tho
    functionally perfect") — worth being ready to try adjacent
    ILI948x drivers in software if the advertised one doesn't
    immediately work, same generic-module caveat as the OLED's
    SSD1306-vs-SSD1309 mismatch.
  - **Input: a 5-way tactile navigation switch (up/down/left/right +
    center select), settled — not discrete buttons, not a rotary
    encoder.** 5 GPIO pins, each a simple digital read (no quadrature
    decoding). Chosen over a rotary encoder specifically because the
    on-unit UI is planned to grow into a genuinely 2D layout later
    (multiple screens/tabs navigated left/right, e.g. WiFi signal,
    brew info — see Display note above) — a rotary encoder only gives
    one rotational axis, which fits a purely linear list-menu well but
    not a 2D one. Traded away the encoder's main advantage (fast,
    precise numeric entry) deliberately, since the one place that
    mattered — Set Full's weight value — moved to preset selection
    instead (see Tare/weight calibration below), removing the need for
    free numeric entry entirely. Not yet wired — GPIO pin assignment
    not yet decided (see Still Open).
  - Still satisfies "no per-tap detail/MCU" below — this is KegStation's
    own on-unit display, unrelated to the per-tap LED fill bars.
  - **Sensor-connection status: red/green per-keg indicator, settled.**
    Reflects the DT timeout watchdog above directly — green means that
    keg's HX711 is responding normally, red means it's not (cable
    unplugged, unpowered module, or a dead sensor — the daemon can't
    distinguish which, just that the keg isn't reporting). Shown
    per-keg on the main screen alongside each keg's fill level, so a
    disconnected sensor is obvious at a glance rather than silently
    reading as an empty keg.

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
  interfacing daemon (Python is the natural fit for the Pi's web
  library support, but not yet committed to) — the daemon just needs to
  read a file, so it can be written in anything.
- Whether to build a small interface PCB (breaking out the hub's RJ45
  connection and the KegDisplay chain's UART-ish GPIO pins to the Pi's
  header) or wire it directly on a protoboard/HAT — these are native Pi
  GPIO peripherals, no special adapter needed, unlike the original
  RS-485 design's USB-RS485 requirement.
- **KegStation's own KegDisplay-chain code**: the piece that reads the
  daemon's readings file and lights each tap's LED fill bar to match
  its keg's remaining % — not yet written (see
  [`../kegdisplay/README.md`](../kegdisplay/README.md) for the chain
  protocol's own still-open details). **Must include a current/
  brightness cap** (color choice + max brightness ceiling) keeping
  total worst-case draw safely under the GST60A05's 6A — see Power
  above for why this is a hard requirement, not a nice-to-have. **Must
  also include the PIR-driven occupancy timer** (see PIR motion sensor
  above) that dims the chain when the room's been empty past the
  timeout.
- **Calibration UI's own screen flow — now designed**, see the on-unit
  calibration wizard under Tare/weight calibration above. Not yet
  implemented in code, and GPIO pin assignment for the 5-way nav
  switch isn't decided either.
- Web dashboard framework, exact GPIO pin mapping for the shared-SCK +
  5×DT KegSensor scheme (now 6×DT including the dedicated bench/debug
  channel above), and the on-disk format/path for the readings file the
  C daemon writes.
- Physical enclosure for KegStation itself (separate from the KegSensor
  case already built) — depends on the display/button decision above,
  and now also needs a pinhole cutout reaching the factory-reset button.
- **Factory-reset daemon logic and GPIO pin choice** — not yet written;
  needs to debounce/time the ~5-10s hold, then clear WiFi creds +
  `calibration.json` and restart the relevant services.
- **LED supply sizing and injection point** — exact PSU wattage (depends
  on final LED count once a strip is picked, and whatever brightness/
  color policy the fill-bar code ends up using), and where in the
  KegHub/KegDisplay wiring the injected 5V actually connects.
