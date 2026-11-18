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


def load(path):
    sessions = []
    for line in csv.reader(Path(path).open()):
        if not line:
            continue
        kind, *values = line
        if kind == '#SESSION':
            sessions.append(dict(version=values[0], schemas={}, rows=defaultdict(list), lost=Counter(), malformed=0))
        elif sessions:
            s = sessions[-1]
            if kind == '#LOST':
                s['lost'][values[0]] += int(values[1])
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
    costs = [sum(q['gpu_us'] for q in queries[a['present']]) for a in matched
        if queries[a['present']] and all(q['valid'] for q in queries[a['present']])]
    result['render'] = dict(matched_frames=len(matched), valid_gpu_frames=len(costs), gpu=stats(costs),
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
    ]
    return s, result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--expect-no-vsync', action='store_true', help='verify immediate late submission and disabled refresh alignment')
    parser.add_argument('--json', type=Path)
    parser.add_argument('--start', type=float, help='inclusive seconds since boot (not since first combat row)')
    parser.add_argument('--end', type=float, help='exclusive seconds since boot')
    args = parser.parse_args()
    if args.start is not None and args.end is not None and args.end <= args.start:
        parser.error('--end must be later than --start')
    session, result = report(load(args.capture), args.start, args.end)
    if args.verify:
        verify(session)
        result['verified'] = True
    if args.expect_no_vsync:
        swaps = session['rows']['V']
        assert swaps and all(v['periods'] == 0 and v['retargeted'] == 0 for v in swaps)
        for before, after in zip(swaps, swaps[1:]):
            if after['native_frame'] == before['native_frame']+1 and after['entry_us']-before['present_start_us'] > 17000:
                assert after['wait_wall_us'] == 0, ('late frame was paced', before, after)
        result['no_vsync_verified'] = True
        result['notes'].append('Refresh alignment is disabled. Any V wait remaining is the independent 60 fps ceiling.')
    output = json.dumps(result, indent=2)
    if args.json:
        args.json.write_text(output+'\n')
    print(output)
