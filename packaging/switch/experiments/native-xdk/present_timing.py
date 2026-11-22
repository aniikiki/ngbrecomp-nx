"""Join UI attempts, queued pictures and GPU completions within one boot."""
from bisect import bisect_right
from math import ceil, floor
from statistics import median


def gpu_ns_per_unit(calibrations):
    """Convert the recorded GPU counter to nanoseconds using one boot's clock pairs."""
    clocks = sorted((k for k in calibrations if not k['result'] and k['gpu_ns']),
                    key=lambda k: k['host_before_us'])
    rates = []
    for a, b in zip(clocks, clocks[1:]):
        ticks = b['gpu_ns'] - a['gpu_ns']
        if ticks > 0 and 100000 <= b['host_before_us']-a['host_after_us'] <= 2500000:
            # Each host timestamp brackets the ioctl. Use midpoints for the
            # rate and retain the entire brackets when mapping an endpoint.
            elapsed_ns = 500 * (b['host_before_us']-a['host_before_us'] +
                                b['host_after_us']-a['host_after_us'])
            rates.append(elapsed_ns / ticks)
    return median(rates) if rates else None


class PresentTimeline:
    def __init__(self, rows):
        self.displays = sorted(rows.get('D', ()), key=lambda d: d['time_us'])
        self.ends = [d['time_us'] for d in self.displays]
        self.waits = sorted(rows.get('H', ()), key=lambda h: h['begin_us'])
        self.starts = [h['begin_us'] for h in self.waits]
        # VK_SUCCESS and VK_SUBOPTIMAL_KHR both queued an image.
        self.submissions = {y['begin_us']: y for y in rows.get('Y', ())
                            if y.get('present_result', 0) in (0, 1000001003)}
        self.scene_ends = {}
        for q in rows.get('Q', ()):
            frame = q['submit_frame']
            # Earlier chunks may retire even if the final query was lost or
            # the application closed. Only the chunk that wrote the screen counts.
            if q.get('writes_screen') and q['valid']:
                self.scene_ends[frame] = q['gpu_end_ns']
        self.clocks = sorted((k for k in rows.get('K', ()) if not k['result'] and k['gpu_ns']),
                             key=lambda k: k['host_before_us'])
        self.clock_times = [k['host_before_us'] for k in self.clocks]
        self.ns_per_unit = gpu_ns_per_unit(self.clocks)
        self.edges = sorted(s['vsync_wake_us'] for s in rows.get('S', ())
                            if s['vsync_wake_us'] - s['wait_start_us'] >= 2000)

    def host_time(self, gpu_ns, near_us):
        # Each ioctl brackets one GPU clock sample on the application's clock.
        # Use the envelope of both adjacent calibrations. Never carry an offset
        # across a suspend, a clock discontinuity or a missing calibration.
        if not gpu_ns or self.ns_per_unit is None:
            return None
        i = bisect_right(self.clock_times, near_us)
        for right in (i, i-1, i+1):
            if not 0 < right < len(self.clocks):
                continue
            a, b = self.clocks[right-1:right+1]
            if (b['host_after_us']-a['host_before_us'] > 2500000 or
                    not a['gpu_ns'] <= gpu_ns <= b['gpu_ns'] or
                    min(abs(near_us-k['host_before_us']) for k in (a,b)) > 2000000):
                continue
            # The Switch NVK build used for these captures reports a 1 ns
            # timestamp period, while its counter advances 614.4 units per us.
            us_per_unit = self.ns_per_unit / 1000
            lo = floor(min(k['host_before_us']+(gpu_ns-k['gpu_ns'])*us_per_unit for k in (a,b)))
            hi = ceil(max(k['host_after_us']+(gpu_ns-k['gpu_ns'])*us_per_unit for k in (a,b))) + 1
            if hi-lo <= 1000:
                return [lo, hi]
        return None

    def attempt(self, display):
        end = display['time_us']
        i = bisect_right(self.starts, end) - 1
        if i < 0:
            return None
        h = self.waits[i]
        # D starts before H (the UI also prepares the overlay). Rounding the
        # three durations in D truncates up to three microseconds.
        start = end - sum(display[k] for k in ('acquire_us', 'blit_overlay_us', 'submit_us'))
        if (h['slot_ready'] and h['image_ready'] and start-4 <= h['begin_us'] and
                h['begin_us']+h['slot_wait_us']+h['image_wait_us'] <= end+2):
            return h
        return None

    def window(self, first_us, last_us):
        long_intervals = []
        matched = unmatched = repeats = skipped = consecutive_sources = 0
        for i in range(max(1, bisect_right(self.ends, first_us)), bisect_right(self.ends, last_us)):
            d = self.displays[i]
            prev = self.ends[i-1]
            h = self.attempt(d)
            if h is None:
                unmatched += 1
                continue
            matched += 1
            y = self.submissions.get(h['begin_us'], {})
            previous = self.attempt(self.displays[i-1])
            py = self.submissions.get(previous['begin_us'], {}) if previous else {}
            source = y.get('source_frame', 0)
            prior = py.get('source_frame', 0)
            if source and prior and source >= prior:
                consecutive_sources += 1
                repeats += source == prior
                skipped += max(0, source-prior-1)
            # D is the UI return. New recordings also include the actual
            # return from vkQueuePresentKHR, ahead of any clock calibration.
            end = y.get('queue_present_end_us', d['time_us'])
            prev = py.get('queue_present_end_us', prev)
            if end-prev < 25000:
                continue
            detail = dict(previous_submit_return_us=prev, submit_return_us=end,
                          interval_us=end-prev, before_attempt_us=h['begin_us']-prev,
                          slot_wait_us=h['slot_wait_us'], image_wait_us=h['image_wait_us'],
                          after_acquire_us=end-h['begin_us']-h['slot_wait_us']-h['image_wait_us'],
                          publications_during_wait=h['generation_after']-h['generation_before'])
            if 'release_fence_us' in h:
                for k in ('dequeue_us','release_event_us','release_fence_us',
                          'dequeue_calls','release_event_calls','release_fence_calls'):
                    detail[k] = h[k]
            if 'source_frame' in y:
                detail.update(source_frame=source, previous_source_frame=prior, image_index=y['image_index'],
                              scene_submit_us=y['scene_submit_us'], window_submit_us=y['window_submit_us'],
                              queue_present_end_us=y['queue_present_end_us'],
                              scene_gpu_done_host_us=self.host_time(self.scene_ends.get(source), d['time_us']),
                              window_gpu_done_host_us=self.host_time(y['gpu_end_ns'], d['time_us']),
                              vsync_wakes_us=self.edges[bisect_right(self.edges,prev):bisect_right(self.edges,end)])
            long_intervals.append(detail)
        return dict(matched_returns=matched, unmatched_returns=unmatched, long_intervals=long_intervals,
                    adjacent_known_sources=consecutive_sources, repeated_sources=repeats, skipped_sources=skipped)
