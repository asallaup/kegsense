# KegHub

**Sallaup Electronics** — part of the **Sallaup KegSense** keg-monitoring
system.

**KegHub** is the passive in-keezer wiring panel: it collects the RJ11
runs from each keg's **KegSensor** module (see
[`../kegsensor/wiring.md`](../kegsensor/wiring.md)) and buses them onto a
single RJ45 run out to **KegStation** (the external Raspberry Pi central
unit — see [`../kegstation/`](../kegstation/)). KegStation's own
hardware/software is a separate, later phase.

## System overview

```
 Keg 1  --RJ11-->  |               |
 Keg 2  --RJ11-->  |    KegHub     |
 Keg 3  --RJ11-->  |   (passive    |  --RJ45-->  KegStation
 Keg 4  --RJ11-->  |    panel)     |             (Raspberry Pi)
 Keg 5  --RJ11-->  |               |
```

- No WiFi/radio inside or on the keezer.
- KegHub is fully passive: no MCU, just bussed wiring.
- 3.3V logic system-wide (Raspberry Pi GPIO is not 5V-tolerant).
- RJ45's 8 wires = VCC + GND + SCK(shared) + 5×DT → hard cap of 5 kegs per KegHub/cable.

## Panel

Perfboard/protoboard in a small project box, cold-rated (silicone-insulated)
hookup wire throughout since it lives inside the keezer:

- 5× RJ11 female jacks, labeled KEG1–KEG5
- 1× RJ45 female jack, facing out to KegStation

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
| 5        | Blue/White    | GND                |
| 6        | Green         | DT — Keg 3        |
| 7        | Brown/White   | DT — Keg 4        |
| 8        | Brown         | DT — Keg 5        |

VCC/GND share the Blue twisted pair (keeps power together, reduces noise
coupling into data lines). SCK is paired with DT‑Keg1 on the Orange pair.

Fine for short indoor runs without shielding. If the KegHub-to-KegStation
run ends up long, switch to shielded Cat5e/6 (STP) and/or slow the SCK
bit-bang rate in the eventual KegStation firmware.

## Parts list (KegHub side)

- 5× RJ11 female panel-mount jacks
- 1× RJ45 female panel-mount jack
- 1× Cat5e/6 patch cable, KegHub to KegStation
- Perfboard/protoboard + small project box
- Silicone-insulated (cold-rated) hookup wire

See [`../kegsensor/wiring.md`](../kegsensor/wiring.md) for the per-keg
(KegSensor-side) parts list.

## Bench-test checklist (before final assembly)

Do this before KegHub is sealed into its enclosure or the load cells are
mounted under kegs — much easier to fix a miswired jack now.

1. With KegHub fully wired but nothing plugged into the RJ11 jacks yet,
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
happens once KegStation (the Raspberry Pi central unit) is built — that's
the next phase.
