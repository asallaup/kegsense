# Sallaup KegSense

Keg weight/level monitoring for a keezer, by **Sallaup Electronics**.

Each keg sits on a load cell. A per-keg board reads the weight and sends
it over a wired connection to a central unit, which streams each keg's
brew name + weight out to a small OLED mounted right at that keg's own
tap (its own tiny MCU drives the display, right where you're pouring
from) and mirrors the same view to a web dashboard you can check
remotely — so you know how much beer is left without opening the lid.

## System overview

```
 Keg 1  --RJ11-->  |                |
 Keg 2  --RJ11-->  |     KegHub     |  --RJ45-->  KegStation
 Keg 3  --RJ11-->  |   (passive     |             (Raspberry Pi,
 Keg 4  --RJ11-->  |    wiring      |              web dashboard)
 Keg 5  --RJ11-->  |    panel)      |                   |
                    |                |                   v
                                              KegDisplay chain (OLED +
                                              Trinket M0 per tap, daisy-
                                              chained tap to tap)
```

Each keg's board is a **KegSensor** module (HX711 + 4 half-bridge strain
gauge sensors + RJ11 out). No Wi-Fi or radio anywhere inside or on the
keezer itself — everything in there is wired; KegStation, which sits
outside the keezer, is the only part with Wi-Fi (for the dashboard).

## Status

- 🚧 **KegSensor** (per-keg module) — **draft design**, still likely to
  change. Schematic + PCB routed and DRC-clean, 3D-printable case
  designed and validated, fab-ready Gerbers generated — but none of it
  has been physically built, and it hasn't been ordered/printed yet.
  Treat as a working draft, not a locked design, until it's been through
  a real build.
- 🚧 **KegHub** (in-keezer passive wiring panel) — wiring design
  (RJ11/RJ45 pin conventions, parts list) documented; physical build not
  started.
- 🚧 **KegStation** (central unit) — architecture decisions documented
  (platform, Wi-Fi provisioning, update mechanism, KegSensor-interfacing
  daemon language); no hardware or software built yet.
- 🚧 **Keg platform** (load cell mounting) — one part done: a derived,
  validated OpenSCAD load cell holder. Top/bottom mounting plates around
  it not designed yet.

## Repo layout

- [`hardware/kegsensor/`](hardware/kegsensor/) — KegSensor: per-keg
  sensor wiring (RJ11 pin conventions, parts list), KiCad schematic/PCB
  project, 3D-printable case (OpenSCAD), fab-ready Gerbers, and the load
  cell platform holder. See its own README(s) for details, known
  assumptions to verify against real hardware, and how to regenerate
  everything.
- [`hardware/keghub/`](hardware/keghub/) — KegHub: the in-keezer passive
  wiring panel design (RJ45 pin conventions, parts list, bench-test
  checklist).
- [`hardware/kegstation/`](hardware/kegstation/) — KegStation (central
  unit) planning doc: decisions made so far and what's still open.
- [`hardware/kegdisplay/`](hardware/kegdisplay/) — KegDisplay (per-keg
  tap indicator) planning doc: a small OLED + its own Trinket M0 MCU per
  tap, daisy-chained back to KegStation, each tap showing its own keg's
  brew name + weight directly.

## Before ordering/building anything

Both `hardware/kegsensor/README.md` and `hardware/kegsensor/wiring.md`
flag specific assumptions (HX711 module pin order, sensor diagonal
wiring) that need confirming against the actual parts once they're in
hand — cheap to fix now, annoying after boards are fabricated.
