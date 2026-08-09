# Keg Sensor & In-Keezer Hub Wiring

Covers the sensor layer only: per-keg load cell + HX711, the RJ11 run to the
in-keezer hub, and the hub's RJ45 run out to the external Raspberry Pi
central unit. The Pi/central-unit side (GPIO mapping, firmware, dashboard)
is a separate, later phase.

## System overview

```
 Keg 1  --RJ11-->  |               |
 Keg 2  --RJ11-->  |  In-keezer    |
 Keg 3  --RJ11-->  |  hub (passive |  --RJ45-->  External Raspberry Pi
 Keg 4  --RJ11-->  |  panel)       |             (central unit)
 Keg 5  --RJ11-->  |               |
```

- No WiFi/radio inside or on the keezer.
- Hub is fully passive: no MCU, just bussed wiring.
- 3.3V logic system-wide (Raspberry Pi GPIO is not 5V-tolerant).
- Shared SCK across all 5 HX711 modules; each keg keeps its own DT line.
- RJ45's 8 wires = VCC + GND + SCK(shared) + 5×DT → hard cap of 5 kegs per hub/cable.

## Per-keg module

**Sensor: HX711 Module + 4 Pcs 50kg Half-Bridge Strain Gauge set (YEMAA or
equivalent).** Each half-bridge sensor is only half a Wheatstone bridge —
it takes all 4 from one set, mounted at the 4 corners of a small platform
(same construction as the inside of a DIY bathroom scale), to form one
complete bridge for one HX711 channel. One set = one keg's platform; for 5
kegs, buy 5 full sets (5× HX711 + 20× sensors total), not 5 individual
sensors.

Combiner wiring (sensor → HX711), typical for this style of kit:
- Each sensor has 3 leads: Red = E+, Black = E-, White = Signal.
- All 4 Red leads bus together → HX711 E+. All 4 Black leads bus together
  → HX711 E-. This shares excitation voltage across all 4 corners.
- The 4 White (signal) leads split into two pairs → HX711 A+ and A-,
  based on which diagonal corners the sensor is mounted at. This pairing
  is orientation-dependent — follow the wiring diagram included with the
  kit rather than guessing, since getting it backwards reads as a
  negative/inverted or dead-flat signal rather than a clean failure.
- Platform construction: a rigid top plate (keg sits here) and bottom
  plate (rests on the keezer floor), with the 4 sensors sandwiched at the
  corners between them — the same structural idea as a bathroom scale.

HX711 mounts on or right next to this platform (keep the sensor-to-HX711
leads short); only the HX711's own 4-wire digital output goes out over the
RJ11 cable — never the raw sensor leads.

Power the HX711 at **3.3V** (confirm the specific breakout supports it —
most do, per HX711 datasheet's 2.6–5.5V VCC range).

### Carrier PCB

[`keg-module-pcb/`](keg-module-pcb/) has a KiCad 9 project (schematic +
blank board outline) implementing all of the above as a small per-keg
carrier board: 4× screw terminals for the sensors (bussing E+/E- across all
4, splitting the diagonal-paired signal leads to A+/A-), a female header
that the HX711 breakout module plugs into, and an RJ11 jack out to the hub.
Schematic passes ERC clean and the netlist has been verified against this
design. Footprint for the RJ11 jack is intentionally left unassigned —
match it to whatever RJ11 jack part you actually buy. See
[`keg-module-pcb/README.md`](keg-module-pcb/README.md) for pin references
and next steps (layout/routing still need to be done in the PCB editor).

**Cable orientation caution**: a flat 4-wire RJ11 cable only preserves the
color convention end-to-end if it's wired "straight through" — the same
common gotcha as old telephone extension cables, where crimping both plugs
facing the same way on a flat cable actually mirrors the pin order at one
end. Before trusting the color convention, verify with a continuity tester
that Black↔Black, Red↔Red, Green↔Green, Yellow↔Yellow end-to-end on every
keg cable, not just Black↔Yellow-reversed.

From the HX711, run a standard 4-wire flat silver-satin RJ11 cable to the
hub, using this fixed color convention on every keg:

| Wire color | Signal                                  |
|------------|------------------------------------------|
| Black      | GND                                      |
| Red        | VCC (3.3V, in from hub)                 |
| Green      | SCK (shared clock, in from hub)         |
| Yellow     | DT (data out to hub — unique per keg)   |

Wiring every keg identically to this color convention means a keg module
can be swapped to any hub jack without needing to relabel/recheck wiring.

## In-keezer hub (passive panel)

Perfboard/protoboard in a small project box, cold-rated (silicone-insulated)
hookup wire throughout since it lives inside the keezer:

- 5× RJ11 female jacks, labeled KEG1–KEG5
- 1× RJ45 female jack, facing out to the central unit

Internal bussing:

- All 5 jacks' **Green (SCK)** pins tied together → RJ45 pin 1
- All 5 jacks' **Red (VCC)** pins tied together → fed from RJ45 pin 4
- All 5 jacks' **Black (GND)** pins tied together → fed from RJ45 pin 5
- Each jack's **Yellow (DT)** stays independent → its own RJ45 pin

### RJ45 pin mapping (T568B colors shown for reference when terminating)

| RJ45 pin | T568B color   | Signal            |
|----------|---------------|-------------------|
| 1        | Orange/White  | SCK (shared)      |
| 2        | Orange        | DT — Keg 1        |
| 3        | Green/White   | DT — Keg 2        |
| 4        | Blue          | VCC (3.3V)        |
| 5        | Blue/White    | GND               |
| 6        | Green         | DT — Keg 3        |
| 7        | Brown/White   | DT — Keg 4        |
| 8        | Brown         | DT — Keg 5        |

VCC/GND share the Blue twisted pair (keeps power together, reduces noise
coupling into data lines). SCK is paired with DT‑Keg1 on the Orange pair.

Fine for short indoor runs without shielding. If the hub-to-Pi run ends up
long, switch to shielded Cat5e/6 (STP) and/or slow the SCK bit-bang rate in
the eventual Pi firmware.

## Parts list

- 5× "HX711 Module + 4 Pcs 50kg Half-Bridge Strain Gauge" sets (YEMAA or
  equivalent) — 5× HX711 + 20× half-bridge sensors total, one set per keg
  platform (verify 50kg rating covers your heaviest full keg)
- 5× rigid top/bottom plate pairs to build each keg's sensor platform
- 5× RJ11 female panel-mount jacks (hub side)
- 5× RJ11 4-wire flat cables with molded plugs (keg side)
- 1× RJ45 female panel-mount jack (hub side)
- 1× Cat5e/6 patch cable, hub to central unit
- Perfboard/protoboard + small project box for the hub
- Silicone-insulated (cold-rated) hookup wire for all in-keezer wiring

## Bench-test checklist (before final assembly)

Do this before the hub is sealed into its enclosure or the load cells are
mounted under kegs — much easier to fix a miswired jack now.

1. With the hub fully wired but nothing plugged into the RJ11 jacks yet,
   multimeter-check RJ45 pin 1 (SCK) for continuity to **all 5** jacks'
   Green pin. All 5 must read continuous; if one doesn't, that jack's SCK
   bus connection is broken.
2. Repeat for VCC: RJ45 pin 4 → all 5 jacks' Red pin.
3. Repeat for GND: RJ45 pin 5 → all 5 jacks' Black pin.
4. For each jack N (1–5), check its Yellow (DT) pin is continuous to *only*
   its assigned RJ45 pin (2/3/6/7/8 per the table above) and to no other
   RJ45 pin, and not to any other jack's Yellow pin. This catches a DT line
   accidentally bussed instead of kept independent.
5. Check for unwanted shorts: no continuity between SCK, VCC, GND, or any
   DT pin pairs other than the intended bus connections above.
6. Plug in one keg module (load cell + HX711 + RJ11 cable) at a time and
   confirm VCC/GND/SCK reach the HX711 and its DT reaches the correct RJ45
   pin, before wiring the rest.

Full end-to-end electrical verification (reading actual weight values)
happens once the central-unit (Raspberry Pi) side is built — that's the
next phase.
