/* KegStation UI simulator -- runs the real on-unit UI code (ui.c) in an
 * SDL2 desktop window instead of on the real Pi Zero 2 W + ILI9488 TFT.
 * Arrow keys navigate, Enter selects -- same up/down/left/right/select
 * scheme as the 5 discrete GPIO buttons on real hardware (see
 * hardware/kegstation/README.md). Only this file and the eventual real
 * SPI/GPIO driver differ between simulator and hardware builds -- ui.c
 * is identical either way. */

#include "lvgl/lvgl.h"
#include "ui.h"
#include <SDL2/SDL.h>

int main(void)
{
    lv_init();

    lv_sdl_window_create(480, 320);
    lv_sdl_mouse_create();
    lv_sdl_mousewheel_create();
    lv_indev_t * keyboard = lv_sdl_keyboard_create();

    kegstation_ui_build();
    lv_indev_set_group(keyboard, kegstation_ui_get_group());

    while (1) {
        uint32_t time_till_next = lv_timer_handler();
        if (time_till_next == LV_NO_TIMER_READY) {
            time_till_next = 50;
        }
        SDL_Delay(time_till_next);
    }

    return 0;
}
