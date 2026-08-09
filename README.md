# Sallaup KegSense

Keg weight/level monitoring for a keezer, by **Sallaup Electronics**.

Each keg sits on a load cell. A per-keg board reads the weight and sends
it over a wired connection to a central unit, which shows all kegs (brew
name + weight/% remaining) on a display mounted on the keezer and mirrors
the same view to a web dashboard you can check remotely — so you know how
much beer is left without opening the lid.

## System overview

```
 Keg 1  --RJ11-->  |                |
 Keg 2  --RJ11-->  |  In-keezer hub |  --RJ45-->  KegStation
 Keg 3  --RJ11-->  |  (passive      |             (Raspberry Pi,
 Keg 4  --RJ11-->  |   wiring       |              OLED + web
 Keg 5  --RJ11-->  |   panel)       |              dashboard)
                    |                |
```

Each keg's board is a **KegSensor** module (HX711 + 4 half-bridge strain
gauge sensors + RJ11 out). No Wi-Fi or radio anywhere inside or on the
keezer itself — everything in there is wired; KegStation, which sits
outside the keezer, is the only part with Wi-Fi (for the dashboard).

## Status

- ✅ **KegSensor** (per-keg module) — schematic + PCB routed and
  DRC-clean, 3D-printable case designed and validated, fab-ready Gerbers
  generated. Ready to order/print; not yet physically built or tested.
- 🚧 **In-keezer hub** — wiring design (RJ11/RJ45 pin conventions, parts
  list) documented; physical build not started.
- 🚧 **KegStation** (central unit) — architecture decisions documented
  (platform, Wi-Fi provisioning, update mechanism, KegSensor-interfacing
  daemon language); no hardware or software built yet.

## Repo layout

- [`hardware/hub-wiring.md`](hardware/hub-wiring.md) — sensor + hub
  wiring design: RJ11/RJ45 pin conventions, parts list, bench-test
  checklist.
- [`hardware/keg-module-pcb/`](hardware/keg-module-pcb/) — KegSensor:
  KiCad schematic/PCB project, 3D-printable case (OpenSCAD), fab-ready
  Gerbers. See its own README for details, known assumptions to verify
  against real hardware, and how to regenerate everything.
- [`kegstation/`](kegstation/) — KegStation (central unit) planning doc:
  decisions made so far and what's still open.

## Before ordering/building anything

Both `hardware/keg-module-pcb/README.md` and `hardware/hub-wiring.md`
flag specific assumptions (HX711 module pin order, sensor diagonal
wiring) that need confirming against the actual parts once they're in
hand — cheap to fix now, annoying after boards are fabricated.
