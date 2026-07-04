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
