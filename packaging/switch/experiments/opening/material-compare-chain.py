"""Keep one checked linear material pointer across six unchanged-state comparisons.
Branch to the original first changed setter, with its original registers and flags.
"""
from pathlib import Path
import re,runpy
def transform(s,u):
 header='loc_0030B8BC: ;'
 assert s.count(header)==1
 addr='uint32_t first=esi+0x30u;'
 guard='if(!(first&3u) && (first&4095u)<=4095u-20 && first+20u<reg_ends[first>>12])'
 lines=[addr,guard+'{volatile const uint32_t *words=(volatile const uint32_t*)(ngb_fast_ram+(first&0x7fffffffu));']
 # Same-page constraint also prevents the first+20 wrapping through zero.
 for i,(start,changed,end) in enumerate([
  ('B8BC','B8C7','B8D2'),('B8D2','B8DD','B8E8'),('B8E8','B8F3','B90B'),
  ('B90B','B916','B92E'),('B92E','B939','B944'),('B944','B94F','B967')]):
  block=s.split('loc_0030'+start+': ;\n',1)[1].split('\nloc_0030'+changed+': ;',1)[0]
  old=f'MEM32(esi + 0x{0x30+i*4:X})'; assert block.count(old)==1
  branch='if (CMP_EQ(_fa, _fb)) goto loc_0030'+end+';'
  assert block.count(branch)==1 and 'ngb_guest_block_poll' not in block and block.count('MEM32(')==3 # one mention in generated comment
  lines.append(block.replace(old,f'words[{i}]').replace(branch,'if (!CMP_EQ(_fa, _fb)) goto loc_0030'+changed+';').replace('/* je: equal / zero */',''))
 lines.append('goto loc_0030B967;}')
 return s.replace(header,header+'\n{'+''.join(lines)+'}\n')
if __name__=='__main__':runpy.run_path(str(Path(__file__).with_name('model-copy.py')))['build']('material-compare-chain',[(False,[28])],transform)
