# KegDisplay — Sallaup Electronics

Part of the **Sallaup KegSense** keg-monitoring system, made by
**Sallaup Electronics**.

**KegDisplay** is the per-keg status indicator: a vertical WS2812 LED
bar in its own enclosure, mounted on the collar's side at each tap,
showing that keg's remaining % as a fill-level bar (more LEDs lit from
the bottom = more left — same read as a fuel gauge). No per-tap MCU —
**KegStation** (the central Raspberry Pi — see
[`../kegstation/`](../kegstation/)) drives the whole chain directly.
An off-the-shelf WS2812 strip is glued or screwed to the front of a
small custom PCB inside the enclosure, which gives it a rigid mount and
carries both chain connectors (see the revision note below for how this
settled). Brew-name display is a separate, experimental add-on — see
[`../kegtag/`](../kegtag/).

This is a planning doc — no hardware or software has been built yet.
Captures decisions made so far so they aren't lost before implementation
starts (see [`../kegsensor/wiring.md`](../kegsensor/wiring.md) and
[`../keghub/README.md`](../keghub/README.md) for the equivalent docs
that preceded the KegSensor module).

**Revision note**: this design has gone through several full rewrites,
kept in git history rather than deleted outright:
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
   fuel gauge or thermometer).
7. **This version**: brought a custom PCB back after all — not because
   the vertical layout was wrong, but to solve two things a bare
   commercial strip couldn't: a rigid mounting surface inside the box,
   and a way to get *both* chain connectors onto the box's bottom edge
   (see "connectors on left/right" below — both need to end up at the
   bottom, and a floppy 3-wire strip has no natural way to route a
   return path back down). Individual WS2812B LEDs are placed directly
   on a 2-layer PCB instead: front layer carries the LED chain bottom to
   top; after the top LED, a via drops the single DATA_OUT signal to the
   back layer, which routes it back down to the bottom-right connector.
   VCC/GND don't need this detour — they're shared rails running the
   full board height on the front layer, tapped directly by both
   connectors.
8. **This version**: swapped the 23 individually-placed LED footprints
   for an off-the-shelf WS2812 strip, glued or screwed to the front of
   the custom PCB. The PCB still solves the same two problems revision 7
   introduced it for (rigid mounting surface, both connectors on the
   bottom edge) — that didn't change. What changed: hand-laying out 23
   LED footprints/nets was more work than buying an assembled strip and
   mounting it. The PCB's job shrinks to rigid backer + both connectors
   + a soldered-wire path (the strip's own DIN/DOUT leads soldered to
   pads) instead of continuous copper running through 23 LED footprints.
   Nothing below reflects revision 7's individual-LED approach.

## Decisions so far

- **Per tap: an off-the-shelf WS2812 LED strip, glued or screwed to the
  front of a custom 2-layer PCB**, mounted vertically inside an
  enclosure on the collar's side. No per-tap MCU — KegStation lights
  however many LEDs correspond to the keg's remaining % as a bottom-up
  fill bar. Same chain-position addressing as every earlier revision —
  purely protocol-level, no firmware/logic at the tap.
- **Topology: daisy chain, 3 conductors (+5V, GND, WS2812 data)**,
  same as every earlier revision.
- **Power: 5V**, matching the Pi's logic level, same as every earlier
  revision — but sourced from its own dedicated supply injected into
  the chain, not drawn through the Pi itself (see
  [`../kegstation/README.md`](../kegstation/README.md) for why: LED
  current draw exceeds what the Pi's own PSU/GPIO can safely provide).
- **Mounting location: collar's right side, vertical**, not the tap
  face — ~50mm width x ~130mm height available there. Confirmed against
  the real keezer, not guessed: tap spacing ~10cm apart horizontally
  (real photo, 5 taps through a single wood plank, plus a direct
  measurement), collar board height 13cm (matches the ~130mm figure
  almost exactly), and the board is confirmed finished wood (despite
  looking unfinished in the photo) — the earlier reasoning against
  drilling a blind bore for cable routing (a visible mistake in
  installed, finished wood, with no way to redo it) holds as originally
  reasoned. Board thickness is the only dimension still unmeasured (see
  Still Open).
- **Housed in a rectangular enclosure** — protects the PCB and gives the
  LEDs a diffuser window instead of exposed dots. Box footprint sized to
  the ~50x130mm mounting budget above.
- **Both connectors live on the box's bottom edge, one on the left, one
  on the right, each with a short wire pigtail to the next tap's box** —
  not top/bottom of the box, even though the PCB inside runs vertically.
  Taps sit ~10cm apart *horizontally* along the collar, so the
  daisy-chain cable between one tap's box and the next needs to run
  sideways; bottom-left/bottom-right connector placement matches that
  real cable path instead of forcing an awkward top-to-bottom-then-across
  route.
- **PCB signal routing**: left connector (chain in) feeds pads at the
  strip's bottom (DIN) end via soldered wire leads. The strip itself
  carries data up its own length front-side; its DOUT lead at the top
  end solders to a pad, where a via drops DATA_OUT to the back layer,
  routing it straight back down to the right connector (chain out) —
  same detour concept as revision 7, now via a soldered wire+pad instead
  of continuous LED-to-LED copper. VCC/GND: the strip's own power leads
  solder to pads tied to shared rails on the front layer spanning the
  full board height, tapped directly by both connectors.
- **Mounting method (glue vs. screw) depends on which strip is
  sourced** — a flexible, adhesive-backed strip (the common type) only
  supports gluing; a rigid-PCB or aluminum-channel strip variant would
  support screws if one is sourced instead. Not decided (see Still
  Open).
- **PCB laid out and DRC-clean, board size settled: 34x132mm**, offset
  from the origin (x: 9.5-43.5mm, y: -2-130mm) — resized/shifted in the
  KiCad GUI from the original 50x130mm placeholder and confirmed as the
  right size. `generate_bar_schematic.py` / `generate_bar_pcb.py` in
  this directory build this board, kept in sync with that GUI edit.
  Which specific off-the-shelf strip to buy is still open (see Still
  Open) but must now fit this board size, not the other way around.
  J1/J2 still near the bottom, outward-
  facing (cable exits sideways), nudged off strict edge-flush/shared-Y
  placement in the GUI to clear each other's and MH2's courtyards after
  the resize. R1/C1 between them (unchanged). TP1-3 (strip's bottom
  GND/VCC/DIN leads) and TP4-6 (strip's top GND/VCC/DOUT leads) remain a
  tight 4mm-pitch cluster of hand-solder test points, replacing the 23
  LED footprints. Mounting holes MH1/MH2 both moved to the board's
  horizontal center in the GUI. ERC/DRC clean aside from known-benign
  warnings (`lib_footprint_mismatch` from UUID regeneration;
  `silk_over_copper` from the connectors' own default pin-1 silkscreen;
  `unconnected_items` since, like every earlier revision's generator
  script, this places components and assigns nets but does **not** emit
  copper traces/vias — it validates physical fit and clearance, not
  routing completeness; the DATA_OUT via + back-layer return trace is a
  routing detail for real layout, not modeled here).

## Superseded (revision 7, individual LEDs on PCB) — kept for reference

- **Per tap: 23x WS2812B-2020 (2.0x2.0mm) LEDs at 5mm pitch (200 LEDs/m)
  soldered directly onto the custom 2-layer PCB** — the smaller 2020
  package (vs. revision 5's 3.5x3.5mm Mini) gave comfortable clearance
  at this tight pitch. Superseded by revision 8's off-the-shelf strip
  glued/screwed to the same PCB — hand-laying out 23 individual LED
  footprints/nets was more generator-script work than buying an
  assembled strip; the PCB's role (rigid mount, both connectors on the
  bottom edge) carries forward unchanged.
- **PCB signal routing (individual-LED version)**: left connector fed
  the bottom LED's DIN directly; data climbed LED to LED on the front
  layer to the top LED's DOUT, where a via dropped DATA_OUT to the back
  layer, routed back down to the right connector. Same detour concept
  revision 8 keeps, just via continuous LED-to-LED copper instead of a
  strip's own leads soldered to pads.
- **PCB laid out and DRC-clean for this construction**:
  `generate_bar_schematic.py` / `generate_bar_pcb.py` in this directory
  build *this* (now superseded) board — 23 LEDs at 5mm pitch, board
  50x130mm, J1 bottom-left / J2 bottom-right both facing outward
  (JST-PH 3-pin horizontal, same footprint/angles as revision 5), R1/C1
  between them. ERC/DRC clean aside from known-benign warnings
  (`power_pin_not_driven` on VCC/GND — same accepted quirk as every
  earlier revision's schematic; `lib_footprint_mismatch` from UUID
  regeneration; `silk_over_copper` from the connectors' own default
  pin-1 silkscreen crossing their own pads). **Not yet regenerated for
  revision 8** — these scripts still model the individual-LED
  construction, not the strip-on-backer-PCB one (see Still Open).

## Superseded (revision 6, off-the-shelf strip) — kept for reference

- **Per tap: a commercial WS2812B LED strip (140-200 LEDs/m), cut to
  length.** No custom PCB. Superseded by revision 7's custom PCB, needed
  to give the strip a rigid mounting surface and to route a return path
  to both bottom connectors (see revision note above) — otherwise the
  core idea (vertical fill bar, ~50x130mm collar-side mounting, no
  per-tap MCU) carries forward unchanged.
- **Topology detail specific to a cut strip**: 3 pads at each end, a
  short pigtail soldered on at each end carrying them to a chain
  connector. Moot once LEDs are placed directly on a PCB instead.

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

- **Which off-the-shelf strip to source** — not chosen. Board size
  (34x132mm) is now settled, so this is a fit-to-board search, not an
  open-ended one: needs a strip whose usable length fits the ~132mm
  board height, with end-lead spacing compatible with the TP1-3/TP4-6
  hand-solder clusters (revisit their exact positions in
  `generate_bar_pcb.py` once a strip is picked, if its real lead spacing
  differs from the current placeholder). Also determines whether glue or
  screws are possible (see "Mounting method" above — needs a rigid-PCB
  or aluminum-channel strip for screw-mounting; a standard flexible
  adhesive-backed strip only glues).
- **Enclosure: first-draft 3D-printable case modeled, NOT verified
  against real hardware yet.** `case_bar.scad` /
  `generate_case_bar.sh` (this directory) build two parts: `base`
  (solid wall — no window, side walls with left/right cutouts for
  J1/J2's cable exit, two PCB standoff posts at MH1/MH2, four corner
  posts for the lid, two mounting flanges on its top/bottom edges with
  wood-screw clearance holes) and `lid` (a frame with the diffuser
  window cut through it over the strip's span, four screw holes to
  close onto the base's corner posts). **The base, not the lid, is the
  face that mounts to the collar** — the lid carries the window and
  must face outward into the room for the LEDs to actually be visible;
  mounting the lid flush against the collar would hide them against the
  wood. Outer footprint ~43x141mm
  (board 34x132mm + margin + wall), depth ~15mm (component/strip
  clearance + board + standoff). Renders cleanly (`openscad`, both
  parts report `Simple: yes`) — see `case_bar_base_preview.png` /
  `case_bar_lid_preview.png`. Component clearance depths (JST-PH body
  height, strip thickness) are typical values, not measured off real
  parts — same "verify before calling it done" standard as the rest of
  this project; don't print for real without checking against actual
  hardware first. Diffuser window material/fit itself is still
  unaddressed (just an open cutout right now, no diffuser panel
  modeled). Two-point standoff mounting (not four-corner) may need a
  card-edge rail added later if the board flexes over its 132mm length
  in practice.
- **Collar board's thickness** — not measured (height 13cm and finished
  status are now confirmed, see above).
- **Wire gauge for the pigtails** at J1/J2 — not decided.
- **Reverse-polarity protection** — not reconsidered for this revision.
- **KegStation's own side**: the code that computes each keg's % and
  drives the WS2812 chain — not written yet. Brew-name/level display
  (ESL hub, tag protocol) is tracked separately, see
  [`../kegtag/`](../kegtag/).
- `case.scad`, the lid board (`keg_display_lid_module`), the ATtiny1614
  main board's KiCad files, and the revision-5 LED-bar KiCad files
  (`generate_schematic.py`/`generate_pcb.py` in this directory) are all
  obsolete — kept in git history, not deleted.
