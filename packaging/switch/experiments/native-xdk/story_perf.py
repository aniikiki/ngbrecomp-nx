"""Compare New Game, second-charge releases and Alma sword landings within each boot."""
from bisect import bisect_left, bisect_right
from collections import defaultdict
from math import ceil
from statistics import median
import struct
from present_timing import PresentTimeline, gpu_ns_per_unit

PHASES = ('opaque', 'alpha', 'additive', 'offscreen', 'composite', 'history', 'scanout')


def quantiles(values):
    values = sorted(values)
    if not values:
        return None
    return dict(n=len(values), median=median(values), p95=values[ceil(.95*len(values))-1], peak=values[-1])


def segments(frames):
    run = []
    for f in sorted(frames):
        if run and f != run[-1]+1:
            yield run
            run = []
        run.append(f)
    if run:
        yield run


def phase_report(frames, phases, materials, gpu, waves, scale=1):
    sampled = {i: phases[i] for i in frames if i in phases}
    complete = {i for i, parts in sampled.items() if all(p['valid'] and not p['omitted_calls'] for p in parts)}
    # One present can drain the same slot more than once after synchronous
    # submissions. Sum its portions before computing per-frame percentiles.
    variants = {}
    for detail, name in enumerate(('coarse', 'material_detail')):
        ids = [i for i in complete if sampled[i][0]['material_detail'] == detail]
        names = PHASES + tuple(k for k in ('feedback','surface_copy')
                               if ids and k+'_ns' in sampled[ids[0]][0])
        variants[name] = dict(frames=len(ids), whole_gpu_us=quantiles(gpu[i] for i in ids if i in gpu),
            phase_gpu_us={k: quantiles(sum(p[k+'_ns'] for p in sampled[i])*scale/1000 for i in ids) for k in names},
            copy_calls={k: quantiles(sum(p[k+'_calls'] for p in sampled[i]) for i in ids)
                        for k in names if k in ('feedback','surface_copy')},
            copy_pixels={k: quantiles(sum(p[k+'_pixels'] for p in sampled[i]) for i in ids)
                         for k in names if k in ('feedback','surface_copy')})
        # This selected draw is already included in its phase total.
        for field in ('screen_mix', 'add128', 'ring_target'):
            if ids and field + '_ns' in sampled[ids[0]][0]:
                variants[name][field + '_gpu_us'] = quantiles(
                    sum(p[field + '_ns'] for p in sampled[i]) * scale / 1000 for i in ids)
                variants[name][field + '_calls'] = quantiles(
                    sum(p[field + '_calls'] for p in sampled[i]) for i in ids)
    hits = defaultdict(dict)
    for i in sorted(complete):
        for m in materials.get(i, ()):
            key = tuple(m.get(k) for k in ('phase', 'texture_sig', 'width', 'height', 'format', 'src', 'dst',
                                           'pixel_shader','texture1_sig','target_stages'))
            per_frame = hits[key]
            per_frame[i] = per_frame.get(i, 0) + m['gpu_ns']
    ordered = sorted(hits.items(), key=lambda kv: sum(kv[1].values()), reverse=True)
    def describe(k, costs):
        return dict(phase=PHASES[k[0]], texture_sig=f'{k[1]:016x}', width=k[2], height=k[3],
                    format=k[4], src=k[5], dst=k[6], pixel_shader=None if k[7] is None else f'{k[7]:016x}',
                    texture1_sig=None if k[8] is None else f'{k[8]:016x}', target_stages=k[9],
                    observed_frames=len(costs), observed_gpu_us=quantiles(ns*scale/1000 for ns in costs.values()))
    clean = [v for i, v in gpu.items() if i not in sampled and
             not any(w['strip_sampled'] or w['sprite_sampled'] or w['unavailable'] for w in waves.get(i, ()))]
    return dict(sampled_frames=len(sampled), complete_frames=len(complete),
        invalid_frames=sum(any(not p['valid'] for p in parts) for parts in sampled.values()),
        omitted_calls=sum(p['omitted_calls'] for parts in sampled.values() for p in parts),
        by_probe=variants, whole_gpu_us_without_draw_timestamps=quantiles(clean),
        ranked_blend_groups=[describe(k,c) for k,c in ordered if k[0] in (1,2)][:8],
        ranked_materials=[describe(k,c) for k,c in ordered[:8]])


def fx_types(player, frames):
    if not frames or 'fx_types_0' not in player[frames[0]]:
        return None
    types = []
    for base in range(0, 256, 64):
        mask = 0
        for i in frames:
            mask |= player[i][f'fx_types_{base}']
        types.extend(base+bit for bit in range(64) if mask & (1 << bit))
    return types


def height(row):
    return struct.unpack('<f', struct.pack('<I', row['player_y_f32bits']))[0]


def main_menu_masks(rows, queries, rendered, ns_per_unit):
    # Each uninterrupted visit starts its own 16-frame A/B/B/A blocks. Only
    # compare equally many blocks of the same workload and observed clocks.
    menu = rows.get('E', ())
    layer_filters = bool(menu and 'native_filter_enabled' in menu[0])
    arm = 'native_filter_enabled' if layer_filters else 'gather_enabled'
    draw_fields = ('opaque_p8_draws', 'soft_a8_draws') if layer_filters else ('eligible_draws',)
    clocks = sorted(rows['C'], key=lambda c: c['time_us'])
    times = [c['time_us'] for c in clocks]
    cycles = defaultdict(lambda: defaultdict(list))
    presentation_blocks = {}
    for e in menu:
        f, age = e['submit_frame'], e['menu_frame']
        r, q = rendered.get(f), queries.get(f)
        if not (64 < age <= 320 and e['eligible_draws'] and r):
            continue
        if (age - 1) % 16 < 2 or r['compile_us'] or r['texture_uploads']:
            continue
        clock = bisect_right(times, r['time_us']) - 1
        rates = tuple(clocks[clock][k+'_hz'] if clock >= 0 and not clocks[clock][k+'_rc'] else None
                      for k in ('cpu', 'gpu', 'emc'))
        settings = (e['render_scale'], e['msaa'], e['aniso'], *(e[k] for k in draw_fields), *rates)
        cycle, block = divmod((age - 1) // 16, 4)
        if e[arm] != int(block in (1, 2)):
            continue
        group = (settings, f - age, cycle)
        presentation_blocks[f] = (group, block)
        if f % 4 != 2 and q and all(p['valid'] for p in q):
            cycles[group][block].append(sum(p['gpu_us'] for p in q))
    groups = defaultdict(list)
    paired_cycles = set()
    for group, blocks in cycles.items():
        if any(len(blocks[k]) < 6 for k in range(4)):
            continue
        a, b, c, d = (median(blocks[k]) for k in range(4))
        if a + d > 0:
            paired_cycles.add(group)
            groups[group[0]].append(((a+d)/2, (b+c)/2, 100*(1-(b+c)/(a+d))))
    # Both submitted source frames and any intervening frames must belong to
    # the same stable block. Use real submission intervals for display FPS.
    intervals = defaultdict(list)
    submitted = sorted((y for y in rows.get('Y', ()) if y.get('present_result') in (0, 1000001003)),
                       key=lambda y: y['queue_present_end_us'])
    for prev, cur in zip(submitted, submitted[1:]):
        first, last = prev['source_frame'], cur['source_frame']
        state = presentation_blocks.get(first)
        if not state or presentation_blocks.get(last) != state or last < first:
            continue
        group, block = state
        if group in paired_cycles and all(presentation_blocks.get(f) == state for f in range(first + 1, last)):
            dt = cur['queue_present_end_us'] - prev['queue_present_end_us']
            if dt > 0:
                intervals[group[0], block in (1, 2)].append(dt)
    out = []
    for settings, pairs in groups.items():
        ref, optimized, gains = zip(*pairs)
        labels = draw_fields if layer_filters else ('mask_draws',)
        entry = dict(zip(('render_scale','msaa','aniso',*labels,'cpu_hz','gpu_hz','emc_hz'), settings),
                        complete_cycles=len(pairs), gpu_time_saved_pct=median(gains),
                        reference_gpu_ms=median(ref)*ns_per_unit/1000 if ns_per_unit else None)
        entry['native_filter_gpu_ms' if layer_filters else 'gather_gpu_ms'] = median(optimized)*ns_per_unit/1000 if ns_per_unit else None
        for native, name in ((False, 'reference'), (True, 'optimized')):
            dt = intervals[settings, native]
            if dt:
                entry[name + '_window_fps'] = round(len(dt)*1e6/sum(dt), 2)
                entry[name + '_window_intervals'] = len(dt)
        out.append(entry)
    return dict(menu_frames=len(menu), frames_with_masks=sum(e['eligible_draws'] > 0 for e in menu),
                paired=out)


def story_report(session, requested_windows=()):
    rows = session['rows']
    measured_scale = gpu_ns_per_unit(rows.get('K', ()))
    scale = measured_scale or 1
    guests = {g['guest_flip']: g for g in rows['G'] if g['active']}
    guest_flips = sorted(guests)
    game = {f: g for f, g in guests.items() if g['mission_id'] == 255 and g['mode'] == 1}
    alma = {f for f, g in guests.items() if g['mission_id'] == 23 and g['mode'] == 3 and g['hp'] > 0}
    missions = {f for f,g in guests.items() if g['mode']==3 and g['mission_id']!=255 and g['hp']>0}
    player = {u['guest_flip']: u for u in rows['U'] if u['guest_flip'] in game or u['guest_flip'] in missions}
    rendered = {r['present']: r for r in rows['R']}
    queries, waves = defaultdict(list), defaultdict(list)
    for q in rows['Q']:
        queries[q['submit_frame']].append(q)
    for w in rows['W']:
        waves[w['submit_frame']].append(w)
    phases, materials = defaultdict(list), defaultdict(list)
    for a in rows.get('A', ()):
        phases[a['submit_frame']].append(a)
    for m in rows.get('L', ()):
        materials[m['submit_frame']].append(m)
    window_waits = sorted(rows.get('H', ()), key=lambda h: h['begin_us'])
    wait_starts = [h['begin_us'] for h in window_waits]
    window_gpu = sorted(rows.get('Y', ()), key=lambda y: y['begin_us'])
    submit_starts = [y['begin_us'] for y in window_gpu]

    def window(first, last):
        frames = guest_flips[bisect_left(guest_flips, first):bisect_right(guest_flips, last)]
        contiguous = [i for i in frames if i-1 in guests]
        rs = [rendered[i] for i in frames if i in rendered]
        timing = {i: guests[i]['time_us']-guests[i-1]['time_us'] for i in contiguous}
        # An FPS interval contains 30 actual adjacent flips. Never bridge a
        # missing row, an inactive scene or the beginning of a short window.
        fps = [30e6/(guests[i]['time_us']-guests[i-30]['time_us']) for run in segments(contiguous)
               for i in run[29:] if guests[i]['time_us'] > guests[i-30]['time_us']]
        gpu = {i: scale * sum(q['gpu_us'] for q in queries[i]) for i in frames
               if i in queries and all(q['valid'] for q in queries[i])}
        part = [w for i in frames for w in waves.get(i, ())]
        wave = None
        if 'W' in session['schemas']:
            wave = {k: sum(w[k] for w in part) for k in
                    ('strip_draws','sprite_draws','strip_sampled','sprite_sampled','unavailable')}
            ns = defaultdict(int)
            for w in part:
                if w['strip_sampled'] or w['sprite_sampled']:
                    ns[w['submit_frame']] += w['strip_gpu_ns'] + w['sprite_gpu_ns']
            wave['sampled_frame_gpu_us'] = quantiles(v*scale/1000 for v in ns.values())
            wave['frames_with_draws'] = len({w['submit_frame'] for w in part})
            probed = {w['submit_frame'] for w in part if w['strip_sampled'] or w['sprite_sampled'] or w['unavailable']}
            wave['whole_gpu_us_without_wave_timestamps'] = quantiles(v for i,v in gpu.items() if i not in probed)
        io = {}
        for key in ('read_bytes','read_us','write_bytes','write_us','archive_write_bytes','archive_write_us'):
            if contiguous and key in guests[contiguous[0]]:
                io[key] = sum(guests[i][key]-guests[i-1][key] for i in contiguous)
        elapsed = sum(timing.values())
        display_count = sum(guests[i]['display_total'] - guests[i-1]['display_total'] for i in contiguous
                            if 'display_total' in guests[i] and 'display_total' in guests[i-1])
        display = dict(fps=round(display_count * 1e6 / elapsed, 2), submits=display_count) if (
            elapsed and 'display_total' in guests[contiguous[0]]) else None
        if display is not None and 'H' in session['schemas']:
            attempts = []
            submits = []
            for run in segments(contiguous):
                begin, end = guests[run[0]-1]['time_us'], guests[run[-1]]['time_us']
                attempts.extend(window_waits[bisect_right(wait_starts, begin):bisect_right(wait_starts, end)])
                submits.extend(window_gpu[bisect_right(submit_starts, begin):bisect_right(submit_starts, end)])
            display['attempts'] = len(attempts)
            display['slot_wait_us'] = quantiles(h['slot_wait_us'] for h in attempts)
            display['image_wait_us'] = quantiles(h['image_wait_us'] for h in attempts if h['slot_ready'])
            display['unavailable_slot'] = sum(not h['slot_ready'] for h in attempts)
            display['unavailable_image'] = sum(h['slot_ready'] and not h['image_ready'] for h in attempts)
            display['attempts_with_new_publication'] = sum(h['generation_before'] != h['generation_after']
                                                           for h in attempts)
            if 'Y' in session['schemas']:
                display['sampled_submits'] = len(submits)
                display['window_gpu_us'] = quantiles(y['window_gpu_ns']*scale/1000 for y in submits if y['valid'])
                for key in ('queue_lock_us', 'queue_submit_us', 'queue_present_us'):
                    display[key] = quantiles(y[key] for y in submits)
        return dict(first=first, last=last, guest_frames=len(frames), render_frames=len(rs), display=display,
                    guest_fps=round(len(timing) * 1e6 / elapsed, 2) if elapsed else None,
                    min_30_flip_fps=round(min(fps),2) if fps else None,
                    flip_us=quantiles(timing.values()), gpu_us=quantiles(gpu.values()),
                    guest_cpu_us=quantiles(guests[i]['cpu_us']-guests[i-1]['cpu_us'] for i in contiguous
                                           if guests[i-1]['cpu_us'] and guests[i]['cpu_us'] >= guests[i-1]['cpu_us']),
                    pipelines=sum(r['pipelines'] for r in rs), shaders=sum(r['shaders'] for r in rs),
                    compile_us=sum(r['compile_us'] for r in rs), texture_uploads=sum(r['texture_uploads'] for r in rs),
                    texture_upload_us=sum(r['texture_us'] for r in rs),
                    gpu_us_without_compile_or_upload=quantiles(gpu[i] for i in gpu if i in rendered and
                        not rendered[i]['compile_us'] and not rendered[i]['texture_uploads']),
                    fence_us=quantiles(r['fence_us'] for r in rs), io=io, wave=wave,
                    draw_phases=phase_report(frames, phases, materials, gpu, waves, scale) if 'A' in session['schemas'] else None,
                    active_fx_types=fx_types(player, [i for i in frames if i in player]))

    charges = []
    story_runs = list(segments(player.keys() & game.keys()))
    alma_runs = list(segments(player.keys() & alma))
    mission_runs = [seq for mid in sorted({guests[f]['mission_id'] for f in missions})
                    for seq in segments(f for f in missions if f in player and guests[f]['mission_id']==mid)]
    for seq in sorted(story_runs + mission_runs):
        # Keep incomplete holds in the result. In particular, an actor can be
        # interrupted or a capture can end before a physical button release.
        full_frames = [i for i in seq if player[i]['charge_level'] == 2]
        holds = list(segments(full_frames))
        for idx, hold in enumerate(holds):
            first, last = hold[0], hold[-1]
            stop = min(seq[-1], holds[idx+1][0]-1 if idx+1 < len(holds) else seq[-1])
            edges = [i for i in range(max(first,seq[0]+1),min(last+1,stop)+1)
                     if player[i-1]['pad_state'] & 0x800 and not player[i]['pad_state'] & 0x800]
            release = edges[0] if edges else None
            action = next((i for i in range(release, min(release+30,stop)+1)
                           if player[i]['action_kind'] != player[first]['action_kind']), None) if release else None
            out = dict(charge_first=first, started_in_capture=first>seq[0], mission_id=guests[first]['mission_id'],
                       weapon=player[first]['melee_item'], last_level_two=last,
                       ring_actor_frames_while_full=(sum(player[i]['ryu_fx_b0']>0 for i in hold)
                           if 'ryu_fx_b0' in player[first] else None),
                       release_flip=release, observed_hold_flips=release-first if release else None,
                       action_change_flip=action, next_action=player[action]['action_kind'] if action else None)
            if release:
                out['before_full'] = window(max(seq[0],first-60),first-1)
                out['full_before_release'] = window(first,release-1)
                out['after_release'] = window(release,min(release+119,stop))
                out['first_30_after_release'] = window(release,min(release+29,stop))
            charges.append(out)

    landings = []
    for seq in alma_runs:
        for start in seq[1:]:
            if (player[start]['melee_item'] not in (1, 0xc9) or player[start-1]['action_kind'] != 11
                    or player[start]['action_kind'] != 111):
                continue
            # Recurrent Dragon Sword grab animation in the real Alma trace.
            # Y is sampled once/flip: the sharp descent is an impact candidate.
            impact = next((i for i in range(start+55, min(seq[-1], start+99)+1)
                           if player[i]['action_kind'] in (111,112) and height(player[i])-height(player[i-1]) < -.65), None)
            if impact is None or any(player[i]['action_kind'] not in (111,112) for i in range(start,impact+1)):
                continue
            before = window(max(seq[0], impact-60), impact-31)
            descent = window(impact-15, impact-1)
            hit = window(impact, min(seq[-1], impact+29))
            landings.append(dict(animation_start=start, impact_candidate=impact,
                alive_segment_start=seq[0], first_in_segment=not landings or landings[-1]['alive_segment_start'] != seq[0],
                melee_item=player[start]['melee_item'], before=before, impact=hit,
                descent=descent, recovery=window(impact+35,min(seq[-1],impact+64)),
                fx_types_new_vs_descent=(sorted(set(hit['active_fx_types']) - set(descent['active_fx_types']))
                    if descent['active_fx_types'] is not None and hit['active_fx_types'] is not None else None)))

    starts = []
    presses = sorted(rows['J'], key=lambda j: j['new_game_press_us'])
    for seq in segments(game):
        start = seq[0]
        press = next((j for j in reversed(presses) if j['last_guest_flip'] <= start and
                      0 <= game[start]['time_us']-j['new_game_press_us'] < 10_000_000), None)
        entry = dict(story_first_flip=start, first_120=window(start,min(start+119,seq[-1])))
        if press:
            entry['menu_press_us'] = press['new_game_press_us']
            entry['press_to_story_us'] = game[start]['time_us']-press['new_game_press_us']
        first_content = start+1
        while first_content in game and first_content in rendered and rendered[first_content]['draw_calls'] <= 2:
            first_content += 1
        if first_content > start+1:
            entry['low_draw_transition'] = window(start+1,first_content-1)
            if first_content in rendered and first_content in game and rendered[first_content]['draw_calls'] > 2:
                entry['story_to_next_content_us'] = game[first_content]['time_us']-game[start]['time_us']
        # Chapter 1's waterfall intro (event 0x6e) ends as gameplay resumes.
        control = next((i for i in seq if i-1 in player and i in player and
                        player[i-1]['event_id']==0x6e and player[i]['event_id']==0xffff), None)
        if control:
            entry['after_waterfall_intro'] = [window(i,min(i+29,seq[-1]))
                for i in range(control,min(control+300,seq[-1]+1),30)]
        starts.append(entry)
    windows = []
    if requested_windows:
        timeline = PresentTimeline(rows)
    for first,last in requested_windows:
        recorded = [g for f,g in guests.items() if first<=f<=last]
        intervals = [timeline.window(guests[run[0]-1]['time_us'], guests[run[-1]]['time_us'])
                     for run in segments(g['guest_flip'] for g in recorded if g['guest_flip']-1 in guests)]
        windows.append(dict(present_timeline=intervals, mission_modes=sorted({(g['mission_id'],g['mode']) for g in recorded}),
                            event_ids=sorted({g['event_id'] for g in recorded if 'event_id' in g}),
                            **window(first,last)))
    return dict(version=session['version'], dropped=dict(session['lost']), malformed=session['malformed'],
                clocks=rows['C'][-1] if rows['C'] else None, menu_presses=presses,
                display_clock=dict(gpu_ns_per_log_unit=measured_scale,
                                   successful_calibrations=sum(k['result']==0 and k['gpu_ns']>0 for k in rows.get('K', ())),
                                   vsync_wakes=len(rows.get('S', ())), vsync_errors=session.get('vsync_errors', []))
                              if 'K' in session['schemas'] else None,
                main_menu_masks=main_menu_masks(rows, queries, rendered, measured_scale) if 'E' in session['schemas'] else None,
                story_entries=starts, second_charges=charges, izuna_landing_candidates=landings, windows=windows)
