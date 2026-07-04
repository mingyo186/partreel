# Contributing to PartReel (for AI agents and humans)

PartReel accepts part contributions via GitHub PR. **CI quality gates auto-review every PR** — if gates pass and dimensions cite a source, it gets merged and published to the registry (site + API + MCP).

## What to contribute

A part = one directory under `library/<category>/<group>/<part_id>/` containing **just five source files** — SVG previews, the site page, the search index and the API entry are **built automatically by CI**:

| File | What |
|---|---|
| `<part_id>.kicad_mod` | KiCad footprint (s-expression, KiCad 7+) |
| `<part_id>.kicad_sym` | KiCad symbol library with one symbol |
| `<part_id>.step` | 3D model (valid solid; body must match footprint fab outline; no coplanar overlapping faces between solids; pins as individual bodies, not one merged strip) |
| `<part_id>.glb` | Colored web preview mesh (small, few KB; housing + metal as separate meshes) |
| `meta.json` | Metadata — see schema below |

`part_id`: lowercase `[a-z0-9_]+`, descriptive (e.g. `jst_ph_4pin`, `usb_c_16p`).

## meta.json schema (follow existing parts as reference)

Required: `id`, `name`, `category`, `family`, `manufacturer`, `mpn_pattern`,
`description`, `parameters` (incl. `pins` or `contacts`; `pitch_mm` for single-row),
`files` (all 6 files above), `formats`, `datasheet` (URL),
`dimensions_source` (**must cite where dimensions came from**), `verified` (bool),
`license` (`CC-BY-4.0`), `generated_by`, `keywords`.

## Quality gates (run locally before PR: `python generators/qa.py`)

1. `validate_kicad.py` — structure: pad count/numbering, pin1 at origin, pitch, layers F.Cu/F.SilkS/F.CrtYd/F.Fab
2. `check_overlap.py` — no overlapping text in SVG previews
3. `check_render.py` — files exist, SVG pad/outline counts match the kicad source, slots obround, part page/API present
4. Drawing rules (KLC): silk 0.12mm (≥0.2mm clearance from pads), fab 0.10mm + 1mm pin1 chamfer, courtyard 0.05mm solid lines
5. STEP must be a valid solid (`generators/validate_step.py`, FreeCAD)

## Rules

- **Dimensions must come from facts** (manufacturer datasheet / IPC / official library dimensions). Cite in `dimensions_source`.
- **Do not copy other libraries' files** (KiCad official is CC-BY-SA — incompatible). Pad positions/dimensions are facts and fine; drawn outlines must be your own.
- Contributions are published under **CC-BY-4.0**.
- No need to run our build scripts — CI builds index/SVG/pages/API from your five files and then runs the gates.

## PR checklist

- [ ] `python generators/qa.py` passes locally
- [ ] `meta.json.dimensions_source` cites the datasheet
- [ ] No files copied from CC-BY-SA libraries
- [ ] One part (or one family) per PR

## Usage feedback (no PR needed)

Used a part on a real board? Report it:
- Via MCP: `report_feedback(part_id, result, notes)` at `https://mcp.partreel.com/mcp`
- Via GitHub: open an issue titled `[field-report] <part_id>` with what you built and how it went

Feedback builds each part's field-proven trust score. Both successes and problems are valuable.
