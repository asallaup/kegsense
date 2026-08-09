# KegSensor Wiring

**Sallaup Electronics** — part of the **Sallaup KegSense** keg-monitoring
system.

Covers the sensor layer: per-keg load cell + HX711 (the **KegSensor**
module — carrier board in this same directory), and the RJ11 run out to
**KegHub** (the in-keezer passive wiring panel — see
[`../keghub/`](../keghub/)). KegHub's own wiring and its RJ45 run out to
**KegStation** (the external Raspberry Pi central unit — see
[`../kegstation/`](../kegstation/)) is documented there.

- No WiFi/radio inside or on the keezer.
- 3.3V logic system-wide (Raspberry Pi GPIO is not 5V-tolerant).
- Shared SCK across all 5 HX711 modules; each keg keeps its own DT line.

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
  See [`load-cell-platform/`](load-cell-platform/) for the load cell
  holder that mounts at each corner.

HX711 mounts on or right next to this platform (keep the sensor-to-HX711
leads short); only the HX711's own 4-wire digital output goes out over the
RJ11 cable — never the raw sensor leads.

Power the HX711 at **3.3V** (confirm the specific breakout supports it —
most do, per HX711 datasheet's 2.6–5.5V VCC range).

### Carrier PCB

This directory has a KiCad 9 project (schematic + routed 2-layer PCB)
implementing all of the above as a small per-keg carrier board: 4× screw
terminals for the sensors (bussing E+/E- across all 4, splitting the
diagonal-paired signal leads to A+/A-), a female header that the HX711
breakout module plugs into, and an RJ11 jack out to KegHub. See
[`README.md`](README.md) for fabrication details, known assumptions, and
validation performed.

**Cable orientation caution**: a flat 4-wire RJ11 cable only preserves the
color convention end-to-end if it's wired "straight through" — the same
common gotcha as old telephone extension cables, where crimping both plugs
facing the same way on a flat cable actually mirrors the pin order at one
end. Before trusting the color convention, verify with a continuity tester
that Black↔Black, Red↔Red, Green↔Green, Yellow↔Yellow end-to-end on every
keg cable, not just Black↔Yellow-reversed.

From the HX711, run a standard 4-wire flat silver-satin RJ11 cable to
KegHub, using this fixed color convention on every keg:

| Wire color | Signal                                  |
|------------|------------------------------------------|
| Black      | GND                                      |
| Red        | VCC (3.3V, in from KegHub)               |
| Green      | SCK (shared clock, in from KegHub)       |
| Yellow     | DT (data out to KegHub — unique per keg) |

Wiring every keg identically to this color convention means a keg module
can be swapped to any KegHub jack without needing to relabel/recheck wiring.

## Parts list (per-keg / KegSensor side)

- 5× "HX711 Module + 4 Pcs 50kg Half-Bridge Strain Gauge" sets (YEMAA or
  equivalent) — 5× HX711 + 20× half-bridge sensors total, one set per keg
  platform (verify 50kg rating covers your heaviest full keg)
- 5× rigid top/bottom plate pairs to build each keg's sensor platform
- 5× RJ11 4-wire flat cables with molded plugs (keg side)
- Silicone-insulated (cold-rated) hookup wire for all in-keezer wiring

See [`../keghub/README.md`](../keghub/README.md) for the KegHub-side parts
list (jacks, panel, RJ45 patch cable) and the bench-test checklist that
covers the full sensor-to-KegHub-to-KegStation path.
