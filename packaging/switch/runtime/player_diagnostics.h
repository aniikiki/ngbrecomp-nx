#pragma once
#ifdef __cplusplus
extern "C" {
#endif
extern int ngb_diagnostics_enabled; /* Set before starting either worker. */
#ifdef __cplusplus
}
#endif
#define NGB_DIAG ngb_diagnostics_enabled

#if defined(NGB_PLAYER_BUILD) && defined(__cplusplus)
#include "mission_perf.h"
#endif
