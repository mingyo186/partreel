# Contributing to PartReel (for AI agents and humans)

PartReel accepts part contributions via GitHub PR. **CI quality gates auto-review every PR** — if gates pass and dimensions cite a source, it gets merged and published to the registry (site + API + MCP).

> **One-prompt pattern for AI agents.** If you are a human with an AI assistant,
> this whole document is designed so that a single instruction works:
> *"Fetch https://github.com/mingyo186/partreel/blob/main/CONTRIBUTING-AGENTS.md
> and follow it to create a part for `<MPN>` from its datasheet, then open a PR."*
> The registry is machine-reviewed end to end — your agent's PR is judged by the
> same CI gates as the maintainer's own commits. This is the intended way the
> catalog grows: **your AI builds, our gates verify, everyone reuses.**
>
> **You don't wait for the merge to use your part** — the files are on your
> machine the moment your AI creates them; drop them into your KiCad project
> immediately. The PR is the give-back step, and it doubles as **free QA**:
> our gates check your part's structure, drawing rules and dimension sourcing
> before your board goes to fab. A failed gate is a defect caught early.
> And a registered part keeps paying you back: if anyone later finds and fixes
> a defect in it, the registry copy gets the fix — the copy sitting alone on
> your disk never will.

## What to contribute

A part = one directory under `library/<category>/<group>/<part_id>/` containing **3-5 source files** — SVG previews, the site page, the search index and the API entry are **built automatically by CI**:

| File | What |
|---|---|
| `<part_id>.kicad_mod` | KiCad footprint (s-expression, KiCad 7-10) |
| `<part_id>.kicad_sym` | KiCad symbol library with one symbol |
| `meta.json` | Metadata — see schema below |
| `<part_id>.step` | *(optional)* 3D model (valid solid; body must match footprint fab outline; no coplanar overlapping faces between solids; pins as individual bodies, not one merged strip) |
| `<part_id>.glb` | *(optional, required if step present)* web preview mesh (small; housing + metal as separate meshes, or a single mesh named "imported") |

Without 3D the part ships at the **verified-2D** tier (set `"tier": "verified-2d"` in meta and omit step/glb from `files`) — perfectly acceptable; ~40% of the catalog is 2D. Large 3D binaries are mirrored to the asset CDN by maintainer automation after merge; just include them in the PR.

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
- **Do not copy other libraries' files** (KiCad official is CC-BY-SA — incompatible). Pad positions/dimensions are facts and fine; drawn outlines must be your own. **This is machine-enforced**: CI compares every contributed footprint's pad geometry against all 15,447 official-library footprints (name-independent) and rejects copies.
- Original contributions are published under **CC-BY-4.0**. Importing from another *permissive* open library (MIT / Apache-2.0 / CERN-OHL-P / CC-BY) is welcome too — keep the original license in `meta.license` and record `meta.import` (source repo, commit, files, attribution, modifications).
- No need to run our build scripts — CI builds index/SVG/pages/API from your source files and then runs the gates.
- **Credit**: merged contributors appear in the GitHub contributors graph; bug reporters whose reports lead to fixes are recorded in [CREDITS.md](CREDITS.md) and in fix commits as `Reported-by:`.

## Failing gates is the normal workflow — iterate

Do not expect a first attempt to pass. Our own parts rarely did; every past
mistake class (merged 3D pins, overlapping labels, missing render elements,
copied footprints...) is now a permanent automated check, so your part gets
the benefit of every lesson this registry has learned. When CI goes red:
feed the CI log back to your AI ("read this gate failure and fix the part"),
push again, repeat until green. The error messages are written to be
machine-actionable. Gate-fail -> fix -> resubmit is the intended loop, not
an exception.

## PR checklist

- [ ] `python generators/qa.py` passes locally
- [ ] `meta.json.dimensions_source` cites the datasheet
- [ ] No files copied from CC-BY-SA libraries
- [ ] One part (or one family) per PR

## Extending a family (cheapest contribution — one config line)

Many parts are parametric family members. If the registry has one member of a
family and you need a sibling (another voltage, grade, pin count):

1. **Fastest: `request_part` via MCP** — variant families (`ht73xx`, `ht78xx`,
   `sy8008`, `max1704x`) and pin-header families generate on demand, pass the
   gates, and publish in ~5 minutes. No PR needed.
2. **Or a one-line PR**: family configs live in `generators/` (e.g.
   `HT73XX_CODES` in `gen_ics.py`, `FAMILIES` in `gen_connectors.py`). Add the
   variant code with its datasheet-verbatim ordering MPN (check the selection
   table — do not invent codes), and CI gates auto-review. This is also how
   you register a NEW on-demand family: add the codes dict + builder and wire
   it into `VARIANT_FAMILIES`.

## Usage feedback (no PR needed)

Used a part on a real board? Report it:
- Via MCP: `report_feedback(part_id, result, notes)` at `https://mcp.partreel.com/mcp`
- Via GitHub: open an issue titled `[field-report] <part_id>` with what you built and how it went

Feedback builds each part's field-proven trust score. Both successes and problems are valuable.

## Found a problem? Fix it yourself (bots welcome)

Problem reports get an automated reply with a fix guide. The registry is
machine-reviewed: your fix PR is judged by the same CI gates as everything
else, so it merges as fast as a maintainer's own. Recipe: read the part's
provenance (`/api/v1/parts/<id>.json` → generator source + datasheet), fix
the **generator** (not just the artifacts), cite the datasheet page for any
dimension you change, open a PR referencing the issue.
