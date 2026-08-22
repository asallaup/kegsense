/* KegStation real-hardware entry point -- NOT the simulator (see main.c).
 * Runs the exact same UI code (ui.c / kegstation_ui_build()) but drives
 * a real ILI9488 SPI TFT + 5 discrete GPIO buttons via pigpio, instead
 * of an SDL2 window + keyboard.
 *
 * Not yet buildable or tested -- there's no CMake target for this file,
 * and it can't be, until real hardware exists to test against (same
 * "validate before calling it done" standard as the rest of this
 * project -- see hardware/kegstation/README.md). Treat this as a
 * verified-API skeleton, not working code: every LVGL call here was
 * checked against the actual v9.6 headers in extern/lvgl, but the GPIO
 * pin numbers and ILI9488 init register values are still placeholders
 * (see hardware/kegstation/README.md's "Still Open" -- GPIO pin
 * assignment for the nav buttons isn't decided yet either).
 *
 * Build (once on real hardware, not from this CMake project):
 *   gcc main_hw.c ui.c -o kegstation \
 *       -I extern/lvgl/include -I. \
 *       $(find extern/lvgl -name '*.c' ! -path '*/drivers/*' ...) \
 *       -lpigpio -lrt -lpthread -lm
 * (a real build would compile LVGL as a static lib with LV_USE_SDL=0,
 * same lv_conf.h otherwise -- not set up here since there's nothing to
 * link/test against yet)
 */

#include <pigpio.h>
#include <stdint.h>
#include <unistd.h>
#include "lvgl/lvgl.h"
#include "ui.h"

/* ---- Pin assignment: PLACEHOLDER, see kegstation/README.md's
 * "Still Open" -- GPIO pin mapping for the shared-SCK/6xDT KegSensor
 * scheme AND the 5 nav buttons are both still undecided. ---- */
#define PIN_DC     24
#define PIN_RESET  25
#define PIN_BTN_UP     5
#define PIN_BTN_DOWN   6
#define PIN_BTN_LEFT  13
#define PIN_BTN_RIGHT 19
#define PIN_BTN_SELECT 26

#define SPI_CHANNEL 0
#define SPI_BAUD 32000000

#define SCREEN_W 480
#define SCREEN_H 320

static int spi_handle;

/* ---- Same low-level SPI helpers as the earlier standalone TFT demo ---- */

static void write_cmd(uint8_t cmd) {
    gpioWrite(PIN_DC, 0);
    spiWrite(spi_handle, (char *)&cmd, 1);
}

static void write_data(const uint8_t *data, int len) {
    gpioWrite(PIN_DC, 1);
    spiWrite(spi_handle, (char *)data, len);
}

static void write_data8(uint8_t d) { write_data(&d, 1); }

/* Typical published ILI9488 init sequence -- verify against the real
 * module once it's on the bench, same caveat as before re: this module
 * sometimes shipping as ILI9484 instead. */
static void ili9488_init(void) {
    gpioWrite(PIN_RESET, 0);
    usleep(20000);
    gpioWrite(PIN_RESET, 1);
    usleep(150000);

    write_cmd(0x01); /* software reset */
    usleep(150000);

    write_cmd(0x11); /* sleep out */
    usleep(150000);

    write_cmd(0x3A); /* interface pixel format */
    write_data8(0x55); /* 16-bit/pixel, matches LV_COLOR_FORMAT_RGB565 below */

    write_cmd(0x36); /* memory access control (orientation) */
    write_data8(0x48); /* adjust if the image comes out mirrored/rotated */

    write_cmd(0xC2);
    write_data8(0x44);

    write_cmd(0xC5);
    { uint8_t d[4] = {0x00, 0x00, 0x00, 0x00}; write_data(d, 4); }

    write_cmd(0x21); /* display inversion on */
    write_cmd(0x29); /* display ON */
    usleep(50000);
}

static void set_window(int x0, int y0, int x1, int y1) {
    write_cmd(0x2A);
    uint8_t colbuf[4] = { x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF };
    write_data(colbuf, 4);

    write_cmd(0x2B);
    uint8_t rowbuf[4] = { y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF };
    write_data(rowbuf, 4);

    write_cmd(0x2C); /* memory write */
}

/* ---- LVGL display driver: flush callback pushes LVGL's rendered
 * buffer over SPI instead of into an SDL2 window. ---- */

static void disp_flush_cb(lv_display_t * disp, const lv_area_t * area, uint8_t * px_map) {
    int32_t w = area->x2 - area->x1 + 1;
    int32_t h = area->y2 - area->y1 + 1;

    set_window(area->x1, area->y1, area->x2, area->y2);
    gpioWrite(PIN_DC, 1);
    spiWrite(spi_handle, (char *)px_map, w * h * 2 /* RGB565 = 2 bytes/px */);

    lv_display_flush_ready(disp);
}

/* Draw buffer: a partial buffer (40 rows) rather than a full 480x320
 * frame, to keep RAM use modest on the Zero 2 W's 512MB. */
static uint8_t draw_buf[SCREEN_W * 40 * 2];

/* ---- LVGL input driver: reads the 5 discrete nav buttons instead of
 * SDL keyboard events. Simple digital reads, active-low assumed
 * (button to GND, internal pull-up) -- adjust once real wiring exists. ---- */

static void keypad_read_cb(lv_indev_t * indev, lv_indev_data_t * data) {
    (void)indev;

    if (gpioRead(PIN_BTN_UP) == 0)          { data->key = LV_KEY_UP;    data->state = LV_INDEV_STATE_PRESSED; }
    else if (gpioRead(PIN_BTN_DOWN) == 0)   { data->key = LV_KEY_DOWN;  data->state = LV_INDEV_STATE_PRESSED; }
    else if (gpioRead(PIN_BTN_LEFT) == 0)   { data->key = LV_KEY_LEFT;  data->state = LV_INDEV_STATE_PRESSED; }
    else if (gpioRead(PIN_BTN_RIGHT) == 0)  { data->key = LV_KEY_RIGHT; data->state = LV_INDEV_STATE_PRESSED; }
    else if (gpioRead(PIN_BTN_SELECT) == 0) { data->key = LV_KEY_ENTER; data->state = LV_INDEV_STATE_PRESSED; }
    else                                    { data->state = LV_INDEV_STATE_RELEASED; }
}

/* ---- Tick source: pigpio's own microsecond tick, matching the pattern
 * the SDL driver uses (lv_tick_set_cb(SDL_GetTicks)) -- no manual
 * lv_tick_inc() needed, LVGL calls this whenever it needs the time. ---- */

static uint32_t tick_get_cb(void) {
    return gpioTick() / 1000; /* microseconds -> milliseconds */
}

int main(void) {
    if (gpioInitialise() < 0) return 1;

    gpioSetMode(PIN_DC, PI_OUTPUT);
    gpioSetMode(PIN_RESET, PI_OUTPUT);
    gpioSetMode(PIN_BTN_UP, PI_INPUT);
    gpioSetMode(PIN_BTN_DOWN, PI_INPUT);
    gpioSetMode(PIN_BTN_LEFT, PI_INPUT);
    gpioSetMode(PIN_BTN_RIGHT, PI_INPUT);
    gpioSetMode(PIN_BTN_SELECT, PI_INPUT);
    gpioSetPullUpDown(PIN_BTN_UP, PI_PUD_UP);
    gpioSetPullUpDown(PIN_BTN_DOWN, PI_PUD_UP);
    gpioSetPullUpDown(PIN_BTN_LEFT, PI_PUD_UP);
    gpioSetPullUpDown(PIN_BTN_RIGHT, PI_PUD_UP);
    gpioSetPullUpDown(PIN_BTN_SELECT, PI_PUD_UP);

    spi_handle = spiOpen(SPI_CHANNEL, SPI_BAUD, 0);
    if (spi_handle < 0) return 1;

    ili9488_init();

    lv_init();
    lv_tick_set_cb(tick_get_cb);

    lv_display_t * disp = lv_display_create(SCREEN_W, SCREEN_H);
    lv_display_set_color_format(disp, LV_COLOR_FORMAT_RGB565);
    lv_display_set_buffers(disp, draw_buf, NULL, sizeof(draw_buf),
                            LV_DISPLAY_RENDER_MODE_PARTIAL);
    lv_display_set_flush_cb(disp, disp_flush_cb);

    lv_indev_t * keypad = lv_indev_create();
    lv_indev_set_type(keypad, LV_INDEV_TYPE_KEYPAD);
    lv_indev_set_read_cb(keypad, keypad_read_cb);

    kegstation_ui_build();
    lv_indev_set_group(keypad, kegstation_ui_get_group());

    while (1) {
        uint32_t time_till_next = lv_timer_handler();
        if (time_till_next == LV_NO_TIMER_READY) {
            time_till_next = 50;
        }
        usleep(time_till_next * 1000);
    }

    return 0;
}
