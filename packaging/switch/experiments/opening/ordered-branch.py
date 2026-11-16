"""Use the original float comparison for JP after LAHF; still produce guest AH and flags."""
from pathlib import Path
import re,runpy
def transform(s,u):
    lines=s.splitlines(True); eligible=False; mask=False; out=[]; producer=0
    for line in lines:
        if '/* lahf (ucomiss) */' in line:
            producer=len(out)
            eligible=('((_fca == _fcb || (_fca != _fca || _fcb != _fcb))) ? 0x40u' in line and '((_fca != _fca || _fcb != _fcb)) ? 0x04u' in line);mask=False
        elif eligible and '_fa = (uint32_t)(HI8(eax)) & 0xFFu; _fb = (uint32_t)(0x44) & 0xFFu;' in line:mask=True
        elif eligible and mask and 'if (RECOMP_PARITY8((_fa) & (_fb))) goto' in line:
            out[producer]='    { unsigned ah; __asm__("fcmp %d[a], %d[b]\\n\\tcsel %w[r], %w[eq], %w[gt], eq\\n\\tcsel %w[r], %w[lt], %w[r], mi\\n\\tcsel %w[r], %w[un], %w[r], vs" : [r] "=&r"(ah) : [a] "w"(_fca), [b] "w"(_fcb), [eq] "r"(0x42u), [gt] "r"(2u), [lt] "r"(3u), [un] "r"(0x47u) : "cc"); eax=(eax & 0xffff00ffu)|(ah<<8); }\n'
            line=line.replace('RECOMP_PARITY8((_fa) & (_fb))','((_fa & 0x44u) != 0x40u)');eligible=False
        elif eligible and mask and (line.strip().startswith('_fas = (int32_t)(int8_t)(_fa);') or line.strip() in ('PUSH32(esp, esi);','PUSH32(esp, edi);','MEM32(esp + 8) = 1;')):pass
        else:eligible=False
        out.append(line)
    return ''.join(out)
if __name__=='__main__':
    base=Path('build/switch-runtime/gen');found={}
    for f in sorted(base.glob('recomp_*.c')):
        s=f.read_text();n=transform(s,0).count('if (((_fa & 0x44u) != 0x40u)) goto')-s.count('if (((_fa & 0x44u) != 0x40u)) goto')
        if n:found[f.name]=n
    print('eligible',sum(found.values()),'sites in',len(found),'units; unit 28:',found.get('recomp_0028.c'))
    runpy.run_path(str(Path(__file__).with_name('model-copy.py')))['build']('ordered-branch',[(False,[28])],transform)
