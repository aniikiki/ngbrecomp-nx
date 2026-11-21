/* Xbox names/32-bit handles above POSIX files, following kernel_path.c and
 * kernel_bridge.c's guest layouts. Disc files are read-only. Data writes are
 * bounded for bring-up. The bridge dispatches overlapped disc reads. */
#define _POSIX_C_SOURCE 200809L
#include "files.h"
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <dirent.h>
#include <errno.h>
#include <limits.h>
#include <unistd.h>

#define PATH_CAP 1024
#define FILE_SLOTS 256u
#define BAD_NAME 0xc0000033u
#define NOT_FOUND 0xc0000034u
#define PATH_NOT_FOUND 0xc000003au
#define DENIED 0xc0000022u
#define TOO_SMALL 0xc0000023u
#define INVALID 0xc000000du
#define DELETE_PENDING 0xc0000056u
#define DIRECTORY_NOT_EMPTY 0xc0000101u
#define FILE_DELETE_ACCESS 0x00010000u
#define FILE_WRITE_ATTRIBUTES 0x00000100u
#define FILE_DIRECTORY_FILE 0x00000001u
#define FILE_NON_DIRECTORY_FILE 0x00000040u
#define FILE_OPEN_FOR_BACKUP_INTENT 0x00004000u
#define FILE_WRITE_THROUGH 0x00000002u
static char disc[PATH_CAP], data[PATH_CAP];
static struct {
    uint32_t token, access, share, options;
    FILE *file;
    DIR *directory;
    char path[PATH_CAP], pattern[256];
    int readonly, volume_root;
    int disc_async, read_unsignalled;
    int packed;
    int raw_disk;
    int dismounted;
    int delete_mark, delete_committed;
    unsigned link_id;
    uint32_t raw_position;
    uint32_t file_limit;
    int64_t logical_position;
} handles[FILE_SLOTS];
static struct { char name[64], target[PATH_CAP]; } links[16];
static uint32_t serial;
/* Ordinary title data and the disposable FATX cache have independent
 * limits. Keep raw formatting metadata in the small system-data budget. */
#define CACHE_BYTES (0x177000u * 512u)
static uint64_t data_bytes, cache_bytes;
static unsigned cache_files;
static int is_cache(const char *path)
{
    size_t n=strlen(data);
    if(strncmp(path,data,n))return 0;
    const char *v=path+n;
    return !strncmp(v,"/hdd/partition",14) && v[14]>='3' && v[14]<='5' &&
           (v[15]=='/' || !v[15]);
}
#define USED(p) (*(is_cache(p)?&cache_bytes:&data_bytes))
#define FILE_COUNT(p) (*(is_cache(p)?&cache_files:&data_files))
#define QUOTA(p) (is_cache(p)?CACHE_BYTES:NGB_DATA_MAX_BYTES)
static unsigned data_files;

/* The private bootstrap RomFS keeps selected byte ranges from the disc.
 * Enumeration reports original file sizes. Reads outside the packaged
 * prefix stop at the bridge, before returning any incomplete data. */
struct disc_entry { char path[160]; uint32_t size, count; struct {uint32_t start,length;} ranges[8]; };
static struct disc_entry catalog[1024];
static size_t catalog_count;
int ngb_disc_archives_direct;
static unsigned char disk_header[4096];
static char disk_header_path[PATH_CAP];
static int disk_header_saved;
static void put32(unsigned char *p, uint32_t n);
static void put64(unsigned char *p, uint64_t n);

static uint32_t error_status(void)
{
    switch (errno) {
    case ENOENT: return NOT_FOUND;
    case ENOTDIR: return 0xc0000103u;
    case EISDIR: return 0xc00000bau;
    case EACCES: case EPERM: case EROFS: return DENIED;
    case EEXIST: return 0xc0000035u;
    case ENOTEMPTY: return DIRECTORY_NOT_EMPTY;
    case EMFILE: case ENFILE: return 0xc000011fu;
    default: return 0xc0000001u;
    }
}
static int copy_path(char *out, size_t capacity, const char *in)
{
    size_t n = strlen(in);
    if (n >= capacity) return 0;
    memcpy(out, in, n + 1);
    return 1;
}
static int append(char *out, const char *component)
{
    size_t n = strlen(out), m = strlen(component);
    int slash = n && out[n - 1] != '/';
    if (n + (unsigned)slash + m >= PATH_CAP) return 0;
    if (slash) out[n++] = '/';
    memcpy(out + n, component, m + 1);
    return 1;
}
static int load_catalog(int *extracted_disc)
{
    char path[PATH_CAP];
    if (!copy_path(path,sizeof(path),disc) || !append(path,".ngb-disc")) return -1;
    catalog_count=0;
    FILE *f=fopen(path,"rb");
    if (!f) {
        if (errno != ENOENT) return -1;
        *extracted_disc = 1;
        return 0;
    }
    unsigned char raw[sizeof(struct disc_entry)];
    size_t n;
    int failed=0;
    while ((n=fread(raw,1,sizeof(raw),f))) {
        if (n!=sizeof(raw) || catalog_count==1024 || !memchr(raw,0,160)) { failed=1; break; }
        struct disc_entry *e=&catalog[catalog_count++];
        memcpy(e,raw,sizeof(*e));
        if (e->count>8) { failed=1; break; }
        uint64_t end=0;
        for (unsigned j=0;j<e->count;++j) {
            if (e->ranges[j].start<end) failed=1;
            end=(uint64_t)e->ranges[j].start+e->ranges[j].length;
            if (end>e->size) failed=1;
        }
        if (failed) break;
    }
    if (ferror(f)) failed=1;
    fclose(f);
    return failed ? -1 : 0;
}

static const struct disc_entry *disc_entry_for(const char *path)
{
    if (!catalog_count) return NULL;
    size_t n=strlen(disc);
    if (strncmp(path,disc,n)) return NULL;
    if (n && disc[n-1]!='/') { if (path[n]!='/') return NULL; ++n; }
    for (size_t i=0;i<catalog_count;i++)
        if (!strcasecmp(path+n,catalog[i].path)) return &catalog[i];
    return NULL;
}

static int plain_stat(const char *path, struct stat *st)
{
#ifdef __SWITCH__
    /* SD and RomFS have no symlinks. */
    return stat(path, st);
#else
    if (lstat(path, st)) return -1;
    if (S_ISLNK(st->st_mode)) { errno = EACCES; return -1; }
    return 0;
#endif
}
static int directory(const char *path)
{
    struct stat st;
    if (!plain_stat(path, &st)) return S_ISDIR(st.st_mode) ? 0 : -1;
    if (errno != ENOENT) return -1;
    return mkdir(path, 0777);
}
static int object_index(uint32_t token)
{
    unsigned index = token & (FILE_SLOTS-1);
    return token && handles[index].token == token ? (int)index : -1;
}
static int index_for(uint32_t token)
{
    int i = object_index(token);
    return i >= 0 && !handles[i].link_id ? i : -1;
}
static uint32_t new_token(unsigned slot)
{
    serial = (serial + 1) & 0x000fffff;
    if (!serial) ++serial;
    return 0x60000000u | (serial << 8) | slot;
}
static int scan_data(const char *path, unsigned depth)
{
    if (depth > 32) return -1;
    DIR *d = opendir(path);
    if (!d) return -1;
    struct dirent *entry;
    int status = 0;
    while ((entry = readdir(d))) {
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        char child[PATH_CAP]; struct stat st;
        if (!copy_path(child, sizeof(child), path) || !append(child, entry->d_name) || plain_stat(child, &st)) { status = -1; break; }
        if (S_ISDIR(st.st_mode)) status = scan_data(child, depth + 1);
        else if (S_ISREG(st.st_mode)) { USED(child) += (uint64_t)st.st_size; ++FILE_COUNT(child); }
        else status = -1;
        if (status) break;
    }
    closedir(d);
    return status;
}
void ngb_files_close_all(void)
{
    ngb_disc_archives_direct = 0;
    for (unsigned i = 0; i < FILE_SLOTS; ++i) {
        if (handles[i].token) ngb_file_close(handles[i].token);
    }
    memset(handles, 0, sizeof(handles));
    memset(links, 0, sizeof(links));
}
FILE *ngb_open_disc_movie(const char *leaf)
{
    if (!leaf || !*leaf || strpbrk(leaf,"/:\\")) return NULL;
    char path[1200];
    int n=snprintf(path,sizeof(path),"%s%smovie/%s",disc,
                   disc[0] && disc[strlen(disc)-1]=='/' ? "" : "/",leaf);
    return n>0 && (size_t)n<sizeof(path) ? fopen(path,"rb") : NULL;
}

int ngb_files_init(const char *disc_root, const char *data_root)
{
    int extracted_disc = 0;
    ngb_files_close_all();
    if (!copy_path(disc, sizeof(disc), disc_root) || !copy_path(data, sizeof(data), data_root)) return -1;
    struct stat st;
    if (plain_stat(disc, &st) || !S_ISDIR(st.st_mode) || load_catalog(&extracted_disc) || directory(data)) return -1;
    char path[PATH_CAP];
    if (!copy_path(path, sizeof(path), data) || !append(path, "hdd") || directory(path)) return -1;
    cache_bytes = data_bytes = 0; cache_files = data_files = 0;
    /* Same retail partition table as upstream kernel_path.c, represented in
     * memory. Never create a multi-GB image or issue raw I/O to the SD card. */
    static const struct { const char *name; uint32_t start, size; } parts[] = {
        {"XBOX_PART_X", 0x400, 0x177000}, {"XBOX_PART_Y", 0x177400, 0x177000},
        {"XBOX_PART_Z", 0x2ee400, 0x177000}, {"XBOX_PART_C", 0x465400, 0xfa000},
        {"XBOX_PART_E", 0x55f400, 0x465400}
    };
    memset(disk_header, 0, sizeof(disk_header));
    memcpy(disk_header + 0x800, "****PARTINFO****", 16);
    for (unsigned i = 0; i < 5; ++i) {
        unsigned char *entry = disk_header + 0x800 + 48 + i * 32;
        memset(entry, ' ', 16); memcpy(entry, parts[i].name, strlen(parts[i].name));
        put32(entry + 16, 0x80000000); put32(entry + 20, parts[i].start);
        put32(entry + 24, parts[i].size);
    }
    if (!copy_path(disk_header_path, sizeof(disk_header_path), path) ||
        !append(disk_header_path, "partition0-header.bin")) return -1;
    disk_header_saved = 0;
    if (!plain_stat(disk_header_path, &st)) {
        if (!S_ISREG(st.st_mode) || st.st_size != sizeof(disk_header)) return -1;
        FILE *f = fopen(disk_header_path, "rb");
        if (!f) return -1;
        size_t got = fread(disk_header, 1, sizeof(disk_header), f);
        int failed = got != sizeof(disk_header) || ferror(f);
        if (fclose(f)) failed = 1;
        if (failed) return -1;
        disk_header_saved = 1;
    } else if (errno != ENOENT) return -1;
    if (scan_data(data, 0)) return -1;
    ngb_disc_archives_direct = extracted_disc;
    return 0;
}

static uint32_t write_disk_header(unsigned i, const void *buffer, uint32_t length,
                                  int64_t offset, uint32_t *written)
{
    if (!(handles[i].access & 0x50000002u)) return DENIED;
    if (offset < 0 && offset != -2) return INVALID;
    uint64_t start = offset == -2 ? handles[i].raw_position : (uint64_t)offset;
    /* Only the small modeled header exists. Never grow a file to disk size. */
    if (start > sizeof(disk_header) || length > sizeof(disk_header) - start) return NGB_FS_UNSUPPORTED;
    if (!length) return 0;
    if (!disk_header_saved && (data_files >= 128 || data_bytes + sizeof(disk_header) > NGB_DATA_MAX_BYTES))
        return 0xc000007fu;
    unsigned char updated[sizeof(disk_header)];
    memcpy(updated, disk_header, sizeof(updated));
    memcpy(updated + start, buffer, length);
    FILE *f = fopen(disk_header_path, disk_header_saved ? "r+b" : "w+b");
    if (!f) return error_status();
    size_t count = fwrite(updated, 1, sizeof(updated), f);
    int failed = count != sizeof(updated) || ferror(f);
    if (fflush(f) || fsync(fileno(f))) failed = 1;
    if (fclose(f)) failed = 1;
    if (failed) return 0xc0000001u;
    if (!disk_header_saved) { data_bytes += sizeof(disk_header); ++data_files; }
    disk_header_saved = 1;
    memcpy(disk_header, updated, sizeof(disk_header));
    handles[i].raw_position = (uint32_t)start + length;
    *written = length;
    return 0;
}

static int prefix(const char *path, const char *start)
{
    size_t n = strlen(start);
    return !strncasecmp(path, start, n) && (!path[n] || path[n] == '/');
}

static int cache_formatted(unsigned partition)
{
    char path[PATH_CAP], leaf[64];
    snprintf(leaf, sizeof(leaf), "hdd/cache-partition%u.bin", partition);
    if (!copy_path(path, sizeof(path), data) || !append(path, leaf)) return 0;
    struct stat st;
    if (plain_stat(path, &st) || !S_ISREG(st.st_mode)) return 0;
    FILE *f = fopen(path, "rb");
    if (!f) return 0;
    uint32_t header[4] = {0};
    int valid = fread(header, 1, sizeof(header), f) == sizeof(header);
    if (fclose(f)) valid = 0;
    uint32_t sectors = header[2];
    if (!valid || header[0] != 0x58544146 || header[3] != 1 || !sectors ||
        sectors > 128 || (sectors & (sectors - 1))) return 0;
    uint64_t cluster = sectors * 512u, clusters = (0x177000ull * 512) / cluster + 1;
    uint64_t fat = (clusters * (clusters < 0xfff0 ? 2 : 4) + 4095) & ~4095ull;
    return (uint64_t)st.st_size >= 4096 + fat + cluster;
}
static uint32_t resolve(const char *guest, uint32_t root, char out[PATH_CAP], int *readonly, int *volume_root)
{
    char normalized[PATH_CAP];
    if (!copy_path(normalized, sizeof(normalized), guest)) return BAD_NAME;
    for (char *p = normalized; *p; ++p) if (*p == '\\') *p = '/';
    char *tail = normalized;
    *volume_root = 1;
    /* ObDosDevicesDirectory() is a pseudo-handle to the drive namespace. */
    if (root == 0xfffffffdu) {
        if (!tail[0] || tail[1] != ':' || tail[2] != '/') return BAD_NAME;
        root = 0;
    }
    if (root) {
        int i = index_for(root);
        if (i < 0 || !handles[i].directory) return NGB_FS_INVALID_HANDLE;
        if (*tail == '/' || strchr(tail, ':')) return BAD_NAME;
        copy_path(out, PATH_CAP, handles[i].path);
        *readonly = handles[i].readonly;
        *volume_root = handles[i].volume_root;
    } else {
        if (tail[0] && tail[1] == ':') {
            char absolute[PATH_CAP] = "/?" "?/";
            if (strlen(tail) + 4 >= sizeof(absolute)) return BAD_NAME;
            strcat(absolute, tail);
            copy_path(normalized, sizeof(normalized), absolute);
        }
        /* Resolve guest drive aliases without creating host symlinks. */
        for (unsigned depth = 0; depth < 8; ++depth) {
            int found = 0;
            for (unsigned i = 0; i < 16; ++i) {
                if (!links[i].name[0] || !prefix(tail, links[i].name)) continue;
                char expanded[PATH_CAP];
                if (!copy_path(expanded, sizeof(expanded), links[i].target) ||
                    !append(expanded, tail + strlen(links[i].name))) return BAD_NAME;
                copy_path(normalized, sizeof(normalized), expanded);
                tail = normalized;
                found = 1;
                break;
            }
            if (!found) break;
            if (depth == 7) return BAD_NAME;
        }
        if (!strncasecmp(tail, "/?" "?/", 4)) tail += 4;
        if (prefix(tail, "D:") || prefix(tail, "/Device/CdRom0")) {
            tail += tail[0] == '/' ? strlen("/Device/CdRom0") : 2;
            copy_path(out, PATH_CAP, disc);
            *readonly = 1;
        } else {
            unsigned partition = 0;
            if (prefix(tail, "E:")) { partition = 1; tail += 2; }
            else if (!strncasecmp(tail, "/Device/Harddisk0/partition", 27) &&
                     tail[27] >= '1' && tail[27] <= '7' && (!tail[28] || tail[28] == '/')) {
                partition = (unsigned)(tail[27] - '0'); tail += 28;
            }
            if (!partition) return PATH_NOT_FOUND;
            if (partition >= 3 && partition <= 5 && !cache_formatted(partition)) return 0xc000014fu;
            char mount[32];
            snprintf(mount, sizeof(mount), "hdd/partition%u", partition);
            if (!copy_path(out, PATH_CAP, data) || !append(out, mount)) return BAD_NAME;
            if (directory(out)) return error_status();
            *readonly = 0;
        }
        while (*tail == '/') ++tail;
    }
    /* Resolve case-insensitively one component at a time. Reject traversal
     * and host symlinks, including a matching leaf, before using native APIs. */
    while (*tail) {
        char *slash = strchr(tail, '/');
        if (slash) *slash = 0;
        if (!strcmp(tail, "..") || strchr(tail, ':')) return DENIED;
        if (*tail && strcmp(tail, ".")) {
            *volume_root = 0;
            char component[PATH_CAP];
            copy_path(component, sizeof(component), tail);
            DIR *parent = opendir(out);
            if (!parent) return error_status();
            struct dirent *entry;
            while ((entry = readdir(parent))) {
                if (!strcasecmp(entry->d_name, tail)) {
                    copy_path(component, sizeof(component), entry->d_name); break;
                }
            }
            closedir(parent);
            if (!append(out, component)) return BAD_NAME;
            struct stat st;
            if (plain_stat(out, &st) && (errno != ENOENT || (slash && slash[1]))) return error_status();
        }
        if (!slash) break;
        tail = slash + 1;
    }
    return 0;
}

uint32_t ngb_file_link(const char *name, const char *target)
{
    char link[64], value[PATH_CAP];
    if (!copy_path(link, sizeof(link), name) || !copy_path(value, sizeof(value), target)) return BAD_NAME;
    for (char *p = link; *p; ++p) if (*p == '\\') *p = '/';
    for (char *p = value; *p; ++p) if (*p == '\\') *p = '/';
    if (strncasecmp(link, "/?" "?/", 4) || strlen(link) != 6 || link[5] != ':') return BAD_NAME;
    for (unsigned i = 0; i < 16; ++i) {
        if (links[i].name[0] && !strcasecmp(links[i].name, link)) return 0xc0000035u;
    }
    for (unsigned i = 0; i < 16; ++i) if (!links[i].name[0]) {
        copy_path(links[i].name, sizeof(links[i].name), link);
        copy_path(links[i].target, sizeof(links[i].target), value);
        return 0;
    }
    return 0xc000009au;
}

uint32_t ngb_link_open(const char *name, int ignore_case, uint32_t *handle)
{
    char normalized[64];
    *handle = 0;
    if (!copy_path(normalized, sizeof(normalized), name)) return BAD_NAME;
    for (char *p = normalized; *p; ++p) if (*p == '\\') *p = '/';
    for (unsigned j = 0; j < 16; ++j) {
        if (!links[j].name[0]) continue;
        int comparison = ignore_case ? strcasecmp(normalized, links[j].name) : strcmp(normalized, links[j].name);
        if (comparison) continue;
        for (unsigned slot = 0; slot < FILE_SLOTS; ++slot) {
            if (handles[slot].token) continue;
            handles[slot].link_id = j + 1;
            *handle = handles[slot].token = new_token(slot);
            return 0;
        }
        return 0xc000011fu;
    }
    return NOT_FOUND;
}

uint32_t ngb_link_target(uint32_t handle, char target[1024])
{
    int i = object_index(handle);
    if (i < 0) return NGB_FS_INVALID_HANDLE;
    unsigned id = handles[i].link_id;
    if (!id) return 0xc0000024u; /* STATUS_OBJECT_TYPE_MISMATCH */
    strcpy(target, links[id - 1].target);
    for (char *p = target; *p; ++p) if (*p == '/') *p = '\\';
    return 0;
}

/* The game installs archive data on its FATX cache volume in 64 KiB writes. */
static uint32_t write_limit(const char *native)
{
    size_t n = strlen(data);
    if (!strncmp(native, data, n)) {
        const char *volume = native + n;
        if (!strncmp(volume, "/hdd/partition", 14) && volume[14] >= '3' && volume[14] <= '5' &&
            volume[15] == '/') {
            const char *ext = strrchr(volume + 16, '.');
            if (ext && !strcasecmp(ext, ".afs")) return CACHE_BYTES;
        }
    }
    return NGB_FILE_MAX_BYTES;
}

uint32_t ngb_file_open(const char *path, uint32_t root, uint32_t access,
                       uint32_t share, uint32_t disposition, uint32_t options,
                       uint32_t *handle, uint32_t *information)
{
    *handle = 0; *information = 0;
    char device[PATH_CAP];
    if (!copy_path(device, sizeof(device), path)) return BAD_NAME;
    for (char *p = device; *p; ++p) if (*p == '\\') *p = '/';
    int partition = -1;
    if (!root && strlen(device) == 28 && !strncasecmp(device, "/Device/Harddisk0/partition", 27) &&
        device[27] >= '0' && device[27] <= '5') partition = device[27] - '0';
    if (partition == 0 || partition >= 3) {
        if (disposition != 1 || !(options & 0x30) || (options & ~0x38u)) return NGB_FS_UNSUPPORTED;
        /* Cache devices have a bounded backing for the formatting metadata.
         * Files under PartitionN/ remain separate host directory entries. */
        for (unsigned j = 0; j < FILE_SLOTS; ++j)
            if (partition && handles[j].token && handles[j].raw_disk == partition + 1) return 0xc0000043u;
        unsigned slot;
        for (slot = 0; slot < FILE_SLOTS && handles[slot].token; ++slot) {}
        if (slot == FILE_SLOTS) return 0xc000011fu;
        if (partition) {
            char leaf[64], native[PATH_CAP]; struct stat st;
            snprintf(leaf, sizeof(leaf), "hdd/cache-partition%d.bin", partition);
            if (!copy_path(native, sizeof(native), data) || !append(native, leaf)) return BAD_NAME;
            int exists = !plain_stat(native, &st);
            if (!exists && errno != ENOENT) return error_status();
            if (exists && (!S_ISREG(st.st_mode) || st.st_size > NGB_FILE_MAX_BYTES)) return DENIED;
            if (!exists && data_files >= 128) return 0xc000007fu;
            handles[slot].file = fopen(native, exists ? "r+b" : "w+b");
            if (!handles[slot].file) return error_status();
            if (!exists) ++data_files;
            copy_path(handles[slot].path, sizeof(handles[slot].path), native);
        }
        handles[slot].token = new_token(slot);
        handles[slot].raw_disk = partition + 1; handles[slot].access = access;
        *handle = handles[slot].token; *information = 1;
        return 0;
    }
    char native[PATH_CAP]; int readonly = 1, volume_root;
    uint32_t status = resolve(path, root, native, &readonly, &volume_root);
    if (status) return status;
    if (readonly && (access & (0x40000000u | 0x10000000u | 6u))) return DENIED;
    /* XDeleteSaveGame opens each child relative to the slot directory. Its
     * DELETE handles also request SYNCHRONIZE, WRITE_ATTRIBUTES and, for a
     * directory, LIST_DIRECTORY. Backup intent does not grant any access. */
    int delete_open = disposition == 1 && (access & FILE_DELETE_ACCESS) &&
        (options == (FILE_OPEN_FOR_BACKUP_INTENT | FILE_NON_DIRECTORY_FILE) ||
         options == (FILE_OPEN_FOR_BACKUP_INTENT | FILE_DIRECTORY_FILE));
    if (readonly && (access & FILE_DELETE_ACCESS)) return DENIED;
    if ((!(options & 0x30) && !delete_open && !(disposition == 1 && !(access & 0x50000006u) && (options & ~0x800u) == 0x48)) ||
        (options & ~(0x00804800u | 0x7fu))) return NGB_FS_UNSUPPORTED;
    struct stat st;
    int exists = !plain_stat(native, &st), created = 0;
    if (!exists && errno != ENOENT) return error_status();
    if (disposition == 2 && exists) return 0xc0000035u;
    int overwrite = disposition == 5; /* FILE_OVERWRITE_IF */
    if (disposition != 1 && disposition != 2 && disposition != 3 && !overwrite) return NGB_FS_UNSUPPORTED;
    if (overwrite && (readonly || !(access & 0x50000002u))) return DENIED;
    if (overwrite && ((options & 1) || (exists && S_ISDIR(st.st_mode)))) return INVALID;
    for (unsigned i = 0; i < FILE_SLOTS; ++i) {
        if (!handles[i].token) continue;
        if ((handles[i].delete_mark || handles[i].delete_committed) &&
            (handles[i].directory ? prefix(native, handles[i].path) : !strcmp(native, handles[i].path)))
            return DELETE_PENDING;
        if (strcmp(handles[i].path, native)) continue;
        if (((access & 0x90000001u) && !(handles[i].share & 1)) ||
            ((handles[i].access & 0x90000001u) && !(share & 1)) ||
            ((access & 0x50000006u) && !(handles[i].share & 2)) ||
            ((handles[i].access & 0x50000006u) && !(share & 2)) ||
            ((access & FILE_DELETE_ACCESS) && !(handles[i].share & 4)) ||
            ((handles[i].access & FILE_DELETE_ACCESS) && !(share & 4))) return 0xc0000043u;
    }
    if (!exists) {
        if (disposition == 1) return NOT_FOUND;
        if (readonly) return DENIED;
        if (options & 1) {
            if (directory(native) || plain_stat(native, &st)) return error_status();
        } else {
            if (FILE_COUNT(native) >= (is_cache(native)?4096u:128u)) return 0xc000007fu;
            memset(&st, 0, sizeof(st));
        }
        created = 1;
    }
    int isdir = S_ISDIR(st.st_mode);
    if ((options & 1) && !isdir) return 0xc0000103u;
    if ((options & 0x40) && isdir) return 0xc00000bau;
    if (!isdir && !created && !S_ISREG(st.st_mode)) return DENIED;
    unsigned slot;
    for (slot = 0; slot < FILE_SLOTS && handles[slot].token; ++slot) {}
    if (slot == FILE_SLOTS) return 0xc000011fu;
    handles[slot].packed = readonly && !isdir && disc_entry_for(native)!=NULL;
    if (isdir) handles[slot].directory = opendir(native);
    else if (!handles[slot].packed) {
        int writable = (access & (0x40000000u | 0x10000000u | 6u)) != 0;
        handles[slot].file = fopen(native, created || overwrite ? "w+b" : writable ? "r+b" : "rb");
        if (handles[slot].file) {
            if (created) ++FILE_COUNT(native);
            else if (overwrite) USED(native) -= (uint64_t)st.st_size;
        }
    }
    if (!handles[slot].packed && !handles[slot].file && !handles[slot].directory) return error_status();
    handles[slot].token = new_token(slot);
    handles[slot].file_limit = write_limit(native);
    handles[slot].options = options;
    handles[slot].disc_async = readonly && !isdir && !handles[slot].packed &&
                               !(options & 0x30) && (access & 0x90000001u);
    handles[slot].volume_root = volume_root;
    handles[slot].readonly = readonly; handles[slot].access = access; handles[slot].share = share;
    copy_path(handles[slot].path, sizeof(handles[slot].path), native);
    *handle = handles[slot].token; *information = created ? 2 : overwrite ? 3 : 1;
    return 0;
}
const char *ngb_file_async_disc_path(uint32_t handle)
{
    int i = index_for(handle);
    return i >= 0 && handles[i].disc_async ? handles[i].path : NULL;
}
void ngb_file_disc_submitted(uint32_t handle)
{
    int i = index_for(handle);
    if (i >= 0) handles[i].read_unsignalled = 1;
}
void ngb_file_disc_completed(uint32_t handle, int64_t offset, uint32_t received, uint32_t status)
{
    int i = index_for(handle);
    if (i < 0) return;
    if (!status || received || status == 0xc0000011u) handles[i].logical_position = offset + received;
    handles[i].read_unsignalled = 0;
}
uint32_t ngb_file_wait_status(uint32_t handle)
{
    int i=object_index(handle);
    if(i<0)return NGB_FS_INVALID_HANDLE;
    if (handles[i].link_id) return 0xc0000024u; /* STATUS_OBJECT_TYPE_MISMATCH */
    return handles[i].read_unsignalled ? NGB_FS_TIMEOUT : 0;
}
uint32_t ngb_file_flush(uint32_t handle)
{
    int i = index_for(handle);
    if (i < 0) return NGB_FS_INVALID_HANDLE;
    if (handles[i].dismounted) return 0xc00000a3u;
    if (!handles[i].file) return INVALID;
    if (handles[i].readonly) return 0;
    if (fflush(handles[i].file) || fsync(fileno(handles[i].file))) return error_status();
    return 0;
}
uint32_t ngb_file_close(uint32_t handle)
{
    int i = object_index(handle);
    if (i < 0) return NGB_FS_INVALID_HANDLE;
    int isdir = handles[i].directory != NULL;
    int rc = handles[i].link_id || handles[i].raw_disk == 1 ? 0 : handles[i].file ? fclose(handles[i].file) : handles[i].directory ? closedir(handles[i].directory) : 0;
    uint32_t status = rc ? error_status() : 0;
    if (handles[i].delete_mark || handles[i].delete_committed) {
        int another=0;
        for (unsigned j=0;j<FILE_SLOTS;j++)
            if ((int)j!=i && handles[j].token && !strcmp(handles[i].path,handles[j].path)) {
                handles[j].delete_committed=1; another=1;
            }
        if (!another && isdir) {
            if (rmdir(handles[i].path)) status = error_status();
        } else if (!another) {
            struct stat st;
            if (plain_stat(handles[i].path,&st) || unlink(handles[i].path)) status=error_status();
            else { USED(handles[i].path)-=(uint64_t)st.st_size; --FILE_COUNT(handles[i].path); }
        }
    }
    memset(&handles[i], 0, sizeof(handles[i]));
    return status;
}
/* Inspect the directory without consuming the guest's enumeration cursor. */
static uint32_t check_empty_directory(const char *path)
{
    DIR *dir = opendir(path);
    if (!dir) return error_status();
    uint32_t status = 0;
    errno = 0;
    struct dirent *entry;
    while ((entry = readdir(dir))) {
        if (strcmp(entry->d_name, ".") && strcmp(entry->d_name, "..")) {
            status = DIRECTORY_NOT_EMPTY;
            break;
        }
    }
    if (!entry && errno) status = error_status();
    if (closedir(dir) && !status) status = error_status();
    return status;
}

/* FileDispositionInformation marks a file or an empty directory for removal
 * once all its handles close. The title itself enumerates and removes children. */
uint32_t ngb_file_disposition(uint32_t handle, int pending)
{
    int i=index_for(handle);
    if (i<0) return NGB_FS_INVALID_HANDLE;
    if (handles[i].readonly || handles[i].raw_disk || handles[i].volume_root ||
        !(handles[i].access & FILE_DELETE_ACCESS)) return DENIED;
    if (pending && handles[i].directory) {
        uint32_t status = check_empty_directory(handles[i].path);
        if (status) return status;
    }
    handles[i].delete_mark=!!pending;
    return 0;
}

uint32_t ngb_file_set_basic(uint32_t handle, const void *buffer, uint32_t length)
{
    int i = index_for(handle);
    if (i < 0) return NGB_FS_INVALID_HANDLE;
    if (length < 40) return 0xc0000004u;
    if (handles[i].readonly || handles[i].raw_disk ||
        !(handles[i].access & (0x50000000u | FILE_WRITE_ATTRIBUTES))) return DENIED;
    /* XDeleteSaveGame clears the read-only attribute with zero timestamps
     * before disposition. All entries on our writable volumes already have
     * normal attributes. Directory type belongs to the object itself. */
    uint32_t attributes;
    memcpy(&attributes, (const unsigned char *)buffer + 32, sizeof(attributes));
    static const unsigned char zero_times[32] = {0};
    if (memcmp(buffer, zero_times, sizeof(zero_times)) ||
        (attributes != 0 && attributes != 0x80)) return NGB_FS_UNSUPPORTED;
    return 0;
}
const char *ngb_file_basename(uint32_t handle)
{
    int i = index_for(handle);
    if (i < 0) return "";
    const char *path = handles[i].path, *slash = strrchr(path, '/');
    return slash ? slash + 1 : path;
}

#ifdef NGB_TEXTURE_PRELOAD
extern void ngb_texture_read(const char*,uint64_t,const uint8_t*,unsigned);
#endif
void ngb_file_disc_textures(const char *name, uint64_t offset, const void *buffer, uint32_t length)
{
#ifdef NGB_TEXTURE_PRELOAD
    const char *ext = strrchr(name, '.');
    if (length && ext && !strcasecmp(ext, ".afs")) ngb_texture_read(name,offset,buffer,length);
#else
    (void)name; (void)offset; (void)buffer; (void)length;
#endif
}
uint32_t ngb_disc_stream_read(FILE *file, void *buffer, uint32_t length,
                              int64_t offset, uint32_t *received)
{
    *received = 0;
    if (!file || fseeko(file, offset, SEEK_SET)) return error_status();
    clearerr(file);
    *received = (uint32_t)fread(buffer, 1, length, file);
    if (ferror(file)) return error_status();
    return length && !*received ? 0xc0000011u : 0;
}
uint32_t ngb_file_read(uint32_t handle, void *buffer, uint32_t length,
                       int64_t offset, uint32_t *received)
{
    *received = 0;
    int i = index_for(handle);
    if (i < 0) return NGB_FS_INVALID_HANDLE;
    if (handles[i].dismounted) return 0xc00000a3u;
    if (handles[i].raw_disk == 1) {
        if (!(handles[i].access & 0x90000001u)) return DENIED;
        if (offset < 0 && offset != -2) return INVALID;
        uint64_t start = offset == -2 ? handles[i].raw_position : (uint64_t)offset;
        if (start > sizeof(disk_header) || length > sizeof(disk_header) - start) return NGB_FS_UNSUPPORTED;
        memcpy(buffer, disk_header + start, length);
        handles[i].raw_position = (uint32_t)start + length;
        *received = length;
        return 0;
    }
    if (!handles[i].packed && !handles[i].file) return 0xc00000bau;
    if (!(handles[i].access & 0x90000001u)) return DENIED;
    if (offset < -2 || offset == -1) return INVALID;
    if (handles[i].disc_async) {
        if (offset == -2) offset = handles[i].logical_position;
        uint32_t status = ngb_disc_stream_read(handles[i].file,buffer,length,offset,received);
        ngb_file_disc_completed(handle,offset,*received,status);
        if (!status) ngb_file_disc_textures(ngb_file_basename(handle),offset,buffer,*received);
        return status;
    }
    if (handles[i].raw_disk) {
        int64_t start = offset == -2 ? ftello(handles[i].file) : offset;
        if (start < 0) return error_status();
        if ((uint64_t)start > NGB_FILE_MAX_BYTES || length > NGB_FILE_MAX_BYTES - (uint64_t)start)
            return NGB_FS_UNSUPPORTED;
        memset(buffer, 0, length);
    }
    const struct disc_entry *entry=handles[i].readonly ? disc_entry_for(handles[i].path) : NULL;
    if (entry) {
        uint64_t pos=offset==-2 ? (uint64_t)handles[i].logical_position : (uint64_t)offset;
        if (!length || pos>=entry->size) return length ? 0xc0000011u : 0;
        if (length>entry->size-pos) length=entry->size-pos;
        uint64_t packed=0;
        for (unsigned j=0;j<entry->count;++j) {
            uint32_t start=entry->ranges[j].start, n=entry->ranges[j].length;
            if (pos>=start && pos+length<=(uint64_t)start+n) {
                if (!handles[i].file) handles[i].file=fopen(handles[i].path,"rb");
                if (!handles[i].file) return error_status();
                if (fseeko(handles[i].file,packed+pos-start,SEEK_SET)) return error_status();
                if (fread(buffer,1,length,handles[i].file)!=length) return 0xc000003eu;
                *received=length;
#ifdef NGB_TEXTURE_PRELOAD
                ngb_texture_read(ngb_file_basename(handle),pos,buffer,length);
#endif
                handles[i].logical_position=pos+length;
                return 0;
            }
            packed+=n;
        }
        return NGB_FS_UNSUPPORTED;
    }
    if (offset >= 0 && fseeko(handles[i].file, (off_t)offset, SEEK_SET)) return error_status();
    clearerr(handles[i].file);
    *received = (uint32_t)fread(buffer, 1, length, handles[i].file);
    if (ferror(handles[i].file)) return error_status();
#ifdef NGB_TEXTURE_PRELOAD
    const char *base=ngb_file_basename(handle);size_t namelen=strlen(base);
    if (*received && !handles[i].raw_disk && namelen>4 && !strcasecmp(base+namelen-4,".afs")) {
        int64_t pos=offset>=0?offset:(int64_t)ftello(handles[i].file)-*received;
        if(pos>=0) ngb_texture_read(ngb_file_basename(handle),pos,buffer,*received);
    }
#endif
    if (handles[i].raw_disk) {
        /* Unwritten sectors in the modeled range are zero-filled. Advance
         * over them so a subsequent current-position transfer stays correct. */
        if (fseeko(handles[i].file, length - *received, SEEK_CUR)) return error_status();
        *received = length;
        return 0;
    }
    return length && !*received ? 0xc0000011u : 0;
}
#ifdef NGB_NATIVE_DIAG
int ngb_file_is_cache_archive(uint32_t handle)
{
    int i = index_for(handle);
    return i >= 0 && !handles[i].raw_disk && handles[i].file_limit == CACHE_BYTES;
}
#endif
uint32_t ngb_file_write(uint32_t handle, const void *buffer, uint32_t length,
                        int64_t offset, uint32_t *written)
{
    *written = 0;
    int i = index_for(handle);
    if (i < 0) return NGB_FS_INVALID_HANDLE;
    if (handles[i].dismounted) return 0xc00000a3u;
    if (handles[i].raw_disk == 1) return write_disk_header((unsigned)i, buffer, length, offset, written);
    if (!handles[i].file) return 0xc00000bau;
    uint32_t access = handles[i].access;
    if (handles[i].readonly || !(access & (0x50000000u | 6u))) return DENIED;
    if (offset < -2) return INVALID;
    if (!length) return 0;
    FILE *f = handles[i].file;
    struct stat before, after;
    if (fstat(fileno(f), &before)) return error_status();
    int append_only = (access & 4) && !(access & (0x50000000u | 2u));
    if (offset == -1 || append_only) {
        if (fseeko(f, 0, SEEK_END)) return error_status();
    } else if (offset >= 0 && fseeko(f, (off_t)offset, SEEK_SET)) return error_status();
    off_t position = ftello(f);
    if (position < 0) return error_status();
    uint64_t end = (uint64_t)position + length;
    uint64_t growth = end > (uint64_t)before.st_size ? end - (uint64_t)before.st_size : 0;
    uint32_t limit = handles[i].raw_disk ? NGB_FILE_MAX_BYTES : handles[i].file_limit;
    if (end > limit || (growth && USED(handles[i].path) + growth > QUOTA(handles[i].path))) return 0xc000007fu;
    clearerr(f);
    *written = (uint32_t)fwrite(buffer, 1, length, f);
    int failed = *written != length || ferror(f);
    /* A synchronous Xbox handle waits for the write to complete. Only a
     * write-through handle or an explicit flush requests a media barrier.
     * Drain stdio on every write so other handles see the data immediately. */
    if (fflush(f)) failed = 1;
    else if ((handles[i].raw_disk || (handles[i].options & FILE_WRITE_THROUGH)) &&
             fsync(fileno(f))) failed = 1;
    if (!fstat(fileno(f), &after) && after.st_size > before.st_size)
        USED(handles[i].path) += (uint64_t)(after.st_size - before.st_size);
    return failed ? 0xc0000001u : 0;
}
static void put32(unsigned char *p, uint32_t n) { memcpy(p, &n, 4); }
static void put64(unsigned char *p, uint64_t n) { memcpy(p, &n, 8); }
uint32_t ngb_file_resize(uint32_t handle, int64_t size, int allocation)
{
    int i = index_for(handle);
    if (i < 0) return NGB_FS_INVALID_HANDLE;
    if (handles[i].dismounted) return 0xc00000a3u;
    if (handles[i].readonly || !(handles[i].access & 0x50000002u)) return DENIED;
    if (size < 0 || !handles[i].file || handles[i].raw_disk) return INVALID;
    struct stat st;
    int fd = fileno(handles[i].file);
    if (fstat(fd, &st)) return error_status();
    if ((uint64_t)size > handles[i].file_limit ||
        (size > st.st_size && USED(handles[i].path) + (size - st.st_size) > QUOTA(handles[i].path)))
        return 0xc000007fu;
    if (allocation && size >= st.st_size) {
        /* XAPI sets allocation immediately after EOF. The FATX cluster that
         * already backs EOF covers this request, with no change in length. */
        return (uint64_t)size <= (((uint64_t)st.st_size + 16383) & ~16383ull)
            ? 0 : NGB_FS_UNSUPPORTED;
    }
    if (fflush(handles[i].file) || ftruncate(fd, (off_t)size)) return error_status();
    USED(handles[i].path) += (uint64_t)size - (uint64_t)st.st_size;
    return 0;
}
uint32_t ngb_file_position(uint32_t handle, int64_t position)
{
    int i = index_for(handle);
    if (i < 0) return NGB_FS_INVALID_HANDLE;
    if (position < 0 || (!handles[i].packed && !handles[i].file)) return INVALID;
    if (handles[i].packed || handles[i].disc_async) {
        handles[i].logical_position=position;
        return 0;
    }
    return fseeko(handles[i].file, (off_t)position, SEEK_SET) ? error_status() : 0;
}
uint32_t ngb_file_query(uint32_t handle, uint32_t kind, void *buffer,
                        uint32_t length, uint32_t *received)
{
    *received = 0;
    int i = index_for(handle);
    if (i < 0) return NGB_FS_INVALID_HANDLE;
    if (handles[i].raw_disk) return NGB_FS_UNSUPPORTED;
    unsigned char info[56] = {0};
    struct stat st;
    /* Query the open object. libnx stat(path) opens a second read handle,
     * which can conflict with this file's existing writable handle. */
    int stat_rc = handles[i].file ? fstat(fileno(handles[i].file), &st) :
                                   plain_stat(handles[i].path, &st);
    if (stat_rc) return error_status();
    const struct disc_entry *entry=handles[i].readonly ? disc_entry_for(handles[i].path) : NULL;
    if (entry) st.st_size=entry->size;
    unsigned size;
    if (kind == 5) { /* FILE_STANDARD_INFORMATION, guest pointers are 32-bit */
        size = 24;
        put64(info, ((uint64_t)st.st_size + 4095) & ~4095ull);
        put64(info + 8, (uint64_t)st.st_size);
        put32(info + 16, 1); info[20] = handles[i].delete_mark || handles[i].delete_committed; info[21] = handles[i].directory != NULL;
    } else if (kind == 14) {
        if (!entry && !handles[i].file) return INVALID;
        size = 8; off_t offset = entry || handles[i].disc_async ? handles[i].logical_position : ftello(handles[i].file);
        if (offset < 0) return error_status();
        put64(info, (uint64_t)offset);
    } else if (kind == 4 || kind == 34) {
        size = kind == 4 ? 40 : 56;
        time_t times[4] = {st.st_ctime, st.st_atime, st.st_mtime, st.st_mtime};
        for (unsigned j = 0; j < 4; ++j)
            put64(info + 8*j, 116444736000000000ull + (uint64_t)times[j] * 10000000);
        if (kind == 34) {
            put64(info + 32, ((uint64_t)st.st_size + 4095) & ~4095ull);
            put64(info + 40, (uint64_t)st.st_size);
        }
        put32(info + (kind == 4 ? 32 : 48), handles[i].directory ? 0x10 : (handles[i].readonly ? 1 : 0x80));
    } else return NGB_FS_UNSUPPORTED;
    if (length < size) return TOO_SMALL;
    memcpy(buffer, info, size); *received = size;
    return 0;
}
uint32_t ngb_file_volume(uint32_t handle, uint32_t kind, void *buffer,
                         uint32_t length, uint32_t *received)
{
    *received = 0;
    int i = index_for(handle);
    if (i < 0) return NGB_FS_INVALID_HANDLE;
    if (handles[i].raw_disk) return NGB_FS_UNSUPPORTED;
    unsigned char info[24] = {0}; unsigned size;
    if (kind == 4) { /* FILE_FS_DEVICE_INFORMATION */
        size = 8; put32(info, handles[i].readonly ? 2 : 7);
        put32(info + 4, handles[i].readonly ? 3 : 0);
    } else if (kind == 3) {
        struct statvfs stats;
        if (statvfs(handles[i].path, &stats)) return error_status();
        size = 24;
        /* Same FATX geometry as upstream kernel_file.c. XAPI checks for
         * 16 KiB clusters; exposing the host's page size sends it to reboot. */
        uint64_t host_block = stats.f_frsize ? stats.f_frsize : stats.f_bsize;
        uint64_t total = (uint64_t)stats.f_blocks * host_block;
        uint64_t available = (uint64_t)stats.f_bavail * host_block;
        /* Report the bring-up volume's quota, not the entire SD/host disk.
         * This also avoids the guest's 32-bit free-block overflow. */
        if (!handles[i].readonly) {
            uint64_t quota=QUOTA(handles[i].path), used=USED(handles[i].path);
            if (total > quota) total = quota;
            uint64_t budget = used < quota ? quota - used : 0;
            if (available > budget) available = budget;
        }
        if (available > total) available = total;
        put64(info, total / 16384);
        put64(info + 8, handles[i].readonly ? 0 : available / 16384);
        put32(info + 16, 32); put32(info + 20, 512);
    } else return NGB_FS_UNSUPPORTED;
    if (length < size) return TOO_SMALL;
    memcpy(buffer, info, size); *received = size;
    return 0;
}

uint32_t ngb_file_ioctl(uint32_t handle, uint32_t code, void *out,
                        uint32_t length, uint32_t *received)
{
    *received = 0;
    int i = index_for(handle);
    if (i < 0) return NGB_FS_INVALID_HANDLE;
    if (handles[i].dismounted) return 0xc00000a3u;
    if (!handles[i].raw_disk) return NGB_FS_UNSUPPORTED;
    if (code == 0x74004 && handles[i].raw_disk >= 4) {
        if (length < 32) return TOO_SMALL;
        unsigned char info[32] = {0};
        put64(info + 8, 0x177000ull * 512);
        put32(info + 20, (uint32_t)handles[i].raw_disk - 1);
        put32(info + 24, 0x00010106);
        memcpy(out, info, sizeof(info)); *received = sizeof(info);
        return 0;
    }
    if (code != 0x70000) return NGB_FS_UNSUPPORTED;
    /* DISK_GEOMETRY, same values as upstream kernel_bridge.c. */
    if (length < 24) return TOO_SMALL;
    unsigned char info[24] = {0};
    put64(info, 1216); put32(info + 8, 11); put32(info + 12, 255);
    put32(info + 16, 63); put32(info + 20, 512);
    memcpy(out, info, sizeof(info)); *received = sizeof(info);
    return 0;
}

uint32_t ngb_file_dismount(uint32_t handle, uint32_t code)
{
    int i = index_for(handle);
    if (i < 0) return NGB_FS_INVALID_HANDLE;
    if (code != 0x90020 || handles[i].raw_disk < 4) return NGB_FS_UNSUPPORTED;
    if (handles[i].dismounted) return 0xc00000a3u;
    if (fflush(handles[i].file) || fsync(fileno(handles[i].file))) return error_status();
    /* There is no cached FAT mount: directory opens revalidate the on-disk
     * formatting metadata. This raw handle is quiescent until closed. */
    handles[i].dismounted = 1;
    return 0;
}

/* The XAPI search mask accepts '*' and '?' and folds ASCII case. */
static int match_name(const char *mask,const char *name)
{
    const char *star=NULL,*retry=NULL;
    while (*name) {
        if (*mask=='*') { star=++mask; retry=name; }
        else if (*mask=='?' || (*mask && !strncasecmp(mask,name,1))) { ++mask; ++name; }
        else if (star) { mask=star; name=++retry; }
        else return 0;
    }
    while (*mask=='*') ++mask;
    return !*mask;
}

uint32_t ngb_file_directory(uint32_t handle,const char *pattern,int restart,
                            void *buffer,uint32_t length,uint32_t *done)
{
    int i=index_for(handle);
    *done=0;
    if (i<0 || !handles[i].directory) return NGB_FS_INVALID_HANDLE;
    if (length<64 || !buffer) return TOO_SMALL;
    if (restart || !handles[i].pattern[0]) {
        if (!copy_path(handles[i].pattern,sizeof(handles[i].pattern), pattern && *pattern ? pattern : "*"))
            return BAD_NAME;
        rewinddir(handles[i].directory);
    }
    struct dirent *entry;
    while ((entry=readdir(handles[i].directory))) {
        if (entry->d_name[0]=='.' || !match_name(handles[i].pattern,entry->d_name)) continue;
        char path[PATH_CAP]; struct stat st;
        if (!copy_path(path,sizeof(path),handles[i].path) || !append(path,entry->d_name)) return BAD_NAME;
        if (plain_stat(path,&st)) return error_status();
        const struct disc_entry *original=handles[i].readonly ? disc_entry_for(path) : NULL;
        if (original) st.st_size=original->size;
        size_t n=strlen(entry->d_name);
        if (n>length-64) return TOO_SMALL;
        unsigned char *out=buffer;
        memset(out,0,64);
        time_t times[]={st.st_ctime,st.st_atime,st.st_mtime,st.st_mtime};
        for (unsigned j=0;j<4;j++) put64(out+8+8*j,116444736000000000ull+(uint64_t)times[j]*10000000);
        put64(out+40,st.st_size);
        put64(out+48,((uint64_t)st.st_size+4095)&~4095ull);
        put32(out+56,S_ISDIR(st.st_mode) ? 0x10 : handles[i].readonly ? 1 : 0x80);
        put32(out+60,n);
        memcpy(out+64,entry->d_name,n);
        *done=64+n;
        return 0;
    }
    return 0x80000006u; /* STATUS_NO_MORE_FILES */
}
