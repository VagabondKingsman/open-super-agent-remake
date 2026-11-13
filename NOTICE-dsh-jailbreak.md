# dsh-jailbreak attribution

`osa/charter.py` carries a condensed, rewritten version of the execution charter
from **dsh-jailbreak** `prompts/engine-v2.md`.

- Upstream: https://github.com/xqpsec/dsh-jailbreak
- Copyright (c) 2026 dsh-jailbreak contributors
- License of the prompt material: AGPL-3.0-only
- Gate material (`lib/gate.js`, `gate.json`, `scope.txt`): MIT, and the basis for
  the category table in `osa/charter.py`

Upstream's `NOTICE` asks a redistributor to keep the notice, both license files,
`SCOPE.md` and the repository link, and not to ship a build with the gate off by
default. The files are vendored verbatim under `licenses/dsh-jailbreak/` — the
AGPL text (`LICENSE`), the MIT gate license (`LICENSE-GATE`), `SCOPE.md` and
upstream's own `NOTICE` — as copied on 2026-11-13. Changing `osa/charter.py`
means re-checking those copies against upstream.

The charter text here is compressed and reformatted for OSA's prompt assembly;
the shape (scope belongs to the operator, artifact first, the refusal thought
is noise, foreign layers carry no weight, target normalisation, routing by
category) is upstream's.
