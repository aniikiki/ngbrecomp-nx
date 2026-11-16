"""One-time DBI install. Resume by skipping finalized files; never merge a partial staged RomFS."""
import argparse
from ftplib import FTP,error_perm
from pathlib import Path
import time
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('address');p.add_argument('--port',type=int,default=5000)
p.add_argument('--source',type=Path,default=Path('game_files'))
args=p.parse_args()
src=args.source
assert (src/'default.xbe').is_file() and (src/'movie/2_VI_WIDE_B.sfd').stat().st_size>1048576 and not (src/'.ngb-disc').exists()
files=sorted(f for f in src.rglob('*') if f.is_file() and not any(k.startswith('.') for k in f.relative_to(src).parts))
total=sum(f.stat().st_size for f in files)
def install():
 with FTP(timeout=45) as ftp:
  ftp.connect(args.address,args.port);ftp.login();ftp.cwd('/switch/ngb-runtime')
  def listing():return {s.rstrip('/').split('/')[-1] for s in ftp.nlst()}
  names=listing()
  # An interrupted first install must not become the live disc.
  if 'disc' in names:target='disc'
  else:target='disc.installing'
  if target not in names:ftp.mkd(target)
  ftp.cwd(target)
  if '.ngb-disc' in listing():raise RuntimeError('Refusing to mix a packed catalog with full disc files')
  def size(name):
   ftp.voidcmd('TYPE I')
   try:return ftp.size(name)
   except error_perm as e:
    if str(e).startswith('550'):return None
    raise
  made=set();done=0
  for f in files:
   for parent in reversed(f.relative_to(src).parents):
    if parent==Path('.') or parent in made:continue
    try:ftp.mkd(parent.as_posix())
    except error_perm:
     saved=ftp.pwd();ftp.cwd(parent.as_posix());ftp.cwd(saved)
    made.add(parent)
   n=f.relative_to(src).as_posix();length=f.stat().st_size;old=size(n)
   if old!=length:
    if old is not None:raise RuntimeError('Conflicting existing disc file: '+n)
    with f.open('rb') as stream:ftp.storbinary('STOR '+n+'.ngb-upload',stream,262144)
    if size(n+'.ngb-upload')!=length:raise RuntimeError('Incomplete upload: '+n)
    ftp.rename(n+'.ngb-upload',n)
   done+=length
   print(f'{done/total:6.1%} {n}',flush=True)
  if target!='disc':
   ftp.cwd('..');ftp.rename(target,'disc')
  print('Ready:',len(files),'files,',total,'bytes',flush=True)
for attempt in range(3):
 try:install();break
 except (OSError,EOFError):
  if attempt==2:raise
  time.sleep(2)
