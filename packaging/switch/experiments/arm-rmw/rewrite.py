"""Fold the generated x86 memory RMW and flags into one checked RAM access.
Only handle a single integer operand. In particular, never substitute the
post-store read for a subsequent *different* x86 compare instruction."""
import re
pattern=re.compile(r'^    (?P<dest>MEM(?P<w>8|16|32)\((?P<addr>[a-zA-Z_0-9 +*\-]+)\)) = (?P=dest) (?P<op>[+&|^\-]) (?P<rhs>0x[\dA-Fa-f]+u?|[0-9]+|e(?:ax|bx|cx|dx|si|di|bp|sp));\n(?P<flags>    _fa = \(uint32_t\)\((?P=dest)\) & 0x[0-9A-F]+u;[^\n]*(?:\n    _fas = [^\n]*)?)',re.M)
def rewrite(m):
 d,w,a,op,rhs,flags=(m[k] for k in ('dest','w','addr','op','rhs','flags'))
 if not any('/* '+word+' result' in flags for word in ['inc','dec','add','sub','or','and','xor']):return m[0]
 if '_fb = (uint32_t)' in flags:return m[0]
 t='uint'+w+'_t';w=int(w)//8
 original=m[0].rstrip()
 return f'''    {{
        uint32_t va_={a};
        if ((va_ & 4095u)+{w}u <= ngb_fast_page_bytes[va_>>12]) {{
            {t} in_,out_;void *p_=ngb_fast_ram+(va_&0x7fffffffu);
            __builtin_memcpy(&in_,p_,{w});
            out_=({t})((uint32_t)in_ {op} ({rhs}));
            __builtin_memcpy(p_,&out_,{w});
{flags.replace(d,'out_')}
        }} else {{
{original}
        }}
    }}'''
