# KegTag — Sallaup Electronics (experimental)

Part of the **Sallaup KegSense** keg-monitoring system, made by
**Sallaup Electronics**.

**KegTag** is an experimental per-tap add-on: a wireless,
battery-powered e-ink tag showing that keg's brew name plus an
on-demand level snapshot. Sits alongside
[`../kegdisplay/`](../kegdisplay/)'s WS2812 bar, not a replacement for
it — the bar keeps the live, continuously-updating fill level (wired,
no battery budget to protect); KegTag only needs to refresh on
infrequent, hands-on events (keg swap, a manual level check).

**Experimental status**: not a committed part of the system. Depends on
an off-the-shelf ESL (electronic shelf label) tag actually meeting the
>1 year battery target in real-world testing — unverified so far, see
Still Open. May end up unbuilt if that doesn't pan out.

This is a planning doc — no hardware or software has been built yet.

## Decisions so far

- **Off-the-shelf ESL tag, not a custom board.** Wireless,
  battery-powered. **Target: >1 year battery life** — this is the
  actual requirement. An earlier idea (button-triggered wake, tag in
  deep sleep otherwise) was one way to hit that target by controlling
  the tag's own firmware, not a goal in itself — if a tag's stock
  firmware already keeps power draw low enough on its own, no custom
  firmware is needed.
- **Primary pick: Gicisky tags** — real direct BLE, talked to over a
  reverse-engineered open protocol
  ([`hass-gicisky`](https://github.com/eigger/hass-gicisky)), stock
  firmware (not reflashed). Bought new, direct
  ([GICIsky Official Store on AliExpress](https://www.aliexpress.com/item/1005002399342939.html),
  2.9" variant, ~162 kr at time of writing) — solves OpenEPaperLink's
  sourcing problem. Tradeoff: no control over the tag's own
  wake/refresh behavior since firmware isn't touched, so the >1 year
  battery claim (per AliExpress/reseller listings) is unverified
  marketing copy — needs real-world testing on one tag before
  committing (see Still Open).
- **Fallback: OpenEPaperLink**, if Gicisky's real battery life doesn't
  hold up. Reflashed tag firmware, full control over sleep/wake
  behavior (deep sleep, wake only on a button press or scheduled
  check-in) at the cost of a harder-to-source tag and more firmware
  work. Sourcing is currently rough: the one easy new-tag source found
  (Tindie seller "Electronics by Nic") has all listings retired, seller
  on a break until Dec 31 2027 — down to secondhand Solum/Hanshow tags
  (eBay, hit-or-miss on compatibility) or the OpenEPaperLink Discord's
  trading channel.
- **Wildcard, not decided: reverse-engineer a closed BT+app tag
  instead** — e.g. the TOP-TECH "2.1"/2.9" NFC+BT" AliExpress listing
  (glass front, IP65, proprietary Android app). One reviewer mentioned
  an unofficial "web app for chrome" alternative to the vendor app,
  suggesting someone's already partially reverse-engineered it, but
  that's unconfirmed — no linked project found. Doing this properly
  means capturing the vendor app's BLE traffic via Android's Bluetooth
  HCI snoop log + Wireshark while pushing an update, then decoding the
  GATT write format from a few varied captures. Real, buildable work
  (this is literally how `hass-gicisky` and most of the OpenEPaperLink
  reverse-engineering got done) but uncertain time investment, and only
  worth it over Gicisky if this tag's IP65/glass build or pricing ends
  up mattering — otherwise it's redoing work Gicisky's community
  already did.
- **Hub**: whichever tag path is chosen, a hub device sits on
  KegStation's network — for Gicisky, a lightweight ESP32 running a
  Home Assistant Bluetooth proxy; for OpenEPaperLink, a full AP (ESP32 +
  matching radio, e.g. ESP32-C6's onboard 802.15.4 or ESP32 + CC1101 for
  sub-GHz tags). Not part of KegDisplay's WS2812 chain either way.

## Still open

- **Gicisky real-world battery test — blocks choosing a path.** Order
  one tag (smallest/cheapest genuine e-paper variant — not the "TFT"
  color option, which is LCD, not e-ink), run it under normal update
  cadence (a few pushes/day), measure actual battery drain over 1-2
  weeks. Gicisky stays the pick if that holds up toward >1 year; falls
  back to OpenEPaperLink (or the reverse-engineering wildcard) if not.
- **ESL tag model/size** — not chosen. Gicisky sizes: 2.1", 2.9", 3.7",
  4.2", 7.5", 10.2" (per `hass-gicisky`). No published case dimensions
  in mm from any Gicisky reseller found so far — estimated ~75-85mm ×
  35-45mm × 8-12mm for the 2.9" variant based on standard 2.9" e-paper
  panel size, not confirmed. OpenEPaperLink's smallest well-documented
  option is the 1.3" Peghook (97.75mm × 28.6mm × 5.9mm, per SoluM's own
  datasheet) but it's a physical peg-hook clip, not a flat mountable
  tag — mismatched to a collar-mount use case without rework.
- **Tag mounting location** — likely needs its own mount point separate
  from KegDisplay's WS2812 bar enclosure (~50mm width budget), given
  ESL tags generally run wider than that. Not decided.
- **Hub hardware** — not built. For Gicisky: an ESP32 running a Home
  Assistant Bluetooth proxy. For OpenEPaperLink: DIY ESP32 + CC1101 vs.
  a bought ready-made AP (e.g. Mini-AP). Not decided.
- **KegStation's own side**: running the chosen hub and pushing
  brew-name/level data to it (see
  [`../kegstation/README.md`](../kegstation/README.md)) — not written.
