#pragma once
#ifdef __cplusplus
extern "C" {
#endif
void ngb_switch_sample_quick(unsigned bits);
int ngb_switch_setting(unsigned id);
void ngb_switch_frame(void);
int ngb_settings_standard_aspect(void);
int ngb_settings_glow(void);
int ngb_settings_skip_intro(void);
void ngb_settings_open(void);
#ifdef __cplusplus
}
#endif
