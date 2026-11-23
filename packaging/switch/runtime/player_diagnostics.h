#pragma once
#ifdef __cplusplus
extern "C" {
#endif
/* The retained renderer uses this symbol for the detailed boot.log probes. */
extern int ngb_diagnostics_enabled;
#ifdef __cplusplus
}
#endif
#define NGB_DIAG ngb_diagnostics_enabled

#if defined(NGB_PLAYER_BUILD) && defined(__cplusplus)
#include "mission_perf.h"
#endif
