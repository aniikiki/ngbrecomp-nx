#pragma once
#include <stdatomic.h>

/* One producer and one consumer each own a slot. Exchanging the middle
 * slot publishes the newest complete sample without waiting for a reader. */
typedef struct {
    unsigned writer;
    atomic_uint middle;
    unsigned reader;
} NgbExchange;
#define NGB_EXCHANGE_INIT {0, 1, 2}
static inline void ngb_publish(NgbExchange *s)
{
    s->writer = atomic_exchange(&s->middle, s->writer | 4u) & 3u;
}
static inline unsigned ngb_latest(NgbExchange *s)
{
    if (atomic_load(&s->middle) & 4u)
        s->reader = atomic_exchange(&s->middle, s->reader) & 3u;
    return s->reader;
}
