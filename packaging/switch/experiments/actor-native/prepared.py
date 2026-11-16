"""Worker prepares masked blocks before publication. Only use a whole block
if it ends at this exact due event; a changed poll phase falls back to the
ordered raw journal for that interval. Original poll service is unchanged."""
from pathlib import Path
import subprocess as sp,sys
here=Path(__file__).resolve().parent
s=sp.check_output([sys.executable,here/'compact-live.py'],text=True)
a=s.index('static void *run_actor(');b=s.index('\n',a)
assert 'return NULL;' in s[a:b]
s=s[:a]+'''static struct patch prepatch[131072];static unsigned rend[8193],pend[8193],btick[8193],blocks,preok;
static void prepare_blocks(void){
 static struct packer p;p.used=0;memset(p.entry,0,sizeof p.entry);blocks=0;preok=0;unsigned cur=0,sum=0;
 if(err||events>8191)return;
 for(unsigned t=1;t<=events;t++){if((ticks-events+t)%64 && t!=events)continue;
  while(cur<nlog && (t==events||write_log[cur][0]<t)){uint32_t *e=write_log[cur++];
   if(!store_byte(&p,e[1],e[2]))return;}
  if(sum+p.used>131072)return;memcpy(prepatch+sum,p.out,p.used*sizeof(*prepatch));sum+=p.used;
  rend[blocks]=cur;pend[blocks]=sum;btick[blocks++]=t;
  for(unsigned k=0;k<p.used;k++)p.entry[p.touched[k]]=0;p.used=0;
 }preok=1;}
static void retire_prepared(unsigned b,uint8_t*ram){
 for(unsigned k=b?pend[b-1]:0;k<pend[b];k++){struct patch p=prepatch[k];uint8_t*d=ram+p.address;
  if(p.mask==15)memcpy(d,&p.value,4);else for(unsigned j=0;j<4;j++)if(p.mask&(1u<<j))d[j]=p.value>>(8*j);}}
'''+s[a:b].replace('return NULL;', 'prepare_blocks();return NULL;')+s[b:]
s=s.replace('unsigned cursor=0,flushes=0,retired=0;', 'unsigned cursor=0,flushes=0,retired=0,block=0,fast=0;')
tag='    while(cursor<nlog&&write_log[cursor][0]<k)'
s=s.replace(tag,'''    while(block<blocks&&btick[block]<k)block++;
    if(preok&&block<blocks&&btick[block]==k&&k<events&&cursor==(block?rend[block-1]:0)){
      retire_prepared(block,base);cursor=rend[block];retired+=pend[block]-(block?pend[block-1]:0);fast++;block++;
    }else
'''+tag)
s=s.replace('masked_words=%u', 'masked_words=%u prepared=%u').replace('flushes,nlog,retired);','flushes,nlog,retired,fast);')
print(s)
