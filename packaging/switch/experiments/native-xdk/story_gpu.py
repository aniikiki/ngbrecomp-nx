"""Apply native-XDK capture switches after the renderer transforms."""
from pathlib import Path
import re


def instrument(source, *, wave=True):
    def replace(before, after):
        nonlocal source
        assert source.count(before) == 1, before
        source = source.replace(before, after)

    # The game flag enables this journal even if the game CSV fails to open.
    # The playable binary caches have their own unconditional lifetime.
    journal = 'material_log_ = std::fopen((dir + "/materials.csv").c_str(), "a");'
    replace(journal, 'if (ngb_game_diagnostics_requested) ' + journal)
    if not wave:
        return source
    # Preserve both endpoints on the device clock as well as the existing
    # interval union. A query's CPU read time can be several frames later.
    replace('    uint32_t cp_tag[2]{};', '    uint32_t cp_tag[2]{}, screen_part_[2]{~0u, ~0u};')
    replace('struct Span { uint64_t start{}, end{}; bool valid{}; };',
            'struct Span { uint64_t start{}, end{}; bool valid{}, writes_screen{}; };')
    replace('(t[1] - origin) & ts_mask_, true};\n            }',
            '(t[1] - origin) & ts_mask_, true};\n            }\n            spans[part].writes_screen = part == screen_part_[slot];')
    replace('        ts_count_[slot] = 0;', '        screen_part_[slot] = ~0u;\n        ts_count_[slot] = 0;')
    replace("ns/1000,span.valid};ngb_combat_row('Q',v,4);",
            """ns/1000,span.valid,
                span.valid ? uint64_t(double((origin + span.start) & ts_mask_) * ts_period_ns_) : 0,
                span.valid ? uint64_t(double((origin + span.end) & ts_mask_) * ts_period_ns_) : 0,
                span.writes_screen};
                ngb_combat_row('Q',v,sizeof v/sizeof *v);""")
    submit = '        result = d_.vkQueueSubmit(queue_, 1, &si, fence);'
    replace(submit, submit + '''
#ifdef NGB_GPU_PRESENT
        // QueueScanout has recorded the write to the shared screen image.
        // Stamp it before dropping the same queue lock used by the UI blit.
        if (result == VK_SUCCESS && screen_queued_ && ngb_combat_enabled) {
            screen_part_[slot_] = chunk_;
            switch_display::note_screen_write(screen_picture_.image, frame_ + 1);
        }
#endif''')
    replace('    struct ReadbackDiag {',
            Path(__file__).with_suffix('.inc').read_text() + '\n    struct ReadbackDiag {')
    replace('tci.queryCount = kFrameChunks * 2;',
            'tci.queryCount = ngb_combat_enabled ? kPhaseBase + 2 * kPhasePairs : kWaveBase;')
    reset = '        d_.vkCmdResetQueryPool(cmd_, ts_pool_[slot_], chunk_ * 2, 2);'
    replace(reset, reset + '''
        if (!chunk_ && ngb_combat_enabled) {
            d_.vkCmdResetQueryPool(cmd_, ts_pool_[slot_], kWaveBase, 2 * kWavePairs);
            if (phase_reset_[slot_]) {
                d_.vkCmdResetQueryPool(cmd_, ts_pool_[slot_], kPhaseBase, phase_reset_[slot_]);
                phase_reset_[slot_] = 0;
            }
        }''')
    active = '    cp_on=ngb_combat_enabled && ngb_combat_active();'
    replace(active, active + '\n    phase_probe_ = cp_on && ((frame_ + 2) & 3) == 2;')
    close = 'void VulkanBackend::EndRendering() {\n    if (!rendering_) return;'
    replace(close, close + '\n    if (phase_probe_) PhaseEnd();')
    replace('    void TsEnd() {', '    void TsEnd() {\n        if (phase_probe_) PhaseEnd();')
    # This anchor also exists in the coverage replay with occlusion queries.
    draw = '    if (a.index_count) {\n        d_.vkCmdBindIndexBuffer'
    replace(draw, '''    if (phase_probe_) {
        Phase kind;
        if (history && from_target[0]) kind = History;
        else if (glow_stage >= 0 || glow_pass) kind = Composite;
        else if (!rt || rt->gw < 640 || rt->gh < 448) kind = Offscreen;
        else if (a.pretransformed && from_target[0] && !info[0].shadow) kind = Composite;
        else if (!k.blend) kind = Opaque;
        else kind = k.dst == 1 && k.op == 0x8006 ? Additive : Alpha;
        EffectPass pass = OtherPass;
        if (rt && rt->gw >= 640 && rt->gh >= 448 && count == 4 && k.blend && k.op == 0x8006) {
            TextureDesc input;
            if (a.pretransformed && from_target[0] && Describe(s.textures[0], input)) {
                if (prim == 6 && k.src == 0x302 && k.dst == 0x303 && input.width == 512 && input.height == 512)
                    pass = HistoryMix512;
                else if (prim == 9 && k.src == 1 && k.dst == 1 && input.width == 128 && input.height == 128 &&
                         !from_target[1] && !from_target[2] && !from_target[3])
                    pass = AddFrom128;
            } else if (!a.pretransformed && prim == 6 && k.src == 0x302 && k.dst == 1 &&
                       !from_target[0] && from_target[1] && !from_target[2] && !from_target[3] &&
                       WaveTextureKind(s, views[0]) == 1) {
                pass = RingWithTarget;
            }
        }
        PhaseDraw(kind, k, s, views, from_target, pass);
    }
    uint32_t wave_query = ~0u;
    if (cp_on && rt && rt->gw >= 640 && prim == 6 && (count == 4 || count == 14) &&
        k.blend && k.src == 0x302 && k.dst == 1 && !from_target[0])
        wave_query = WaveBegin(s, views[0]);
''' + draw)
    end = '        d_.vkCmdDraw(cmd_, a.draw_count, 1, 0, 0);\n    }'
    replace(end, end + '''
    if (wave_query != ~0u)
        d_.vkCmdWriteTimestamp(cmd_, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, ts_pool_[slot_], wave_query + 1);''')
    # Both the 720p GPU route and the software fallback have a transfer here.
    # Narrow the anchors to QueueScanout so an unrelated transfer cannot match.
    first = source.index('void VulkanBackend::QueueScanout(')
    last = source.index('\n}', first)
    scan = source[first:last]
    barrier = 'Barrier(t->img, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL);'
    assert scan.count(barrier) == 2
    scan = re.sub(r'^( +)' + re.escape(barrier), r'\1if (phase_probe_) PhaseBegin({Scanout});\n\1' + barrier, scan, flags=re.M)
    source = source[:first] + scan + source[last:]
    replace('    QueueScanout(front);', '    QueueScanout(front);\n    if (phase_probe_) PhaseEnd();')
    feedback = '            Barrier(t.img, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL);\n            Barrier(t.fb,'
    replace(feedback, '''            if (phase_probe_) {
                PhaseBegin({Feedback});
                phase_[slot_].feedback_pixels += uint64_t(t.img.w) * t.img.h;
            }
''' + feedback)
    replace('            draw_feedback_ready_ = true;',
            '            if (phase_probe_) PhaseEnd();\n            draw_feedback_ready_ = true;')
    transfer = '    Barrier(a->img, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL);\n    Barrier(b->img,'
    replace(transfer, '    if (phase_probe_) PhaseBegin({SurfaceCopy});\n' + transfer)
    end_copy = 'VK_FILTER_LINEAR);\n    b->drawn = true;'
    replace(end_copy, '''VK_FILTER_LINEAR);
    if (phase_probe_) {
        PhaseEnd();
        for (const auto& r : rs)
            phase_[slot_].copy_pixels += uint64_t(std::abs(r.dstOffsets[1].x - r.dstOffsets[0].x)) *
                                         std::abs(r.dstOffsets[1].y - r.dstOffsets[0].y);
    }
    b->drawn = true;''')
    replace('    TsRead(slot);', '    TsRead(slot);\n    if (ngb_combat_enabled) { WaveRead(slot); PhaseRead(slot); }')
    return source
