/* A standalone libnx bring-up probe; it does not load the game or its saves. */
#include <switch.h>
#include <errno.h>
#include <inttypes.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define PROBE_DIR "sdmc:/switch/ngb-probe"
#define MEMORY_BYTES (8u * 1024u * 1024u)

static FILE *log_file;
static char log_path[256];
static char io_status[100] = "not run";
static char memory_status[100] = "not run";
static atomic_bool stop_worker;
static atomic_uint heartbeat;

static void log_line(const char *fmt, ...)
{
    if (!log_file) return;
    fprintf(log_file, "[%" PRIu64 " ms] ", armTicksToNs(armGetSystemTick()) / 1000000);
    va_list ap;
    va_start(ap, fmt);
    vfprintf(log_file, fmt, ap);
    va_end(ap);
    fputc('\n', log_file);
    fflush(log_file); /* Preserve diagnostics if a later test stops responding. */
}

static bool ensure_dir(const char *path)
{
    if (mkdir(path, 0777) == 0) return true;
    struct stat st;
    return errno == EEXIST && stat(path, &st) == 0 && S_ISDIR(st.st_mode);
}

static void test_sd(void)
{
    char path[300];
    snprintf(path, sizeof(path), "%s.io", log_path);
    const char expected[] = "NGB Switch probe: SD write/read verification\n";
    char actual[sizeof(expected)] = {0};
    FILE *f = fopen(path, "wbx");
    bool ok = false;
    int saved_errno = errno;
    if (f) {
        ok = fwrite(expected, 1, sizeof(expected), f) == sizeof(expected);
        if (fflush(f) != 0) ok = false;
        if (fsync(fileno(f)) != 0) ok = false;
        if (fclose(f) != 0) ok = false;
        saved_errno = errno;
        if (ok) {
            f = fopen(path, "rb");
            if (f) {
                ok = fread(actual, 1, sizeof(actual), f) == sizeof(actual);
                ok = ok && memcmp(actual, expected, sizeof(expected)) == 0;
                if (fclose(f) != 0) ok = false;
            } else ok = false;
            saved_errno = errno;
        }
        /* Only remove the scratch file created by this invocation. */
        if (remove(path) != 0) { ok = false; saved_errno = errno; }
    }
    if (ok) snprintf(io_status, sizeof(io_status), "PASS: write / flush / reopen / compare / remove");
    else snprintf(io_status, sizeof(io_status), "FAIL: errno=%d (%s)", saved_errno, strerror(saved_errno));
    log_line("SD: %s", io_status);
}

static void test_memory(void)
{
    uint32_t *p = aligned_alloc(0x1000, MEMORY_BYTES);
    if (!p) {
        snprintf(memory_status, sizeof(memory_status), "FAIL: 8 MiB allocation");
    } else {
        size_t count = MEMORY_BYTES / sizeof(*p), i;
        /* Volatile reads ensure the compiler cannot elide the verification. */
        volatile uint32_t *v = p;
        for (i = 0; i < count; ++i) v[i] = (uint32_t)i ^ UINT32_C(0xa57c0de5);
        for (i = 0; i < count; ++i)
            if (v[i] != ((uint32_t)i ^ UINT32_C(0xa57c0de5))) break;
        snprintf(memory_status, sizeof(memory_status), "%s: 8 MiB aligned heap pattern", i == count ? "PASS" : "FAIL");
        free(p);
    }
    log_line("MEMORY: %s (does not test guest address mappings)", memory_status);
}

static void worker_main(void *unused)
{
    (void)unused;
    while (!atomic_load_explicit(&stop_worker, memory_order_relaxed)) {
        atomic_fetch_add_explicit(&heartbeat, 1, memory_order_relaxed);
        svcSleepThread(100000000); /* 100 ms; no busy loop. */
    }
}

int main(int argc, char **argv)
{
    (void)argc; (void)argv;
    consoleInit(NULL);
    padConfigureInput(1, HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);

    bool dirs = ensure_dir("sdmc:/switch") && ensure_dir(PROBE_DIR) && ensure_dir(PROBE_DIR "/logs");
    snprintf(log_path, sizeof(log_path), PROBE_DIR "/logs/basic-%016" PRIx64 ".log", armGetSystemTick());
    if (dirs) log_file = fopen(log_path, "wx");
    log_line("NGB Switch basic probe 0.1.0; no game assets loaded");
    log_line("applet_type=%d hos=%u.%u.%u", appletGetAppletType(),
             HOSVER_MAJOR(hosversionGet()), HOSVER_MINOR(hosversionGet()), HOSVER_MICRO(hosversionGet()));

    u64 total = 0, used = 0;
    Result total_rc = svcGetInfo(&total, InfoType_TotalMemorySize, CUR_PROCESS_HANDLE, 0);
    Result used_rc = svcGetInfo(&used, InfoType_UsedMemorySize, CUR_PROCESS_HANDLE, 0);
    log_line("process_memory: total=%" PRIu64 " used=%" PRIu64 " query_rc=%08x/%08x", total, used, total_rc, used_rc);
    if (log_file) test_sd();
    else snprintf(io_status, sizeof(io_status), "FAIL: cannot create SD log (errno=%d)", errno);
    test_memory();

    Thread worker;
    Result thread_rc = threadCreate(&worker, worker_main, NULL, NULL, 0x10000, 0x2c, -2);
    bool worker_created = R_SUCCEEDED(thread_rc);
    if (worker_created) thread_rc = threadStart(&worker);
    bool worker_started = worker_created && R_SUCCEEDED(thread_rc);
    log_line("THREAD create/start: rc=%08x", thread_rc);

    u64 last_buttons = 0;
    unsigned frames = 0;
    bool plus_exit = false;
    while (appletMainLoop()) {
        padUpdate(&pad);
        u64 down = padGetButtonsDown(&pad);
        u64 held = padGetButtons(&pad);
        HidAnalogStickState left = padGetStickPos(&pad, 0);
        HidAnalogStickState right = padGetStickPos(&pad, 1);
        if (held != last_buttons || (down & HidNpadButton_X)) {
            log_line("INPUT connected=%d buttons=%016" PRIx64 " left=%d,%d right=%d,%d heartbeat=%u",
                     padIsConnected(&pad), held, left.x, left.y, right.x, right.y, atomic_load(&heartbeat));
            last_buttons = held;
        }
        if (down & HidNpadButton_Plus) { plus_exit = true; break; }
        if ((down & HidNpadButton_A) && log_file) test_sd();
        if (down & HidNpadButton_B) test_memory();
        if (frames++ % 6 == 0) {
            consoleClear();
            printf("NGB SWITCH - BASIC PROBE 0.1.0\n\n");
            printf("Mode: %s (type %d)\n", appletGetAppletType() == AppletType_Application ? "Application" : "Applet/other", appletGetAppletType());
            if (R_SUCCEEDED(total_rc) && R_SUCCEEDED(used_rc))
                printf("Memory at startup: total=%" PRIu64 " MiB, used=%" PRIu64 " MiB\n", total >> 20, used >> 20);
            else printf("Memory query unavailable: %08x / %08x\n", total_rc, used_rc);
            printf("SD:     %s\nHeap:   %s\n", io_status, memory_status);
            printf("Worker: %s; heartbeat=%u (should increase)\n\n", worker_started ? "started" : "FAIL", atomic_load(&heartbeat));
            printf("Controller: %s\n", padIsConnected(&pad) ? "connected" : "NOT CONNECTED");
            printf("Held buttons: %016" PRIx64 "\n", held);
            printf("Left stick:  %6d %6d\nRight stick: %6d %6d\n\n", left.x, left.y, right.x, right.y);
            printf("A: repeat SD test    B: repeat heap test\n");
            printf("X: log sticks/buttons    PLUS: exit to hbmenu\n\n");
            printf("Log: %s\n%s\n\n", log_file ? "OPEN" : "FAILED", log_path);
            printf("This is a platform probe, NOT the game.\n");
            printf("Guest mapping, Xbox scheduling and GPU are not tested here.\n");
        }
        consoleUpdate(NULL);
    }

    atomic_store(&stop_worker, true);
    if (worker_started) log_line("THREAD join: rc=%08x", threadWaitForExit(&worker));
    if (worker_created) log_line("THREAD close: rc=%08x", threadClose(&worker));
    log_line("EXIT clean; reason=%s; heartbeat=%u", plus_exit ? "PLUS" : "appletMainLoop", atomic_load(&heartbeat));
    if (log_file) { fsync(fileno(log_file)); fclose(log_file); }
    consoleExit(NULL);
    return 0;
}
