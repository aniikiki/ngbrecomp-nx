/* Autosaves made while leaving the front end. The game has already encoded
 * and signed the entire record. Only the guest thread accesses file handles.
 * The writer owns its own bytes and never consults guest RAM. */
#include <pthread.h>

enum { PROFILE_BYTES = 1360 };
static struct {
    pthread_mutex_t lock;
    pthread_cond_t changed;
    pthread_t thread;
    int started, pending, writing, failed, stop;
    unsigned char latest[PROFILE_BYTES];
    char path[PATH_CAP];
} profile = { .lock = PTHREAD_MUTEX_INITIALIZER, .changed = PTHREAD_COND_INITIALIZER };

#define PROFILE_DIR "/hdd/partition1/TDATA/5443000d"
static int profile_location(const char *native, const char *relative)
{
    size_t n = strlen(data);
    while (n && data[n-1] == '/') --n;
    return !strncmp(native, data, n) && !strcasecmp(native + n, relative);
}

static int profile_temp(const char *name)
{
    return !strcasecmp(name, "system.dat.ngb-new") || !strcasecmp(name, "system.dat.ngb-old");
}

static int profile_sidecar(char *out, const char *path, const char *suffix)
{
    return snprintf(out, PATH_CAP, "%s%s", path, suffix) < PATH_CAP;
}

/* Horizon may refuse to rename over an existing file. If interrupted between
 * its two renames, the old file is complete and the new one was already synced. */
static int recover_profile(const char *path)
{
    char old[PATH_CAP], next[PATH_CAP];
    if (!profile_sidecar(old, path, ".ngb-old") || !profile_sidecar(next, path, ".ngb-new")) return -1;
    struct stat st;
    if (!plain_stat(old, &st)) {
        if (!S_ISREG(st.st_mode)) return -1;
        if (plain_stat(path, &st)) {
            if (errno != ENOENT) return -1;
            if (plain_stat(next, &st) || !S_ISREG(st.st_mode) || st.st_size != PROFILE_BYTES || rename(next, path)) {
                if (rename(old, path)) return -1;
            }
        } else if (!S_ISREG(st.st_mode)) return -1;
        if (unlink(old) && errno != ENOENT) return -1;
    } else if (errno != ENOENT) return -1;
    return unlink(next) && errno != ENOENT ? -1 : 0;
}

/* Recover before charging files to the Xbox quota. Keep the original
 * spelling of system.dat on case-sensitive host filesystems. */
static int recover_profile_directory(DIR *dir, const char *path)
{
    struct dirent *entry;
    while ((entry = readdir(dir))) {
        if (!profile_temp(entry->d_name)) continue;
        char native[PATH_CAP], leaf[sizeof "system.dat"];
        memcpy(leaf, entry->d_name, sizeof leaf - 1);
        leaf[sizeof leaf - 1] = 0;
        if (!copy_path(native, sizeof native, path) || !append(native, leaf) || recover_profile(native)) return -1;
        break;
    }
    rewinddir(dir);
    return 0;
}

static int publish_profile(const unsigned char *bytes)
{
    char next[PATH_CAP], old[PATH_CAP];
    const char *path = profile.path;
    if (!profile_sidecar(next, path, ".ngb-new") || !profile_sidecar(old, path, ".ngb-old") ||
        recover_profile(path)) return -1;
    /* Exclusive create prevents following a link in a host replay directory. */
    FILE *f = fopen(next, "wbx");
    if (!f) return -1;
    int ok = fwrite(bytes, 1, PROFILE_BYTES, f) == PROFILE_BYTES && !fflush(f) && !fsync(fileno(f));
    if (fclose(f)) ok = 0;
    if (ok && !rename(next, path)) return 0;
    if (ok && (errno == EEXIST || errno == EACCES || errno == ENOTEMPTY) && !rename(path, old)) {
        if (!rename(next, path)) {
            (void)unlink(old);
            return 0;
        }
        if (rename(old, path)) return -1; /* Both candidates remain recoverable. */
    }
    (void)unlink(next);
    return -1;
}

static void *profile_writer(void *unused)
{
    (void)unused;
    unsigned char bytes[PROFILE_BYTES];
    pthread_mutex_lock(&profile.lock);
    for (;;) {
        while (!profile.pending && !profile.stop) pthread_cond_wait(&profile.changed, &profile.lock);
        if (!profile.pending) break;
        memcpy(bytes, profile.latest, sizeof bytes);
        profile.pending = 0;
        profile.writing = 1;
        pthread_mutex_unlock(&profile.lock);
        int failed = publish_profile(bytes);
        pthread_mutex_lock(&profile.lock);
        profile.writing = 0;
        profile.failed = failed;
        pthread_cond_broadcast(&profile.changed);
    }
    pthread_mutex_unlock(&profile.lock);
    return NULL;
}

/* A real guest open or normal shutdown must see the latest complete record.
 * Retry a media error at this boundary, retaining the last good disk record. */
static int drain_profile(void)
{
    if (!profile.started) return 0;
    pthread_mutex_lock(&profile.lock);
    while (profile.pending || profile.writing) pthread_cond_wait(&profile.changed, &profile.lock);
    if (profile.failed) profile.failed = publish_profile(profile.latest);
    int failed = profile.failed;
    pthread_mutex_unlock(&profile.lock);
    return failed;
}

static int stop_profile(void)
{
    int failed = drain_profile();
    if (profile.started) {
        pthread_mutex_lock(&profile.lock);
        profile.stop = 1;
        pthread_cond_signal(&profile.changed);
        pthread_mutex_unlock(&profile.lock);
        pthread_join(profile.thread, NULL);
    }
    profile.started = profile.stop = profile.failed = 0;
    profile.path[0] = 0;
    return failed;
}

int ngb_queue_menu_profile(const void *bytes, unsigned size)
{
    /* A successful ordinary close established the exact path and record size.
     * A first creation, a different layout or a sharing conflict uses retail I/O. */
    if (size != PROFILE_BYTES || !profile.path[0]) return 0;
    for (unsigned i = 0; i < FILE_SLOTS; ++i)
        if (handles[i].token && !strcasecmp(handles[i].path, profile.path)) return 0;
    if (!profile.started) {
        if (pthread_create(&profile.thread, NULL, profile_writer, NULL)) return 0;
        profile.started = 1;
    }
    pthread_mutex_lock(&profile.lock);
    memcpy(profile.latest, bytes, size);
    profile.pending = 1;
    pthread_cond_signal(&profile.changed);
    pthread_mutex_unlock(&profile.lock);
    return 1;
}
