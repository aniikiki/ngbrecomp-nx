#include "files_bridge.h"
#include "files.h"
#include "runtime.h"
#include "scene.h"
#if defined(NGB_NATIVE_DIAG) || defined(NGB_COMBAT_PERF)
#include "combat_perf.h"
#endif
#include "vm.h"
#include "ohci_boot.h"
#include <strings.h>
#include <string.h>
#include <errno.h>

static uint32_t u32(uint32_t p)
{
    uint32_t n;
    memcpy(&n, (void *)ngb_guest_pointer(p, 4), 4);
    return n;
}
static void store32(uint32_t p, uint32_t n)
{
    memcpy((void *)ngb_guest_pointer(p, 4), &n, 4);
}
#include "disc_reads.inc"
static int64_t i64(uint32_t p)
{
    return (int64_t)((uint64_t)u32(p) | (uint64_t)u32(p + 4) << 32);
}
static uint32_t name_at(uint32_t p, char out[1024])
{
    if (!p) return 0xc000000du;
    uint32_t sizes = u32(p), length = sizes & 0xffff, maximum = sizes >> 16;
    if (length > maximum || length >= 1024) return 0xc0000033u;
    const char *s = (void *)ngb_guest_pointer(u32(p + 4), length);
    if (memchr(s, 0, length)) return 0xc0000033u;
    memcpy(out, s, length); out[length] = 0;
    return 0;
}
/* Xbox DEVICE_OBJECT layout (nxdk xboxkrnl.h). The device queue and lock
 * belong to the header, ahead of the driver-owned extension at 0x48. */
#define DEVICE_BYTES 0x48u
static struct { uint32_t object; char name[1024]; } devices[16];

void ngb_devices_reset(void)
{
    stop_disc_reads();
    /* The boot VM releases the guest allocations together. */
    memset(devices, 0, sizeof(devices));
}

static uint32_t create_device(const uint32_t *a)
{
    uint32_t driver = a[0], extension = a[1], type = a[3], output = a[5];
    if (!output) return 0xc000000du;
    store32(output, 0);
    if (!driver || extension > UINT16_MAX - DEVICE_BYTES) return 0xc000000du;
    if (type != 0x3a) ngb_stop("unsupported device type", type);
    char name[1024] = "";
    if (a[2]) {
        uint32_t status = name_at(a[2], name);
        if (status) return status;
    }
    size_t count = sizeof(devices) / sizeof(devices[0]), slot = count;
    for (size_t i = 0; i < count; ++i) {
        if (!devices[i].object) {
            if (slot == count) slot = i;
        } else if (name[0] && !strcasecmp(devices[i].name, name)) return 0xc0000035u;
    }
    uint32_t object = 0, size = DEVICE_BYTES + extension;
    if (slot == count || ngb_vm_allocate(&object, &size, 0, 0x3000, 4)) return 0xc000009au;
    /* Newly committed VM pages already contain zeroes. The embedded list
     * heads point back to themselves in the guest address space. */
    store32(object, 3 | ((DEVICE_BYTES + extension) << 16));
    store32(object + 8, driver);
    store32(object + 0x14, 0x10u | (name[0] ? 8u : 0u) | (a[4] ? 2u : 0u));
    store32(object + 0x18, extension ? object + DEVICE_BYTES : 0);
    store32(object + 0x1c, type | (1u << 16));
    store32(object + 0x28, 0x000c0014); /* KDEVICE_QUEUE */
    store32(object + 0x2c, object + 0x2c);
    store32(object + 0x30, object + 0x2c);
    store32(object + 0x34, 0x00040001); /* signalled synchronization event */
    store32(object + 0x38, 1);
    store32(object + 0x3c, object + 0x3c);
    store32(object + 0x40, object + 0x3c);
    devices[slot].object = object;
    strcpy(devices[slot].name, name);
    store32(output, object);
    NGB_BOOT_LOGF("created device name=%s type=%08x extension=%u object=%08x", name, type, extension, object);
    return 0;
}

unsigned ngb_files_arg_count(uint32_t ordinal)
{
    switch (ordinal) {
    case 65: return 6;
    case 67: case 203: return 2;
    case 215: return 3;
    case 198: return 2;
    case 187: return 1;
    case 190: return 9;
    case 196: case 200: case 207: return 10;
    case 202: return 6;
    case 211: case 218: case 226: return 5;
    case 219: case 236: return 8;
    default: return 0;
    }
}
uint32_t ngb_files_dispatch(uint32_t ordinal, const uint32_t *a)
{
    uint32_t status = NGB_FS_UNSUPPORTED, done = 0, ios = 0;
    if (ordinal == 65) return create_device(a);
    if (ordinal == 198) {
        if (!a[1]) return 0xc000000du;
        (void)ngb_guest_pointer(a[1],8);
        status=ngb_file_flush(a[0]);
        store32(a[1],status); store32(a[1]+4,0);
        return status;
    }
    if (ordinal == 187) {
        if (ngb_pending_disc_reads) cancel_disc_reads(a[0]);
        return ngb_file_close(a[0]);
    }
    if (ordinal == 67) {
        char name[1024], target[1024];
        status = name_at(a[0], name);
        if (!status) status = name_at(a[1], target);
        if (!status) {
            status = ngb_file_link(name, target);
            NGB_BOOT_LOGF("link %.63s -> %.1023s status=%08x", name, target, status);
        }
        return status;
    }
    if (ordinal == 203) {
        if (!a[0] || !a[1]) return 0xc000000du;
        (void)ngb_guest_pointer(a[0], 4);
        (void)ngb_guest_pointer(a[1], 12);
        char name[1024] = {0};
        uint32_t handle = 0;
        status = name_at(u32(a[1] + 4), name);
        if (!status && u32(a[1])) ngb_stop("unsupported relative link root", u32(a[1]));
        if (!status) status = ngb_link_open(name, u32(a[1] + 8) & 0x40, &handle);
        store32(a[0], handle);
        NGB_BOOT_LOGF("open link %s status=%08x handle=%08x", name, status, handle);
        return status;
    }
    if (ordinal == 215) {
        char target[1024];
        status = ngb_link_target(a[0], target);
        if (status) return status;
        uint32_t length = (uint32_t)strlen(target);
        if (a[2]) store32(a[2], length);
        if (!a[1]) return 0xc0000023u;
        (void)ngb_guest_pointer(a[1], 8);
        uint32_t max = u32(a[1]) >> 16, buffer = u32(a[1] + 4);
        if (!buffer || max <= length) return 0xc0000023u;
        memcpy((void *)ngb_guest_pointer(buffer, length + 1), target, length + 1);
        store32(a[1], (max << 16) | length);
        NGB_BOOT_LOGF("query link handle=%08x target=%s bytes=%u", a[0], target, length);
        return 0;
    }
    if (ordinal==207) {
        ios=a[4];
        if (!ios || !a[5] || a[7]!=1 || a[1] || a[2] || a[3]) ngb_stop("unsupported directory query",a[7]);
        (void)ngb_guest_pointer(ios,8);
        char pattern[1024]="";
        status=a[8] ? name_at(a[8],pattern) : 0;
        if (!status) status=ngb_file_directory(a[0],pattern,a[9],(void *)ngb_guest_pointer(a[5],a[6]),a[6],&done);
        NGB_BOOT_LOGF("directory query mask=%.255s status=%08x bytes=%u", pattern, status, done);
    } else if (ordinal == 196 || ordinal == 200) {
        ios = a[4];
        if (!ios) return 0xc000000du;
        (void)ngb_guest_pointer(ios, 8);
        if (a[1] || a[2]) ngb_stop("async device completion not connected", ordinal);
        if (ordinal == 200) {
            if (a[7] || a[9]) status = NGB_FS_UNSUPPORTED;
            else status = ngb_file_dismount(a[0], a[5]);
        } else status = ngb_file_ioctl(a[0], a[5], (void *)ngb_guest_pointer(a[8], a[9]), a[9], &done);
        NGB_BOOT_LOGF("device control code=%08x out=%u status=%08x", a[5], a[9], status);
    } else if (ordinal == 190 || ordinal == 202) {
        if (!a[0] || !a[2] || !a[3]) return 0xc000000du;
        (void)ngb_guest_pointer(a[0], 4);
        (void)ngb_guest_pointer(a[3], 8);
        char path[1024] = {0};
        status = name_at(u32(a[2] + 4), path);
        uint32_t handle = 0, root = u32(a[2]);
        uint32_t share = a[ordinal == 190 ? 6 : 4];
        uint32_t disposition = ordinal == 190 ? a[7] : 1;
        uint32_t options = a[ordinal == 190 ? 8 : 5];
        /* Like the upstream POSIX backend, hidden/system attributes do not
         * change the host mode; read-only attributes require a later mapping. */
        /* XCreateSaveGame opens SaveMeta.xbx with AllocationSize=1. This is a
         * FATX allocation hint, not EndOfFile: keep new files empty and existing
         * slots intact. Leave quotas and real allocation errors to file writes. */
        int64_t allocation = ordinal == 190 && a[4] ? i64(a[4]) : 0;
        int small_hint = allocation > 0 && allocation <= 16384 &&
                         !(options & 1) && (a[1] & 0x50000002u) &&
                         (disposition == 2 || disposition == 3 || disposition == 5);
        if (ordinal == 190 && ((allocation && !small_hint) || (a[5] & ~0xb6u)))
            status = NGB_FS_UNSUPPORTED;
        if (!status) {
            status = ngb_file_open(path, root, a[1], share, disposition, options, &handle, &done);
        }
        NGB_BOOT_LOGF("open path=%s root=%08x access=%08x disposition=%u options=%08x status=%08x handle=%08x",
                      path, root, a[1], disposition, options, status, handle);
        if (ordinal == 190 && status == NGB_FS_UNSUPPORTED) {
            NGB_BOOT_LOGF("create allocation=%lld attributes=%08x", (long long)allocation, a[5]);
        }
        store32(a[0], handle); ios = a[3];
    } else if (ordinal == 219 || ordinal == 236) {
        ios = a[4];
        if (!ios) return 0xc000000du;
        (void)ngb_guest_pointer(ios, 8);
        if (a[2]) ngb_stop("file completion APC not connected",ordinal);
        if (a[1] && !ngb_io_event(a[1],0)) return NGB_FS_INVALID_HANDLE;
        int64_t offset = a[7] ? i64(a[7]) : -2;
        int timed = ngb_scene_active && NGB_DIAG;
#if defined(NGB_NATIVE_DIAG) || defined(NGB_COMBAT_PERF)
        timed |= ngb_combat_enabled;
#endif
        if (ordinal == 219) {
            const char *path = ngb_file_async_disc_path(a[0]);
            if (path && offset >= 0 && a[6]) {
                (void)ngb_guest_pointer(a[5],a[6]);
                if (queue_disc_read(path,a,offset,timed)) return NGB_FS_PENDING;
            }
            /* A current-position read, or a synchronous fallback under
             * pressure, observes the cursor left by earlier completions. */
            if (path) finish_prior_disc_reads(a[0]);
        }
        void *buffer = (void *)ngb_guest_pointer(a[5],a[6]);
        uint64_t start = timed ? ngb_elapsed_ns() : 0;
        status = ordinal == 219 ? ngb_file_read(a[0], buffer, a[6], offset, &done) :
                                  ngb_file_write(a[0], buffer, a[6], offset, &done);
        if (start) {
            uint64_t ns = ngb_elapsed_ns() - start;
            if (ngb_scene_active) ngb_scene_file_time(done, ns);
#ifdef NGB_NATIVE_DIAG
            if (ngb_combat_enabled)
                ngb_combat_file(ordinal == 236, ordinal == 236 && ngb_file_is_cache_archive(a[0]), done, ns);
#endif
        }
        if (ordinal == 219 && status == NGB_FS_UNSUPPORTED) {
            NGB_BOOT_LOGF("Disc read unavailable file=%s offset=%lld bytes=%u",
                          ngb_file_basename(a[0]), (long long)offset, a[6]);
        }
        if (ordinal == 219 && !status && done)
            ngb_warning_file_read(ngb_file_basename(a[0]), offset);
        NGB_BOOT_LOGF("%s handle=%08x offset=%lld requested=%u transferred=%u status=%08x",
                      ordinal == 219 ? "read" : "write", a[0], (long long)offset, a[6], done, status);
    } else if (ordinal == 211 || ordinal == 218 || ordinal == 226) {
        ios = a[1];
        if (!ios) return 0xc000000du;
        (void)ngb_guest_pointer(ios, 8);
        if (ordinal == 226 && a[4] == 14) finish_prior_disc_reads(a[0]);
        void *buffer = (void *)ngb_guest_pointer(a[2], a[3]);
        errno = 0;
        if (ordinal == 211) status = ngb_file_query(a[0], a[4], buffer, a[3], &done);
        else if (ordinal == 218) status = ngb_file_volume(a[0], a[4], buffer, a[3], &done);
        else if (a[4] == 4) status = ngb_file_set_basic(a[0], buffer, a[3]);
        else if (a[4] == 13) status = a[3] >= 1 ? ngb_file_disposition(a[0], *(const uint8_t *)buffer) : 0xc0000004u;
        else if (a[4] == 14 && a[3] >= 8) status = ngb_file_position(a[0], i64(a[2]));
        else if (a[4] == 19 || a[4] == 20) status = a[3] >= 8 ? ngb_file_resize(a[0], i64(a[2]), a[4] == 19) : 0xc0000004u;
        int native_errno = errno;
        NGB_BOOT_LOGF("file information ordinal=%u class=%u length=%u status=%08x", ordinal, a[4], a[3], status);
        if (status && native_errno) {
            NGB_BOOT_LOGF("file information native errno=%d", native_errno);
        }
    }
    if (status == NGB_FS_UNSUPPORTED) {
        char reason[160];
        if (ordinal == 190 || ordinal == 202)
            snprintf(reason,sizeof(reason),"unsupported open: access=%08x disposition=%u options=%08x alloc=%lld",
                a[1],ordinal==190?a[7]:1,ordinal==190?a[8]:a[5],(long long)(ordinal==190 && a[4]?i64(a[4]):0));
        else if (ordinal==211 || ordinal==218 || ordinal==226)
            snprintf(reason,sizeof(reason),"unsupported file information: class=%u length=%u",a[4],a[3]);
        else snprintf(reason,sizeof(reason),"unsupported file operation");
        ngb_stop(reason, ordinal);
    }
    if (ios) { store32(ios, status); store32(ios + 4, done); }
    if ((ordinal==219 || ordinal==236) && a[1]) ngb_io_event(a[1],1);
    return status;
}
