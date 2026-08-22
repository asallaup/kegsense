#include "ui.h"
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

#define NUM_KEGS 5

static lv_group_t * group;
static lv_obj_t * scr_keg_select;
static lv_obj_t * scr_keg_detail;
static lv_obj_t * keg_buttons[NUM_KEGS];
static lv_obj_t * detail_status_label;

static void build_keg_select_screen(void);
static void build_keg_detail_screen(int keg_num);

/* Placeholder for the per-keg sensor-connected status (red/green
 * indicator, see kegstation/README.md "Sensor-connection status").
 * Real data will come from the C daemon's readings file once it
 * exists -- for now this just demonstrates where that data plugs in. */
static bool keg_sensor_connected(int keg_num)
{
    (void)keg_num;
    return true; /* TODO: read from the daemon's readings file */
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

static void build_keg_select_screen(void)
{
    scr_keg_select = lv_obj_create(NULL);

    lv_obj_t * title = lv_label_create(scr_keg_select);
    lv_label_set_text(title, "KegStation");
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 10);

    lv_obj_t * list = lv_list_create(scr_keg_select);
    lv_obj_set_size(list, 220, 260);
    lv_obj_align(list, LV_ALIGN_CENTER, 0, 10);

    lv_list_add_text(list, "Select a keg");

    for (int i = 0; i < NUM_KEGS; i++) {
        int keg_num = i + 1;
        char buf[16];
        snprintf(buf, sizeof(buf), "Keg %d", keg_num);

        lv_obj_t * btn = lv_list_add_button(list, NULL, buf);
        lv_obj_add_event_cb(btn, keg_button_event_cb, LV_EVENT_CLICKED,
                             (void *)(intptr_t)keg_num);

        /* Red/green sensor-connection indicator, per the settled design
         * in kegstation/README.md -- currently faked via
         * keg_sensor_connected(), not the real daemon readings file. */
        lv_obj_t * status_dot = lv_obj_create(btn);
        lv_obj_set_size(status_dot, 14, 14);
        lv_obj_set_style_radius(status_dot, LV_RADIUS_CIRCLE, 0);
        lv_obj_set_style_bg_color(status_dot,
            keg_sensor_connected(keg_num) ? lv_color_hex(0x2ecc71)
                                           : lv_color_hex(0xe74c3c),
            0);
        lv_obj_align(status_dot, LV_ALIGN_RIGHT_MID, -10, 0);

        keg_buttons[i] = btn;
        lv_group_add_obj(group, btn);
    }
}

static void build_keg_detail_screen(int keg_num)
{
    if (scr_keg_detail) {
        lv_obj_delete(scr_keg_detail);
    }
    scr_keg_detail = lv_obj_create(NULL);

    lv_obj_t * title = lv_label_create(scr_keg_detail);
    char title_buf[16];
    snprintf(title_buf, sizeof(title_buf), "Keg %d", keg_num);
    lv_label_set_text(title, title_buf);
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
    lv_obj_align(detail_status_label, LV_ALIGN_BOTTOM_MID, 0, -10);

    lv_group_remove_all_objs(group);
    lv_group_add_obj(group, tare_btn);
    lv_group_add_obj(group, setfull_btn);
    lv_group_add_obj(group, back_btn);

    lv_screen_load(scr_keg_detail);
}

void kegstation_ui_build(void)
{
    group = lv_group_create();
    lv_group_set_default(group);

    build_keg_select_screen();
    lv_screen_load(scr_keg_select);
}

lv_group_t * kegstation_ui_get_group(void)
{
    return group;
}
