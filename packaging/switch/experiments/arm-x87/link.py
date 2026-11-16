from pathlib import Path
import sys
h=Path(__file__).resolve().parent;mode=sys.argv[1];assert mode in ('integer','fcvt')
s=(h.parent/'arm-bias/link.py').read_text().replace("d=BASE/'opt050/bias';p=NativeProbe('bias')",f"d=BASE/'opt050/x87-{mode}';p=NativeProbe('x87-{mode}')")
a=s.index("for n in ('vm.c'");b=s.index('public=set',a);s=s[:a]+s[b:]
exec(compile(s,'x87-link','exec'))
