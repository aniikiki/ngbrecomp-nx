#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
enum { NGB_RENDER_720P = 0 }; /* Fixed picture size in the render-scale API. */
void ngb_switch_sample_quick(unsigned bits);
int ngb_switch_setting(unsigned id);
void ngb_switch_frame(void);
int ngb_settings_standard_aspect(void);
int ngb_settings_glow(void);
int ngb_settings_skip_intro(void);
int ngb_switch_exit_report(int tab,uint8_t *report);
void ngb_settings_open(void);
#ifdef __cplusplus
}
#endif
