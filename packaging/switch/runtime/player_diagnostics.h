#pragma once
#ifdef __cplusplus
extern "C" {
#endif
extern int ngb_diagnostics_enabled; /* Set before starting either worker. */
#ifdef __cplusplus
}
#endif
#define NGB_DIAG ngb_diagnostics_enabled
