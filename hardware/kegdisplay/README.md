# KegDisplay — Sallaup Electronics

Part of the **Sallaup KegSense** keg-monitoring system, made by
**Sallaup Electronics**.

**KegDisplay** is the per-keg display: a small board mounted at/over
each keg's own tap, showing that keg's brew name and weight/%
remaining — right where you're pouring from, not on one shared display
listing all 5 kegs. One per keg, daisy-chained back to **KegStation**
(the central Raspberry Pi unit — see [`../kegstation/`](../kegstation/)).

This is a planning doc — no hardware or software has been built yet.
Captures decisions made so far so they aren't lost before implementation
starts (see [`../kegsensor/wiring.md`](../kegsensor/wiring.md) and
[`../keghub/README.md`](../keghub/README.md) for the equivalent docs
that preceded the KegSensor module).

## Decisions so far

- **Board: Arduino Nano + OLED on one combined PCB, mounted via
  headers.** The Nano sockets into female headers rather than being
  soldered/bare-chip — swappable without desoldering if one fails. The
  OLED is a **0.96" SSD1306, I2C** — wired directly to its own Nano over
  short local I2C traces on the same PCB, no cable or connector for that
  link (it's the RS-485 run back to KegStation that's the long one, not
  this).
- **Why not just 5 bare I2C OLEDs straight to the Pi**: cheap small
  OLEDs like the SSD1306 ship at a fixed I2C address (usually 0x3C) —
  putting 5 on one bus directly doesn't work, at most 2 could coexist by
  address alone. An I2C multiplexer (TCA9548A) or per-display SPI
  chip-selects were both considered and ruled out in favor of the
  Nano-per-tap design below, which solves both the addressing problem
  *and* the long-cable-run problem in one move.
  - **Why this solves addressing**: an OLED driver chip's I2C address is
    fixed in hardware, but a microcontroller's address (here, its node
    address on the RS-485 line) is just a value set in its own firmware
    — freely chosen, no collision between the 5 KegDisplay boards even
    though every OLED behind them answers to the same fixed address
    locally.
  - **Why RS-485, not I2C, for the run back to KegStation**: I2C's
    open-drain bus has a real capacitance/distance budget that gets
    tight over long or multi-drop cable runs; RS-485 is a differential
    signaling standard built specifically for long, noisy, multi-drop
    runs (the same class of problem as industrial sensor networks).
- **RS-485 transceiver: MAX485** (the standard, cheap choice). KegStation
  needs a USB-to-RS485 adapter or HAT to get onto the same bus.
- **Daisy-chain connector: RJ12 (6P6C)** — the same physical jack body as
  KegSensor's "RJ11" (which is actually RJ14, 6P4C — see
  [`../kegsensor/wiring.md`](../kegsensor/wiring.md)), just with all 6
  positions wired instead of 4. Chosen over screw terminals (bulkier) or
  JST-XH (needs crimped cables you can't buy pre-made as easily) since
  it reuses connector hardware and crimping tools this project already
  has, for a short run where RS-485's longer-distance robustness isn't
  even strictly needed — it's used here mainly for the clean multi-drop
  daisy-chain electrical behavior, not because the distance demands it.
  Not a real telecom RJ12 pinout — like KegSensor's connector, this
  project defines its own pin convention (below), not an official
  standard.
  - **Two jacks per board (IN/OUT), wired in parallel** — one cable hops
    from KegStation to keg 1's board, out to keg 2's, and so on, instead
    of 5 separate home-run cables. RS-485 actively prefers this daisy-
    chain topology (star wiring causes reflections). A bare OLED
    wouldn't have this connector pattern — only the Nano side does.
  - **6 conductors used**: A, B (RS-485 differential pair), GND, +V,
    ENABLE (see addressing, below), +1 spare.
  - **Cable caution — same gotcha as KegSensor's RJ11 cables**: flat
    silver-satin style phone cables only preserve pin order end-to-end
    if crimped "straight through" — crimping both plugs facing the same
    way on a flat cable actually mirrors the pin order at one end (the
    classic old-telephone-cord gotcha). Matters more here than for
    KegSensor's 4-wire cable: a mirrored 6-wire cable wouldn't just flip
    one signal, it could put A/B backwards, cross ENABLE onto the spare,
    or worse, feed +V into what the far end expects to be GND. Verify
    pin-for-pin continuity with a multimeter before trusting any cable
    — don't rely on a "patch cable" label, since that terminology isn't
    reliably used for phone-style cords the way it is for Ethernet.
  - **Termination**: a 120Ω resistor at each *end* of the chain
    (KegStation end and the last KegDisplay) — not at the intermediate
    boards — to prevent signal reflections. Cheap insurance even on a
    short, slow bus.
- **Addressing: chain-position auto-addressing, chosen over hardware
  address switches deliberately.** Switches (a rotary hex switch or DIP
  bank per board) are the simpler, more robust option at this scale (5
  hand-built units) and were the initial recommendation — auto-
  addressing was picked anyway as the more interesting thing to build,
  with its real trade-off understood going in, not overlooked.
  - **Wiring: auto-detecting `ENABLE`, not a fixed `ENABLE_IN`/
    `ENABLE_OUT` pin pair.** Each board's two RJ12 jacks get their own
    GPIO for the `ENABLE` conductor (no fixed upstream/downstream role
    per jack) — at boot, a board checks which of its two `ENABLE` pins
    is already driven high; whichever one is, that jack is upstream, and
    the board then drives the *other* jack's `ENABLE` pin high to enable
    the next board in the chain. KegStation permanently drives `ENABLE`
    high on its own connector, enabling whichever board is plugged in
    first (KegDisplay #1). Chosen over fixed `ENABLE_IN`/`ENABLE_OUT`
    pins specifically so a cable plugged into the "wrong" jack (an easy
    mistake with two visually-identical RJ12 jacks) still works instead
    of silently breaking the chain past that board — see
    `enable_wiring_options.png` (generated by
    `generate_enable_wiring_diagram.py`) for a side-by-side of both
    schemes and the failure case this avoids.
  - **Discovery handshake** (Pi-driven, over the RS-485 line): Pi
    broadcasts "any enabled, unaddressed board, respond"; only the one
    currently-enabled blank board answers; Pi assigns it the next
    address; that board drives its downstream jack's `ENABLE` pin high
    (per the auto-detect logic above), waking the next one in the chain;
    repeat until a broadcast gets no response.
  - **Address persists after first assignment** (stored in EEPROM, not
    just RAM) — a board that already knows its address skips discovery
    entirely on future boots and starts responding immediately, with no
    dependency on being "woken" by the board before it. This confines
    the chain-dependency fragility to *initial commissioning only*: once
    all 5 have been addressed once, a board dying later doesn't take its
    downstream neighbors down with it during normal operation.
  - **Residual risk, by design, not overlooked**: a board that already
    has a stored address must still run its upstream-detection and
    drive its downstream jack's `ENABLE` pin high immediately on every
    boot (not just its own first one), purely so a *replacement* board
    further down the chain can still be discovered later. So: a
    newly-inserted/replacement board can only be discovered if every
    board between KegStation and it is currently alive and passing its
    enable signal through. Narrower and less likely than "any dead board
    breaks everything downstream," but still real — worth remembering at
    replacement time.
  - **Protocol on top of RS-485: Modbus RTU** — established, off-the-
    shelf, existing Arduino libraries, so no custom protocol to design/
    debug. Independent of the chain-position addressing scheme above:
    addressing decides *what* Modbus address a board ends up with,
    Modbus RTU itself is just the request/response framing on top of
    that. KegStation is the Modbus master and polls each KegDisplay by
    its assigned address; KegDisplay boards are slaves, they only ever
    respond, never initiate.
- **Power: 12V**, distributed down the same RJ12 daisy-chain cable as
  the RS-485 signal (A, B, GND, +V, ENABLE) — RS-485 itself doesn't
  carry power (unlike PoE), but nothing stops running power on separate
  conductors in the same cable, so no separate power supply is needed at
  each KegDisplay. The chain as a whole needs its own 12V supply,
  separate from the Pi's own 5V one; exact current/wattage rating still
  depends on chain length and final board count (see Still Open).
  - **No separate regulator needed on the board**: the Nano module
    already has its own onboard 5V regulator, accepting 7–12V directly
    on its VIN pin — 12V sits right at the top of that range, not
    beyond it. Feeding the chain's incoming +V straight into the Nano's
    VIN and tapping its own 5V output pin to power the OLED and the
    MAX485 removes a component that would otherwise be needed.
- **Reverse-polarity protection**: a P-MOSFET high-side protection
  circuit sits in the +V line right where the RJ12 cable's power enters
  the board, guarding against a reversed/miscrimped cable. See
  `power_protection.png` (generated by
  `generate_power_protection_diagram.py` — regenerate after editing that
  script with `python3 generate_power_protection_diagram.py`).
  - **Q1 (P-channel MOSFET)**: Source ties to the incoming, possibly-
    reversed +V pin; Drain feeds the protected +V rail onward to the
    Nano's VIN.
  - **R1 (10kΩ)**: pulls the Gate down toward the board's own GND
    reference (tied to the cable's GND pin) — this is what makes the
    protection actually work. Correct polarity: Source sits well above
    Gate (Vgs strongly negative) → MOSFET conducts. Reversed: the GND
    pin ends up carrying the real +V, so Gate ends up *above* Source
    (Vgs positive) → MOSFET blocks, board just doesn't power up instead
    of getting damaged.
  - **D1 (optional)**: a small zener from Gate to Source, clamping Vgs
    in case a fault ever delivers more voltage than expected. Skippable
    if minimizing part count matters more.
  - **A real mistake caught before finalizing, not just assumed
    correct**: the first draft had R1 wired from Gate to *Source*
    instead of Gate to GND, which would have given ~0V Vgs and never
    turned the MOSFET on at all, in either polarity. Caught by working
    through the correct-vs-reversed cases explicitly (what voltage ends
    up where, on each pin, under each scenario) rather than trusting the
    first sketch.
  - A/B and ENABLE don't get the same protection treatment, and don't
    need it: RS-485 transceivers like the MAX485 are built to tolerate
    an A/B swap (inverts the signal, doesn't damage the chip — the most
    common RS-485 wiring mistake there is), and ENABLE crossed with A,
    B, or the spare pin is a similar low-voltage logic-level mixup, not
    a damage risk. Only GND/+V reversal actually threatens the hardware,
    so that's the one pair worth active protection.
- **Status LED: bi-color (yellow/green, common-cathode, 3-lead), driven by
  2 Nano GPIO pins** through current-limiting resistors — separate pins
  from the ENABLE detection and RS-485 lines, mounted somewhere visible
  on the board without opening anything up.
  - **Yellow (solid)**: board has power but no address yet — covers both
    "waiting its turn" (upstream board hasn't enabled it) and "enabled,
    mid-discovery-handshake."
  - **Green (solid)**: board has an address and is being actively polled
    by KegStation — i.e. it has received a valid Modbus RTU request
    addressed to it within the heartbeat timeout (see below).
  - **Green (blinking)**: board has an address but has *not* received a
    valid Modbus request addressed to it within the heartbeat timeout —
    covers a dead upstream cable, a crashed KegStation poll loop, or
    this board itself losing the bus, without collapsing that into the
    same solid green as "everything's fine." Reverts to solid the moment
    another valid request for its address comes in.
  - **Off**: no power. Free — doesn't need firmware, it's just the LED
    having no supply.
  - **Heartbeat timeout**: each board runs its own watchdog timer, reset
    on every valid Modbus request addressed to it (not just any traffic
    on the shared bus — RS-485 is multi-drop, other boards' polls don't
    count). Exact timeout value not yet tuned — needs to be a small
    multiple of KegStation's actual poll interval once that's decided,
    long enough to not false-trigger on a single dropped frame.
- **Not yet built or prototyped** — this whole design came out of
  conversation, not a physical test yet. Same "verify against real
  hardware before calling it done" standard as everything else in this
  project.

## Still open

- **The RS-485 chain's current/wattage budget at 12V** — voltage is
  decided, but the actual supply still needs sizing once chain length
  and final board count (currently 5) are locked in.
- KiCad schematic/PCB project — not started. Next concrete step once the
  component list above is final.
- Physical mounting method at/over each tap.
- The physical cable path from KegStation out to keg 1's board (then
  daisy-chained on from there, so only that first leg needs separate
  scoping).
- Exact MOSFET/regulator part numbers (Q1, R1's exact value tolerance,
  whether D1 is populated) — the circuit topology in
  `power_protection.png` is settled, specific parts aren't yet.
- **Status LED heartbeat timeout value and KegStation's Modbus poll
  interval** — the blinking-on-missed-heartbeat behavior above is
  decided, the actual numbers aren't; the timeout needs to be set as a
  multiple of whatever poll interval KegStation ends up using, which
  isn't decided either (depends on the KegStation daemon design, see
  `../kegstation/README.md`).
