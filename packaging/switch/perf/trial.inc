unsigned trial_variant;
void ngb_trial_flip(unsigned frame, unsigned draws)
{
    static uint64_t before, last_entries, last_polls;
    static unsigned last_draws;
    unsigned start = frame <= 120 ? 32 : 1680;
    if (frame < start || frame > 1920) return;
    struct timespec t;
    if (clock_gettime(CLOCK_THREAD_CPUTIME_ID, &t)) abort();
    uint64_t now = (uint64_t)t.tv_sec * 1000000000u + t.tv_nsec;
    if (frame != start) {
        fprintf(stderr, "[PAIR] %u %u %llu %u %llu %llu\n", frame, trial_variant,
                (unsigned long long)(now-before), draws-last_draws,
                (unsigned long long)(entries-last_entries),
                (unsigned long long)(ngb_guest_polls-last_polls));
    }
    before = now;
    last_entries = entries;
    last_polls = ngb_guest_polls;
    last_draws = draws;
    unsigned i = frame - start, hash = (i/2 + 12345) * 2654435761u;
    trial_variant = (frame == 120 || frame == 1920) ? 0 : (hash >> 31) ^ (i & 1);
}
