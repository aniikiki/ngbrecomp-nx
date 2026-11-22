"""Read native pacing diagnostics. Wall waits overlap CPU work; never sum them.

Selects the last session containing N records, reporting any trailing empty boots.
--verify checks the real emitted schemas, frame joins and exclusive timer budget.
"""
import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
from statistics import mean, median
from present_timing import gpu_ns_per_unit


def load(path):
    sessions = []
    for line in csv.reader(Path(path).open()):
        if not line:
            continue
        kind, *values = line
        if kind == '#SESSION':
            sessions.append(dict(version=values[0], schemas={}, rows=defaultdict(list), lost=Counter(),
                                 vsync_errors=[], malformed=0))
        elif sessions:
            s = sessions[-1]
            if kind == '#LOST':
                s['lost'][values[0]] += int(values[1])
            elif kind == '#VSYNC_ERROR':
                s['vsync_errors'].append(int(values[0]))
            elif kind.startswith('#'):
                s['schemas'][kind[1:]] = values
            elif kind in s['schemas']:
                names = s['schemas'][kind]
                if len(values) != len(names) or not all(v.isdecimal() for v in values):
                    s['malformed'] += 1
                else:
                    s['rows'][kind].append(dict(zip(names, map(int, values))))
    return sessions


def stats(values):
    values = sorted(values)
    if not values:
        return None
    return dict(n=len(values), mean_ms=mean(values)/1000, p50_ms=median(values)/1000,
                p95_ms=values[min(len(values)-1, int(len(values)*.95))]/1000)


def verify(s):
    r = s['rows']
    assert not s['lost'] and not s['malformed'], ('incomplete capture', s['lost'], s['malformed'])
    n = {v['native_frame']: v for v in r['N']}
    v = {v['native_frame']: v for v in r['V']}
    assert len(n) == len(r['N']) and len(v) == len(r['V']), 'duplicate frame IDs'
    assert n and r['T'], 'missing frame or sampled timers'
    for frame, a in n.items():
        b = v[frame]
        assert a['draws'] == b['draws'], (frame, 'draw count')
        assert b['exit_blank'] >= b['entry_blank']
        assert b['wait_wall_us'] + b['present_wall_us'] <= b['swap_wall_us'] + 2
        if b['retargeted']:
            assert not b['interval'] & 0x80000000 and b['periods']
            assert b['entry_blank'] >= b['previous_blank'] + b['periods']
            assert b['target_blank'] == b['entry_blank'] + 1
    for t in r['T']:
        a = n[t['native_frame']]
        assert a['profiled'], ('unexpected detailed sample', t)
        total = sum(value for name, value in t.items() if name.endswith('_ns'))
        assert total <= a['frame_wall_us']*1000 + 999, ('overlapping timers', a, t)
    assert len(r['T']) == sum(a['profiled'] for a in n.values()), 'missing detailed samples'
    if 'native_filter_enabled' in s['schemas'].get('E', ()):
        for e in r['E']:
            assert e['eligible_draws'] == e['opaque_p8_draws'] + e['soft_a8_draws']
            assert e['native_filter_enabled'] in (0, 1)
    for window in r.get('O', ()):
        assert window['min_images'] <= window['requested_images'] <= window['actual_images']
        assert not window['max_images'] or window['actual_images'] <= window['max_images']
    if 'A' in s['schemas']:
        phase_calls = [k for k in s['schemas']['A'] if k.endswith('_calls') and k not in ('omitted_calls','screen_mix_calls')]
        details = set()
        for a in r['A']:
            frame = a['submit_frame']
            assert frame % 4 == 2 and a['material_detail'] == int(frame % 8 == 6), ('GPU sample cadence', a)
            assert a['spans'] + a['omitted_calls'] <= sum(a[k] for k in phase_calls), ('GPU span counts', a)
            assert not a['valid'] or a['spans'] > 0
            if 'screen_mix_ns' in a:
                assert a['screen_mix_calls'] <= sum(a[k] for k in phase_calls)
                assert a['screen_mix_ns'] <= sum(a[k[:-6]+'_ns'] for k in phase_calls)
            if a['valid'] and a['material_detail']:
                details.add(frame)
        material_phases = range(6) if 'pixel_shader' in s['schemas'].get('L', ()) else (1, 2)
        for m in r['L']:
            assert m['submit_frame'] in details and m['phase'] in material_phases, ('orphan material group', m)
            assert 0 < m['spans'] <= m['calls']
    if 'Y' in s['schemas']:
        acquired = {h['begin_us'] for h in r['H'] if h['slot_ready'] and h['image_ready']}
        for y in r['Y']:
            assert y['begin_us'] in acquired, ('window sample without acquire', y)
            assert y['valid'] in (0, 1) and (y['valid'] or not y['window_gpu_ns'])
            if 'source_frame' in y:
                assert y['begin_us'] <= y['window_submit_us'] <= y['queue_present_end_us']
                assert not y['source_frame'] or 0 < y['scene_submit_us'] <= y['window_submit_us']
                if y['valid']:
                    assert abs(y['gpu_end_ns']-y['gpu_start_ns']-y['window_gpu_ns']) <= 2
        for h in r['H']:
            if 'release_fence_us' in h:
                assert sum(h[k] for k in ('dequeue_us','release_event_us','release_fence_us')) <= h['image_wait_us']+2
    for q in r['Q']:
        if 'gpu_start_ns' in q and q['valid']:
            assert q['gpu_end_ns']-q['gpu_start_ns'] >= q['gpu_us']*1000-2
    for k in r.get('K', ()):
        assert k['host_after_us'] >= k['host_before_us']
    for edge in r.get('S', ()):
        assert edge['vsync_wake_us'] >= edge['wait_start_us']


def report(sessions, start=None, end=None):
    selected = [i for i, s in enumerate(sessions) if s['rows']['N']]
    if not selected:
        raise ValueError('No native diagnostics in this capture; need the 0.57.1-diag package and alma-perf.flag.')
    index = selected[-1]
    s, r = sessions[index], sessions[index]['rows']
    guests = r['G']
    times = [g['time_us'] for g in guests]
    alive = []
    for n in r['N']:
        at = bisect_right(times, n['time_us'])-1
        g = guests[at] if at >= 0 else None
        if (n['draws'] >= 250 and g and g['active'] and
                g['max_hp'] == 2400 and g['hp'] > 0 and n['time_us']-g['time_us'] < 250000 and
                (start is None or n['time_us'] >= start*1e6) and
                (end is None or n['time_us'] < end*1e6)):
            alive.append(n)
    frames = [n for n in alive if not n['profiled']]
    wanted = {n['native_frame'] for n in frames}
    swaps = [v for v in r['V'] if v['native_frame'] in wanted]
    # Detailed samples are reported separately: they are excluded from the FPS
    # estimate so the observer cost can be checked against neighbouring frames.
    alive_ids = {n['native_frame'] for n in alive}
    detailed = [t for t in r['T'] if t['native_frame'] in alive_ids]
    result = dict(version=s['version'], session_index=index, trailing_sessions=len(sessions)-index-1,
        records={k: len(v) for k, v in r.items()}, dropped=dict(s['lost']), malformed=s['malformed'],
        window_seconds_since_boot=[start, end],
        selection='alive Alma, max_hp=2400, draws>=250, detailed samples excluded',
        frames=len(frames), fps=len(frames)*1e6/sum(n['frame_wall_us'] for n in frames) if frames else None)
    result['timing'] = {k: stats(n[k] for n in frames) for k in
        ('frame_wall_us','frame_cpu_us','frame_wait_us','resource_wait_us','fence_wait_us',
         'readback_wait_us','vblank_active_us','pace_active_us','present_us','callback_us')}
    result['pacing'] = dict(intervals=dict(Counter(hex(v['interval']) for v in swaps)),
        periods=dict(Counter(v['periods'] for v in swaps)), retargeted=sum(v['retargeted'] for v in swaps),
        frames=len(swaps), wait_wall=stats(v['wait_wall_us'] for v in swaps),
        wait_cpu=stats(v['wait_cpu_us'] for v in swaps),
        requested_wait=stats(max(0,v['deadline_us']-v['wait_start_us']) for v in swaps if v['wait_start_us']),
        blank_steps=dict(Counter(v['exit_blank']-v['previous_blank'] for v in swaps)))
    byswap = {v['native_frame']: v for v in swaps}
    result['outside_pace_wall'] = stats(n['frame_wall_us']-byswap[n['native_frame']]['wait_wall_us']
        for n in frames if n['native_frame'] in byswap)
    result['calls_per_frame'] = {k: mean(n[k] for n in frames) if frames else None
        for k in s['schemas']['N'] if k.endswith('_calls') or k in ('draws','inline_words')}
    # Native and render presents use the same counter in this package. GPU
    # timestamps are read later, so join by submit_frame, never read_time_us.
    queries = defaultdict(list)
    for q in r['Q']:
        queries[q['submit_frame']].append(q)
    rendered = {a['present']: a for a in r['R']}
    matched = [rendered[n['native_frame']] for n in frames if n['native_frame'] in rendered]
    measured_scale = gpu_ns_per_unit(r.get('K', ()))
    scale = measured_scale or 1
    costs = [scale * sum(q['gpu_us'] for q in queries[a['present']]) for a in matched
        if queries[a['present']] and all(q['valid'] for q in queries[a['present']])]
    result['render'] = dict(matched_frames=len(matched), valid_gpu_frames=len(costs), gpu=stats(costs),
        gpu_ns_per_log_unit=measured_scale,
        mean_command_buffers=mean(len(queries[a['present']]) for a in matched) if matched else None,
        max_command_buffers=max((len(queries[a['present']]) for a in matched), default=0),
        mean_drawn=mean(a['drawn'] for a in matched) if matched else None,
        compile_us=sum(a['compile_us'] for a in matched), shaders=sum(a['shaders'] for a in matched),
        pipelines=sum(a['pipelines'] for a in matched),
        texture_upload=stats(a['texture_us'] for a in matched))
    result['sampled_exclusive_wall'] = {k: stats(t[k]/1000 for t in detailed)
        for k in s['schemas']['T'] if k.endswith('_ns')}
    result['sampled_frame_cpu'] = stats(n['frame_cpu_us'] for n in alive if n['profiled'])
    result['readback'] = {k: sum(b[k] for b in r['B']) for k in
        ('requests','targets','staging_bytes','wall_us','cpu_us','submit_us')}
    result['latest_clocks'] = r['C'][-1] if r['C'] else None
    result['notes'] = [
        'N measures end-of-Swap/FrameWait to the next end. V describes that same numbered Swap.',
        'V wait_wall includes other cooperative guest workers; wait_cpu is the whole host thread during it.',
        'N waits and T are exclusive scheduled wall time, pausing when another guest worker runs. They are not CPU attribution.',
        'T hot scopes sample one frame in 32; rare coarse waits are timed every recorded frame.',
        'Readback B runs on the render thread. Its time overlaps the guest readback wait; do not add them.',
        'From 0.57.9, asynchronous chunks share a frame ID. Their Q rows count each covered GPU interval once, excluding gaps between submissions.',
    ]
    return s, result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--expect-no-vsync', action='store_true', help='verify guest pacing and immediate window presentation')
    parser.add_argument('--expect-guest-no-vsync', action='store_true', help='check guest pacing alone, including captures without a window')
    parser.add_argument('--json', type=Path)
    parser.add_argument('--story', action='store_true', help='compare New Game entries, full charges and Alma sword landing candidates in each boot')
    parser.add_argument('--frames', type=int, nargs=2, action='append', default=[],
                        metavar=('FIRST','LAST'), help='include this inclusive guest-flip window in --story output')
    parser.add_argument('--start', type=float, help='inclusive seconds since boot (not since first combat row)')
    parser.add_argument('--end', type=float, help='exclusive seconds since boot')
    args = parser.parse_args()
    if args.frames and (not args.story or any(first<0 or last<first for first,last in args.frames)):
        parser.error('--frames requires --story and an inclusive range of nonnegative flip numbers')
    if args.start is not None and args.end is not None and args.end <= args.start:
        parser.error('--end must be later than --start')
    sessions = load(args.capture)
    if args.story:
        if args.expect_no_vsync or args.expect_guest_no_vsync or args.start is not None or args.end is not None:
            parser.error('--story compares complete sessions')
        from story_perf import story_report
        if args.verify:
            for session in sessions:
                if session['rows']['N']:
                    verify(session)
        result = {'sessions': [story_report(s, args.frames) for s in sessions]}
        output = json.dumps(result, indent=2)
        if args.json:
            args.json.write_text(output+'\n')
        print(output)
        raise SystemExit(0)
    session, result = report(sessions, args.start, args.end)
    if args.verify:
        verify(session)
        result['verified'] = True
    if args.expect_no_vsync or args.expect_guest_no_vsync:
        swaps = session['rows']['V']
        assert swaps and all(v['periods'] == 0 and v['retargeted'] == 0 for v in swaps)
        for before, after in zip(swaps, swaps[1:]):
            if after['native_frame'] == before['native_frame']+1 and after['entry_us']-before['present_start_us'] > 17000:
                assert after['wait_wall_us'] == 0, ('late frame was paced', before, after)
        result['guest_no_vsync_verified'] = True
        result['notes'].append('Guest swaps use an independent 60 fps ceiling.')
    if args.expect_no_vsync:
        windows = session['rows']['O']
        assert windows, 'no window present mode recorded'
        for window in windows:
            assert window['present_mode'] == 0, ('window did not request VK_PRESENT_MODE_IMMEDIATE_KHR', window)
            if 'native_swap_interval' in window:
                assert window['native_swap_interval'] == 0, ('Switch window still waits for display refresh', window)
        result['no_vsync_verified'] = True
    output = json.dumps(result, indent=2)
    if args.json:
        args.json.write_text(output+'\n')
    print(output)
