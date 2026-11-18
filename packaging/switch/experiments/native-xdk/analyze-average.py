"""Measure a fixed combat window, retaining detailed samples and long frames.

Use seconds since boot from a single session. This measures generated frames
and display submissions separately; D is not a scanout/panel timestamp.
"""
import argparse
import importlib.util
import json
from pathlib import Path
from statistics import mean

spec = importlib.util.spec_from_file_location('diag', Path(__file__).with_name('analyze-diag.py'))
diag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diag)


def measure(session, start, end):
    assert end > start >= 0
    assert not session['lost'] and not session['malformed'], 'Incomplete log; recapture before acceptance.'
    rows = session['rows']
    lo, hi = start * 1e6, end * 1e6
    within = lambda row: lo <= row['time_us'] <= hi
    frames = [r for r in rows['N'] if within(r)]
    display = [r for r in rows['D'] if within(r)]
    guests = [r for r in rows['G'] if within(r)]
    assert len(frames) > 1 and guests, 'Window has no continuous combat record.'
    assert all(r['active'] and r['hp'] and r['max_hp'] == 2400 for r in guests), 'Window includes inactive/dead play.'
    assert frames[0]['time_us'] - lo < 250000 and hi - frames[-1]['time_us'] < 250000, 'Window extends outside recorded combat.'
    assert all(b['native_frame'] == a['native_frame'] + 1 for a, b in zip(frames, frames[1:])), 'Window crosses a logging gap.'

    # N's first row includes time before the selected first endpoint. Use
    # successive endpoints instead, retaining every interval between them.
    intervals = [b['time_us'] - a['time_us'] for a, b in zip(frames, frames[1:])]
    assert all(t > 0 for t in intervals)
    assert all(abs(t - b['frame_wall_us']) <= 1 for t, b in zip(intervals, frames[1:])), 'Frame clock mismatch.'
    generated = dict(frames=len(intervals), seconds=sum(intervals)/1e6,
        average_fps=len(intervals)*1e6/sum(intervals),
        frame_time=diag.stats(intervals), longest_frame_ms=max(intervals)/1000,
        cpu=diag.stats(r['frame_cpu_us'] for r in frames[1:]),
        profiled_frames=sum(r['profiled'] for r in frames[1:]))
    nonprofiled = [r['frame_cpu_us'] for r in frames[1:] if not r['profiled']]
    generated['nonprofiled_mean_cpu_ms'] = mean(nonprofiled)/1000 if nonprofiled else None

    displayed = None
    if len(display) > 1:
        assert all(b['generation'] > a['generation'] for a, b in zip(display, display[1:])), 'Display reset or duplicate generation in window.'
        gaps = [b['time_us'] - a['time_us'] for a, b in zip(display, display[1:])]
        assert all(t > 0 for t in gaps)
        displayed = dict(updates=len(gaps), seconds=sum(gaps)/1e6,
            average_fps=len(gaps)*1e6/sum(gaps), interval=diag.stats(gaps),
            longest_gap_ms=max(gaps)/1000,
            skipped_generations=sum(b['generation']-a['generation']-1 for a,b in zip(display,display[1:])),
            gaps_over_40_ms=sum(t > 40000 for t in gaps))

    writes = [r for r in rows['F'] if r['time_us'] <= hi and r['time_us'] + r['write_us'] >= lo]
    return dict(version=session['version'], window_seconds_since_boot=[start,end],
        generated=generated, display_submissions=displayed,
        background_log_writes=diag.stats(r['write_us'] for r in writes),
        notes=['All intervals inside the window are retained, including detailed samples and combat hitches.',
               'FPS is total frames divided by elapsed time, not an average of HUD FPS values.',
               'Display submission timestamps do not prove when the physical panel scanned out the image.'])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    p.add_argument('--session', type=int, help='zero-based session index; defaults to last native session')
    p.add_argument('--start', type=float, required=True)
    p.add_argument('--end', type=float, required=True)
    p.add_argument('--json', type=Path)
    args = p.parse_args()
    sessions = diag.load(args.capture)
    index = args.session if args.session is not None else max(i for i,s in enumerate(sessions) if s['rows']['N'])
    result = dict(session_index=index, **measure(sessions[index],args.start,args.end))
    text = json.dumps(result,indent=2) + '\n'
    if args.json:
        args.json.write_text(text)
    print(text,end='')
