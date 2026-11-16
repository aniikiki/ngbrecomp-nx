    extern unsigned trial_variant;
    if (!trial_variant) {
        unsigned i = running_worker;
        do {
            i = (i + 1) % thread_count;
            if (i == running_worker) return i;
        } while (workers[i].suspended || workers[i].exited || workers[i].wake_tick > now);
        return i;
    }
