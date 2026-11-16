"""Extend the ARM four-dot fast path, preserving the order visible to the guest.
Compile only unit 39, using the same set of private callee symbols as full-guest."""
from pathlib import Path
import os,re,subprocess as sp
def header(s):
 old='    if (a < b + (column ? 52 : 16) && b < a + 64) return false;'
 assert s.count(old)==1
 s=s.replace(old,'''    if (a < b + (column ? 52 : 16) && b < a + 64) {
        // This in-place shape overwrites only an already-consumed
        // component of the matrix. For the others, the scalar path can see
        // an earlier output as a later input; never vectorize those cases.
        if (column || b!=a) return false;
    }''')
 a=s.index('    uint32x4_t valid =');b=s.index('    /* The last lane',a)
 return s[:a]+'''    if (!(g_fp_control_word & 0x300u)) {
        uint32x4_t valid = ngb_arm_dot_range(vld1q_f32(k));
        for (unsigned i=0;i<4;++i)valid=vandq_u32(valid,ngb_arm_dot_range(row.val[i]));
        if (!vminvq_u32(valid)) return false;
    } else {
        // Every product and sum of four finite binary32 inputs fits the
        // binary64 exponent range. No binary32 range test is needed here.
        for(unsigned i=0;i<4;++i) if((double)k[i]!=g_fp_stack[(t+3-i)&7]) return false;
        uint32x4_t mx=vandq_u32(vreinterpretq_u32_f32(vld1q_f32(k)),vdupq_n_u32(0x7fffffff));
        for(unsigned i=0;i<4;i++)
            mx=vmaxq_u32(mx,vandq_u32(vreinterpretq_u32_f32(row.val[i]),vdupq_n_u32(0x7fffffff)));
        if(vmaxvq_u32(mx)>=0x7f800000u) return false;
    }
'''+s[b:]
if __name__=='__main__':
 root=Path('/work');base=root/'build/switch-runtime';abi=root/'packaging/switch/arm-registers';d=base/'core-perf/opening-matrix-row';d.mkdir(exist_ok=True)
 os.environ['NGB_REG_OUT']=str(d)
 (d/'arm_math.h').write_text(header((abi.parent/'runtime/arm_math.h').read_text()))
 name='recomp_0039.c';(d/name).write_bytes((base/'gen'/name).read_bytes())
 s=(abi/'compile.py').read_text()
 s=re.sub(r'^ns=\[[\d,]+\]$', 'ns=list(range(47))',s,flags=re.M)
 num=r'(?:sub_|d3d_orig_)[0-9A-F]+'
 s=s.replace(num,'(?:'+num+'|xbe_entry_point)')
 s=s[:s.index("f=o/'entry.S'")];s=s.replace('ex.map(build,units)','ex.map(build,["recomp_0039.c"])')
 k=' sp.run(c,cwd=w,check=True)';assert s.count(k)==1
 exec(compile(s.replace(k,' c[-1]=str(o/n)\n'+k),'row-build','exec'),{})
 exec(compile((abi/'gates.py').read_text(),'row-gates','exec'),{})
 for pat in ('*.s','recomp_*.c'):
  for f in d.glob(pat):f.unlink()
