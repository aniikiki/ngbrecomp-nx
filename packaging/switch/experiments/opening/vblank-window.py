"""Use a cached start timestamp to recognize the current field without division."""
def transform(s):
 k='static uint64_t frame;';assert s.count(k)==1
 s=s.replace(k,k+'\nstatic uint64_t frame_start_ns;')
 k='    uint64_t current = ngb_elapsed_ns() / 16666667u;';assert s.count(k)==1
 s=s.replace(k,'''    uint64_t sample = ngb_elapsed_ns();
    if (sample >= frame_start_ns && sample-frame_start_ns < 16666667u) return;
    uint64_t current = sample / 16666667u;''')
 # Publish after refresh, as the original frame update does, including re-entry.
 for k in ['    frame = current;','    frame = 0;','            frame = ngb_elapsed_ns() / 16666667u;']:
  assert s.count(k)==1;s=s.replace(k,k+'\n'+k[:len(k)-len(k.lstrip())]+'frame_start_ns = frame * 16666667ull;')
 return s
