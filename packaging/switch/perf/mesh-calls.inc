/* Offline only. Capture calls as well as the zero-call submissions. */
static FILE *mesh_calls;
static unsigned mesh_call_frame, mesh_call_active;
static void mesh_event(uint32_t type, uint32_t a, uint32_t b)
{
    uint32_t event[3] = {type, a, b};
    if (fwrite(event, sizeof(event), 1, mesh_calls) != 1) abort();
}
static void mesh_call_boundary(int enter)
{
    if (enter && !index_time.mesh_depth && mesh_call_frame >= 1800 && mesh_call_frame < 1920) {
        if (!mesh_calls) {
            mesh_calls = fopen("/work/build/switch-runtime/core-perf/mesh-calls.bin", "wb");
            if (!mesh_calls) abort();
        }
        mesh_call_active = 1;
        mesh_event(1, mesh_call_frame + 1, MEM32(esp + 4));
    }
    if (!enter && index_time.mesh_depth == 1 && mesh_call_active) {
        mesh_event(3, 0, 0);
        mesh_call_active = 0;
    }
}
