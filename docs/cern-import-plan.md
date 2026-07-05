# CERN KiCad Library Import Plan (partreel.com)

Analyzed: `https://gitlab.com/ohwr/cern-kicad-libs` @ `53054c17` (2026-07-04, nightly auto-update).
Local clone: `scratchpad/cern/`. Compared against `D:\seriouscode\opencad-lib` (217 parts, 197MB, GitHub Pages).

## 0. Headline findings

| Metric | Value |
|---|---|
| DB rows (parts) | **23,971** in 55 sqlite tables (more than the "~17k" claim) |
| Rows resolving to both symbol+footprint file | **23,949 (99.9%)** |
| Distinct real MPNs | **19,867** (23,801 rows have an MPN; 3,578 MPNs appear >1×) |
| 3D models | **ZERO** — README: "3D models and datasheets are not included" (vendor IP) |
| Datasheet URLs | 3 http out of 23,960 — rest are `${CERN_DATASHEET_DIR}\<file>.pdf` internal paths |
| Footprints | 9,304 files / 59 `.pretty` dirs / **407MB** (mean 43.8KB, median 16.5KB, max 1.75MB) |
| Symbols | 8,432 top-level in 29 `.kicad_sym` / **157MB** (mean block 17.4KB, median 6.2KB) |
| F.CrtYd coverage | **4,116/9,304 (44%)** — 5,188 need auto-courtyard |
| Multi-unit symbols | **1,765/8,432 (21%)** — current importer skips these |
| Naive per-part copy size (SparkFun pattern) | **895MB** source alone → busts GitHub Pages 1GB |
| License | CERN-OHL-P-2.0, blanket REUSE dep5, no per-file SPDX headers |

The two facts that reshape the pipeline: **no 3D at all**, and **per-part asset copying is arithmetically impossible on Pages**.

## 1. Structure

```
CERN.sqlite                 14.2MB, 55 tables (one per category/vendor), 23,971 rows
CERN_{Windows,Linux}.kicad_dbl   ODBC config; key column = "Part Number Nocolon";
                                 maps LibSymbol/LibFootprint + per-table visible fields
SchLib/  29 .kicad_sym      157MB, 8,432 symbols  (KiCad format 20241209, generator 9.0)
PcbLib/  59 .pretty         407MB, 9,304 .kicad_mod (format 20241229, generator 9.0)
fp-lib-table / sym-lib-table   58 + 29 nicknames → ${CERN_LIB_DIR} paths
CHECKSUMS                   md5 per library file (usable for re-sync diffing)
.reuse/dep5                 Files: * → Copyright 2024-2025 CERN, CERN-OHL-P-2.0
LICENSES/CERN-OHL-P-2.0.txt
*_conversion_log.txt        nightly kicad-cli Altium→KiCad conversion; 0 errors/warnings in pcblib log
```

Mapping: DB row → `LibSymbol` = `"<SchLib name>:<Symbol name>"` → `SchLib/<name>.kicad_sym`; `LibFootprint` = `"<pretty name>:<fp name>"` → `PcbLib/<name>.pretty/<fp>.kicad_mod`. **Many-to-one both ways**: 23,971 rows share 9,112 referenced footprints (p50=1, p90=3, max=1,009 for `SOIC127P600X175-8N`) and ~8.4k symbols. The DB row is the *part*; symbol/footprint are *shared packages* — exactly the dedup schema REQUIREMENTS.md line 315 already calls for.

Per-part metadata (columns vary per table): `Part Number` (CERN internal, unique-ish), `Manufacturer`, `Manufacturer Part Number`, `Part Description`, `Comment`/`Value`, `Status` (lifecycle), `Pin Count`, `ComponentHeight`, category params (Power/TC/Tolerance/Voltage/...), `Author`, `CreateDate`/`LatestRevisionDate`, `Datasheet` (internal path), `HelpURL` (CERN DFS UNC path). Text is clean UTF-8 (± and ° render fine; earlier mojibake was console cp949, not the data).

Footprints DO carry `(model "${CERN_3DMODEL_DIR}/...")` references (9,105/9,304) but the files are not shipped — the refs are dead weight to strip on import.

## 2. Volume & quality

- **Complete bundles by partreel's current definition (sym+fp+3D): 0.** By sym+fp: 23,949/23,971 (99.9%). The ~22 broken refs are edge cases (WAGO terminal blocks, a CERN_OHL logo pad, etc.).
- Format: KiCad 9.x s-expressions (20241209/20241229) — newer than SparkFun's but same grammar; existing regex/balanced-block parser works (verified by running it here).
- Layers, all 9,304 footprints: F.SilkS 100%, F.Fab 100%, F.CrtYd 44%. Worst courtyard libs: 3M THD 0/194, COMATEL THD 0/70, LEMO THD 1/81, HARTING THD 3/225, Capacitors THD 10/407. Pads present in 8,782 (rest are mechanical/graphic: `Pads`, `Metal Screening Box`, logos).
- 5-footprint sample (random, seed 42):

| Footprint | Size | Layers |
|---|---|---|
| SOP65P640X120-21N-S295 | 8.8KB | F.Cu, F.SilkS, F.Fab, **F.CrtYd** ✓ |
| AVX_14 5602 040 000 829 | 74KB | + Cmts.User, **F.CrtYd** ✓ |
| FUSR_TYCO_SMD150F-2 | 6.9KB | + Cmts.User, **F.CrtYd** ✓ |
| FCI_D15P13A4GV00LF | 62KB | **no F.CrtYd** ✗ |
| MOLEX_52745-1597 | 57KB | + Cmts.User, **F.CrtYd** ✓ |

- Lifecycle `Status`: None 19,283 / Not Recommended 2,548 / Preferred 1,633 / Obsolete+EOL+Discontinued 454 / other 53.
- Pin counts: p50=5, p90=34, max=2,577 (backplane connectors) — footprint SVG rendering must handle huge parts.

## 3. Overlap vs official KiCad lib (20-part random sample, seed 7)

| Verdict | n | Examples |
|---|---|---|
| Unique atomic MPN part, no official equivalent | **15** | XCZU7EV-2FBVB900I (Zynq US+ BGA900!), CRYDOM CN024D05, SAMTEC MTLW-125-07-L-D-250, TYCO HM-Zd 6469081-1, IXYS DSDI60-18A, Micrel SY100ELT22ZG, Susumu PAT0510S, Fischer DBPC 102, Recom RLS-226, NSVJ3910SB3, HEF4521BP, LT1236ACS8-10, 3M 961/N3428, Bourns 4310R network, Tyco YR1B precision R |
| Real-MPN part where official lib has the *footprint or family* but not the atomic part | 3 | OPA277UA (official has OPA277x symbols but no MPN-keyed record), Coilcraft XAL5050 (official has the footprint, generic L symbol), 3M IDC headers (generic equivalents) |
| GENERIC value-level passive, pseudo-MPN | 2 | R0603_464R_0.1%..., R0805_51K_0.1%... |

So ~75% cleanly unique, ~15% partially overlapping but still adding MPN-keyed value, ~10% low-value generics. The "generic package but real MPN" argument **holds for branded passives** (Panasonic 366, Bourns 358, TT/Tyco precision resistors, etc. — real orderable MPN + tolerance/TC/power params that official `Device:R` never carries) and **fails for the `Manufacturer=GENERIC` slice: 3,324 rows (13.9%)** whose "MPN" is just the internal part number. Recommend: import branded passives, defer GENERIC.

Vendor mix supports uniqueness: top manufacturers TI 2,210, Samtec 1,367, ADI 1,229, Tyco 564, Molex 510, Linear 486, OnSemi 478 — atomic vendor parts are precisely where the official lib is thinnest.

## 4. License mechanics (CERN-OHL-P-2.0 — text verified in LICENSES/)

- **§3.1** verbatim conveying: retain all Notices. **§3.3** modified conveying (us: symbol extraction, courtyard addition, model-ref stripping): (a) retain Notices, (b) **add a Notice stating we modified it, with date and brief description**. **§3.4** even relicensing is allowed if 3.3 is met + license copy provided — but we keep `CERN-OHL-P-2.0` per-part (same no-relicense principle as the SparkFun CC-BY import). **§4** products: recipients need access to Notices.
- No per-file SPDX headers; REUSE via blanket `.reuse/dep5` (`Files: * / Copyright: 2024-2025 CERN / License: CERN-OHL-P-2.0`). So per-file provenance burden is on our record, not on headers.
- Per-part `meta.import` must record: `license: CERN-OHL-P-2.0`; `copyright: 2024-2025 CERN`; `source_repo` + `source_commit`; source file paths (`PcbLib/X.pretty/Y.kicad_mod`, `SchLib/Z.kicad_sym#Symbol`, sqlite table + `Part Number Nocolon` key); `attribution: CERN (kicad-dev@cern.ch)`; **modifications list + import date** (this IS the §3.3(b) notice); upstream datasheet filename (from `Datasheet` basename) even though unresolvable. Ship `LICENSES/CERN-OHL-P-2.0.txt` once in the repo + ATTRIBUTIONS.md entry. Add a "not endorsed by CERN" line (license preamble explicitly disclaims endorsement).

## 5. Pipeline deltas vs `generators/import_sparkfun.py` — and THE size question

Code deltas:
1. **Source of truth = sqlite, not symbol properties.** Only 10/8,432 symbols embed a `Footprint` property; the DB `LibSymbol`/`LibFootprint` columns drive pairing. `sqlite3` stdlib, iterate 55 tables (schemas vary — column-presence guards needed; verified pattern works).
2. **No 3D → gate set degrades.** zfight/STEP-kernel/GLB gates are N/A. Options in §7 (decision #2). Strip dead `(model "${CERN_3DMODEL_DIR}/...")` refs.
3. **Auto-courtyard at scale**: 5,188 footprints (56%) need it; existing bbox+0.25mm generator is reused, but THD connector bboxes must include `fp_poly`/`fp_arc` (CERN Altium conversions are polygon-heavy; SparkFun version only reads pads+fp_line).
4. **Multi-unit symbol support** (21% of symbols; concentrated in Op Amps 1,575 / Logic 767 / Standard Logic 804 rows): render unit A or all units side-by-side; current "skip multi-unit" rule would silently drop ~3,000+ of the best ICs.
5. **Shared-package schema before scale** (REQUIREMENTS line 315): parts reference `package/<fp-hash>` + `symbol/<sym-hash>` instead of copying. Copying: 895MB; dedup: 553MB. SOIC-8 would otherwise be duplicated 1,009×.
6. **Naming/keys**: internal Part Numbers contain `%`, `/`, spaces, `'''`, `±` — slug carefully. 3,578 MPNs are non-unique (package/variant rows). ID = `cern_<slug(mpn)>`, on collision `cern_<slug(mpn)>_<pkg-slug>`; stable upstream key stored = `(table, "Part Number Nocolon")`. Rows without real MPN fall back to internal PN slug.
7. **Nightly-moving upstream**: pin the commit per wave; quarterly re-sync by diffing upstream `CHECKSUMS` (md5 per lib file) against pinned values.
8. **CI scale**: render_svg/build_site are O(n). Full import = up to 2×23,949 part SVGs (or 2×17.5k deduped) ≈ hours of render; must go incremental (content-hash cache, only render new/changed packages) and sharded. GitHub Actions 6h job cap is reachable otherwise.

### Size arithmetic (the key open question)

Current site: 197MB / 217 parts (STEP 141MB + GLB 51MB dominate — 886KB/part of 3D that CERN parts won't have).

| Scenario | Source assets | SVGs | meta+pages | Total added | Verdict vs GitHub Pages 1GB |
|---|---|---|---|---|---|
| A. Full 23.9k, per-part copies (SparkFun pattern) | 895MB | 2×23.9k ≈ 190–380MB | ~48MB + ~215MB html | **1.35–1.55GB** | **FAIL** (also ~145k files) |
| B. Full 23.9k, deduped packages | 553MB | 17.5k ≈ 105MB | ~48MB + ~215MB | **~920MB** (+197MB existing = 1.12GB) | **FAIL** (marginal even alone) |
| C. Tiered: metadata-all + assets top-5k | ~150–200MB (curated dedup) | ~40MB | ~45MB + ~50MB | **~300MB** → site ≈ 500MB | **OK** |
| D. Metadata-all on Pages + ALL assets in Cloudflare R2 | 0 on Pages (553MB in R2) | R2 | ~45MB on Pages | Pages +~50MB; R2 ≈ 0.7GB ≈ **$0.01/mo** | **OK, scales** |

(Cloudflare Pages as alternative host is also out for scenario A/B: 20k files/deploy cap — already noted in REQUIREMENTS §9.)

**Recommendation: C now, D before Wave 2.** Metadata tier = all 19,867 MPNs in sharded JSON (~1.5KB/part), each searchable with full params/provenance and an "request full assets" hook wired to the existing MCP `request_part` → CI → inline-deploy flow (E2E-proven 2026-07-04). Full-asset tier = curated waves within a ~450MB budget until R2 lands; after R2, promote everything.

### 3D strategy (no upstream 3D)

- 1,172 distinct footprints (13% of files) have parseable IPC-7351 names (QFN 249, BGA 204, SOP 114, CAPC 100, SOIC 93, SON 87, SOT 68, QFP 60, RESC 60...), but they cover a disproportionate share of *parts* (SOIC-8 alone = 1,009 parts; RESC/CAPC = ~4,000 passives). Parametric synthesis via the existing `gen_*_3d.py` + FreeCAD→GLB pipeline can plausibly give real 3D to **~8–10k parts (33–42%)** by writing ~6 package generators (chip R/C/L, SOIC/SOP, SOT, QFN/SON, QFP, BGA) that parse dimensions straight from the IPC name (`RESC1608X55N` = 1.6×0.8×0.55mm — dimensions are in the name).
- Everything else (vendor connectors — the crown jewels) ships as a **"verified-2D" tier**: gates = structure/courtyard/overlap/render only; `formats: [kicad_mod, kicad_sym]`, no `model_3d`. Honest badge > fake box models.

## 6. Staged import plan

| Wave | Scope | Parts (rows) | Prereqs | Asset tier |
|---|---|---|---|---|
| **0 pilot** | Crystals & Oscillators (335) + LEMO (90) | ~425 | sqlite importer, naming, §3.3 notice format, verified-2D badge | full |
| **1** | All vendor connector tables (SAMTEC 1,367, MOLEX 505, TYCO 467, PHOENIX 362, 3M 359, HARTING 323, AMPHENOL 195, HARWIN 145, STELVIO/COMATEL 107, SOURIAU 97, FCI 83, ERNI 78, WEIDMULLER 62, MENTOR 10) + Sockets 167 | ~4,300 | dedup schema live; fp_poly-aware auto-courtyard (THD libs ~0% CrtYd); incremental render | full if ≤ budget, else top-2k full + rest metadata |
| **2** | ICs: Analog & Interface 2,215, Op Amps 1,575, Regulators 1,067, Diodes 964, Logic 767+804, Transistors 685, DC-DC 445, Optocouplers 213, Sensors 249 | ~9,000 | **multi-unit symbols; R2 migration; parametric 3D for SOIC/SOT/QFN/QFP/BGA** | metadata-all + R2 assets |
| **3** | Branded passives (Resistors/Caps/Inductors/Networks/Thermistors, minus GENERIC), Relays 304, Fuses 316, Switches 227, Transformers 232 | ~5,500 | chip-package parametric 3D | metadata-all + R2 |
| **4** | Decisions: GENERIC 3,324, Obsolete/EOL 454, mechanical (Pads 138, Screening 67, Fasteners 363, Heat-Sinks 123, Batteries, PCB Modules) | ~4,700 | maintainer call | mostly metadata-only |

Naming: `cern_<slug(mpn)>` (collision → `_<pkg>` suffix); keep `name: "<MPN> (<Manufacturer>)"`, `family` from sqlite table name, provenance key `(table, Part Number Nocolon)`.

## 7. Open decisions for the maintainer

1. **Hosting**: accept scenario C now and schedule R2 (D) before Wave 2? (Numbers above say Pages alone cannot ever hold full CERN assets.) — recommended: yes.
2. **"Verified" definition**: is a no-3D "verified-2D" tier acceptable on a site whose pitch is verified sym+fp+3D bundles? Recommended: yes with explicit badge + parametric-3D backfill; the alternative (skip CERN) forfeits ~20k real-MPN parts.
3. **Multi-unit symbols** (21%, gates Wave 2): invest in renderer/exporter support, or ship unit-A-only with a flag? Recommended: proper support; op-amps are the single biggest IC category (1,575).
4. **GENERIC slice** (3,324 rows, 13.9%): import as metadata mapped onto existing partreel generic packages, or exclude? Recommended: exclude from MPN registry (no orderable MPN).
5. **Lifecycle**: import Obsolete/NRND (~3,000 rows) with `status` field, or drop? Recommended: import with status — engineers search for legacy parts precisely when replacing them.
6. **Datasheets**: leave blank vs record upstream filename vs auto-resolve by MPN search later? Recommended: record filename in provenance only; never fabricate URLs (only 3/23,960 are real URLs).
7. **Re-sync cadence** vs nightly upstream: pin per-wave commit + quarterly CHECKSUMS diff? Recommended: yes; treat upstream as append-mostly.
8. **Courtyard gate**: keep hard-require (auto-generate where missing, drop on failure) — 56% of footprints exercise this path; the bbox logic needs the fp_poly upgrade first.

## Appendix: verification cross-checks performed
- Row counts via sqlite3 (23,971) cross-checked against dbl library list (55 tables both) and README claim (~17k understated).
- Symbol/footprint resolution tested two ways: regex top-level symbol scan AND balanced-block extraction (8,432 vs 8,433 — one nested-name artifact); footprint file existence checked per DB ref (23,956 fp-ok).
- Sizes measured as exact bytes (not du blocks): PcbLib 407.4MB/9,304, SchLib 157.0MB, per-symbol blocks summed independently (146MB) — consistent.
- Encoding verified at raw-byte level (`\xc2\xb1` = UTF-8 '±'), ruling out the suspected cp1252 mojibake.
- Conversion quality: `pcblib_conversion_log.txt` grep for error/warn = 0 hits.
