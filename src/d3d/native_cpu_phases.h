#pragma once

// The register-ABI pass gates and the cooperative scheduler share these IDs.
#define NGB_CPU_OTHER             0
#define NGB_CPU_PARTICLE_UPDATE   1
#define NGB_CPU_PARTICLE_PREPARE  2
#define NGB_CPU_ORDERED_LIST      3
#define NGB_CPU_EFFECT_PREPARE    4
#define NGB_CPU_DRAW_TASK         5
#define NGB_CPU_PLAYER_UPDATE     6
#define NGB_CPU_SCENE_ACTORS      7
#define NGB_CPU_INTERRUPT         8
#define NGB_CPU_PHASE_COUNT       9

#ifndef __ASSEMBLER__
#ifdef __cplusplus
extern "C" {
#endif
unsigned ngb_native_cpu_resume(unsigned phase);
unsigned ngb_native_cpu_enter(unsigned phase);
#ifdef __cplusplus
}
#endif
#endif
