#ifndef KEGSTATION_UI_H
#define KEGSTATION_UI_H

#include "lvgl/lvgl.h"

/* Builds the initial screen (keg select) and returns the input group
 * every focusable widget gets added to as screens change. Call this
 * once at startup, then hand the returned group to whichever input
 * device drives navigation (SDL keyboard in the simulator, the 5
 * discrete GPIO buttons on real hardware). */
void kegstation_ui_build(void);
lv_group_t * kegstation_ui_get_group(void);

#endif /* KEGSTATION_UI_H */
