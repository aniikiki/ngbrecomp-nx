/* Host only. Charge the interval to exactly one task across Xbox thread
 * and fiber switches. The clock excludes CPU consumed by the renderer. */
static struct { uint32_t key; uint64_t ns; } task_time[512];
static uint32_t task_key;
static uint64_t task_since;
static int task_measuring;

static uint64_t task_now(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_THREAD_CPUTIME_ID, &t)) abort();
    return (uint64_t)t.tv_sec * 1000000000ull + t.tv_nsec;
}

static void task_charge(uint64_t now)
{
    unsigned i = (task_key * 2654435761u) >> 23;
    for (unsigned n = 0; n < 512; ++n, i = (i+1)&511) {
        if (!task_time[i].ns || task_time[i].key == task_key) {
            task_time[i].key = task_key;
            task_time[i].ns += now-task_since;
            task_since = now;
            return;
        }
    }
    abort();
}

static void task_set(uint32_t key)
{
    if (key == task_key) return;
    if (task_measuring) task_charge(task_now());
    task_key = key;
}

static void task_window(unsigned flip)
{
#ifdef NGB_TASK_STORY
    if (flip != 1200 && flip != 1320 && flip != 1440) return;
    int next_window = flip != 1440;
#else
    if (flip != 30 && flip != 120 && flip != 1680 &&
        flip != 1800 && flip != 1920) return;
    int next_window = flip == 30 || flip == 1680 || flip == 1800;
#endif
    if (task_measuring) {
        task_charge(task_now());
        for (unsigned i = 0; i < 512; ++i)
            if (task_time[i].ns) fprintf(stderr, "[TASK] end=%u key=%08x ns=%llu\n",
                flip, task_time[i].key, (unsigned long long)task_time[i].ns);
    }
    memset(task_time, 0, sizeof(task_time));
    task_measuring = next_window;
    if (task_measuring) task_since = task_now();
}
