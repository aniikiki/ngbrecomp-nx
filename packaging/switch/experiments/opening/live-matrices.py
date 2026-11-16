"""Feed contiguous live guest transforms into the recorder once. Compare the
actual source bytes against the last submitted values instead of copying into
State and rescanning. Publish g_state too: other calls can observe it."""
from pathlib import Path
def install(p,audit):
 root=Path('/work')
 decl='extern "C" {extern void *op_mat_state;extern const unsigned char *op_mat_live;}\n'
 s=(root/'src/d3d/hle.cpp').read_text()
 k='    SyncDeferred();'; assert s.count(k)==1
 # Only enable synchronous recorder consumption for a real threaded draw.
 s=s.replace(k,'    op_mat_state=nullptr;op_mat_live=nullptr;\n'+k)
 k='    if (dev) {\n        for (uint32_t t = 0; t < 10; t++) {'
 assert s.count(k)==1
 s=s.replace(k,'''    if (dev && __atomic_load_n(&ngb_render_threaded,__ATOMIC_RELAXED)) {
        // A host pointer for the whole interval must agree with both endpoints;
        // only low physical RAM is contiguous here. No callback occurs between
        // SyncDeferred and recording this draw.
        if(dev<0x04000000u-0xF44u && dev>=0x8000u) {
            const auto *first=static_cast<const unsigned char*>(DirectPage(dev+0xC60,0x2e4));
            if(first) {op_mat_state=&g_state;op_mat_live=first;return;}
        }
    }
'''+k)
 k='    if (g_backend) g_backend->Draw(g_state, prim, start, count, indices);'
 assert s.count(k)==1;s=s.replace(k,k+'\n    op_mat_state=nullptr;op_mat_live=nullptr;')
 if audit:s=s.replace('op_mat_live=first;return;', 'op_mat_live=first;')
 p.add('hle.cpp',decl+'extern "C" {void *op_mat_state;const unsigned char *op_mat_live;}\n'+s)
 s=(root/'src/d3d/gpu/threaded.cpp').read_text();k='        if (!std::memcmp(previous, now + r.off, r.len)) return;'
 assert s.count(k)==1
 s=s.replace(k,'''        if constexpr(I>=9 && I<=12) {
            if (op_mat_state==now && op_mat_live) {
                constexpr size_t off=I==9?0:I==10?128:I==11?384:672;
                const uint8_t *live=op_mat_live+off;
                AUDIT
                // g_state can have been updated by SetTransform between draws.
                // Publish unconditionally, even if sent_ already equals live.
                if(!std::memcmp(previous,live,r.len)){
                    std::memcpy(static_cast<uint8_t*>(op_mat_state)+r.off,live,r.len);
                    return;
                }
                std::memcpy(static_cast<uint8_t*>(op_mat_state)+r.off,live,r.len);
                WriteDelta(r.off,now,r.len);
                return;
            }
        }
'''.replace('AUDIT','static bool visited=false;if(!visited){fprintf(stderr, "[MATRIX_AUDIT] group=%u first live comparison\\n",unsigned(I));visited=true;}if(std::memcmp(live,now+r.off,r.len)) std::abort();' if audit else '')+k)
 p.add('threaded.cpp',decl+s)
