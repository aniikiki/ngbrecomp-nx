"""Differentially exercise the private block predicate, including wraps,
public polls, grouped poll-free increments and invalidation inside callbacks."""
from random import Random
r=Random(1785); U=(1<<64)-1
class State:
 def __init__(self,start):self.t=start;self.mask=3;self.pending=0;self.deadline=0;self.events=[]
 def post(self):self.pending+=1;self.deadline=0
 def service(self):
  self.events.append(self.t)
  if self.pending and self.t&1:self.pending-=1
  if self.t%61==0 and self.pending<4:self.post()
 def tick(self,fast):
  self.t=(self.t+1)&U
  due=not(self.t&self.mask) or self.pending
  if fast:
   if self.t>=self.deadline or not self.t:
    self.deadline=0 if self.pending else ((self.t|self.mask)+1)&U
   else:assert not due;return
  if due:self.service()
for start in (0,U-1024,128):
 a,b=State(start),State(start)
 for n in range(150000):
  op=r.randrange(16)
  if op==0:
   for s in (a,b):s.post()
  if op==1:
   for s in (a,b):s.mask={3:63,63:3}[s.mask];s.deadline=0
  if op==2 and not a.pending and a.mask-(a.t&a.mask)>=3:
   for s in (a,b):s.t=(s.t+3)&U
  else:a.tick(False);b.tick(op>4)
  assert (a.t,a.pending)==(b.t,b.pending)
 assert a.events==b.events
print('450000 mixed operations: ticket and callback sequences identical')
