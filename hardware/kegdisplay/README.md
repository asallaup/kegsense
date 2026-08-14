# KegDisplay — Sallaup Electronics

Part of the **Sallaup KegSense** keg-monitoring system, made by
**Sallaup Electronics**.

**KegDisplay** is the per-keg status indicator: a vertical WS2812 LED
strip mounted on the collar's side at each tap, showing that keg's
remaining % as a fill-level bar (more LEDs lit from the bottom = more
left — same read as a fuel gauge). No per-tap MCU, no custom PCB —
**KegStation** (the central Raspberry Pi — see
[`../kegstation/`](../kegstation/)) drives the whole chain directly,
and the strip itself is an off-the-shelf part, just cut to length. See
the revision note below for how this replaced the OLED+MCU approach.

This is a planning doc — no hardware or software has been built yet.
Captures decisions made so far so they aren't lost before implementation
starts (see [`../kegsensor/wiring.md`](../kegsensor/wiring.md) and
[`../keghub/README.md`](../keghub/README.md) for the equivalent docs
that preceded the KegSensor module).

**Revision note**: this design has gone through three full rewrites, kept
in git history rather than deleted outright:
1. Originally an Arduino Nano + MAX485 board per tap, daisy-chained over
   RS-485 with a custom chain-position auto-addressing scheme.
2. Then a bare OLED module per tap wired star-topology through a
   TCA9548A I2C multiplexer at KegStation, dropping the Nano entirely.
3. Then, realizing an OLED at every tap was itself more display than the
   job needed, the per-tap hardware shrank further to just a status LED
   + a pushbutton, with the actual detailed information (brew name,
   weight) moved to a screen at KegStation instead.
4. **This version**: brings the OLED back, but on a much smaller MCU
   with its own onboard I2C - each tap's OLED shows its own brew name +
   weight directly, all the time, no button/KegStation-touchscreen
   detail view needed. The Nano-sized objection that killed revision 1
   doesn't apply this time; the shared-I2C-address conflict that killed
   the mux approach in revision 2 doesn't apply either (each tap's OLED
   is on its *own* MCU's I2C bus, not a bus shared across taps). The MCU
   choice within this revision itself went through several rounds:
   Adafruit Trinket M0 (real hardware I2C, easy USB/Arduino flashing,
   but ~$5-6/unit) -> Seeeduino XIAO SAMD21 (same capability, smaller
   board, similar cost) -> ATtiny10 (tiny and ~$0.30, but no hardware
   I2C/UART and needs a TPI programmer) -> CH32V003 (cheapest of all,
   ~$0.10-0.15, real hardware I2C, but RISC-V + WCH-LinkE is a bigger
   toolchain departure than anything else in this project) ->
   **ATtiny1614 in SOIC-14**, the settled choice: real hardware I2C,
   16KB flash/2KB RAM (enough for real OLED text, unlike ATtiny10's
   1KB), ~$0.60-1.20/unit (far cheaper than Trinket M0/XIAO, only a
   modest premium over CH32V003), programmed over UPDI (simpler than
   ATtiny10's TPI - a USB-serial adapter + one resistor is enough), and
   SOIC-14 is still hand-solderable (unlike QFN packages, which need
   reflow/hot air).
5. **This version**: dropped the OLED+MCU entirely. The real physical
   constraints at the mounting location (~100mm between taps, ~30mm max
   height) kept defeating every attempt to fit the ATtiny1614+OLED+
   connector assembly — landscape reorientation, connector swaps
   (KK-254 vs RJ14 vs audio jack), aggressive layout compaction all hit
   walls, most fundamentally that any locking/panel-mount connector's
   physical plug needs ~12-20mm of depth, which doesn't fit in the
   ~12mm gap left between taps once a board of any reasonable size is
   in place. Back to a WS2812 LED chain (first explored in revision 3),
   but as a 10-LED bar graph per tap instead of a single status LED,
   and with KegStation driving the chain directly — no per-tap
   MCU/logic at all, sidestepping the space problem instead of
   continuing to fight it.
6. **This version**: switched from a horizontal custom-PCB LED bar to a
   **vertical off-the-shelf WS2812B LED strip** mounted on the collar's
   side (~50mm width x ~130mm height available there - a much bigger
   budget than the ~100x30mm the horizontal layout was fighting for).
   Two wins at once: (1) a commercial strip at 140-200 LEDs/m gives
   18-26 LEDs over that length, cut to whatever length is wanted, so
   there's no custom PCB to design/fab at all - just a cut strip with a
   few wires soldered on at each end; (2) a vertical fill-level bar
   reads more intuitively than a horizontal one (same mental model as a
   fuel gauge or thermometer). Nothing below reflects any earlier
   revision.

## Decisions so far

- **Per tap: a commercial WS2812B LED strip (140-200 LEDs/m), cut to
  length, mounted vertically on the collar's side.** No custom PCB, no
  MCU. KegStation lights however many LEDs correspond to the keg's
  remaining % as a bottom-up fill bar. Same chain-position addressing as
  revision 3/5 — purely protocol-level, no firmware/logic at the tap.
- **Topology: daisy chain, 3 conductors (+5V, GND, WS2812 data)** — cut
  strip has these 3 pads at each end; a short pigtail at each end
  carries them to a chain connector.
- **Power: 5V**, matching the Pi's rail, same as every earlier revision.
- **Mounting location: collar's right side, vertical**, not the tap
  face — ~50mm width x ~130mm height available there, established this
  session as the actual space budget (see revision note).

## Superseded (revision 5, custom PCB LED bar) — kept for reference

The horizontal custom-PCB version (generate_schematic.py/generate_pcb.py
in this directory) went through extensive layout work — 10 LEDs down to
5, connector swaps, edge-flush J1/J2 for case-wall cutout access — all
now moot since revision 6 uses a cut length of commercial strip instead
of a custom board. Kept as-is in this directory rather than deleted;
treat as historical, not a current target to keep building against.

## Superseded (revision 4, ATtiny1614+OLED) — kept for reference

- **Per tap: one ATtiny1614 (SOIC-14) + one 0.91" SSD1306 I2C OLED.** The
  ATtiny1614 is its own I2C master for its own OLED — no shared bus, no
  address conflict, no mux (that was revision 2's problem, and it simply
  doesn't arise here since each tap's I2C bus is private to that tap).
  No button, no resistor ladder, no KegStation-side ADC — the OLED just
  always shows its own keg's brew name + weight. See the revision note
  above for the full MCU comparison (Trinket M0/XIAO/ATtiny10/CH32V003)
  that led here.
- **Development workflow: Arduino IDE + megaTinyCore, prototype on a
  SOIC-to-DIP adapter, flash over UPDI, keep a UPDI header on the final
  board.** Concretely:
  1. Write firmware as a normal Arduino sketch (megaTinyCore adds
     ATtiny1614 as a board option, `Wire.h` works for I2C).
  2. Prototype on a breadboard by soldering the chip onto a cheap
     SOIC-14-to-DIP adapter board first, rather than committing straight
     to a custom PCB.
  3. Flash via **SerialUPDI** — a plain USB-to-serial adapter plus one
     resistor between its TX/RX lines, wired to the chip's UPDI pin.
     megaTinyCore supports this directly as an Arduino IDE upload
     method, so it's still just "hit Upload."
  4. Once firmware is solid, solder a chip onto the real per-tap PCB,
     which includes its own **3-pin UPDI header (UPDI/VCC/GND)** so it
     can be reflashed in place later (fixing a bug or tweaking the OLED
     layout after it's already mounted at the tap) without desoldering.
  5. **Field reflashing: temporary cable from KegStation's own UART pins
     to J4, one tap at a time** — a Pi's UART (TX/RX) can run SerialUPDI
     directly, so KegStation itself is the programmer, no separate
     laptop/USB adapter needed. Not a permanent connection (UPDI is
     point-to-point; it can't ride the shared chain bus without hitting
     every tap's chip at once) — walk up to the tap, plug in, flash,
     unplug. J4 stays inside the case (no dedicated access port needed
     in the lid/body — see Still Open) since this is infrequent enough
     that opening the case is an acceptable cost.
  6. **Possible future upgrade, not implemented now**: a bootloader that
     receives firmware over the chain itself (via J1, reusing the same
     "consume my chunk, relay the rest" addressing idea as the brew-data
     relay), removing the need to physically visit a tap at all for
     routine updates. J4/UPDI would still be needed for a blank chip's
     very first flash either way. Deliberately deferred — not worth the
     bootloader complexity until the rest of the system is proven out.
- **Chain addressing: still positional, like the WS2812 version, but now
  relayed by firmware instead of being protocol-free.** KegStation
  streams all 5 kegs' data down the chain in tap order; each ATtiny1614
  reads its own chunk off its "chain in" pin (a bit-banged serial RX),
  keeps that chunk for its own OLED, and relays everything after it out
  its "chain out" pin (bit-banged serial TX) to the next tap. No
  per-tap address to configure, same principle as the LED chain, just
  carrying real data (text) instead of raw color bits.
  - **Pin budget**: ATtiny1614 (SOIC-14) has 14 pins total: VDD, GND,
    UPDI (shared with reset, freed up by the UPDI header above), and 11
    GPIO. 2 go to hardware I2C (SDA/SCL, to the OLED), 2 to chain
    in/chain out, leaving several spare — a much more comfortable
    budget than Trinket M0's 5 broken-out GPIO.
- **Topology: daisy chain**, one cable hopping tap to tap, same as the
  WS2812 version and for the same reason — the chain-position addressing
  scheme requires it.
  - **3 conductors used: +5V, GND, chain data** (one direction only —
    KegStation "down" through the chain; no need for a return path,
    since each tap only needs to receive, not report back). 2 jacks per
    tap (IN from upstream, OUT to downstream), **Molex KK-254 (4-pin,
    2.54mm pitch)** — not RJ14 like KegSensor's jack, switched for board
    size (KK-254's courtyard is ~1/3 RJ14's) while keeping a real
    locking latch, unlike JST-PH (used only for the short internal OLED
    cable, where no latch is needed). 4th contact left unused/spare.
  - **Same known IN/OUT-swap fragility as the WS2812 version, re-accepted
    for the same reason**: chain-in and chain-out are different pins on
    the Trinket, not symmetric, so a swapped cable breaks that tap and
    everything downstream of it. Worth keying/labeling the jacks clearly
    at install time.
  - **Chain fragility**: a disconnected or dead tap breaks every tap
    downstream of it, same as any physical daisy chain — already
    discussed and accepted in the WS2812 revision, still true here.
- **Power: 5V** on the shared rail, matching the Pi's own 5V — the OLED
  module runs fine off 5V directly (most SSD1306 breakouts have their
  own onboard 3.3V regulator). ATtiny1614's own VDD range/regulation
  need still needs confirming (see Still Open) - it may need a small
  local 3.3V regulator on the per-tap board, unlike Trinket M0 which
  handled that internally.
- **OLED-to-board cable: 4-pin JST-PH (2mm pitch).** The lid-to-body run
  is under 2cm, short enough that a compact connector fits better than
  a pin header — hand-solderable, unlike the finer 1mm-pitch JST-SH
  alternative.
- **Mounting location: outside the keezer** — the OLED/ATtiny1614
  assembly sits on the tap's own exterior face, same reasoning as every
  earlier revision: no part of the wiring needs to enter the cold zone.
- **Mechanical split: main board inside the case body, OLED mounted on
  the case lid, connected between them by a short wire harness** (not a
  single rigid board carrying both) - decided when starting the case/lid
  design, still in progress (see Still Open). The OLED's 4-pin header
  (VCC/GND/SCL/SDA) on the main board is exactly this cable's connection
  point, not a directly-soldered display.
- **Physical cable routing: hidden along the collar's exterior, under a
  paintable plastic cord cover** — not routed through the collar's
  interior cavity (both ends are already outside, so dipping into the
  cold zone would be pure downside), and not bored through the solid
  wood either (the collar here is already built and finished — a long
  blind bore through installed wood risks a visible drilling mistake
  with no way to redo it, unlike drilling before assembly). Cable runs
  along an inconspicuous exterior seam (e.g. where the collar meets the
  freezer body) and is covered by an off-the-shelf paintable plastic
  cord cover, painted to match — reads as a deliberate trim detail
  instead of an exposed wire.
- **Not yet built or prototyped** — this whole design came out of
  conversation, not a physical test yet. Same "verify against real
  hardware before calling it done" standard as everything else in this
  project.

## Still open

- **Exact strip part/density** — 140-200 LEDs/m suggested, not a
  specific product picked yet. Also: how many LEDs to actually light
  (cut length vs. how many are addressed) - a longer strip physically
  mounted doesn't have to mean every LED is used.
- **Pigtail-to-chain-connector details** — wire gauge, how the cut
  strip's pads get connected to a 3-wire pigtail, and what connector
  that pigtail terminates in (the JST-PH work from revision 5 may or may
  not carry over - not reconfirmed for this mounting approach).
- **Mounting hardware for the strip on the collar** — most strips are
  adhesive-backed, but whether that alone is enough for a keezer
  (temperature swings, humidity) or something more is needed isn't
  decided.
- **Reverse-polarity protection** — not reconsidered for this revision.
- **KegStation's own side**: the code that computes each keg's % and
  drives the WS2812 chain, and what happens to the brew-name/weight
  display now that neither an OLED nor a touchscreen is in the current
  plan (see [`../kegstation/README.md`](../kegstation/README.md) — likely
  back to web-dashboard-only for that detail).
- `case.scad`, the lid board (`keg_display_lid_module`), the ATtiny1614
  main board's KiCad files, and the revision-5 LED-bar KiCad files
  (`generate_schematic.py`/`generate_pcb.py` in this directory) are all
  obsolete as of this revision — kept in git history, not deleted.
