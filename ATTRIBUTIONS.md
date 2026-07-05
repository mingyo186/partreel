# Attributions

PartReel includes assets imported from third-party open libraries. Imported
parts keep their **original license** (never relicensed) and carry a
machine-readable `import` block in their metadata (source repository, commit,
files, and the list of modifications we made). Every imported part passed the
same automated quality gates as our generated parts before publication.

## SparkFun Electronics — CC-BY-4.0

Parts with `origin: "imported"` and family `SparkFun *` come from the
[SparkFun KiCad Libraries](https://github.com/sparkfun/SparkFun-KiCad-Libraries)
(commit `2423e36aead98c5756ae09366e0388ff21a82808`), © SparkFun Electronics,
licensed [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) per the
repository README (snapshot archived at import time).

Modifications made during import (recorded per part in `meta.json → import.modifications`):
single-symbol extraction from library files, 3D model path rewrite,
auto-generated courtyard where missing (IPC-7351 bbox+0.25mm), and single-color
GLB preview meshes tessellated from the original STEP models.

Thank you, SparkFun, for keeping your library open.

## CERN — CERN-OHL-P-2.0

Parts with family `CERN *` come from the
[CERN KiCad Libraries](https://gitlab.com/ohwr/cern-kicad-libs)
(commit `53054c17`), © CERN, licensed
[CERN-OHL-P-2.0](LICENSES/CERN-OHL-P-2.0.txt). Per §3.3 each part's
`meta.json → import` records the modification notice and date.
Modifications: single-symbol extraction, dead 3D-model reference removal
(upstream ships no 3D — these parts are published as **verified-2D**),
auto-generated courtyard where missing. Not endorsed by CERN.

## ai03 MX_V2 — MIT

Parts with family `ai03 *` come from the
[ai03 MX_V2 keyboard switch library](https://github.com/ai03-2725/MX_V2)
(commit `0b379ee`), © ai03, licensed [MIT](LICENSES/MIT-ai03.txt) — footprints
designed from scratch from official switch datasheets per the upstream README.
Modifications (recorded per part in `meta.json → import.modifications`):
schematic symbols authored by PartReel (upstream pairs with stock KiCad
symbols), Dwgs.User outlines remapped to F.Fab, minimal silk pin-1 marker,
auto-generated courtyard where missing, socket-only 3D references removed
(parts published as **verified-2D**). Thank you, ai03.
