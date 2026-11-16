#include "timers.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); exit(1); } } while (0)
static unsigned calls;
static int cancel_in_callback;
static void fire(uint32_t address, uint32_t dpc, int periodic)
{
    CHECK(address == 0x1000 && dpc == 0x2000);
    ++calls;
    if (cancel_in_callback) { CHECK(periodic); CHECK(ngb_timer_cancel(address) == 1); }
}
int main(void)
{
    ngb_timers_reset();
    CHECK(ngb_timer_arm(0x1000, 0, 0, 0, 0) == -1);
    CHECK(ngb_timer_initialize(0x1000) == 0);
    CHECK(ngb_timer_arm(0x1000, 100, 50, 0, 0x2000) == 0);
    ngb_timers_poll(149, fire); CHECK(calls == 0);
    ngb_timers_poll(150, fire); CHECK(calls == 1);
    ngb_timers_poll(200, fire); CHECK(calls == 1);
    CHECK(ngb_timer_cancel(0x1000) == 0);
    CHECK(ngb_timer_arm(0x1000, 200, 0, 10, 0x2000) == 0);
    CHECK(ngb_timer_arm(0x1000, 200, 0, 10, 0x2000) == 1);
    ngb_timers_poll(200, fire); CHECK(calls == 2);
    ngb_timers_poll(209, fire); CHECK(calls == 2);
    ngb_timers_poll(210, fire); CHECK(calls == 3);
    cancel_in_callback = 1;
    ngb_timers_poll(220, fire); CHECK(calls == 4);
    ngb_timers_poll(1000, fire); CHECK(calls == 4);
    CHECK(ngb_timer_arm(0x1000, UINT64_MAX - 10, 20, 0, 0x2000) == 0);
    ngb_timers_poll(UINT64_MAX - 1, fire); CHECK(calls == 4);
    cancel_in_callback = 0;
    ngb_timers_poll(UINT64_MAX, fire); CHECK(calls == 5);
    ngb_timers_reset();
    for (unsigned i = 1; i <= 32; ++i) CHECK(ngb_timer_initialize(i) == 0);
    CHECK(ngb_timer_initialize(33) == -1);
    puts("Guest timers: one-shot/periodic/rearm/cancel/callback/overflow passed");
}
