# PartReel — open KiCad parts registry for humans & AI agents

**No login. No paywall. Machine-verified.** Every part ships as a bundle of
KiCad footprint (`.kicad_mod`) + symbol (`.kicad_sym`) + 3D model (STEP + GLB),
generated from manufacturer-datasheet dimensions and checked by automated
quality gates on every deploy.

**Site:** https://partreel.com · **API:** https://partreel.com/api/ ·
**MCP server:** `https://mcp.partreel.com/mcp` · **Agent guide:** https://partreel.com/agents/

## Why this exists

- The official KiCad library is excellent — use it when it has your part.
  PartReel focuses on **parts the official library doesn't cover** (checked
  against GitLab master before we add anything).
- Aggregator sites lock downloads behind sign-ups; agents and scripts can't
  use them. Everything here is a plain URL.
- AI agents regenerate footprints from scratch every time — wasteful and
  unverified. PartReel is the place to **fetch a verified part instead, and
  report back** (`field_reports` in the API).

## Provenance — verify us, don't trust us

Every part's API entry (`/api/v1/parts/<id>.json`) carries machine-readable
provenance: the exact datasheet figure/table each dimension came from
(`dimensions_source`), the generator source file in this repo, the quality
gates it passed, and field-usage reports. Gates run in CI on every push and
**block deployment on failure** — see [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml).

| Gate | Checks |
|---|---|
| `validate_kicad.py` | s-expression structure, pads, layers, pin-1 |
| KLC drawing rules | silk 0.12 / fab 0.10 + pin-1 chamfer / courtyard 0.05 |
| `check_overlap.py` | no overlapping text in previews |
| `check_render.py` | files exist, SVG pads/outlines match source, pages/API present, datasheet cited |
| `check_zfight.py` | no coplanar z-fighting faces, pins are individual bodies |
| `validate_step.py` | STEP solids pass FreeCAD kernel isValid |

## For AI agents

- Static JSON API, no auth, no rate limit: [`/api/v1/parts.json`](https://partreel.com/api/v1/parts.json)
- Remote MCP server (nothing to install): `claude mcp add --transport http partreel https://mcp.partreel.com/mcp`
  — tools: `search_parts`, `get_part`, `list_parts`, `report_feedback`, `request_part`, `how_to_contribute`
- Machine guide: [`/llms.txt`](https://partreel.com/llms.txt)
- Missing a part? `request_part` generates, gates and publishes it in ~5 minutes,
  or contribute via PR — CI gates auto-review ([CONTRIBUTING-AGENTS.md](CONTRIBUTING-AGENTS.md)).

## Repository layout

```
library/                 part assets (CC-BY-4.0): .kicad_mod / .kicad_sym / .step / .glb / meta.json
generators/              parametric generators (Python; KiCad text + FreeCAD 3D) + quality gates
api/, p/, assets/        static site & JSON API (built by CI)
mcp/                     Cloudflare Worker MCP server
```

## License

- **Code** (generators, site): [MIT](LICENSE)
- **Part assets** (library/): [CC-BY-4.0](library/LICENSE)

Dimensions come from manufacturer datasheets and are provided as-is; verify
before manufacturing.

## Parts index

<!-- PARTS:BEGIN -->
Currently **202 parts**, all machine-verified (structure, KLC drawing rules, render completeness, 3D coplanar/merged-pin checks, STEP kernel) with datasheet-cited dimensions.

### connector (110)

| Part | MPN | Manufacturer | Files |
|---|---|---|---|
| [Audio_Jack_TRRS_3.5mm_SMD (SparkFun)](https://partreel.com/p/sparkfun_audio_jack_trrs_3_5mm_smd/) | `Audio_Jack_TRRS_3.5mm_SMD` | SparkFun Electronics | [sparkfun_audio_jack_trrs_3_5mm_smd](library/connector/sparkfun/sparkfun_audio_jack_trrs_3_5mm_smd) |
| [Barrel_Jack_PTH (SparkFun)](https://partreel.com/p/sparkfun_barrel_jack_pth/) | `Barrel_Jack_PTH` | SparkFun Electronics | [sparkfun_barrel_jack_pth](library/connector/sparkfun/sparkfun_barrel_jack_pth) |
| [Barrel_Jack_PTH_Slot (SparkFun)](https://partreel.com/p/sparkfun_barrel_jack_pth_slot/) | `Barrel_Jack_PTH_Slot` | SparkFun Electronics | [sparkfun_barrel_jack_pth_slot](library/connector/sparkfun/sparkfun_barrel_jack_pth_slot) |
| [Conn_01x02_JST_P2.0mm_Horizontal_PTH (SparkFun)](https://partreel.com/p/sparkfun_conn_01x02_jst_p2_0mm_horizontal_pth/) | `Conn_01x02_JST_P2.0mm_Horizontal_PTH` | SparkFun Electronics | [sparkfun_conn_01x02_jst_p2_0mm_horizontal_pth](library/connector/sparkfun/sparkfun_conn_01x02_jst_p2_0mm_horizontal_pth) |
| [Conn_01x02_JST_P2.0mm_Horizontal_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x02_jst_p2_0mm_horizontal_smd/) | `Conn_01x02_JST_P2.0mm_Horizontal_SMD` | SparkFun Electronics | [sparkfun_conn_01x02_jst_p2_0mm_horizontal_smd](library/connector/sparkfun/sparkfun_conn_01x02_jst_p2_0mm_horizontal_smd) |
| [Conn_01x02_JST_P2.0mm_Horizontal_SMD_LiPo (SparkFun)](https://partreel.com/p/sparkfun_conn_01x02_jst_p2_0mm_horizontal_smd_lipo/) | `Conn_01x02_JST_P2.0mm_Horizontal_SMD_LiPo` | SparkFun Electronics | [sparkfun_conn_01x02_jst_p2_0mm_horizontal_smd_lipo](library/connector/sparkfun/sparkfun_conn_01x02_jst_p2_0mm_horizontal_smd_lipo) |
| [Conn_01x03_JST_P1.0mm_Horizontal_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x03_jst_p1_0mm_horizontal_smd/) | `Conn_01x03_JST_P1.0mm_Horizontal_SMD` | SparkFun Electronics | [sparkfun_conn_01x03_jst_p1_0mm_horizontal_smd](library/connector/sparkfun/sparkfun_conn_01x03_jst_p1_0mm_horizontal_smd) |
| [Conn_01x03_JST_P1.0mm_Vertical_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x03_jst_p1_0mm_vertical_smd/) | `Conn_01x03_JST_P1.0mm_Vertical_SMD` | SparkFun Electronics | [sparkfun_conn_01x03_jst_p1_0mm_vertical_smd](library/connector/sparkfun/sparkfun_conn_01x03_jst_p1_0mm_vertical_smd) |
| [Conn_01x03_JST_P1.25mm_Locking_Horizontal_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x03_jst_p1_25mm_locking_horizontal_smd/) | `Conn_01x03_JST_P1.25mm_Locking_Horizontal_SMD` | SparkFun Electronics | [sparkfun_conn_01x03_jst_p1_25mm_locking_horizontal_smd](library/connector/sparkfun/sparkfun_conn_01x03_jst_p1_25mm_locking_horizontal_smd) |
| [Conn_01x04_JST_P1.0mm_Horizontal_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x04_jst_p1_0mm_horizontal_smd/) | `Conn_01x04_JST_P1.0mm_Horizontal_SMD` | SparkFun Electronics | [sparkfun_conn_01x04_jst_p1_0mm_horizontal_smd](library/connector/sparkfun/sparkfun_conn_01x04_jst_p1_0mm_horizontal_smd) |
| [Conn_01x04_JST_P1.0mm_Vertical_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x04_jst_p1_0mm_vertical_smd/) | `Conn_01x04_JST_P1.0mm_Vertical_SMD` | SparkFun Electronics | [sparkfun_conn_01x04_jst_p1_0mm_vertical_smd](library/connector/sparkfun/sparkfun_conn_01x04_jst_p1_0mm_vertical_smd) |
| [Conn_01x04_JST_P1.25mm_Locking_Horizontal_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x04_jst_p1_25mm_locking_horizontal_smd/) | `Conn_01x04_JST_P1.25mm_Locking_Horizontal_SMD` | SparkFun Electronics | [sparkfun_conn_01x04_jst_p1_25mm_locking_horizontal_smd](library/connector/sparkfun/sparkfun_conn_01x04_jst_p1_25mm_locking_horizontal_smd) |
| [Conn_01x05_JST_P1.0mm_Horizontal_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x05_jst_p1_0mm_horizontal_smd/) | `Conn_01x05_JST_P1.0mm_Horizontal_SMD` | SparkFun Electronics | [sparkfun_conn_01x05_jst_p1_0mm_horizontal_smd](library/connector/sparkfun/sparkfun_conn_01x05_jst_p1_0mm_horizontal_smd) |
| [Conn_01x05_JST_P1.25mm_Locking_Horizontal_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x05_jst_p1_25mm_locking_horizontal_smd/) | `Conn_01x05_JST_P1.25mm_Locking_Horizontal_SMD` | SparkFun Electronics | [sparkfun_conn_01x05_jst_p1_25mm_locking_horizontal_smd](library/connector/sparkfun/sparkfun_conn_01x05_jst_p1_25mm_locking_horizontal_smd) |
| [Conn_01x05_P2.0mm_Socket_Vertical_PTH (SparkFun)](https://partreel.com/p/sparkfun_conn_01x05_p2_0mm_socket_vertical_pth/) | `Conn_01x05_P2.0mm_Socket_Vertical_PTH` | SparkFun Electronics | [sparkfun_conn_01x05_p2_0mm_socket_vertical_pth](library/connector/sparkfun/sparkfun_conn_01x05_p2_0mm_socket_vertical_pth) |
| [Conn_01x05_P2.0mm_Socket_Vertical_SMD_Pin1RightUp (SparkFun)](https://partreel.com/p/sparkfun_conn_01x05_p2_0mm_socket_vertical_smd_pin1rightup/) | `Conn_01x05_P2.0mm_Socket_Vertical_SMD_Pin1RightUp` | SparkFun Electronics | [sparkfun_conn_01x05_p2_0mm_socket_vertical_smd_pin1rightup](library/connector/sparkfun/sparkfun_conn_01x05_p2_0mm_socket_vertical_smd_pin1rightup) |
| [Conn_01x06_JST_P1.0mm_Horizontal_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x06_jst_p1_0mm_horizontal_smd/) | `Conn_01x06_JST_P1.0mm_Horizontal_SMD` | SparkFun Electronics | [sparkfun_conn_01x06_jst_p1_0mm_horizontal_smd](library/connector/sparkfun/sparkfun_conn_01x06_jst_p1_0mm_horizontal_smd) |
| [Conn_01x06_JST_P1.0mm_Vertical_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x06_jst_p1_0mm_vertical_smd/) | `Conn_01x06_JST_P1.0mm_Vertical_SMD` | SparkFun Electronics | [sparkfun_conn_01x06_jst_p1_0mm_vertical_smd](library/connector/sparkfun/sparkfun_conn_01x06_jst_p1_0mm_vertical_smd) |
| [Conn_01x06_JST_P1.25mm_Locking_Horizontal_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x06_jst_p1_25mm_locking_horizontal_smd/) | `Conn_01x06_JST_P1.25mm_Locking_Horizontal_SMD` | SparkFun Electronics | [sparkfun_conn_01x06_jst_p1_25mm_locking_horizontal_smd](library/connector/sparkfun/sparkfun_conn_01x06_jst_p1_25mm_locking_horizontal_smd) |
| [Conn_01x06_P2.54mm_Socket_Vertical_SMD_Combined (SparkFun)](https://partreel.com/p/sparkfun_conn_01x06_p2_54mm_socket_vertical_smd_combined/) | `Conn_01x06_P2.54mm_Socket_Vertical_SMD_Combined` | SparkFun Electronics | [sparkfun_conn_01x06_p2_54mm_socket_vertical_smd_combined](library/connector/sparkfun/sparkfun_conn_01x06_p2_54mm_socket_vertical_smd_combined) |
| [Conn_01x06_P2.54mm_Socket_Vertical_SMD_Pin1RightDown (SparkFun)](https://partreel.com/p/sparkfun_conn_01x06_p2_54mm_socket_vertical_smd_pin1rightdown/) | `Conn_01x06_P2.54mm_Socket_Vertical_SMD_Pin1RightDown` | SparkFun Electronics | [sparkfun_conn_01x06_p2_54mm_socket_vertical_smd_pin1rightdown](library/connector/sparkfun/sparkfun_conn_01x06_p2_54mm_socket_vertical_smd_pin1rightdown) |
| [Conn_01x06_P2.54mm_Socket_Vertical_SMD_Pin1RightDown_Passthru (SparkFun)](https://partreel.com/p/sparkfun_conn_01x06_p2_54mm_socket_vertical_smd_pin1rightdown_passthru/) | `Conn_01x06_P2.54mm_Socket_Vertical_SMD_Pin1RightDown_Passthru` | SparkFun Electronics | [sparkfun_conn_01x06_p2_54mm_socket_vertical_smd_pin1rightdown_passthru](library/connector/sparkfun/sparkfun_conn_01x06_p2_54mm_socket_vertical_smd_pin1rightdown_passthru) |
| [Conn_01x07_JST_P1.25mm_Locking_Horizontal_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x07_jst_p1_25mm_locking_horizontal_smd/) | `Conn_01x07_JST_P1.25mm_Locking_Horizontal_SMD` | SparkFun Electronics | [sparkfun_conn_01x07_jst_p1_25mm_locking_horizontal_smd](library/connector/sparkfun/sparkfun_conn_01x07_jst_p1_25mm_locking_horizontal_smd) |
| [Conn_01x07_P2.0mm_Socket_Vertical_PTH (SparkFun)](https://partreel.com/p/sparkfun_conn_01x07_p2_0mm_socket_vertical_pth/) | `Conn_01x07_P2.0mm_Socket_Vertical_PTH` | SparkFun Electronics | [sparkfun_conn_01x07_p2_0mm_socket_vertical_pth](library/connector/sparkfun/sparkfun_conn_01x07_p2_0mm_socket_vertical_pth) |
| [Conn_01x07_P2.0mm_Socket_Vertical_SMD_Pin1RightUp (SparkFun)](https://partreel.com/p/sparkfun_conn_01x07_p2_0mm_socket_vertical_smd_pin1rightup/) | `Conn_01x07_P2.0mm_Socket_Vertical_SMD_Pin1RightUp` | SparkFun Electronics | [sparkfun_conn_01x07_p2_0mm_socket_vertical_smd_pin1rightup](library/connector/sparkfun/sparkfun_conn_01x07_p2_0mm_socket_vertical_smd_pin1rightup) |
| [Conn_01x08_FPC_P1.0mm_Horizontal_DualContact_LIF (SparkFun)](https://partreel.com/p/sparkfun_conn_01x08_fpc_p1_0mm_horizontal_dualcontact_lif/) | `Conn_01x08_FPC_P1.0mm_Horizontal_DualContact_LIF` | SparkFun Electronics | [sparkfun_conn_01x08_fpc_p1_0mm_horizontal_dualcontact_lif](library/connector/sparkfun/sparkfun_conn_01x08_fpc_p1_0mm_horizontal_dualcontact_lif) |
| [Conn_01x08_JST_P1.0mm_Horizontal_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x08_jst_p1_0mm_horizontal_smd/) | `Conn_01x08_JST_P1.0mm_Horizontal_SMD` | SparkFun Electronics | [sparkfun_conn_01x08_jst_p1_0mm_horizontal_smd](library/connector/sparkfun/sparkfun_conn_01x08_jst_p1_0mm_horizontal_smd) |
| [Conn_01x08_JST_P1.25mm_Locking_Horizontal_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x08_jst_p1_25mm_locking_horizontal_smd/) | `Conn_01x08_JST_P1.25mm_Locking_Horizontal_SMD` | SparkFun Electronics | [sparkfun_conn_01x08_jst_p1_25mm_locking_horizontal_smd](library/connector/sparkfun/sparkfun_conn_01x08_jst_p1_25mm_locking_horizontal_smd) |
| [Conn_01x08_P2.54mm_Socket_Vertical_SMD_Combined (SparkFun)](https://partreel.com/p/sparkfun_conn_01x08_p2_54mm_socket_vertical_smd_combined/) | `Conn_01x08_P2.54mm_Socket_Vertical_SMD_Combined` | SparkFun Electronics | [sparkfun_conn_01x08_p2_54mm_socket_vertical_smd_combined](library/connector/sparkfun/sparkfun_conn_01x08_p2_54mm_socket_vertical_smd_combined) |
| [Conn_01x08_P2.54mm_Socket_Vertical_SMD_Pin1RightDown (SparkFun)](https://partreel.com/p/sparkfun_conn_01x08_p2_54mm_socket_vertical_smd_pin1rightdown/) | `Conn_01x08_P2.54mm_Socket_Vertical_SMD_Pin1RightDown` | SparkFun Electronics | [sparkfun_conn_01x08_p2_54mm_socket_vertical_smd_pin1rightdown](library/connector/sparkfun/sparkfun_conn_01x08_p2_54mm_socket_vertical_smd_pin1rightdown) |
| [Conn_01x08_P2.54mm_Socket_Vertical_SMD_Pin1RightDown_Passthru (SparkFun)](https://partreel.com/p/sparkfun_conn_01x08_p2_54mm_socket_vertical_smd_pin1rightdown_passthru/) | `Conn_01x08_P2.54mm_Socket_Vertical_SMD_Pin1RightDown_Passthru` | SparkFun Electronics | [sparkfun_conn_01x08_p2_54mm_socket_vertical_smd_pin1rightdown_passthru](library/connector/sparkfun/sparkfun_conn_01x08_p2_54mm_socket_vertical_smd_pin1rightdown_passthru) |
| [Conn_01x09_JST_P1.0mm_Horizontal_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x09_jst_p1_0mm_horizontal_smd/) | `Conn_01x09_JST_P1.0mm_Horizontal_SMD` | SparkFun Electronics | [sparkfun_conn_01x09_jst_p1_0mm_horizontal_smd](library/connector/sparkfun/sparkfun_conn_01x09_jst_p1_0mm_horizontal_smd) |
| [Conn_01x09_JST_P1.25mm_Locking_Horizontal_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x09_jst_p1_25mm_locking_horizontal_smd/) | `Conn_01x09_JST_P1.25mm_Locking_Horizontal_SMD` | SparkFun Electronics | [sparkfun_conn_01x09_jst_p1_25mm_locking_horizontal_smd](library/connector/sparkfun/sparkfun_conn_01x09_jst_p1_25mm_locking_horizontal_smd) |
| [Conn_01x10_FPC_P1.0mm_Horizontal_DualContact_LIF (SparkFun)](https://partreel.com/p/sparkfun_conn_01x10_fpc_p1_0mm_horizontal_dualcontact_lif/) | `Conn_01x10_FPC_P1.0mm_Horizontal_DualContact_LIF` | SparkFun Electronics | [sparkfun_conn_01x10_fpc_p1_0mm_horizontal_dualcontact_lif](library/connector/sparkfun/sparkfun_conn_01x10_fpc_p1_0mm_horizontal_dualcontact_lif) |
| [Conn_01x10_JST_P1.0mm_Horizontal_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x10_jst_p1_0mm_horizontal_smd/) | `Conn_01x10_JST_P1.0mm_Horizontal_SMD` | SparkFun Electronics | [sparkfun_conn_01x10_jst_p1_0mm_horizontal_smd](library/connector/sparkfun/sparkfun_conn_01x10_jst_p1_0mm_horizontal_smd) |
| [Conn_01x10_JST_P1.25mm_Locking_Horizontal_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x10_jst_p1_25mm_locking_horizontal_smd/) | `Conn_01x10_JST_P1.25mm_Locking_Horizontal_SMD` | SparkFun Electronics | [sparkfun_conn_01x10_jst_p1_25mm_locking_horizontal_smd](library/connector/sparkfun/sparkfun_conn_01x10_jst_p1_25mm_locking_horizontal_smd) |
| [Conn_01x10_P2.54mm_Socket_Vertical_SMD_Combined (SparkFun)](https://partreel.com/p/sparkfun_conn_01x10_p2_54mm_socket_vertical_smd_combined/) | `Conn_01x10_P2.54mm_Socket_Vertical_SMD_Combined` | SparkFun Electronics | [sparkfun_conn_01x10_p2_54mm_socket_vertical_smd_combined](library/connector/sparkfun/sparkfun_conn_01x10_p2_54mm_socket_vertical_smd_combined) |
| [Conn_01x10_P2.54mm_Socket_Vertical_SMD_Pin1RightDown (SparkFun)](https://partreel.com/p/sparkfun_conn_01x10_p2_54mm_socket_vertical_smd_pin1rightdown/) | `Conn_01x10_P2.54mm_Socket_Vertical_SMD_Pin1RightDown` | SparkFun Electronics | [sparkfun_conn_01x10_p2_54mm_socket_vertical_smd_pin1rightdown](library/connector/sparkfun/sparkfun_conn_01x10_p2_54mm_socket_vertical_smd_pin1rightdown) |
| [Conn_01x10_P2.54mm_Socket_Vertical_SMD_Pin1RightDown_Passthru (SparkFun)](https://partreel.com/p/sparkfun_conn_01x10_p2_54mm_socket_vertical_smd_pin1rightdown_passthru/) | `Conn_01x10_P2.54mm_Socket_Vertical_SMD_Pin1RightDown_Passthru` | SparkFun Electronics | [sparkfun_conn_01x10_p2_54mm_socket_vertical_smd_pin1rightdown_passthru](library/connector/sparkfun/sparkfun_conn_01x10_p2_54mm_socket_vertical_smd_pin1rightdown_passthru) |
| [Conn_01x12_JST_P1.0mm_Horizontal_SMD (SparkFun)](https://partreel.com/p/sparkfun_conn_01x12_jst_p1_0mm_horizontal_smd/) | `Conn_01x12_JST_P1.0mm_Horizontal_SMD` | SparkFun Electronics | [sparkfun_conn_01x12_jst_p1_0mm_horizontal_smd](library/connector/sparkfun/sparkfun_conn_01x12_jst_p1_0mm_horizontal_smd) |
| [Conn_01x16_FPC_P0.5mm_Horizontal_DualContact (SparkFun)](https://partreel.com/p/sparkfun_conn_01x16_fpc_p0_5mm_horizontal_dualcontact/) | `Conn_01x16_FPC_P0.5mm_Horizontal_DualContact` | SparkFun Electronics | [sparkfun_conn_01x16_fpc_p0_5mm_horizontal_dualcontact](library/connector/sparkfun/sparkfun_conn_01x16_fpc_p0_5mm_horizontal_dualcontact) |
| [Conn_01x20_SMD_Pin1RightUp (SparkFun)](https://partreel.com/p/sparkfun_conn_01x20_smd_pin1rightup/) | `Conn_01x20_SMD_Pin1RightUp` | SparkFun Electronics | [sparkfun_conn_01x20_smd_pin1rightup](library/connector/sparkfun/sparkfun_conn_01x20_smd_pin1rightup) |
| [Conn_01x22_FPC_P0.5mm_Vertical_LowerContact (SparkFun)](https://partreel.com/p/sparkfun_conn_01x22_fpc_p0_5mm_vertical_lowercontact/) | `Conn_01x22_FPC_P0.5mm_Vertical_LowerContact` | SparkFun Electronics | [sparkfun_conn_01x22_fpc_p0_5mm_vertical_lowercontact](library/connector/sparkfun/sparkfun_conn_01x22_fpc_p0_5mm_vertical_lowercontact) |
| [Conn_01x24_FPC_P0.5mm_Horizontal_BottomContact (SparkFun)](https://partreel.com/p/sparkfun_conn_01x24_fpc_p0_5mm_horizontal_bottomcontact/) | `Conn_01x24_FPC_P0.5mm_Horizontal_BottomContact` | SparkFun Electronics | [sparkfun_conn_01x24_fpc_p0_5mm_horizontal_bottomcontact](library/connector/sparkfun/sparkfun_conn_01x24_fpc_p0_5mm_horizontal_bottomcontact) |
| [Conn_01x24_FPC_P0.5mm_Horizontal_DualContact (SparkFun)](https://partreel.com/p/sparkfun_conn_01x24_fpc_p0_5mm_horizontal_dualcontact/) | `Conn_01x24_FPC_P0.5mm_Horizontal_DualContact` | SparkFun Electronics | [sparkfun_conn_01x24_fpc_p0_5mm_horizontal_dualcontact](library/connector/sparkfun/sparkfun_conn_01x24_fpc_p0_5mm_horizontal_dualcontact) |
| [Debug-Cortex-2x5_P1.27mm-SMD-Unshrouded (SparkFun)](https://partreel.com/p/sparkfun_debug_cortex_2x5_p1_27mm_smd_unshrouded/) | `Debug-Cortex-2x5_P1.27mm-SMD-Unshrouded` | SparkFun Electronics | [sparkfun_debug_cortex_2x5_p1_27mm_smd_unshrouded](library/connector/sparkfun/sparkfun_debug_cortex_2x5_p1_27mm_smd_unshrouded) |
| [JST GH 10-pin (BM10B-GHS-TBT)](https://partreel.com/p/jst_gh_10pin/) | `BM10B-GHS-TBT` | JST | [jst_gh_10pin](library/connector/jst/gh/jst_gh_10pin) |
| [JST GH 11-pin (BM11B-GHS-TBT)](https://partreel.com/p/jst_gh_11pin/) | `BM11B-GHS-TBT` | JST | [jst_gh_11pin](library/connector/jst/gh/jst_gh_11pin) |
| [JST GH 12-pin (BM12B-GHS-TBT)](https://partreel.com/p/jst_gh_12pin/) | `BM12B-GHS-TBT` | JST | [jst_gh_12pin](library/connector/jst/gh/jst_gh_12pin) |
| [JST GH 2-pin (BM02B-GHS-TBT)](https://partreel.com/p/jst_gh_2pin/) | `BM02B-GHS-TBT` | JST | [jst_gh_2pin](library/connector/jst/gh/jst_gh_2pin) |
| [JST GH 3-pin (BM03B-GHS-TBT)](https://partreel.com/p/jst_gh_3pin/) | `BM03B-GHS-TBT` | JST | [jst_gh_3pin](library/connector/jst/gh/jst_gh_3pin) |
| [JST GH 4-pin (BM04B-GHS-TBT)](https://partreel.com/p/jst_gh_4pin/) | `BM04B-GHS-TBT` | JST | [jst_gh_4pin](library/connector/jst/gh/jst_gh_4pin) |
| [JST GH 5-pin (BM05B-GHS-TBT)](https://partreel.com/p/jst_gh_5pin/) | `BM05B-GHS-TBT` | JST | [jst_gh_5pin](library/connector/jst/gh/jst_gh_5pin) |
| [JST GH 6-pin (BM06B-GHS-TBT)](https://partreel.com/p/jst_gh_6pin/) | `BM06B-GHS-TBT` | JST | [jst_gh_6pin](library/connector/jst/gh/jst_gh_6pin) |
| [JST GH 7-pin (BM07B-GHS-TBT)](https://partreel.com/p/jst_gh_7pin/) | `BM07B-GHS-TBT` | JST | [jst_gh_7pin](library/connector/jst/gh/jst_gh_7pin) |
| [JST GH 8-pin (BM08B-GHS-TBT)](https://partreel.com/p/jst_gh_8pin/) | `BM08B-GHS-TBT` | JST | [jst_gh_8pin](library/connector/jst/gh/jst_gh_8pin) |
| [JST GH 9-pin (BM09B-GHS-TBT)](https://partreel.com/p/jst_gh_9pin/) | `BM09B-GHS-TBT` | JST | [jst_gh_9pin](library/connector/jst/gh/jst_gh_9pin) |
| [JST PH 10-pin (B10B-PH-K-S)](https://partreel.com/p/jst_ph_10pin/) | `B10B-PH-K-S` | JST | [jst_ph_10pin](library/connector/jst/ph/jst_ph_10pin) |
| [JST PH 11-pin (B11B-PH-K-S)](https://partreel.com/p/jst_ph_11pin/) | `B11B-PH-K-S` | JST | [jst_ph_11pin](library/connector/jst/ph/jst_ph_11pin) |
| [JST PH 12-pin (B12B-PH-K-S)](https://partreel.com/p/jst_ph_12pin/) | `B12B-PH-K-S` | JST | [jst_ph_12pin](library/connector/jst/ph/jst_ph_12pin) |
| [JST PH 13-pin (B13B-PH-K-S)](https://partreel.com/p/jst_ph_13pin/) | `B13B-PH-K-S` | JST | [jst_ph_13pin](library/connector/jst/ph/jst_ph_13pin) |
| [JST PH 14-pin (B14B-PH-K-S)](https://partreel.com/p/jst_ph_14pin/) | `B14B-PH-K-S` | JST | [jst_ph_14pin](library/connector/jst/ph/jst_ph_14pin) |
| [JST PH 15-pin (B15B-PH-K-S)](https://partreel.com/p/jst_ph_15pin/) | `B15B-PH-K-S` | JST | [jst_ph_15pin](library/connector/jst/ph/jst_ph_15pin) |
| [JST PH 16-pin (B16B-PH-K-S)](https://partreel.com/p/jst_ph_16pin/) | `B16B-PH-K-S` | JST | [jst_ph_16pin](library/connector/jst/ph/jst_ph_16pin) |
| [JST PH 2-pin (B2B-PH-K-S)](https://partreel.com/p/jst_ph_2pin/) | `B2B-PH-K-S` | JST | [jst_ph_2pin](library/connector/jst/ph/jst_ph_2pin) |
| [JST PH 3-pin (B3B-PH-K-S)](https://partreel.com/p/jst_ph_3pin/) | `B3B-PH-K-S` | JST | [jst_ph_3pin](library/connector/jst/ph/jst_ph_3pin) |
| [JST PH 4-pin (B4B-PH-K-S)](https://partreel.com/p/jst_ph_4pin/) | `B4B-PH-K-S` | JST | [jst_ph_4pin](library/connector/jst/ph/jst_ph_4pin) |
| [JST PH 5-pin (B5B-PH-K-S)](https://partreel.com/p/jst_ph_5pin/) | `B5B-PH-K-S` | JST | [jst_ph_5pin](library/connector/jst/ph/jst_ph_5pin) |
| [JST PH 6-pin (B6B-PH-K-S)](https://partreel.com/p/jst_ph_6pin/) | `B6B-PH-K-S` | JST | [jst_ph_6pin](library/connector/jst/ph/jst_ph_6pin) |
| [JST PH 7-pin (B7B-PH-K-S)](https://partreel.com/p/jst_ph_7pin/) | `B7B-PH-K-S` | JST | [jst_ph_7pin](library/connector/jst/ph/jst_ph_7pin) |
| [JST PH 8-pin (B8B-PH-K-S)](https://partreel.com/p/jst_ph_8pin/) | `B8B-PH-K-S` | JST | [jst_ph_8pin](library/connector/jst/ph/jst_ph_8pin) |
| [JST PH 9-pin (B9B-PH-K-S)](https://partreel.com/p/jst_ph_9pin/) | `B9B-PH-K-S` | JST | [jst_ph_9pin](library/connector/jst/ph/jst_ph_9pin) |
| [JST XH 10-pin (B10B-XH-A)](https://partreel.com/p/jst_xh_10pin/) | `B10B-XH-A` | JST | [jst_xh_10pin](library/connector/jst/xh/jst_xh_10pin) |
| [JST XH 11-pin (B11B-XH-A)](https://partreel.com/p/jst_xh_11pin/) | `B11B-XH-A` | JST | [jst_xh_11pin](library/connector/jst/xh/jst_xh_11pin) |
| [JST XH 12-pin (B12B-XH-A)](https://partreel.com/p/jst_xh_12pin/) | `B12B-XH-A` | JST | [jst_xh_12pin](library/connector/jst/xh/jst_xh_12pin) |
| [JST XH 13-pin (B13B-XH-A)](https://partreel.com/p/jst_xh_13pin/) | `B13B-XH-A` | JST | [jst_xh_13pin](library/connector/jst/xh/jst_xh_13pin) |
| [JST XH 14-pin (B14B-XH-A)](https://partreel.com/p/jst_xh_14pin/) | `B14B-XH-A` | JST | [jst_xh_14pin](library/connector/jst/xh/jst_xh_14pin) |
| [JST XH 15-pin (B15B-XH-A)](https://partreel.com/p/jst_xh_15pin/) | `B15B-XH-A` | JST | [jst_xh_15pin](library/connector/jst/xh/jst_xh_15pin) |
| [JST XH 16-pin (B16B-XH-A)](https://partreel.com/p/jst_xh_16pin/) | `B16B-XH-A` | JST | [jst_xh_16pin](library/connector/jst/xh/jst_xh_16pin) |
| [JST XH 2-pin (B2B-XH-A)](https://partreel.com/p/jst_xh_2pin/) | `B2B-XH-A` | JST | [jst_xh_2pin](library/connector/jst/xh/jst_xh_2pin) |
| [JST XH 3-pin (B3B-XH-A)](https://partreel.com/p/jst_xh_3pin/) | `B3B-XH-A` | JST | [jst_xh_3pin](library/connector/jst/xh/jst_xh_3pin) |
| [JST XH 4-pin (B4B-XH-A)](https://partreel.com/p/jst_xh_4pin/) | `B4B-XH-A` | JST | [jst_xh_4pin](library/connector/jst/xh/jst_xh_4pin) |
| [JST XH 5-pin (B5B-XH-A)](https://partreel.com/p/jst_xh_5pin/) | `B5B-XH-A` | JST | [jst_xh_5pin](library/connector/jst/xh/jst_xh_5pin) |
| [JST XH 6-pin (B6B-XH-A)](https://partreel.com/p/jst_xh_6pin/) | `B6B-XH-A` | JST | [jst_xh_6pin](library/connector/jst/xh/jst_xh_6pin) |
| [JST XH 7-pin (B7B-XH-A)](https://partreel.com/p/jst_xh_7pin/) | `B7B-XH-A` | JST | [jst_xh_7pin](library/connector/jst/xh/jst_xh_7pin) |
| [JST XH 8-pin (B8B-XH-A)](https://partreel.com/p/jst_xh_8pin/) | `B8B-XH-A` | JST | [jst_xh_8pin](library/connector/jst/xh/jst_xh_8pin) |
| [JST XH 9-pin (B9B-XH-A)](https://partreel.com/p/jst_xh_9pin/) | `B9B-XH-A` | JST | [jst_xh_9pin](library/connector/jst/xh/jst_xh_9pin) |
| [Pin Header 2.54mm 4-pin (PinHeader_1x04_P2.54mm)](https://partreel.com/p/pin_header_254_4pin/) | `PinHeader_1x04_P2.54mm` | Generic | [pin_header_254_4pin](library/connector/header/p254/pin_header_254_4pin) |
| [Pin Header 2.54mm 7-pin (PinHeader_1x07_P2.54mm)](https://partreel.com/p/pin_header_254_7pin/) | `PinHeader_1x07_P2.54mm` | Generic | [pin_header_254_7pin](library/connector/header/p254/pin_header_254_7pin) |
| [Qwiic_Horizontal (SparkFun)](https://partreel.com/p/sparkfun_qwiic_horizontal/) | `Qwiic_Horizontal` | SparkFun Electronics | [sparkfun_qwiic_horizontal](library/connector/sparkfun/sparkfun_qwiic_horizontal) |
| [Qwiic_Vertical (SparkFun)](https://partreel.com/p/sparkfun_qwiic_vertical/) | `Qwiic_Vertical` | SparkFun Electronics | [sparkfun_qwiic_vertical](library/connector/sparkfun/sparkfun_qwiic_vertical) |
| [RJ45_MagJack_PoE (SparkFun)](https://partreel.com/p/sparkfun_rj45_magjack_poe/) | `RJ45_MagJack_PoE` | SparkFun Electronics | [sparkfun_rj45_magjack_poe](library/connector/sparkfun/sparkfun_rj45_magjack_poe) |
| [Raspberry_Pi_2x20_PTH (SparkFun)](https://partreel.com/p/sparkfun_raspberry_pi_2x20_pth/) | `Raspberry_Pi_2x20_PTH` | SparkFun Electronics | [sparkfun_raspberry_pi_2x20_pth](library/connector/sparkfun/sparkfun_raspberry_pi_2x20_pth) |
| [Raspberry_Pi_2x20_PTH_NoSilk (SparkFun)](https://partreel.com/p/sparkfun_raspberry_pi_2x20_pth_nosilk/) | `Raspberry_Pi_2x20_PTH_NoSilk` | SparkFun Electronics | [sparkfun_raspberry_pi_2x20_pth_nosilk](library/connector/sparkfun/sparkfun_raspberry_pi_2x20_pth_nosilk) |
| [Raspberry_Pi_2x20_PTH_SMD_Pass_Through_Top_Mount (SparkFun)](https://partreel.com/p/sparkfun_raspberry_pi_2x20_pth_smd_pass_through_top_mount/) | `Raspberry_Pi_2x20_PTH_SMD_Pass_Through_Top_Mount` | SparkFun Electronics | [sparkfun_raspberry_pi_2x20_pth_smd_pass_through_top_mount](library/connector/sparkfun/sparkfun_raspberry_pi_2x20_pth_smd_pass_through_top_mount) |
| [Screw Terminal 5.08mm 2-pin (KF301-5.08-2P)](https://partreel.com/p/screw_terminal_5_08_2pin/) | `KF301-5.08-2P` | Generic (KF301) | [screw_terminal_5_08_2pin](library/connector/terminal/screw_5_08/screw_terminal_5_08_2pin) |
| [Screw Terminal 5.08mm 3-pin (KF301-5.08-3P)](https://partreel.com/p/screw_terminal_5_08_3pin/) | `KF301-5.08-3P` | Generic (KF301) | [screw_terminal_5_08_3pin](library/connector/terminal/screw_5_08/screw_terminal_5_08_3pin) |
| [Screw Terminal 5.08mm 4-pin (KF301-5.08-4P)](https://partreel.com/p/screw_terminal_5_08_4pin/) | `KF301-5.08-4P` | Generic (KF301) | [screw_terminal_5_08_4pin](library/connector/terminal/screw_5_08/screw_terminal_5_08_4pin) |
| [Screw Terminal 5.08mm 5-pin (KF301-5.08-5P)](https://partreel.com/p/screw_terminal_5_08_5pin/) | `KF301-5.08-5P` | Generic (KF301) | [screw_terminal_5_08_5pin](library/connector/terminal/screw_5_08/screw_terminal_5_08_5pin) |
| [Screw Terminal 5.08mm 6-pin (KF301-5.08-6P)](https://partreel.com/p/screw_terminal_5_08_6pin/) | `KF301-5.08-6P` | Generic (KF301) | [screw_terminal_5_08_6pin](library/connector/terminal/screw_5_08/screw_terminal_5_08_6pin) |
| [Screw Terminal 5.08mm 7-pin (KF301-5.08-7P)](https://partreel.com/p/screw_terminal_5_08_7pin/) | `KF301-5.08-7P` | Generic (KF301) | [screw_terminal_5_08_7pin](library/connector/terminal/screw_5_08/screw_terminal_5_08_7pin) |
| [Screw Terminal 5.08mm 8-pin (KF301-5.08-8P)](https://partreel.com/p/screw_terminal_5_08_8pin/) | `KF301-5.08-8P` | Generic (KF301) | [screw_terminal_5_08_8pin](library/connector/terminal/screw_5_08/screw_terminal_5_08_8pin) |
| [ScrewCage_1x10_P3.5mm_Green (SparkFun)](https://partreel.com/p/sparkfun_screwcage_1x10_p3_5mm_green/) | `ScrewCage_1x10_P3.5mm_Green` | SparkFun Electronics | [sparkfun_screwcage_1x10_p3_5mm_green](library/connector/sparkfun/sparkfun_screwcage_1x10_p3_5mm_green) |
| [ScrewTerminal_1x02_P3.5mm_Horizontal_Black (SparkFun)](https://partreel.com/p/sparkfun_screwterminal_1x02_p3_5mm_horizontal_black/) | `ScrewTerminal_1x02_P3.5mm_Horizontal_Black` | SparkFun Electronics | [sparkfun_screwterminal_1x02_p3_5mm_horizontal_black](library/connector/sparkfun/sparkfun_screwterminal_1x02_p3_5mm_horizontal_black) |
| [ScrewTerminal_1x03_P3.5mm_Horizontal_Black (SparkFun)](https://partreel.com/p/sparkfun_screwterminal_1x03_p3_5mm_horizontal_black/) | `ScrewTerminal_1x03_P3.5mm_Horizontal_Black` | SparkFun Electronics | [sparkfun_screwterminal_1x03_p3_5mm_horizontal_black](library/connector/sparkfun/sparkfun_screwterminal_1x03_p3_5mm_horizontal_black) |
| [USB Type-C Receptacle 16-pin (USB 2.0)](https://partreel.com/p/usb_c_16p/) | `TYPE-C-31-M-12` | HRO / Generic | [usb_c_16p](library/connector/usb/usb_c_16p/usb_c_16p) |
| [USB_C_Receptacle (SparkFun)](https://partreel.com/p/sparkfun_usb_c_receptacle/) | `USB_C_Receptacle` | SparkFun Electronics | [sparkfun_usb_c_receptacle](library/connector/sparkfun/sparkfun_usb_c_receptacle) |
| [microSD Card Socket (push-push)](https://partreel.com/p/microsd_hc/) | `DM3AT-SF-PEJM5` | Hirose / Generic | [microsd_hc](library/connector/card/microsd_hc/microsd_hc) |
| [microSD_Friction (SparkFun)](https://partreel.com/p/sparkfun_microsd_friction/) | `microSD_Friction` | SparkFun Electronics | [sparkfun_microsd_friction](library/connector/sparkfun/sparkfun_microsd_friction) |
| [microSD_PushPush (SparkFun)](https://partreel.com/p/sparkfun_microsd_pushpush/) | `microSD_PushPush` | SparkFun Electronics | [sparkfun_microsd_pushpush](library/connector/sparkfun/sparkfun_microsd_pushpush) |

### ic (22)

| Part | MPN | Manufacturer | Files |
|---|---|---|---|
| [A4988 Microstepping Motor Driver](https://partreel.com/p/a4988/) | `A4988SETTR-T` | Allegro MicroSystems | [a4988](library/ic/driver/a4988/a4988) |
| [AS5600 Magnetic Angle Sensor](https://partreel.com/p/as5600/) | `AS5600-ASOT` | ams-OSRAM | [as5600](library/ic/sensor_if/as5600/as5600) |
| [BH1750FVI Ambient Light Sensor](https://partreel.com/p/bh1750/) | `BH1750FVI-TR` | Rohm | [bh1750](library/ic/sensor_if/bh1750/bh1750) |
| [CN3791 MPPT Solar Li-Ion Charger](https://partreel.com/p/cn3791/) | `CN3791` | Consonance | [cn3791](library/ic/power/cn3791/cn3791) |
| [DRV8825 Stepper Motor Driver](https://partreel.com/p/drv8825/) | `DRV8825PWP` | Texas Instruments | [drv8825](library/ic/driver/drv8825/drv8825) |
| [HT7330-A Low-Power LDO 3.0V](https://partreel.com/p/ht7330/) | `HT7330-A` | Holtek | [ht7330](library/ic/regulator/ht7330/ht7330) |
| [HT7333-A Low-Power LDO 3.3V](https://partreel.com/p/ht7333/) | `HT7333-A` | Holtek | [ht7333](library/ic/regulator/ht7333/ht7333) |
| [HT7350-A Low-Power LDO 5.0V](https://partreel.com/p/ht7350/) | `HT7350-A` | Holtek | [ht7350](library/ic/regulator/ht7350/ht7350) |
| [HT7833 500mA LDO 3.3V](https://partreel.com/p/ht7833/) | `HT7833` | Holtek | [ht7833](library/ic/regulator/ht7833/ht7833) |
| [INMP441 I2S MEMS Microphone](https://partreel.com/p/inmp441/) | `INMP441ACEZ-R7` | TDK InvenSense | [inmp441](library/ic/audio/inmp441/inmp441) |
| [IP5306 Power Bank SoC](https://partreel.com/p/ip5306/) | `IP5306` | Injoinic | [ip5306](library/ic/power/ip5306/ip5306) |
| [MAX17048 LiPo Fuel Gauge](https://partreel.com/p/max17048/) | `MAX17048G+T10` | Maxim Integrated | [max17048](library/ic/power/max17048/max17048) |
| [MAX6675 Thermocouple-to-Digital Converter](https://partreel.com/p/max6675/) | `MAX6675ISA` | Maxim Integrated | [max6675](library/ic/sensor_if/max6675/max6675) |
| [MP1584EN 3A Buck Converter](https://partreel.com/p/mp1584/) | `MP1584EN` | MPS | [mp1584](library/ic/regulator/mp1584/mp1584) |
| [SY8008B 1A Buck Converter](https://partreel.com/p/sy8008/) | `SY8008BAAC` | Silergy | [sy8008](library/ic/regulator/sy8008/sy8008) |
| [SY8089A 2A Buck Converter](https://partreel.com/p/sy8089/) | `SY8089AAAC` | Silergy | [sy8089](library/ic/regulator/sy8089/sy8089) |
| [TM1637 LED Display Driver](https://partreel.com/p/tm1637/) | `TM1637` | Titan Micro | [tm1637](library/ic/driver/tm1637/tm1637) |
| [TP5100 1/2-Cell Switching Charger](https://partreel.com/p/tp5100/) | `TP5100` | NanJing TopPower | [tp5100](library/ic/power/tp5100/tp5100) |
| [TTP223-BA6 Touch Key IC](https://partreel.com/p/ttp223/) | `TTP223-BA6` | Tontek | [ttp223](library/ic/touch/ttp223/ttp223) |
| [TTP229-BSF 16-Key Touch IC](https://partreel.com/p/ttp229/) | `TTP229-BSF` | Tontek | [ttp229](library/ic/touch/ttp229/ttp229) |
| [W25Q64JV 64Mbit SPI Flash (SOIC-8 208mil)](https://partreel.com/p/w25q64jv/) | `W25Q64JVSSIQ` | Winbond | [w25q64jv](library/ic/memory/w25q64jv/w25q64jv) |
| [XL6009 4A Boost Converter](https://partreel.com/p/xl6009/) | `XL6009E1` | XLSEMI | [xl6009](library/ic/regulator/xl6009/xl6009) |

### module (42)

| Part | MPN | Manufacturer | Files |
|---|---|---|---|
| [0.96" SSD1306 I2C OLED Module (128x64)](https://partreel.com/p/ssd1306_module_096/) | `MC096VX` | Generic (LCDwiki MC096VX) | [ssd1306_module_096](library/module/display/ssd1306_module_096/ssd1306_module_096) |
| [1.28" GC9A01 Round LCD Module (240x240, SPI)](https://partreel.com/p/gc9a01_module_128/) | `MSP1281` | Generic (lcdwiki MSP1281) | [gc9a01_module_128](library/module/display/gc9a01_module_128/gc9a01_module_128) |
| [1.3" SH1106 I2C OLED Module (128x64)](https://partreel.com/p/sh1106_module_13/) | `MC130VX` | Generic (LCDwiki MC130VX) | [sh1106_module_13](library/module/display/sh1106_module_13/sh1106_module_13) |
| [1.3" ST7789 IPS TFT Module (240x240, SPI)](https://partreel.com/p/st7789_module_13/) | `MSP1308` | Generic (LCDwiki MSP1308) | [st7789_module_13](library/module/display/st7789_module_13/st7789_module_13) |
| [DAN-F10N (SparkFun)](https://partreel.com/p/sparkfun_dan_f10n/) | `DAN-F10N` | SparkFun Electronics | [sparkfun_dan_f10n](library/module/sparkfun/sparkfun_dan_f10n) |
| [DFPlayer Mini MP3 Player Module](https://partreel.com/p/dfplayer_mini/) | `DFR0299` | DFRobot | [dfplayer_mini](library/module/audio/dfplayer_mini/dfplayer_mini) |
| [ESP32-C5-WROOM-1 (SparkFun)](https://partreel.com/p/sparkfun_esp32_c5_wroom_1/) | `ESP32-C5-WROOM-1` | SparkFun Electronics | [sparkfun_esp32_c5_wroom_1](library/module/sparkfun/sparkfun_esp32_c5_wroom_1) |
| [ESP32-C5-WROOM-1-NARROW (SparkFun)](https://partreel.com/p/sparkfun_esp32_c5_wroom_1_narrow/) | `ESP32-C5-WROOM-1-NARROW` | SparkFun Electronics | [sparkfun_esp32_c5_wroom_1_narrow](library/module/sparkfun/sparkfun_esp32_c5_wroom_1_narrow) |
| [ESP32-DevKitC V4 Development Board](https://partreel.com/p/esp32_devkitc_v4/) | `ESP32-DevKitC-32E` | Espressif | [esp32_devkitc_v4](library/module/devboard/esp32_devkitc_v4/esp32_devkitc_v4) |
| [ESP32-PICO-V3-02 (SparkFun)](https://partreel.com/p/sparkfun_esp32_pico_v3_02/) | `ESP32-PICO-V3-02` | SparkFun Electronics | [sparkfun_esp32_pico_v3_02](library/module/sparkfun/sparkfun_esp32_pico_v3_02) |
| [ESP32-S3-MINI (SparkFun)](https://partreel.com/p/sparkfun_esp32_s3_mini/) | `ESP32-S3-MINI` | SparkFun Electronics | [sparkfun_esp32_s3_mini](library/module/sparkfun/sparkfun_esp32_s3_mini) |
| [ESP32-WROOM (SparkFun)](https://partreel.com/p/sparkfun_esp32_wroom/) | `ESP32-WROOM` | SparkFun Electronics | [sparkfun_esp32_wroom](library/module/sparkfun/sparkfun_esp32_wroom) |
| [ESP32-WROOM-32 Module](https://partreel.com/p/esp32_wroom32/) | `ESP32-WROOM-32` | Espressif | [esp32_wroom32](library/module/espressif/esp32_wroom32/esp32_wroom32) |
| [GNSS_Flex_Carrier_Left (SparkFun)](https://partreel.com/p/sparkfun_gnss_flex_carrier_left/) | `GNSS_Flex_Carrier_Left` | SparkFun Electronics | [sparkfun_gnss_flex_carrier_left](library/module/sparkfun/sparkfun_gnss_flex_carrier_left) |
| [GNSS_Flex_Carrier_Mid (SparkFun)](https://partreel.com/p/sparkfun_gnss_flex_carrier_mid/) | `GNSS_Flex_Carrier_Mid` | SparkFun Electronics | [sparkfun_gnss_flex_carrier_mid](library/module/sparkfun/sparkfun_gnss_flex_carrier_mid) |
| [GNSS_Flex_Carrier_Right (SparkFun)](https://partreel.com/p/sparkfun_gnss_flex_carrier_right/) | `GNSS_Flex_Carrier_Right` | SparkFun Electronics | [sparkfun_gnss_flex_carrier_right](library/module/sparkfun/sparkfun_gnss_flex_carrier_right) |
| [GNSS_Flex_Module_Left (SparkFun)](https://partreel.com/p/sparkfun_gnss_flex_module_left/) | `GNSS_Flex_Module_Left` | SparkFun Electronics | [sparkfun_gnss_flex_module_left](library/module/sparkfun/sparkfun_gnss_flex_module_left) |
| [GNSS_Flex_Module_Mid (SparkFun)](https://partreel.com/p/sparkfun_gnss_flex_module_mid/) | `GNSS_Flex_Module_Mid` | SparkFun Electronics | [sparkfun_gnss_flex_module_mid](library/module/sparkfun/sparkfun_gnss_flex_module_mid) |
| [GNSS_Flex_Module_Right (SparkFun)](https://partreel.com/p/sparkfun_gnss_flex_module_right/) | `GNSS_Flex_Module_Right` | SparkFun Electronics | [sparkfun_gnss_flex_module_right](library/module/sparkfun/sparkfun_gnss_flex_module_right) |
| [HC-05 Bluetooth Module (ZS-040)](https://partreel.com/p/hc05/) | `HC-05` | Generic (ZS-040) | [hc05](library/module/rf/hc05/hc05) |
| [HC-SR04 Ultrasonic Distance Sensor Module](https://partreel.com/p/hc_sr04/) | `HC-SR04` | Generic | [hc_sr04](library/module/sensor/hc_sr04/hc_sr04) |
| [HLK-LD2410C 24GHz mmWave Presence Radar](https://partreel.com/p/ld2410c/) | `HLK-LD2410C` | Hi-Link | [ld2410c](library/module/sensor/ld2410c/ld2410c) |
| [LC762Z (SparkFun)](https://partreel.com/p/sparkfun_lc762z/) | `LC762Z` | SparkFun Electronics | [sparkfun_lc762z](library/module/sparkfun/sparkfun_lc762z) |
| [LG290P (SparkFun)](https://partreel.com/p/sparkfun_lg290p/) | `LG290P` | SparkFun Electronics | [sparkfun_lg290p](library/module/sparkfun/sparkfun_lg290p) |
| [LG580P (SparkFun)](https://partreel.com/p/sparkfun_lg580p/) | `LG580P` | SparkFun Electronics | [sparkfun_lg580p](library/module/sparkfun/sparkfun_lg580p) |
| [MAX7219 8x8 LED Matrix Module (FC-16)](https://partreel.com/p/max7219_matrix_module/) | `FC-16 MAX7219` | Generic (FC-16) | [max7219_matrix_module](library/module/display/max7219_matrix_module/max7219_matrix_module) |
| [NEO-D9S (SparkFun)](https://partreel.com/p/sparkfun_neo_d9s/) | `NEO-D9S` | SparkFun Electronics | [sparkfun_neo_d9s](library/module/sparkfun/sparkfun_neo_d9s) |
| [NEO-F10N (SparkFun)](https://partreel.com/p/sparkfun_neo_f10n/) | `NEO-F10N` | SparkFun Electronics | [sparkfun_neo_f10n](library/module/sparkfun/sparkfun_neo_f10n) |
| [P23M (SparkFun)](https://partreel.com/p/sparkfun_p23m/) | `P23M` | SparkFun Electronics | [sparkfun_p23m](library/module/sparkfun/sparkfun_p23m) |
| [Power_Divider_BP2G1+ (SparkFun)](https://partreel.com/p/sparkfun_power_divider_bp2g1/) | `Power_Divider_BP2G1+` | SparkFun Electronics | [sparkfun_power_divider_bp2g1](library/module/sparkfun/sparkfun_power_divider_bp2g1) |
| [Power_Divider_BP2G1+_Bypass1 (SparkFun)](https://partreel.com/p/sparkfun_power_divider_bp2g1_bypass1/) | `Power_Divider_BP2G1+_Bypass1` | SparkFun Electronics | [sparkfun_power_divider_bp2g1_bypass1](library/module/sparkfun/sparkfun_power_divider_bp2g1_bypass1) |
| [Power_Divider_BP2G1+_Bypass2 (SparkFun)](https://partreel.com/p/sparkfun_power_divider_bp2g1_bypass2/) | `Power_Divider_BP2G1+_Bypass2` | SparkFun Electronics | [sparkfun_power_divider_bp2g1_bypass2](library/module/sparkfun/sparkfun_power_divider_bp2g1_bypass2) |
| [Power_Splitter_JPS-3-1+ (SparkFun)](https://partreel.com/p/sparkfun_power_splitter_jps_3_1/) | `Power_Splitter_JPS-3-1+` | SparkFun Electronics | [sparkfun_power_splitter_jps_3_1](library/module/sparkfun/sparkfun_power_splitter_jps_3_1) |
| [RC522 (SparkFun)](https://partreel.com/p/sparkfun_rc522/) | `RC522` | SparkFun Electronics | [sparkfun_rc522](library/module/sparkfun/sparkfun_rc522) |
| [RM2 (SparkFun)](https://partreel.com/p/sparkfun_rm2/) | `RM2` | SparkFun Electronics | [sparkfun_rm2](library/module/sparkfun/sparkfun_rm2) |
| [RM2_Tight (SparkFun)](https://partreel.com/p/sparkfun_rm2_tight/) | `RM2_Tight` | SparkFun Electronics | [sparkfun_rm2_tight](library/module/sparkfun/sparkfun_rm2_tight) |
| [SAW_Filter_1575MHz (SparkFun)](https://partreel.com/p/sparkfun_saw_filter_1575mhz/) | `SAW_Filter_1575MHz` | SparkFun Electronics | [sparkfun_saw_filter_1575mhz](library/module/sparkfun/sparkfun_saw_filter_1575mhz) |
| [SIM800L GSM/GPRS Module (Red Breakout)](https://partreel.com/p/sim800l/) | `SIM800L` | SIMCom (generic breakout) | [sim800l](library/module/rf/sim800l/sim800l) |
| [ZED-F9P (SparkFun)](https://partreel.com/p/sparkfun_zed_f9p/) | `ZED-F9P` | SparkFun Electronics | [sparkfun_zed_f9p](library/module/sparkfun/sparkfun_zed_f9p) |
| [ZED-F9T (SparkFun)](https://partreel.com/p/sparkfun_zed_f9t/) | `ZED-F9T` | SparkFun Electronics | [sparkfun_zed_f9t](library/module/sparkfun/sparkfun_zed_f9t) |
| [ZED-X20P (SparkFun)](https://partreel.com/p/sparkfun_zed_x20p/) | `ZED-X20P` | SparkFun Electronics | [sparkfun_zed_x20p](library/module/sparkfun/sparkfun_zed_x20p) |
| [mosaic-G5_P3 (SparkFun)](https://partreel.com/p/sparkfun_mosaic_g5_p3/) | `mosaic-G5_P3` | SparkFun Electronics | [sparkfun_mosaic_g5_p3](library/module/sparkfun/sparkfun_mosaic_g5_p3) |

### sensor (28)

| Part | MPN | Manufacturer | Files |
|---|---|---|---|
| [ADXL345 3-Axis Accelerometer](https://partreel.com/p/adxl345/) | `ADXL345BCCZ` | Analog Devices | [adxl345](library/sensor/adi/adxl345/adxl345) |
| [AHT10 Temperature and Humidity Sensor](https://partreel.com/p/aht10/) | `AHT10` | Aosong (ASAIR) | [aht10](library/sensor/asair/aht10/aht10) |
| [AHT20 Humidity and Temperature Sensor](https://partreel.com/p/aht20/) | `AHT20` | Aosong (ASAIR) | [aht20](library/sensor/asair/aht20/aht20) |
| [AHT21 Humidity and Temperature Sensor](https://partreel.com/p/aht21/) | `AHT21` | Aosong (ASAIR) | [aht21](library/sensor/asair/aht21/aht21) |
| [CAP1203 (SparkFun)](https://partreel.com/p/sparkfun_cap1203/) | `CAP1203` | SparkFun Electronics | [sparkfun_cap1203](library/sensor/sparkfun/sparkfun_cap1203) |
| [CY8CMBR3102 (SparkFun)](https://partreel.com/p/sparkfun_cy8cmbr3102/) | `CY8CMBR3102` | SparkFun Electronics | [sparkfun_cy8cmbr3102](library/sensor/sparkfun/sparkfun_cy8cmbr3102) |
| [FPC235x (SparkFun)](https://partreel.com/p/sparkfun_fpc235x/) | `FPC235x` | SparkFun Electronics | [sparkfun_fpc235x](library/sensor/sparkfun/sparkfun_fpc235x) |
| [HMC5883L 3-Axis Magnetometer](https://partreel.com/p/hmc5883l/) | `HMC5883L` | Honeywell | [hmc5883l](library/sensor/honeywell/hmc5883l/hmc5883l) |
| [HMC6343 (SparkFun)](https://partreel.com/p/sparkfun_hmc6343/) | `HMC6343` | SparkFun Electronics | [sparkfun_hmc6343](library/sensor/sparkfun/sparkfun_hmc6343) |
| [HX711 (SparkFun)](https://partreel.com/p/sparkfun_hx711/) | `HX711` | SparkFun Electronics | [sparkfun_hx711](library/sensor/sparkfun/sparkfun_hx711) |
| [IM19 (SparkFun)](https://partreel.com/p/sparkfun_im19/) | `IM19` | SparkFun Electronics | [sparkfun_im19](library/sensor/sparkfun/sparkfun_im19) |
| [LIS3DH (SparkFun)](https://partreel.com/p/sparkfun_lis3dh/) | `LIS3DH` | SparkFun Electronics | [sparkfun_lis3dh](library/sensor/sparkfun/sparkfun_lis3dh) |
| [LSM6DSOX (SparkFun)](https://partreel.com/p/sparkfun_lsm6dsox/) | `LSM6DSOX` | SparkFun Electronics | [sparkfun_lsm6dsox](library/sensor/sparkfun/sparkfun_lsm6dsox) |
| [MLX90614 IR Thermometer (TO-39)](https://partreel.com/p/mlx90614/) | `MLX90614ESF-BAA` | Melexis | [mlx90614](library/sensor/melexis/mlx90614/mlx90614) |
| [MPR121QR2 (SparkFun)](https://partreel.com/p/sparkfun_mpr121qr2/) | `MPR121QR2` | SparkFun Electronics | [sparkfun_mpr121qr2](library/sensor/sparkfun/sparkfun_mpr121qr2) |
| [MPU-6050 (SparkFun)](https://partreel.com/p/sparkfun_mpu_6050/) | `MPU-6050` | SparkFun Electronics | [sparkfun_mpu_6050](library/sensor/sparkfun/sparkfun_mpu_6050) |
| [MS8607-02BA (SparkFun)](https://partreel.com/p/sparkfun_ms8607_02ba/) | `MS8607-02BA` | SparkFun Electronics | [sparkfun_ms8607_02ba](library/sensor/sparkfun/sparkfun_ms8607_02ba) |
| [QMC5883L 3-Axis Magnetometer](https://partreel.com/p/qmc5883l/) | `QMC5883L` | QST | [qmc5883l](library/sensor/qst/qmc5883l/qmc5883l) |
| [SCD41 (SparkFun)](https://partreel.com/p/sparkfun_scd41/) | `SCD41` | SparkFun Electronics | [sparkfun_scd41](library/sensor/sparkfun/sparkfun_scd41) |
| [SGP40 VOC Air Quality Sensor](https://partreel.com/p/sgp40/) | `SGP40-D-R4` | Sensirion | [sgp40](library/sensor/sensirion/sgp40/sgp40) |
| [SHT40 (SparkFun)](https://partreel.com/p/sparkfun_sht40/) | `SHT40` | SparkFun Electronics | [sparkfun_sht40](library/sensor/sparkfun/sparkfun_sht40) |
| [SHTC3 (SparkFun)](https://partreel.com/p/sparkfun_shtc3/) | `SHTC3` | SparkFun Electronics | [sparkfun_shtc3](library/sensor/sparkfun/sparkfun_shtc3) |
| [STC31 (SparkFun)](https://partreel.com/p/sparkfun_stc31/) | `STC31` | SparkFun Electronics | [sparkfun_stc31](library/sensor/sparkfun/sparkfun_stc31) |
| [STCC4 (SparkFun)](https://partreel.com/p/sparkfun_stcc4/) | `STCC4` | SparkFun Electronics | [sparkfun_stcc4](library/sensor/sparkfun/sparkfun_stcc4) |
| [TMP102 (SparkFun)](https://partreel.com/p/sparkfun_tmp102/) | `TMP102` | SparkFun Electronics | [sparkfun_tmp102](library/sensor/sparkfun/sparkfun_tmp102) |
| [VCNL4040 (SparkFun)](https://partreel.com/p/sparkfun_vcnl4040/) | `VCNL4040` | SparkFun Electronics | [sparkfun_vcnl4040](library/sensor/sparkfun/sparkfun_vcnl4040) |
| [VEML7700 Ambient Light Sensor](https://partreel.com/p/veml7700/) | `VEML7700-TR` | Vishay | [veml7700](library/sensor/vishay/veml7700/veml7700) |
| [VEML7700-TT (SparkFun)](https://partreel.com/p/sparkfun_veml7700_tt/) | `VEML7700-TT` | SparkFun Electronics | [sparkfun_veml7700_tt](library/sensor/sparkfun/sparkfun_veml7700_tt) |

<!-- PARTS:END -->
