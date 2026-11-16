"""Partition actual decoder visits by whether this pass handles the word."""
from pathlib import Path
import re,sys
s=Path(sys.argv[1]).read_text()
if '[RESULT] status=1 reason=verified 120 original demo frames' not in s:
    raise SystemExit('incomplete opening')
rows=re.findall(r'^\[CMD_PASS\] (\d+) (\d+) ([0-9 ]+)$',s,re.M)
assert [(int(f),int(i)) for f,i,_ in rows]==[(f,i) for f in (30,120) for i in range(3)]
for f,i,data in rows:
    i=int(i);n=list(map(int,data.split()));assert len(n)==13
    print(f'end={f} pass={i+1} decoded={sum(n[4*i:4*i+4])} other_pass_opcode={sum(n[:12])-sum(n[4*i:4*i+4])} other_word={n[-1]} total={sum(n)}')
