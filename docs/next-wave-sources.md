# PartReel — Next Import Wave: Source Audit

**Date:** 2026-07-26 · **Method:** GitHub API + full clones + file-level inspection (Opus research) · **Baseline for overlap:** live official KiCad footprint library (gitlab.com/kicad/libraries/kicad-footprints, 15,447 footprints)

## 요약 (3줄)

- **1순위는 Antmicro** (Apache-2.0, 3,480 부품 + glTF 3D 2,207개, KiCad 10, MPN 단위 data.json이 우리 구조와 거의 1:1). 이거 하나로 다음 웨이브가 채워진다.
- 2순위는 **marbastlib**(CERN-OHL-P — 이미 만든 파이프라인 그대로), **agg-kicad**(MIT 심볼 293), **Olimex**(Apache-2.0 878개, 단 검증 필요).
- **Espressif·Seeed OPL·DigiKey·Würth는 전부 탈락** — 앞의 셋은 CC-BY-SA, Würth는 원본 그대로 재배포 권리를 안 준다.

⚠️ **Methodology correction:** `github.com/KiCad/kicad-footprints` is an **archived Dec-2021 KiCad-5 mirror**. The live library is on GitLab and has 15,447 footprints vs the mirror's 12,011. If any of our tooling or prior audits used the GitHub mirror as the "official coverage" baseline, those overlap numbers are understated. All numbers below use the live GitLab list.

---

## GO candidates

### 1. antmicro/hardware-components — **GO (rank 1, by a wide margin)**

| | |
|---|---|
| Repo | https://github.com/antmicro/hardware-components |
| License | **Apache-2.0** — real `LICENSE` file at root, verbatim Apache 2.0 text, verified. README: "This project is licensed under the Apache-2.0 license." © 2023-2026 Antmicro |
| Authorship | **Genuine.** All footprints `(generator "pcbnew") (generator_version "10.0")` — hand-drawn/re-saved in KiCad 10, with UUIDs. Contamination is 1 file: `BAT_BAT-HLD-012-SMT-TR` descr says "from SnapEDA" → exclude. 2 more files merely carry SnapEDA *datasheet URLs* in a property (not converted geometry). 9 files reference `kicad-footprint-generator`. That is 1–12 tainted files out of 5,100. |
| Counts | **3,480 components** (MPN-level dirs), **1,633 footprints**, **3,476 symbols**, **2,207 glTF 3D models**, plus Blender models + rendered previews |
| Format | **KiCad 10** — uniform `(version 20260206)`, `generator_version "10.0"` |
| Coverage | Bourns 758, TI 281, Murata 151, Würth 144, Microchip 113, Samtec 104, Molex 102, KEMET 84, Vishay 74, ADI 73, TDK 68, Nexperia 59, NXP 56, Diodes 56, TE 55, ST 54, Panasonic 49, YAGEO 47, Amphenol 47, onsemi 37, Abracon 36, Coilcraft 33, JST 32, Littelfuse 29, Hirose 28, Infineon 27. By footprint class: conn 237, inductors 83, pinheader 71, BGA 67, QFN 62, USB 39, oscillator 34, DDR4/DDR5 sockets, M.2 sockets, PCIe, RJ45, FFC/FPC, WLCSP, BGA up to 1369-ball |
| Overlap w/ official | **106 / 1,633 footprint names (6.5%)** — the generic tail (`C_0603_1608Metric`, `D_SOD-123`, `DFN-*`, `HTSSOP-*`) |
| Import effort | **LOW–MEDIUM.** `data.json` per component already carries reference, symbol, footprint, datasheet, manufacturer, mpn, description, keywords, and a full `pads[]` array with pin names + electrical types. 3,480/3,480 have data.json, 3,480 have MPN+manufacturer, 3,472 have datasheet URLs. glTF is ready-made — no STEP tessellation step needed for 2,207 of them. |
| Risks | (a) **1,389 of the 3,480 components use a footprint whose name exactly matches the official KiCad library** → treat as CC-BY-SA-derived and exclude the footprint (import symbol + metadata, substitute our own generated package). Clean remainder = **2,091 components, 898 of them with glTF**. (b) Repo is **14 GB** — sparse checkout mandatory (`kicad-footprints kicad-symbols components`, exclude `blender-models`/`gltf-models` until needed). (c) 3 files exceed Windows MAX_PATH on checkout (long Samtec/PinSocket names) — enable `core.longpaths`. (d) Commits are all "Antmicro Bot | Update assets from pipeline" — git history gives no per-file authorship trail, so the authorship verdict rests on file content, not commit log. |

**Why this is the right #1:** it is the only candidate whose data model already matches PartReel's (one directory per MPN, machine-readable metadata, symbol+footprint+3D linked). It covers server/high-speed hardware — DDR5 sockets, M.2, PCIe, large BGAs — that the official KiCad library does not, and that no library we've imported so far touches.

### 2. ebastler/marbastlib — **GO**

| | |
|---|---|
| Repo | https://github.com/ebastler/marbastlib |
| License | **CERN-OHL-P-2.0** — full verbatim CERN-OHL-P v2 text in `LICENSE`. **Same license as our CERN wave — the attribution/provenance pipeline already exists.** |
| Authorship | **Genuine.** 45/54 commits by Moritz Plattner (ebastler), co-maintained with Marble. README documents each part individually with datasheet links. 0 EasyEDA/SnapEDA/UltraLibrarian markers. |
| Counts | **368 footprints, 74 symbols, 94 STEP** (162/368 footprints reference a 3D model) |
| Format | KiCad 10 current (`20260206`, `generator_version "10.0"` on 42 files); older files back to `20210623`. Repo tracks KiCad 10 stable; 9.0/8.0/7.0 branches exist via PCM. |
| Coverage | Switches 113 (MX, Choc v1/v2, Gateron LP/KS33, hall-effect), stabilizers 32, plate cutouts 69, LEDs 27 (SK6812MINI-E, 6028R reverse-mount), Molex Pico-EZmate/PLUS/HC 14, Hirose FH33J FFC, XUNPU FPC, JST ACH/SM-SRSS, USB-C (HRO TYPE-C-31-M), Johanson antennas, crystals, Elite-C / ProMicro / Xiao / nice!nano / Liatris / SuperMini / RP2040 module footprints |
| Overlap | **7/368 vs official.** vs our ai03 import: ai03 is **MX solderable only** (~34 parts) — marbastlib adds hotswap, Choc, low-profile, hall-effect, stabilizers, plate cutouts. Complementary, not duplicative. |
| Effort | **LOW** |
| Risks | README **self-declares two derivatives of the official KiCad library** — `CON_JST_ACH_BM02B` ("Copy of the default KiCad lib's ACH footprint with pre-assigned 3d model") and `ROT_Alps_EC11E-Switch` ("Improved version of the original KiCad EC11E footprint"). **Exclude these 2** — same invalid-relicensing class as the rejected CDFER files. Two further files carry LCSC part numbers in `descr` text only (sourcing hint, not a conversion). |

### 3. adamgreig/agg-kicad — **GO (verified-2D)**

| | |
|---|---|
| Repo | https://github.com/adamgreig/agg-kicad |
| License | **MIT** — real LICENSE file. README: "they're all licensed under a permissive MIT licence" |
| Authorship | **Genuine, strongest evidence of any candidate.** 54/54 commits by Adam Greig. Symbols carry `(generator agg_kicad.build_lib_ic)` — his own build tool, driven by his own YAML dimension sets. README: "Every symbol and footprint is very carefully checked against either the relevant standard (generally IPC-7351B) or specific manufacturer footprints… Many are procedurally generated from a simple set of dimensions." CI rule-checks every commit. |
| Counts | **427 footprints** (395 `agg.pretty` + 39 `unchecked.pretty`), **293 symbols** (one file per symbol) |
| Format | **KiCad 6 era** — `(version 20211014)`, old `(property Reference IC (id 0) …)` syntax. Needs up-conversion. |
| Coverage | Symbols by class: power ICs **65**, analogue 27, microcontroller 26, interface 23, module 21, connector 20, logic 13, radio 11, sensor 10, memory 5, FPGA 5, isolation 4, clock 4, UI 4; passives 47 |
| Overlap | **7/427** footprints vs official. Symbol overlap likely medium for generic ICs, but the drawing is his own style throughout. |
| Effort | **MEDIUM** — KiCad 6 → 9/10 property syntax conversion |
| Risks | **Only 1 STEP model in the whole repo** → import as **verified-2D** (the grade we already use for the CERN wave). Last commit 2025-09, lightly maintained. `unchecked.pretty` (39 fp) is the author's own "not yet verified" bucket — quarantine or skip. |

### 4. keebio/Keebio-Parts.pretty — **GO after dedup**

| | |
|---|---|
| Repo | https://github.com/keebio/Keebio-Parts.pretty |
| License | **MIT** — "Copyright (c) 2018 Keebio", full verbatim MIT text |
| Authorship | **Genuine.** 58/59 commits by Danny Nguyen. 0 EasyEDA/SnapEDA/LCSC markers. |
| Counts | **216 footprints, 0 symbols, 7 3D models** |
| Format | **Mixed, mostly legacy** — 157 legacy `(module …)` KiCad-5 files, 59 s-expression. Conversion required. |
| Coverage | Unique value is the module/connector set: Arduino Pro Micro variants (7), Elite-C / Elite-G / Elite-AF castellated module footprints (12+), audio jacks, EN11 encoders, zigzag header variants, Gateron KS33 stabilizer cutouts, HRO Type-C |
| Overlap | 8/216 vs official; **substantial overlap with marbastlib + ai03 on MX switches** — import the module/connector subset, drop switch duplicates |
| Effort | **MEDIUM** (legacy format conversion) |
| Risks | **Exclude 5 files** generated by official KiCad's own generators (`generator ipc_gullwing_generator.py` / `ipc_dfn_qfn_generator.py`): `RP2040-QFN-56`, `SOIC-8_5.23mm-USON-8_2x3mm`, `SOIC-8_5.23x5.23mm_P1.27mm`, `SOIC-USON-8`, `USON-8_2x3mm` — **exactly the CDFER rejection class**. Only 7 3D models. |

### 5. hlord2000/nordic-lib-kicad — **GO (highest demand-per-part; one caveat needs a human call)**

| | |
|---|---|
| Repo | https://github.com/hlord2000/nordic-lib-kicad |
| License | **CERN-OHL-P-2.0** — full verbatim text |
| Authorship | **Genuine, but read the caveat.** 69/73 commits by Helmut Lord. |
| Counts | **29 footprints, 60 symbols, 29 STEP** — small |
| Format | **KiCad 10** (`20260206`) |
| Coverage | nRF9151 / nRF9161 / nRF9160 (LGA, cellular); nRF7002 / 7001 / 7000 (QFN + WLCSP, Wi-Fi); nRF54L; nRF53; nRF52; nPM PMICs; plus third-party modules — Ebyte E73/E83, Insight ISP1907/ISP2053, Fanstel BC15/BM15x/BM20x, Laird BL54Lxx |
| Overlap | **0/29** vs official |
| Effort | **LOW** |
| **Caveat** | All 29 footprints carry `(generator "kicad-footprint-generator")` — the same tool behind the rejected CDFER files. **Judged materially different**, on three pieces of evidence: (a) the `descr` strings carry Nordic-specific dimensions and nordicsemi.com URLs (e.g. `BGA-16_4x4_1.9175x1.8975mm … https://www.nordicsemi.com/products/nPM2100`); (b) the footprint names are bespoke and **0 collide with the official library**; (c) the repo vendors the generator + a `patches/` dir and runs it on the author's own dimension inputs. That is tool-use, not file-copying — the CDFER files were byte-copies of official KiCad library output. **Flagged for explicit user sign-off** since it sits adjacent to a prior rejection line. |

**Note:** Nordic Semiconductor itself publishes **no** official KiCad library — reference designs are Altium-only (verified four ways). This community repo is the only route to modern Nordic parts outside the CC-BY-SA official `MCU_Nordic` library.

### 6. Seeed-Studio/OSHW-XIAO-Series — **GO (small, high demand)**

- **License: MIT** — real LICENSE file, "Copyright (c) 2024 Seeed-Projects". Verified independently by license API + code search (32 `.kicad_mod` hits).
- **~37 footprints + ~20 symbols**: XIAO-ESP32-C3/C5/C6/S3/S3-Plus, XIAO-MG24, XIAO-RA4M1, XIAO-RP2040, XIAO-RP2350, Add-On/Plus/PRO carriers. **KiCad 10.**
- **Key finding:** this folder is **byte-identical** to the one in the CC-BY-SA `OPL_Kicad_Library` — same git tree SHA (`95e2f8c9a53f…`), every blob SHA matching. Same files, two licenses. **Take the MIT route**, cite `OSHW-XIAO-Series`, never the OPL repo.
- Effort **LOW**. Verdict **GO**.

### 7. Raspberry Pi RP2040 / RP2350 — **GO (small)**

- **License: MIT**, and it's real. `RP-008296-DS-2-Minimal-KiCAD.zip` ships its own `LICENSE.txt`: *"Permission is hereby granted, free of charge… to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, **distribute**, sublicense…"* © 2026 Raspberry Pi Ltd. Site policy (raspberrypi.com/licensing/): *"Most of the design files released and hosted by us are made available openly, with no limitations."*
- **CC-BY-ND concern resolved:** RPi runs three licenses — online docs CC-BY-SA-4.0, **datasheet PDFs CC-BY-ND-4.0**, **design files MIT/unrestricted**. The ND covers the PDFs, not the KiCad files.
- **RP2350 Minimal** ships real standalone libraries: `MCU_RaspberryPi_RP2350.kicad_sym` + `.pretty` with `RP2350-QFN-60-1EP_7x7_P0.4mm` / `RP2350-QFN-80-1EP_10x10_P0.4mm` (with thermal vias) + QFN STEP. Format is **older, KiCad 6/7** (`20221018`/`20220914`). ⚠️ No LICENSE.txt inside these two archives — they rely on the site-wide policy.
- **RP2040 Minimal** is KiCad 10 but has **no standalone library files** — 11 footprints + 20 `lib_symbols` embedded in `.kicad_pcb`/`.kicad_sch`, STEP via `kicad-embed://`. Extraction step required.
- Pico board itself is **Cadence `.DSN`/`.brd`**, not KiCad. Compute Modules ship **no design files at all**.
- ~20 parts. Effort **MEDIUM** (extraction from project files). Verdict **GO**.
- Caveat: site policy carves out third-party-supplied elements (Diodes, MTCONN, Toby, TRXCOM) — doesn't affect the RP2040/RP2350 MCU symbols and footprints.

### 8. clacktronics/AudioJacks — **GO (small, clean)**

MIT ("Copyright (c) 2021 Barwise"). **8 footprints + 22 STEP models** — 3.5 mm jacks (Cliff FCR1281, QingPu WQP-PJ301BM/301CM/301M-12/302M/3410/366ST/398SM). **0 collisions** with official. Ships FreeCAD source drawings for the 3D. Eurorack/synth demand; official KiCad audio-jack coverage is thin. Effort **LOW**.

---

## MAYBE

### OLIMEX/KiCAD — **MAYBE (high value, but gated on a geometry diff)**

| | |
|---|---|
| Repo | https://github.com/OLIMEX/KiCAD |
| License | **Apache-2.0** — real LICENSE file, verbatim Apache 2.0 |
| Counts | **878 unique footprints** in the current `Used-In-KiCad_v7` release (~2,400 across all release dirs incl. `Old/`); **904 STEP + 156 WRL**; **310 legacy `.lib` symbol libraries** + 30 `.kicad_sym` |
| Format | **Poor.** 2,132 of the `.kicad_mod` are legacy `(module …)` KiCad-5 format; only ~282 are s-expression. Symbols are legacy `.lib` + `.dcm` → conversion required. |
| Coverage | Connectors 334, IC packages 148, RLC 83, Cases 39, Signs 39, LCDs, Antennas, Relays, Regulators, Buttons, Jumpers, Proto, Switches, Diodes, Crystals |
| Overlap by name | 5/878 |
| **Blocking risk** | **The README self-declares derivation from the official KiCad library**, verbatim: *"In most of the cases these are duplicate components and packages with those in the standard KiCAD library, plus small edits to fit our goals."* That places an unknown but potentially large fraction in the **invalid-relicensing bucket** (official KiCad = CC-BY-SA, Olimex re-marks Apache-2.0) — precisely the CDFER rejection reason #2. **Name matching will not catch this** (only 5 collisions) because Olimex renames everything to its own MPN scheme. Clearing this requires a **geometry-level diff** (pad positions/sizes/shapes) against the official library. |
| Verdict | **MAYBE.** Defensible subset without diff work: `OLIMEX_Cases-FP` (39), `OLIMEX_Signs-FP` (39), LCDs, Antennas, Proto, and connectors carrying vendor MPNs. Skip RLC/IC packages entirely. |

### adafruit/Adafruit_CAD_Parts — **MAYBE (3D enrichment only, not a parts source)**

**MIT**, real LICENSE, © 2016 Adafruit Industries, actively updated (2026-07). **476 STEP + 464 Fusion `.f3d` + 340 STL + 80 3MF.** **Zero `.kicad_mod` / `.kicad_sym`** — mechanical models only. Useful to attach 3D to parts we already have; not a footprint/symbol source.

### siderakb/key-switches.pretty — **MAYBE (low priority)**

CERN-OHL-P-2.0, 33 footprints, 0 official collisions, genuine authorship (ZiTe). But **stale since 2023-05** and heavily overlapping ai03 + marbastlib. Only worth it for Alps/Choc variants marbastlib lacks.

### LibreSolar/kicad-footprints + kicad-symbols — **MAYBE (low)**

MIT, single author (Martin Jäger), 131 footprints + 1 symbol lib, **no 3D**, 15 official collisions, 1 file from `ipc_gullwing_generator.py` (exclude). Power/solar/BMS niche.

---

## REJECT

| Source | License found (verbatim basis) | Reason |
|---|---|---|
| **espressif/kicad-libraries** | `LICENSE.md`: CC-BY-SA 4.0 with KiCad-style exception | **CC-BY-SA → share-alike quarantine.** No permissive Espressif alternative exists (Apache repos contain zero KiCad files). |
| **Seeed-Studio/OPL_Kicad_Library** | pure CC BY-SA 4.0, **no design exception** | Stricter than official KiCad's. Use `OSHW-XIAO-Series` (MIT) instead — byte-identical XIAO subset. |
| **Digi-Key/digikey-kicad-library** | CC-BY-SA 4.0, collection-redistribution explicitly share-alike | The exact thing we'd be doing. KiCad-5 legacy, unmaintained, no 3D. **Hard reject.** |
| **perigoso/keyswitch-kicad-library** | CC-BY-SA 4.0 | Share-alike; stale; superseded by marbastlib + siderakb. |
| **wntrblm/winterbloom_kicad_library** | CC-BY-SA 4.0, self-declared official-KiCad derivation | Doubly disqualified. |
| **octopart/CPL-KiCad-Library** | CC-BY-SA 4.0 | Share-alike; dead since 2019. |
| **Alarm-Siren/arduino-kicad-library, 6502-kicad-library** | CC-BY-SA 4.0 | Share-alike. |
| **WurthElektronik/KiCad-Library** | PDF terms: non-transferable, **non-sublicensable**; unmodified redistribution not among enumerated rights | **Not redistributable.** (7,493 fp / 7,290 STEP — if ever wanted, ask libraries@we-online.com; their GitHub vs website terms contradict each other.) |
| **Samtec, Molex, TE, Hirose, JST** | ToS all prohibit redistribution | None publish an official KiCad library; all route via SnapMagic/UltraLibrarian. |
| **Adafruit KiCad library** | **Does not exist** (adafruit/kicad-libraries is an unmodified fork of Espressif's). Eagle library has **no LICENSE file** + admits third-party content | Reject. |
| **Nordic (official)** | N/A — Altium only | Use hlord2000/nordic-lib-kicad instead. |
| **Raspberry Pi Pico board / Compute Modules** | N/A | Pico = Cadence files; CMs ship no design files. |

---

## Ranked shortlist

| # | Source | License | New parts | 3D | Effort | Why |
|---|---|---|---|---|---|---|
| **1** | **antmicro/hardware-components** | Apache-2.0 | **2,091** clean (up to 3,480) | 898 glTF clean / 2,207 total | LOW-MED | Data model matches ours 1:1; DDR5/M.2/PCIe/large-BGA coverage nobody else has; KiCad 10; actively built |
| **2** | **ebastler/marbastlib** | CERN-OHL-P-2.0 | **366** | 94 STEP | LOW | Same license as CERN wave → pipeline reuse; complements ai03 |
| **3** | **adamgreig/agg-kicad** | MIT | **427 fp + 293 sym** | ~0 | MED | 65 power-IC symbols; best-documented authorship; verified-2D |
| **4** | **OLIMEX/KiCAD** | Apache-2.0 | **~878** (gated) | 904 STEP + 156 WRL | HIGH | Biggest permissive 3D haul — needs geometry diff vs official first |
| **5** | **Micro-GO bundle** | mixed permissive | **~125** | ~60 | LOW-MED | nordic-lib (60) + Seeed XIAO (37) + RPi RP2040/2350 (20) + AudioJacks (8) |
| *6* | *keebio/Keebio-Parts.pretty* | *MIT* | *~200 after exclusions* | *7* | *MED* | *Legacy conversion + marbastlib dedup; module/connector subset* |

## New-part potential

- **Conservative** (clean subsets, Olimex excluded, Keebio deferred): **≈ 3,000 parts**
- With Keebio: ≈ 3,200 · Olimex cleared: ≈ 4,100 · Antmicro generic tail re-footprinted with our own packages: **≈ 5,500**
- **3D assets:** ≈ **3,700** (Antmicro 2,207 glTF + Olimex 904 + Adafruit 476 + marbastlib 94 + AudioJacks 22)

라이브러리 규모가 대략 **2배**가 되고, 무게중심이 CERN 일변도에서 모듈·개발보드·무선·고속 소켓·키보드·오디오 등 **실검색 수요 니치**로 이동한다.

## Action items before the wave starts

1. **KiCad 10 지원 확인** — Antmicro/marbastlib/nordic/XIAO 모두 `(version 20260206)`. CERN 웨이브는 KiCad 9였음. `validate_kicad.py`·렌더 경로의 KiCad 10 s-expression 처리 확인 필수.
2. **Nordic 생성기 판정 (사용자 결정 필요)** — `kicad-footprint-generator` 출력물. CDFER 탈락 건과 도구는 같지만 성격이 다름(자기 치수 입력 + 공식 이름 충돌 0 = 도구 사용, CDFER는 공식 산출물 바이트 카피). 결정은 REQUIREMENTS에 재사용 규칙으로 기록할 것 (Keebio·LibreSolar도 동일 쟁점).
3. **지오메트리 diff 도구** — Olimex 살리려면 필요. Antmicro의 공식-이름-충돌 1,389개도 정량 판정 가능해짐 (상당수 회수 가능성).
4. **공식 커버리지 기준선 수정** — github.com/KiCad/kicad-footprints는 2021년 KiCad-5 아카이브 미러 (3,436개 부족). 도구가 이걸 보고 있다면 gitlab.com/kicad/libraries/kicad-footprints로 교체.
5. **제외 목록은 이미 계산됨** — Antmicro: SnapEDA 1 + 공식이름 풋프린트 106 (부품 1,389개); marbastlib: 공식 파생 선언 2; Keebio: ipc 생성기 5; LibreSolar: 1.
