/* Case-insensitive Xbox lookups on the extracted, read-only disc. Only the
 * guest worker owns this index. The file is disposable and contains names,
 * never resource bytes, handles, attributes or a promise that a file exists. */
#include <ctype.h>
#include <stdlib.h>

enum { NAME_BUCKETS = 64, NAME_INDEX_LIMIT = 2 * 1024 * 1024 };
static const char name_magic[] = "NGB-DISC-NAMES-1";
struct disc_name {
    struct disc_name *next;
    char text[];
};
struct name_directory {
    struct name_directory *next;
    struct disc_name *buckets[NAME_BUCKETS];
    size_t count;
    char relative[];
};
static struct name_directory *name_dirs;
static char name_cache_path[PATH_CAP];
static size_t name_memory;
static int names_active, names_dirty;

static unsigned name_bucket(const char *s)
{
    unsigned hash = 5381;
    while (*s) hash = hash * 33u + (unsigned)tolower((unsigned char)*s++);
    return hash % NAME_BUCKETS;
}

static const char *find_disc_name(const struct name_directory *d, const char *name)
{
    if (d) {
        for (struct disc_name *e = d->buckets[name_bucket(name)]; e; e = e->next)
            if (!strcasecmp(e->text, name)) return e->text;
    }
    return NULL;
}

static struct name_directory **name_slot(const char *relative)
{
    struct name_directory **slot = &name_dirs;
    while (*slot && strcmp((*slot)->relative, relative)) slot = &(*slot)->next;
    return slot;
}

static struct name_directory *new_name_directory(const char *relative)
{
    size_t size = sizeof(struct name_directory) + strlen(relative) + 1;
    if (size > NAME_INDEX_LIMIT - name_memory) return NULL;
    struct name_directory *d = calloc(1, size);
    if (d) { strcpy(d->relative, relative); name_memory += size; }
    return d;
}

static int add_disc_name(struct name_directory *d, const char *name)
{
    /* Keep the spelling of the first directory entry, as the guest file
     * bridge does when a case-sensitive host contains two equivalent names. */
    if (find_disc_name(d, name)) return 1;
    size_t size = sizeof(struct disc_name) + strlen(name) + 1;
    if (size > NAME_INDEX_LIMIT - name_memory) return 0;
    struct disc_name *e = malloc(size);
    if (!e) return 0;
    name_memory += size;
    strcpy(e->text, name);
    unsigned bucket = name_bucket(name);
    e->next = d->buckets[bucket];
    d->buckets[bucket] = e;
    ++d->count;
    return 1;
}

static void free_name_directory(struct name_directory *d)
{
    for (unsigned i = 0; i < NAME_BUCKETS; ++i) {
        struct disc_name *e = d->buckets[i];
        while (e) {
            struct disc_name *next = e->next;
            name_memory -= sizeof(*e) + strlen(e->text) + 1;
            free(e);
            e = next;
        }
    }
    name_memory -= sizeof(*d) + strlen(d->relative) + 1;
    free(d);
}

static void clear_disc_names(void)
{
    while (name_dirs) {
        struct name_directory *next = name_dirs->next;
        free_name_directory(name_dirs);
        name_dirs = next;
    }
    names_active = names_dirty = 0;
}

static int valid_disc_leaf(const char *name)
{
    return *name && !strpbrk(name, "/:\\") && strcmp(name, ".") && strcmp(name, "..");
}

static int same_names(const struct name_directory *a, const struct name_directory *b)
{
    if (!a || a->count != b->count) return 0;
    for (unsigned i = 0; i < NAME_BUCKETS; ++i)
        for (struct disc_name *e = b->buckets[i]; e; e = e->next) {
            const char *old = find_disc_name(a, e->text);
            if (!old || strcmp(old, e->text)) return 0;
        }
    return 1;
}

static int disc_entry_is_dir(const struct dirent *entry, const char *path)
{
#ifdef DT_DIR
    if (entry->d_type != DT_UNKNOWN) return entry->d_type == DT_DIR;
#endif
    (void)entry;
    struct stat st;
    return !plain_stat(path, &st) && S_ISDIR(st.st_mode);
}

/* Build a replacement privately. A read error must not publish half a folder.
 * Walk children only on the first build. A lookup miss refreshes one parent. */
static struct name_directory *scan_disc_names(const char *path, const char *relative, int walk, unsigned depth)
{
    if (depth > 32) return NULL;
    DIR *stream = opendir(path);
    if (!stream) return NULL;
    struct name_directory *fresh = new_name_directory(relative);
    int ok = fresh != NULL;
    while (ok) {
        errno = 0;
        struct dirent *e = readdir(stream);
        if (!e) { ok = errno == 0; break; }
        if (!valid_disc_leaf(e->d_name)) continue;
        if (!add_disc_name(fresh, e->d_name)) { ok = 0; break; }
        if (walk) {
            char child[PATH_CAP];
            if (!copy_path(child, sizeof child, path) || !append(child, e->d_name)) continue;
            if (disc_entry_is_dir(e, child)) {
                const char *rel = child + strlen(disc);
                if (*rel == '/') ++rel;
                ok = scan_disc_names(child, rel, 1, depth + 1) != NULL;
            }
        }
    }
    if (closedir(stream)) ok = 0;
    if (!ok) {
        if (fresh) free_name_directory(fresh);
        return NULL;
    }
    struct name_directory **slot = name_slot(relative);
    struct name_directory *old = *slot;
    if (same_names(old, fresh)) { free_name_directory(fresh); return old; }
    fresh->next = old ? old->next : NULL;
    *slot = fresh;
    if (old) free_name_directory(old);
    names_dirty = 1;
    return fresh;
}

/* NUL-terminated records: magic, mount path, then P<relative parent> and
 * N<leaf> groups, followed by E. A truncated or unknown format is rebuilt. */
static int load_disc_names(void)
{
    struct stat st;
    if (plain_stat(name_cache_path, &st) || !S_ISREG(st.st_mode) ||
        st.st_size <= 0 || st.st_size > NAME_INDEX_LIMIT) return 0;
    size_t size = (size_t)st.st_size;
    char *bytes = malloc(size);
    if (!bytes) return 0;
    FILE *f = fopen(name_cache_path, "rb");
    int ok = f && fread(bytes, 1, size, f) == size && fgetc(f) == EOF && !ferror(f);
    if (f && fclose(f)) ok = 0;
    char *at = bytes, *end = bytes + size;
    struct name_directory *group = NULL;
    size_t header = sizeof(name_magic) + strlen(disc) + 1;
    ok = ok && size >= header && !memcmp(bytes, name_magic, sizeof name_magic) &&
         !memcmp(bytes + sizeof name_magic, disc, strlen(disc) + 1);
    if (ok) at += header;
    int finished = 0;
    while (ok && at < end) {
        char *zero = memchr(at, 0, (size_t)(end - at));
        if (!zero || zero == at || zero - at > PATH_CAP) { ok = 0; break; }
        char tag = *at++;
        if (tag == 'P') {
            /* A parent is only a lookup key. Cached paths are never used to
             * open a directory. File access still walks the live guest path. */
            struct name_directory **slot = name_slot(at);
            if (*slot || !(group = new_name_directory(at))) ok = 0;
            else *slot = group;
        } else if (tag == 'N') {
            ok = group && valid_disc_leaf(at) && add_disc_name(group, at);
        } else if (tag == 'E') {
            finished = zero == at && zero + 1 == end;
            break;
        } else ok = 0;
        at = zero + 1;
    }
    free(bytes);
    return ok && finished && *name_slot("") != NULL;
}

static int write_name_record(FILE *f, int tag, const char *s)
{
    size_t n = strlen(s) + 1;
    return fputc(tag, f) != EOF && fwrite(s, 1, n, f) == n;
}

static void store_disc_names(void)
{
    if (!names_dirty || !name_cache_path[0]) return;
    char tmp[PATH_CAP];
    if (snprintf(tmp, sizeof tmp, "%s.XXXXXX", name_cache_path) >= (int)sizeof tmp) return;
    int fd = mkstemp(tmp);
    if (fd < 0) return;
    FILE *f = fdopen(fd, "wb");
    if (!f) { close(fd); unlink(tmp); return; }
    size_t root_size = strlen(disc) + 1;
    int ok = fwrite(name_magic, 1, sizeof name_magic, f) == sizeof name_magic &&
             fwrite(disc, 1, root_size, f) == root_size;
    for (struct name_directory *d = name_dirs; ok && d; d = d->next) {
        ok = write_name_record(f, 'P', d->relative);
        for (unsigned i = 0; ok && i < NAME_BUCKETS; ++i)
            for (struct disc_name *e = d->buckets[i]; ok && e; e = e->next)
                ok = write_name_record(f, 'N', e->text);
    }
    if (ok) ok = write_name_record(f, 'E', "");
    if (fclose(f)) ok = 0;
    if (ok && rename(tmp, name_cache_path)) {
        /* Horizon can refuse replacement. A missing cache after an
         * interrupted rename is rebuilt from the disc on the next launch. */
        struct stat st;
        ok = (errno == EEXIST || errno == EACCES || errno == ENOTEMPTY) &&
             !plain_stat(name_cache_path, &st) && S_ISREG(st.st_mode) &&
             !unlink(name_cache_path) && !rename(tmp, name_cache_path);
    }
    if (ok) names_dirty = 0;
    else unlink(tmp);
}

static void start_disc_names(const char *cache_dir)
{
    name_cache_path[0] = 0;
    if (cache_dir && *cache_dir && !directory(cache_dir) &&
        copy_path(name_cache_path, sizeof name_cache_path, cache_dir) &&
        append(name_cache_path, "disc-names-v1.bin")) {
        if (load_disc_names()) { names_active = 1; return; }
        clear_disc_names();
    } else name_cache_path[0] = 0;
    if (scan_disc_names(disc, "", 1, 0)) {
        names_active = 1;
        store_disc_names();
    } else clear_disc_names();
}
