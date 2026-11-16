"""Time the thirteen direct calls in the model state setup routine."""
from pathlib import Path
import runpy
p=Path(__file__).resolve().parent
wrap=runpy.run_path(str(p/'mesh-cost.py'))['transform']
runpy.run_path(str(p/'model-copy.py'))['build']('setup-cost',[(False,[28])],lambda s,u:wrap(s,u,"0030B7E0",13))
