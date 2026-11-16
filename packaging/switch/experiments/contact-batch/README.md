Offline experiments on the candidate loop in the original 0013D330 function.
No experiment in this directory is enabled in the Switch build.

- bounds.cpp checks the recorded, complete narrow-phase inputs against both
  the original float plane tests and the replay's actual return. Its input
  files are local and are not distributable. The fast rejection's input and
  result rates describe that capture only.
- check.inc and shadow.py compile an observer into the original parent loop.
  The observer never suppresses the real collision query. The host driver
  compares its prediction to EAX after the original call.
- leaf.h and leaf.py test the full no-contact path, including the original
  register, memory and interrupt bookkeeping. Run the full architectural
  shadow check before treating performance numbers as meaningful. Do not use
  this as a draw or collision suppression switch.
