# KegStation — Sallaup Electronics

Part of the **Sallaup KegSense** keg-monitoring system, made by
**Sallaup Electronics**.

**KegStation** is the central unit: reads all 5 KegSensor modules over
the wired in-keezer hub connection, drives an OLED display (keg list +
weight + brew name), and hosts a web dashboard mirroring the same
information remotely.

This is a planning doc — no hardware or software has been built yet.
Captures decisions made so far so they aren't lost before implementation
starts (see `hardware/hub-wiring.md` for the equivalent doc that preceded
the KegSensor module).

## Decisions so far

- **Platform**: Raspberry Pi 4, 5, or Zero 2 W — any of these have
  built-in Wi-Fi + Bluetooth, so no wireless add-on hardware is needed.
- **Connectivity**: reads the 5× KegSensor modules over the wired hub
  connection (shared SCK + 5× DT + power, see `hardware/hub-wiring.md`) —
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

## Still open

- Software language/stack (Python is the natural fit for Pi
  GPIO/OLED/web-dashboard library support, but not yet committed to).
- Whether to build a small interface PCB (breaking out the hub's RJ45
  connection + OLED header to the Pi's GPIO header) or wire it directly
  on a protoboard/HAT.
- OLED model/size, web dashboard framework, exact GPIO pin mapping for
  the shared-SCK + 5×DT scheme.
- Physical enclosure for KegStation itself (separate from the KegSensor
  case already built).
