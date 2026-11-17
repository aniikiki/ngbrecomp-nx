#pragma once
#include <stdint.h>
enum { MP_STRIP, MP_READ, MP_UPLOAD, MP_GL_DRAW, MP_VK_DRAW, MP_VK_PRESENT, MP_FLIP, MP_THUMB_HIT, MP_THUMB_MISS, MP_PAD, MP_FINISH, MP_POST_FINISH, MP_COUNT };
#if defined(NGB_PLAYER_BUILD) || defined(NGB_MISSION_PROBE)
#ifdef __cplusplus
extern "C" {
#endif
extern int ngb_mission_enabled, ngb_mission_gl_split;
extern unsigned ngb_mission_guest_id; /* guest thread only */
void ngb_mission_stage(unsigned stage, unsigned state);
void ngb_mission_count(unsigned kind, uint64_t ns, unsigned amount);
void ngb_mission_dump(void);
#ifdef __cplusplus
}
#endif
#define MP_ACTIVE (ngb_mission_guest_id != 0)
#define MP_ADD(k,ns,n) do { if (MP_ACTIVE) ngb_mission_count(k,ns,n); } while (0)
#else
#define MP_ACTIVE 0
#define MP_ADD(k,ns,n) ((void)0)
#endif
