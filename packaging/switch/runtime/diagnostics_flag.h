#pragma once

#include <stdio.h>
#include <sys/stat.h>

#define NGB_RUNTIME_DIR "sdmc:/switch/ngb-runtime/"
#define NGB_LOG_DIR NGB_RUNTIME_DIR "logs"
#define NGB_DIAGNOSTICS_FLAG "diagnostics.flag"
#define NGB_BOOT_FLAG "boot.flag"
#define NGB_MENU_PERF_FLAG "menu-perf.flag"
#define NGB_GAME_PERF_CSV "game-perf.csv"

static inline int ngb_diagnostics_requested(const char *path)
{
    struct stat st;
    return stat(path, &st) == 0 && S_ISREG(st.st_mode);
}

static inline FILE *ngb_open_error_log(void)
{
    mkdir(NGB_LOG_DIR, 0777);
    return fopen(NGB_LOG_DIR "/error.log", "a");
}
