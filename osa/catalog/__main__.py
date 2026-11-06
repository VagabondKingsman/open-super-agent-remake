"""python -m osa.catalog：检查所有应用清单。有错时逐个列出来，退出码为 1（CI 里也跑）。"""

from ..i18n import s as _s
import sys
from . import LOCAL, _files, _show, load

items, errors = load()
for e in errors:
    print("✗", e)
local = [_show(p) for p in _files().values() if p.parent == LOCAL]
if local:
    print(_s('audit_62e8d3faa8', v0=_show(LOCAL), v1=', '.join(local)))
print(_s('audit_eb7aa0ca17', v0=len(items)) + (_s('audit_25df029b15', v0=len(errors)) if errors else _s('audit_9ccce06625')))
sys.exit(1 if errors else 0)
