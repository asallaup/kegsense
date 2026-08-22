#include "ui.h"
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <time.h>

#define NUM_KEGS 5

/* Matches the real ILI9488 panel's resolution (see
 * hardware/kegstation/README.md) and the simulator's SDL window size
 * (main.c). */
#define SCREEN_W 480
#define SCREEN_H 320

/* Cornelius keg icon: a real product photo (assets/keg_photo.jpg) with
 * the fill-level bar overlaid directly on the metallic body -- not the
 * black cap/base. The photo is pre-processed with Python/Pillow: the
 * stock photo's white studio background is flood-filled to the app's
 * dark theme color (so the icon reads as sitting in the scene, not a
 * white card), then cropped and resized to exactly KEG_W x KEG_H (same
 * reasoning as the background photo in style_screen_background:
 * LV_IMAGE_ALIGN_STRETCH silently truncated a 155x450 source scaled
 * down to this size instead of showing the whole thing, so this
 * sidesteps LVGL's scaling path entirely -- the image is drawn 1:1, no
 * runtime scale/align needed). BODY_* mark where the metallic body
 * sits within that KEG_W x KEG_H frame (measured off the source photo,
 * same coordinate space since the resize is proportional) -- not the
 * black cap/base. The body turned out already horizontally centered in
 * the crop, so the bar only needs a vertical offset, not a horizontal
 * one. */
#define KEG_W        65
#define KEG_H        190
#define KEG_SPACING  92   /* distance between keg centers */
#define KEG_ROW_Y    100  /* below the "Sallaup" sign in the background photo, which is now the branding */
#define BODY_TOP     28   /* y-offset within the icon where the metallic body starts (below the black cap) */
#define BODY_BOTTOM  170  /* y-offset where the body ends (above the black base) */
#define BAR_W        52
#define BAR_H        (BODY_BOTTOM - BODY_TOP)
#define BAR_FILL_OPA 190  /* translucent tint over the photo, not fully opaque -- reads as liquid, not paint */

static lv_group_t * group;
static lv_obj_t * scr_keg_select;
static lv_obj_t * scr_keg_detail;
static lv_obj_t * keg_buttons[NUM_KEGS];
static lv_obj_t * detail_status_label;

/* Live per-keg state for the simulator's "levels drift over time" demo
 * (see level_update_timer_cb below). Indexed by keg_num - 1. Real
 * hardware reads this from the daemon's readings file instead. */
static lv_obj_t * keg_bars[NUM_KEGS];
static int keg_levels[NUM_KEGS];
static bool keg_blinking[NUM_KEGS];

static void build_keg_select_screen(void);
static void build_keg_detail_screen(int keg_num);
static void keg_button_event_cb(lv_event_t * e);

/* Placeholder for the per-keg sensor-connected status (red/green
 * indicator, see kegstation/README.md "Sensor-connection status").
 * Real data will come from the C daemon's readings file once it
 * exists -- for now this just demonstrates where that data plugs in. */
static bool keg_sensor_connected(int keg_num)
{
    (void)keg_num;
    return true; /* TODO: read from the daemon's readings file */
}

/* Placeholder fill level (0-100%). Real data comes from the daemon's
 * readings file (raw ADC -> kegcal's tare/setfull linear scale) once
 * that exists -- these are varied fake values so the row of kegs
 * demonstrates all four level-color states (green/yellow/red/blinking
 * red) at once. */
static int keg_fill_level(int keg_num)
{
    static const int fake_levels[NUM_KEGS] = {80, 45, 12, 3, 95};
    return fake_levels[(keg_num - 1) % NUM_KEGS]; /* TODO: read from readings file */
}

/* Level color thresholds: >=50% green, >=20% yellow, >=5% red,
 * <5% still red but blinking (see keg_level_is_critical below). */
static lv_color_t keg_level_color(int level)
{
    if (level >= 50) return lv_color_hex(0x2ecc71); /* green */
    if (level >= 20) return lv_color_hex(0xF1C40F); /* yellow */
    return lv_color_hex(0xE74C3C);                  /* red (also used blinking, below) */
}

static bool keg_level_is_critical(int level)
{
    return level < 5;
}

/* Blinks the bar's indicator opacity, for a critically low keg. */
static void indicator_opa_anim_cb(void * var, int32_t v)
{
    lv_obj_set_style_bg_opa((lv_obj_t *)var, (lv_opa_t)v, LV_PART_INDICATOR);
}

static void start_critical_blink(lv_obj_t * bar)
{
    /* lv_anim_start() copies this by value, so a plain stack local is
     * fine even though it goes out of scope right after the call. */
    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, bar);
    lv_anim_set_exec_cb(&a, indicator_opa_anim_cb);
    lv_anim_set_values(&a, BAR_FILL_OPA, LV_OPA_TRANSP);
    lv_anim_set_duration(&a, 400);
    lv_anim_set_reverse_duration(&a, 400);
    lv_anim_set_repeat_count(&a, LV_ANIM_REPEAT_INFINITE);
    lv_anim_start(&a);
}

/* Applies keg_levels[idx] to keg_bars[idx]: value, color, and
 * starting/stopping the critical blink animation as it crosses the
 * threshold (rather than restarting it every tick, which would look
 * like a flicker/reset instead of a smooth blink). */
static void update_keg_bar(int idx)
{
    lv_obj_t * bar = keg_bars[idx];
    int level = keg_levels[idx];

    lv_bar_set_value(bar, level, LV_ANIM_OFF);
    lv_obj_set_style_bg_color(bar, keg_level_color(level), LV_PART_INDICATOR);

    bool critical = keg_level_is_critical(level);
    if (critical && !keg_blinking[idx]) {
        start_critical_blink(bar);
        keg_blinking[idx] = true;
    } else if (!critical && keg_blinking[idx]) {
        lv_anim_delete(bar, indicator_opa_anim_cb);
        lv_obj_set_style_bg_opa(bar, BAR_FILL_OPA, LV_PART_INDICATOR); /* undo mid-fade */
        keg_blinking[idx] = false;
    }
}

/* Simulator-only: drifts each keg's level by a small random step every
 * tick, so the row of kegs visibly changes over time instead of sitting
 * static. Real hardware has no equivalent -- levels there only change
 * because someone's actually pouring beer, read from the daemon. */
static void level_update_timer_cb(lv_timer_t * timer)
{
    (void)timer;
    for (int i = 0; i < NUM_KEGS; i++) {
        int step = (rand() % 7) - 3; /* -3..+3 */
        int level = keg_levels[i] + step;
        if (level < 0) level = 0;
        if (level > 100) level = 100;
        keg_levels[i] = level;
        update_keg_bar(i);
    }
}

/* Builds one Cornelius-keg icon: the real product photo
 * (assets/keg_photo.jpg) with a translucent vertical lv_bar overlaid
 * directly on the metallic body (not the black cap/base) showing fill
 * level, a red/green sensor-status dot, and a "Keg N" label underneath.
 * Returns the outer container -- the clickable/focusable object added
 * to the nav group. */
static lv_obj_t * build_keg_icon(lv_obj_t * parent, int keg_num, int x_ofs)
{
    lv_obj_t * keg = lv_obj_create(parent);
    lv_obj_remove_style_all(keg);
    lv_obj_add_flag(keg, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_set_size(keg, KEG_W, KEG_H);
    lv_obj_align(keg, LV_ALIGN_TOP_MID, x_ofs, KEG_ROW_Y);

    lv_obj_t * photo = lv_image_create(keg);
    lv_image_set_src(photo, "A:assets/keg_photo.jpg");
    lv_obj_align(photo, LV_ALIGN_TOP_LEFT, 0, 0);

    /* Fill-level bar, translucent, overlaid on the body region measured
     * off the photo (BODY_TOP/BODY_BOTTOM) -- not the black cap/base.
     * Colored green/yellow/red by level, blinking red if critically
     * low. Initial value/color/blink state set via update_keg_bar() so
     * the build path and the periodic timer share the exact same
     * logic. */
    lv_obj_t * bar = lv_bar_create(keg);
    lv_obj_set_size(bar, BAR_W, BAR_H); /* taller than wide -> vertical, per lv_bar's own hor=(w>=h) check */
    lv_obj_align(bar, LV_ALIGN_TOP_MID, 0, BODY_TOP); /* body turned out already horizontally centered in the crop */
    lv_bar_set_range(bar, 0, 100);
    lv_obj_set_style_bg_opa(bar, LV_OPA_TRANSP, 0);      /* empty track: fully see-through, shows the bare photo */
    lv_obj_set_style_bg_opa(bar, BAR_FILL_OPA, LV_PART_INDICATOR);
    lv_obj_set_style_radius(bar, 0, 0);                  /* rectangle, not the default pill shape */
    lv_obj_set_style_radius(bar, 0, LV_PART_INDICATOR);

    keg_bars[keg_num - 1] = bar;
    keg_levels[keg_num - 1] = keg_fill_level(keg_num);
    keg_blinking[keg_num - 1] = false;
    update_keg_bar(keg_num - 1);

    /* Red/green sensor-connection status dot, top-right of the body. */
    lv_obj_t * status_dot = lv_obj_create(keg);
    lv_obj_set_size(status_dot, 10, 10);
    lv_obj_set_style_radius(status_dot, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_color(status_dot,
        keg_sensor_connected(keg_num) ? lv_color_hex(0x2ecc71)
                                       : lv_color_hex(0xe74c3c),
        0);
    lv_obj_align(status_dot, LV_ALIGN_TOP_RIGHT, -2, 2);

    /* "Keg N" label underneath. */
    lv_obj_t * label = lv_label_create(parent);
    char buf[16];
    snprintf(buf, sizeof(buf), "Keg %d", keg_num);
    lv_label_set_text(label, buf);
    lv_obj_set_style_text_color(label, lv_color_hex(0xE4E7EA), 0); /* readable on the dark background */
    lv_obj_align(label, LV_ALIGN_TOP_MID, x_ofs, KEG_ROW_Y + KEG_H + 6);

    lv_obj_add_event_cb(keg, keg_button_event_cb, LV_EVENT_CLICKED,
                         (void *)(intptr_t)keg_num);

    return keg;
}

static void back_to_keg_select(lv_event_t * e)
{
    (void)e;
    lv_group_remove_all_objs(group);
    for (int i = 0; i < NUM_KEGS; i++) {
        lv_group_add_obj(group, keg_buttons[i]);
    }
    lv_screen_load(scr_keg_select);
}

static void tare_button_cb(lv_event_t * e)
{
    int keg_num = (int)(intptr_t)lv_event_get_user_data(e);
    char buf[64];
    /* TODO: real flow is the guided wizard from kegstation/README.md --
     * "Place empty keg, confirm" -> read raw ADC -> kegcal tare.
     * This just shows where that hooks in. */
    snprintf(buf, sizeof(buf), "Tare requested for Keg %d (not wired up yet)", keg_num);
    lv_label_set_text(detail_status_label, buf);
}

static void setfull_button_cb(lv_event_t * e)
{
    int keg_num = (int)(intptr_t)lv_event_get_user_data(e);
    char buf[64];
    /* TODO: real flow presents the 5/10/15/20kg preset list from
     * kegstation/README.md, not free numeric entry. */
    snprintf(buf, sizeof(buf), "Set Full requested for Keg %d (not wired up yet)", keg_num);
    lv_label_set_text(detail_status_label, buf);
}

static void keg_button_event_cb(lv_event_t * e)
{
    int keg_num = (int)(intptr_t)lv_event_get_user_data(e);
    build_keg_detail_screen(keg_num);
}

/* Background photo of the actual Sallaup rig, with a dark scrim over it
 * so the wordmark/keg icons/text stay readable against a busy photo --
 * same reasoning as any UI laying text over a photographic background.
 * Path is relative to wherever kegstation_sim is run from (see the
 * README's "Run" section -- from software/kegstation/). The flat dark
 * color set first is a fallback if the image fails to load, and shows
 * through at the edges the photo's aspect ratio doesn't cover. */
#define BACKGROUND_IMAGE_PATH "A:assets/sallauprampen.jpg"

static void style_screen_background(lv_obj_t * scr)
{
    lv_obj_set_style_bg_color(scr, lv_color_hex(0x1B1E24), 0);

    lv_obj_t * bg_img = lv_image_create(scr);
    lv_image_set_src(bg_img, BACKGROUND_IMAGE_PATH);
    lv_obj_set_size(bg_img, SCREEN_W, SCREEN_H);
    lv_image_set_inner_align(bg_img, LV_IMAGE_ALIGN_COVER);
    lv_obj_align(bg_img, LV_ALIGN_TOP_LEFT, 0, 0);

    lv_obj_t * scrim = lv_obj_create(scr);
    lv_obj_remove_style_all(scrim);
    lv_obj_set_size(scrim, SCREEN_W, SCREEN_H);
    lv_obj_align(scrim, LV_ALIGN_TOP_LEFT, 0, 0);
    lv_obj_set_style_bg_color(scrim, lv_color_hex(0x0A0C10), 0);
    lv_obj_set_style_bg_opa(scrim, 170, 0); /* ~67% -- dark enough to read text, photo still visible */
}

static void build_keg_select_screen(void)
{
    scr_keg_select = lv_obj_create(NULL);
    style_screen_background(scr_keg_select);

    /* Row of 5 Cornelius-keg icons, centered, each with its fill level
     * as a vertical bar inside the body. */
    for (int i = 0; i < NUM_KEGS; i++) {
        int keg_num = i + 1;
        int x_ofs = (i - (NUM_KEGS - 1) / 2) * KEG_SPACING
                    - ((NUM_KEGS % 2 == 0) ? KEG_SPACING / 2 : 0);

        lv_obj_t * keg = build_keg_icon(scr_keg_select, keg_num, x_ofs);
        keg_buttons[i] = keg;
        lv_group_add_obj(group, keg);
    }
}

static void build_keg_detail_screen(int keg_num)
{
    if (scr_keg_detail) {
        lv_obj_delete(scr_keg_detail);
    }
    scr_keg_detail = lv_obj_create(NULL);
    style_screen_background(scr_keg_detail);

    lv_obj_t * title = lv_label_create(scr_keg_detail);
    char title_buf[16];
    snprintf(title_buf, sizeof(title_buf), "Keg %d", keg_num);
    lv_label_set_text(title, title_buf);
    lv_obj_set_style_text_font(title, &lv_font_montserrat_24, 0);
    lv_obj_set_style_text_color(title, lv_color_hex(0xF2F4F6), 0);
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 10);

    lv_obj_t * list = lv_list_create(scr_keg_detail);
    lv_obj_set_size(list, 220, 160);
    lv_obj_align(list, LV_ALIGN_TOP_MID, 0, 40);

    lv_obj_t * tare_btn = lv_list_add_button(list, NULL, "Tare");
    lv_obj_add_event_cb(tare_btn, tare_button_cb, LV_EVENT_CLICKED,
                         (void *)(intptr_t)keg_num);

    lv_obj_t * setfull_btn = lv_list_add_button(list, NULL, "Set Full");
    lv_obj_add_event_cb(setfull_btn, setfull_button_cb, LV_EVENT_CLICKED,
                         (void *)(intptr_t)keg_num);

    lv_obj_t * back_btn = lv_list_add_button(list, NULL, "Back");
    lv_obj_add_event_cb(back_btn, back_to_keg_select, LV_EVENT_CLICKED, NULL);

    detail_status_label = lv_label_create(scr_keg_detail);
    lv_label_set_text(detail_status_label, "");
    lv_obj_set_style_text_color(detail_status_label, lv_color_hex(0xE4E7EA), 0);
    lv_obj_align(detail_status_label, LV_ALIGN_BOTTOM_MID, 0, -10);

    lv_group_remove_all_objs(group);
    lv_group_add_obj(group, tare_btn);
    lv_group_add_obj(group, setfull_btn);
    lv_group_add_obj(group, back_btn);

    lv_screen_load(scr_keg_detail);
}

void kegstation_ui_build(void)
{
    srand((unsigned)time(NULL));

    group = lv_group_create();
    lv_group_set_default(group);

    build_keg_select_screen();
    lv_screen_load(scr_keg_select);

    /* Simulator-only random level drift -- see level_update_timer_cb. */
    lv_timer_create(level_update_timer_cb, 1000, NULL);
}

lv_group_t * kegstation_ui_get_group(void)
{
    return group;
}
