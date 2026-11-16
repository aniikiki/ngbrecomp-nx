/* Reuse the upstream EEPROM defaults without its desktop platform runtime. */
#include "kernel/kernel.h"
#include "runtime.h"
#include "services.h"
#include <stdarg.h>
#include <string.h>
#include <strings.h>

/* The same narrow host primitive used by upstream win32_compat.c. */
int _strnicmp(const char *a, const char *b, SIZE_T n) { return strncasecmp(a, b, n); }

void xbox_log(int level, const char *subsystem, const char *format, ...)
{
    (void)level;
    (void)subsystem;
    char message[512];
    va_list ap;
    va_start(ap, format);
    vsnprintf(message, sizeof(message), format, ap);
    va_end(ap);
    ngb_kernel_log(message);
}

uint32_t ngb_status_to_error(uint32_t status)
{
    return xbox_RtlNtStatusToDosError((NTSTATUS)status);
}

uint32_t ngb_equal_string(uint32_t first, uint32_t second, uint32_t nocase)
{
    if (!first || !second) return 0;
    XBOX_ANSI_STRING strings[2];
    uint32_t addresses[2] = {first, second};
    for (unsigned i = 0; i < 2; ++i) {
        uint32_t raw[2];
        memcpy(raw, (void *)ngb_guest_pointer(addresses[i], 8), 8);
        strings[i].Length = (USHORT)raw[0];
        strings[i].MaximumLength = (USHORT)(raw[0] >> 16);
        if (strings[i].Length > strings[i].MaximumLength) ngb_stop("invalid ANSI string", addresses[i]);
        strings[i].Buffer = (void *)ngb_guest_pointer(raw[1], strings[i].Length);
    }
    return xbox_RtlEqualString(&strings[0], &strings[1], nocase != 0) != 0;
}

uint32_t ngb_query_setting(uint32_t index, uint32_t type, uint32_t value,
                           uint32_t length, uint32_t result)
{
    if (index == 0xffff) {
        /* XAPI reads bytes 0x36..0x45 for its fallback save signature.
         * Keep the synthetic identity bytes zero, as in the desktop port. */
        uint32_t image[64] = {0};
        if (!value) return 0xc000000du;
        if (result) memcpy((void *)ngb_guest_pointer(result, 4), &(uint32_t){sizeof(image)}, 4);
        if (length < sizeof(image)) return 0xc0000023u;
        image[0x2c / 4] = 1;            /* Game region */
        image[0x58 / 4] = 0x00400100;   /* Factory AV region */
        image[0x30 / 4] = ~image[0x58 / 4];
        image[0x64 / 4] = (uint32_t)-300;
        image[0x90 / 4] = 1;            /* English */
        image[0x94 / 4] = xbox_XcVideoFlags;
        image[0xbc / 4] = 1;            /* DVD region */
        uint64_t sum = 0;
        for (unsigned i = 0x64 / 4; i < 0xc0 / 4; ++i) {
            sum += image[i];
            sum = (uint32_t)sum + (sum >> 32);
        }
        image[0x60 / 4] = ~(uint32_t)sum;
        memcpy((void *)ngb_guest_pointer(value, sizeof(image)), image, sizeof(image));
        if (type) memcpy((void *)ngb_guest_pointer(type, 4), &(uint32_t){3}, 4);
        return 0;
    }
    /* Upstream also returns zeroes for unknown indices. During bring-up keep
     * those visible, and avoid its success-with-no-write on a short buffer. */
    switch (index) {
    case XC_LANGUAGE: case XC_VIDEO: case XC_AUDIO: case XC_P_CONTROL_GAMES:
    case XC_P_CONTROL_MOVIES: case XC_DVD_REGION: case XC_MISC:
    case XC_TIMEZONE_BIAS: case 0x103: case 0x104: break;
    default: ngb_stop("unsupported EEPROM index", index);
    }
    uint32_t *result_ptr = result ? (void *)ngb_guest_pointer(result, 4) : NULL;
    if (!value) return 0xc000000d;
    if (length < 4) {
        if (result_ptr) *result_ptr = 4;
        return 0xc0000023;
    }
    return xbox_ExQueryNonVolatileSetting(index,
        type ? (void *)ngb_guest_pointer(type, 4) : NULL,
        (void *)ngb_guest_pointer(value, length), length, result_ptr);
}

void ngb_video_init(void) { xbox_XcVideoFlags |= XC_VIDEO_FLAGS_WIDESCREEN; }

uint32_t ngb_av_pack(void)
{
    return AV_PACK_HDTV | (AV_STANDARD_NTSC_M << AV_STANDARD_SHIFT) |
           AV_REFRESH_60Hz | (xbox_XcVideoFlags & ~0x00c0ffffu);
}

void ngb_xc_sha(unsigned ordinal,uint32_t ctx,uint32_t data,uint32_t bytes)
{
    PXBOX_SHA_CONTEXT context=(void *)ngb_guest_pointer(ctx,sizeof(*context));
    if (ordinal==335) xbox_XcSHAInit(context);
    else if (ordinal==336) xbox_XcSHAUpdate(context,(void *)ngb_guest_pointer(data,bytes),bytes);
    else xbox_XcSHAFinal(context,(void *)ngb_guest_pointer(data,20));
}
