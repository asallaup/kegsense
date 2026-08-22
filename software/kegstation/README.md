# KegStation software — UI simulator skeleton

Part of **Sallaup KegSense**. This is a PC-simulator build of KegStation's
on-unit UI — the same [LVGL](https://lvgl.io) application code that will
eventually run on the real Raspberry Pi Zero 2 W + 4.0" ILI9488 TFT (see
[`../../hardware/kegstation/README.md`](../../hardware/kegstation/README.md))
runs here in an SDL2 desktop window instead, so the UI can be built and
demoed well before the real hardware arrives. Only the display/input
*driver* differs between simulator and hardware — `src/ui.c` is the actual
production UI code, identical either way.

**Status**: navigation skeleton only. Opens a keg-select screen (5 kegs,
with the settled red/green sensor-connection indicator per keg) that
drills into a per-keg "Tare / Set Full / Back" screen. The Tare/Set Full
buttons just update a status label for now — the real guided calibration
wizard (place empty keg → confirm → select preset weight → confirm, see
the hardware README's "On-unit calibration wizard") isn't wired up yet,
this only demonstrates the screen-navigation structure it will sit on top
of.

## Build (macOS)

```sh
brew install cmake sdl2 pkg-config
cmake -S . -B build
cmake --build build --target kegstation_sim -j4
```

## Run

```sh
./build/kegstation_sim
```

Opens a 480×320 window (matching the real panel's resolution). Controls:

- **Arrow keys**: move focus between menu items (same up/down/left/right
  scheme the real 5 discrete GPIO buttons will drive — see the hardware
  README's "Display + input" note on why buttons were picked over a
  rotary encoder)
- **Enter**: select the focused item
- **Mouse**: also works (click directly), since the SDL mouse indev is
  registered alongside the keyboard one — convenient for testing but not
  representative of the real hardware's input

## Layout

- `lv_conf.h` — LVGL config, copied from `extern/lvgl/lv_conf_template.h`
  with two changes: the top `#if 0` flipped to `#if 1` to enable the file,
  and `LV_USE_SDL` flipped to `1`. Left everything else at LVGL's own
  defaults (`LV_COLOR_DEPTH 16` matches the RGB565 pixel format already
  planned for the real SPI driver).
- `extern/lvgl/` — LVGL itself, as a git submodule (run
  `git submodule update --init` if it's empty after cloning this repo).
  Currently pinned to a `master` snapshot (v9.6.0-dev), not a tagged
  release — worth moving to a stable tag later if this grows past a
  skeleton.
- `src/main.c` — the only genuinely simulator-specific file: opens the
  SDL2 window/input devices and hands off to `ui.c`. The real-hardware
  build will have its own `main.c` that sets up the actual SPI/GPIO
  driver instead, calling the same `kegstation_ui_build()`.
- `src/ui.c` / `src/ui.h` — the actual UI: keg-select screen, per-keg
  detail screen, navigation group. This is the file that matters — it's
  meant to run unmodified on real hardware.
- `src/main_hw.c` — the real-hardware counterpart to `main.c`: drives an
  ILI9488 SPI TFT + 5 GPIO buttons via `pigpio` instead of SDL2, calling
  the same `kegstation_ui_build()`. **Not built or tested** — no CMake
  target links it, and it can't be verified until real hardware exists
  (same standard as the rest of this project). Every LVGL call in it was
  checked against the real v9.6 headers here, but the GPIO pin numbers
  and ILI9488 init register values are still placeholders.

## Known rough edges

- Uses `lv_list_*` widgets, which this LVGL snapshot marks deprecated in
  favor of building lists from flex columns (`lv_example_flex_list`) —
  still compiles and works, just noisy `-Wdeprecated-declarations`
  warnings. Worth migrating if this grows into the real implementation.
- LVGL is pinned to whatever `master` commit was current when the
  submodule was added, not a tagged release.
