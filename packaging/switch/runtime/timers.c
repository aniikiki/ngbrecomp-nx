/* One guest CPU: run due timers at generated-code polling points. Time is in
 * 100 ns units. The caller delivers the guest DPC and dispatcher signal. */
#include "timers.h"
#include <string.h>
static struct { uint32_t address, dpc; uint64_t due, period; int armed; } timers[32];
void ngb_timers_reset(void) { memset(timers, 0, sizeof(timers)); }
static int find(uint32_t address)
{
    if (address) for (int i = 0; i < 32; ++i) if (timers[i].address == address) return i;
    return -1;
}
int ngb_timer_initialize(uint32_t address)
{
    if (!address) return -1;
    int i = find(address);
    if (i < 0) for (i = 0; i < 32 && timers[i].address; ++i) {}
    if (i == 32) return -1;
    memset(&timers[i], 0, sizeof(timers[i]));
    timers[i].address = address;
    return 0;
}
int ngb_timer_arm(uint32_t address, uint64_t now, uint64_t delay,
                  uint64_t period, uint32_t dpc)
{
    int i = find(address);
    if (i < 0) return -1;
    int previous = timers[i].armed;
    timers[i].due = delay > UINT64_MAX - now ? UINT64_MAX : now + delay;
    timers[i].period = period;
    timers[i].dpc = dpc;
    timers[i].armed = 1;
    return previous;
}
int ngb_timer_cancel(uint32_t address)
{
    int i = find(address);
    if (i < 0) return -1;
    int previous = timers[i].armed;
    timers[i].armed = 0;
    return previous;
}
void ngb_timers_poll(uint64_t now, void (*fire)(uint32_t, uint32_t, int))
{
    for (int i = 0; i < 32; ++i) {
        if (!timers[i].armed || now < timers[i].due) continue;
        uint64_t period = timers[i].period;
        if (period) timers[i].due = period > UINT64_MAX - now ? UINT64_MAX : now + period;
        else timers[i].armed = 0;
        fire(timers[i].address, timers[i].dpc, period != 0);
    }
}
