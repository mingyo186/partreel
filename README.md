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
Currently **75 parts**, all machine-verified (structure, KLC drawing rules, render completeness, 3D coplanar/merged-pin checks, STEP kernel) with datasheet-cited dimensions.

### connector (52)

| Part | MPN | Manufacturer | Files |
|---|---|---|---|
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
| [Screw Terminal 5.08mm 2-pin (KF301-5.08-2P)](https://partreel.com/p/screw_terminal_5_08_2pin/) | `KF301-5.08-2P` | Generic (KF301) | [screw_terminal_5_08_2pin](library/connector/terminal/screw_5_08/screw_terminal_5_08_2pin) |
| [Screw Terminal 5.08mm 3-pin (KF301-5.08-3P)](https://partreel.com/p/screw_terminal_5_08_3pin/) | `KF301-5.08-3P` | Generic (KF301) | [screw_terminal_5_08_3pin](library/connector/terminal/screw_5_08/screw_terminal_5_08_3pin) |
| [Screw Terminal 5.08mm 4-pin (KF301-5.08-4P)](https://partreel.com/p/screw_terminal_5_08_4pin/) | `KF301-5.08-4P` | Generic (KF301) | [screw_terminal_5_08_4pin](library/connector/terminal/screw_5_08/screw_terminal_5_08_4pin) |
| [Screw Terminal 5.08mm 5-pin (KF301-5.08-5P)](https://partreel.com/p/screw_terminal_5_08_5pin/) | `KF301-5.08-5P` | Generic (KF301) | [screw_terminal_5_08_5pin](library/connector/terminal/screw_5_08/screw_terminal_5_08_5pin) |
| [Screw Terminal 5.08mm 6-pin (KF301-5.08-6P)](https://partreel.com/p/screw_terminal_5_08_6pin/) | `KF301-5.08-6P` | Generic (KF301) | [screw_terminal_5_08_6pin](library/connector/terminal/screw_5_08/screw_terminal_5_08_6pin) |
| [Screw Terminal 5.08mm 7-pin (KF301-5.08-7P)](https://partreel.com/p/screw_terminal_5_08_7pin/) | `KF301-5.08-7P` | Generic (KF301) | [screw_terminal_5_08_7pin](library/connector/terminal/screw_5_08/screw_terminal_5_08_7pin) |
| [Screw Terminal 5.08mm 8-pin (KF301-5.08-8P)](https://partreel.com/p/screw_terminal_5_08_8pin/) | `KF301-5.08-8P` | Generic (KF301) | [screw_terminal_5_08_8pin](library/connector/terminal/screw_5_08/screw_terminal_5_08_8pin) |
| [USB Type-C Receptacle 16-pin (USB 2.0)](https://partreel.com/p/usb_c_16p/) | `TYPE-C-31-M-12` | HRO / Generic | [usb_c_16p](library/connector/usb/usb_c_16p/usb_c_16p) |
| [microSD Card Socket (push-push)](https://partreel.com/p/microsd_hc/) | `DM3AT-SF-PEJM5` | Hirose / Generic | [microsd_hc](library/connector/card/microsd_hc/microsd_hc) |

### ic (13)

| Part | MPN | Manufacturer | Files |
|---|---|---|---|
| [A4988 Microstepping Motor Driver](https://partreel.com/p/a4988/) | `A4988SETTR-T` | Allegro MicroSystems | [a4988](library/ic/driver/a4988/a4988) |
| [CN3791 MPPT Solar Li-Ion Charger](https://partreel.com/p/cn3791/) | `CN3791` | Consonance | [cn3791](library/ic/power/cn3791/cn3791) |
| [DRV8825 Stepper Motor Driver](https://partreel.com/p/drv8825/) | `DRV8825PWP` | Texas Instruments | [drv8825](library/ic/driver/drv8825/drv8825) |
| [HT7333-A Low-Power LDO 3.3V](https://partreel.com/p/ht7333/) | `HT7333-A` | Holtek | [ht7333](library/ic/regulator/ht7333/ht7333) |
| [HT7833 500mA LDO 3.3V](https://partreel.com/p/ht7833/) | `HT7833` | Holtek | [ht7833](library/ic/regulator/ht7833/ht7833) |
| [IP5306 Power Bank SoC](https://partreel.com/p/ip5306/) | `IP5306` | Injoinic | [ip5306](library/ic/power/ip5306/ip5306) |
| [MP1584EN 3A Buck Converter](https://partreel.com/p/mp1584/) | `MP1584EN` | MPS | [mp1584](library/ic/regulator/mp1584/mp1584) |
| [SY8008B 1A Buck Converter](https://partreel.com/p/sy8008/) | `SY8008BAAC` | Silergy | [sy8008](library/ic/regulator/sy8008/sy8008) |
| [SY8089A 2A Buck Converter](https://partreel.com/p/sy8089/) | `SY8089AAAC` | Silergy | [sy8089](library/ic/regulator/sy8089/sy8089) |
| [TP5100 1/2-Cell Switching Charger](https://partreel.com/p/tp5100/) | `TP5100` | NanJing TopPower | [tp5100](library/ic/power/tp5100/tp5100) |
| [TTP223-BA6 Touch Key IC](https://partreel.com/p/ttp223/) | `TTP223-BA6` | Tontek | [ttp223](library/ic/touch/ttp223/ttp223) |
| [TTP229-BSF 16-Key Touch IC](https://partreel.com/p/ttp229/) | `TTP229-BSF` | Tontek | [ttp229](library/ic/touch/ttp229/ttp229) |
| [W25Q64JV 64Mbit SPI Flash (SOIC-8 208mil)](https://partreel.com/p/w25q64jv/) | `W25Q64JVSSIQ` | Winbond | [w25q64jv](library/ic/memory/w25q64jv/w25q64jv) |

### module (4)

| Part | MPN | Manufacturer | Files |
|---|---|---|---|
| [0.96" SSD1306 I2C OLED Module (128x64)](https://partreel.com/p/ssd1306_module_096/) | `MC096VX` | Generic (LCDwiki MC096VX) | [ssd1306_module_096](library/module/display/ssd1306_module_096/ssd1306_module_096) |
| [1.3" SH1106 I2C OLED Module (128x64)](https://partreel.com/p/sh1106_module_13/) | `MC130VX` | Generic (LCDwiki MC130VX) | [sh1106_module_13](library/module/display/sh1106_module_13/sh1106_module_13) |
| [1.3" ST7789 IPS TFT Module (240x240, SPI)](https://partreel.com/p/st7789_module_13/) | `MSP1308` | Generic (LCDwiki MSP1308) | [st7789_module_13](library/module/display/st7789_module_13/st7789_module_13) |
| [ESP32-WROOM-32 Module](https://partreel.com/p/esp32_wroom32/) | `ESP32-WROOM-32` | Espressif | [esp32_wroom32](library/module/espressif/esp32_wroom32/esp32_wroom32) |

### sensor (6)

| Part | MPN | Manufacturer | Files |
|---|---|---|---|
| [ADXL345 3-Axis Accelerometer](https://partreel.com/p/adxl345/) | `ADXL345BCCZ` | Analog Devices | [adxl345](library/sensor/adi/adxl345/adxl345) |
| [AHT10 Temperature and Humidity Sensor](https://partreel.com/p/aht10/) | `AHT10` | Aosong (ASAIR) | [aht10](library/sensor/asair/aht10/aht10) |
| [AHT20 Humidity and Temperature Sensor](https://partreel.com/p/aht20/) | `AHT20` | Aosong (ASAIR) | [aht20](library/sensor/asair/aht20/aht20) |
| [AHT21 Humidity and Temperature Sensor](https://partreel.com/p/aht21/) | `AHT21` | Aosong (ASAIR) | [aht21](library/sensor/asair/aht21/aht21) |
| [HMC5883L 3-Axis Magnetometer](https://partreel.com/p/hmc5883l/) | `HMC5883L` | Honeywell | [hmc5883l](library/sensor/honeywell/hmc5883l/hmc5883l) |
| [QMC5883L 3-Axis Magnetometer](https://partreel.com/p/qmc5883l/) | `QMC5883L` | QST | [qmc5883l](library/sensor/qst/qmc5883l/qmc5883l) |

<!-- PARTS:END -->
