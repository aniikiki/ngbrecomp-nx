"""Exercise the actual generated blocks, both native page-end table and baseline fallback."""
from pathlib import Path
p=Path(__file__).parent
s=(p/'cmd-page-run-check.py').read_text().replace("str(here/'cmd-page-run.py'))['transform'](src)[0]","str(here/'cmd-service-span.py'))['transform'](src,10)")
s=s.replace('static unsigned char ram[16384]','static unsigned reg_ends[4];static unsigned char ram[16384]')
s=s.replace('if(mode&2)ngb_fast_page_bytes[ecx/4096]=0;', 'if(mode&2){ngb_fast_page_bytes[ecx/4096]=0;reg_ends[ecx/4096]=0;}')
s=s.replace('calls=special=0;', 'for(unsigned j=0;j<4;j++)reg_ends[j]=ngb_fast_page_bytes[j]>=4?4096*j+ngb_fast_page_bytes[j]-3:0;calls=special=0;')
s=s.replace('ngb_guest_polls=test%13;', 'ngb_guest_polls=test&256?~0ull-test%13:test%13;').replace('ngb_pending_dpcs=(test>>6)&1;', 'if(test&8192)ngb_poll_mask=0x52;ngb_pending_dpcs=(test>>6)&1;')
exec(compile(s,'cmd-span-test','exec'),{'__file__':str(p/'cmd-page-run-check.py')})
