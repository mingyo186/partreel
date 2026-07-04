"""
배치 IC/모듈 생성기 (REQUIREMENTS §21-4, 19종).
치수 근거: 각 부품 제조사 데이터시트 (추출 기록: 세션 scratchpad batch20/FACTS.md).
공용 패키지 빌더(two-row/quad/LGA/SOT-89/모듈)로 중복 제거 — §21 패키지 재활용 방향 1차 적용.
실행: python generators/gen_ics.py
"""
import json
import os
from gen_connectors import _line, LIB_ROOT
from gen_parts import _rect_lines, _lr_symbol

F = "F.Cu"


# ---------- 풋프린트 공용 조각 ----------

def _fp_open(fid, descr, tags, ref_y, val_y, attr="smd"):
    return [f'(footprint "{fid}" (version 20221018) (generator opencad-lib)',
            '  (layer "F.Cu")',
            f'  (descr "{descr}")',
            f'  (tags "{tags}")',
            f'  (attr {attr})',
            f'  (fp_text reference "REF**" (at 0 {ref_y}) (layer "F.SilkS")'
            '\n    (effects (font (size 1 1) (thickness 0.15))))',
            f'  (fp_text value "{fid}" (at 0 {val_y}) (layer "F.Fab")'
            '\n    (effects (font (size 1 1) (thickness 0.15))))']


def _fab_body(x0, y0, x1, y1, ch):
    """팹 외곽 + 좌상 핀1 챔퍼(ch)."""
    return _rect_lines([(x0 + ch, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1),
                        (x0, y1, x0, y0 + ch), (x0, y0 + ch, x0 + ch, y0)], "F.Fab", 0.10)


def _silk_box(h, tick_y0, tick_y1, tick_x):
    """정사각/직사각 실크 박스(반폭 h=(hx,hy)) + 좌측 핀1 틱."""
    hx, hy = h
    out = _rect_lines([(-hx, -hy, hx, -hy), (hx, -hy, hx, hy),
                       (hx, hy, -hx, hy), (-hx, hy, -hx, -hy)], "F.SilkS", 0.12)
    out.append(_line(tick_x, tick_y0, tick_x, tick_y1, "F.SilkS", 0.12))
    return out


def _silk_topbot(hx, ytop, ybot, tick):
    """상/하 수평 실크선(패드가 좌우로 나오는 two-row용) + 핀1 틱."""
    out = _rect_lines([(-hx, ytop, hx, ytop), (-hx, ybot, hx, ybot)], "F.SilkS", 0.12)
    tx, ty0, ty1 = tick
    out.append(_line(tx, ty0, tx, ty1, "F.SilkS", 0.12))
    return out


def _court(x0, y0, x1, y1):
    return _rect_lines([(x0, y0, x1, y0), (x1, y0, x1, y1),
                        (x1, y1, x0, y1), (x0, y1, x0, y0)], "F.CrtYd", 0.05)


def _smd(name, x, y, w, h, shape="rect"):
    return (f'  (pad "{name}" smd {shape} (at {x:.4g} {y:.4g}) (size {w} {h}) '
            f'(layers "F.Cu" "F.Paste" "F.Mask"))')


def _tht(name, x, y, dia, drill, shape="circle"):
    return (f'  (pad "{name}" thru_hole {shape} (at {x:.4g} {y:.4g}) (size {dia} {dia}) '
            f'(drill {drill}) (layers "*.Cu" "*.Mask"))')


def _npth(x, y, d):
    return (f'  (pad "" np_thru_hole circle (at {x:.4g} {y:.4g}) (size {d} {d}) '
            f'(drill {d}) (layers "*.Cu" "*.Mask"))')


# ---------- 패드 배치 빌더 (번호는 전부 CCW, 데이터시트 핀다이어그램 검증 완료) ----------

def two_row_pads(n, pitch, span, pw, ph, right_ys=None):
    """좌열 1..n/2 위→아래, 우열 나머지 아래→위 (SOIC/SSOP/ESOP/SOT-23 계열).
    right_ys: 우열 y 명시 (SOT23-5처럼 비대칭일 때, 아래→위 순)."""
    n2 = n // 2 if right_ys is None else n - len(right_ys)
    top = (n2 - 1) * pitch / 2.0
    pads = [(str(i + 1), -span / 2, -top + i * pitch, pw, ph) for i in range(n2)]
    if right_ys is None:
        pads += [(str(n2 + 1 + i), span / 2, top - i * pitch, pw, ph) for i in range(n2)]
    else:
        pads += [(str(n2 + 1 + i), span / 2, y, pw, ph) for i, y in enumerate(right_ys)]
    return pads


def quad_pads(per_side, pitch, span, pw, ph):
    """4변 균등 (LGA/QFN): 좌 위→아래, 하 좌→우, 우 아래→위, 상 우→좌.
    pw=radial(변에 수직) 길이, ph=변 방향 폭."""
    k, top, pads, n = per_side, (per_side - 1) * pitch / 2.0, [], 1
    for i in range(k):
        pads.append((str(n), -span / 2, -top + i * pitch, pw, ph)); n += 1
    for i in range(k):
        pads.append((str(n), -top + i * pitch, span / 2, ph, pw)); n += 1
    for i in range(k):
        pads.append((str(n), span / 2, top - i * pitch, pw, ph)); n += 1
    for i in range(k):
        pads.append((str(n), top - i * pitch, -span / 2, ph, pw)); n += 1
    return pads


# ---------- 공용 메타 ----------

def _meta(fid, name, category, family, manuf, mpn, desc, params, datasheet, dim_src, kw):
    return {
        "id": fid, "name": name, "category": category, "family": family,
        "manufacturer": manuf, "mpn_pattern": mpn, "description": desc,
        "parameters": params,
        "files": {"footprint": f"{fid}.kicad_mod", "symbol": f"{fid}.kicad_sym",
                  "model_3d": f"{fid}.step", "preview": f"{fid}.glb",
                  "footprint_svg": f"{fid}.footprint.svg", "symbol_svg": f"{fid}.symbol.svg"},
        "formats": ["kicad_mod", "kicad_sym", "step", "glb"],
        "datasheet": datasheet, "dimensions_source": dim_src,
        "verified": True, "license": "CC-BY-4.0", "generated_by": "generators/gen_ics.py",
        "keywords": kw,
    }


def _fp_two_row(fid, descr, tags, pads, body, ep=None):
    """two-row SMD IC 풋프린트 (몸통 좌우로 패드)."""
    bx, by = body  # 반폭
    pad_top = min(p[2] for p in pads) - pads[0][4] / 2
    ref_y = pad_top - 1.3
    val_y = -ref_y
    out = _fp_open(fid, descr, tags, round(ref_y, 2), round(val_y, 2))
    out += _fab_body(-bx, -by, bx, by, min(1.0, bx * 0.5))
    ytop, ybot = -by - 0.11, by + 0.11
    p1 = pads[0]
    tickx = p1[1] - p1[3] / 2 - 0.4
    out += _silk_topbot(bx, ytop, ybot, (tickx, p1[2] - 0.25, p1[2] + 0.25))
    cx = max(max(abs(p[1]) + p[3] / 2 for p in pads), bx) + 0.25
    cy = max(by, max(abs(p[2]) + p[4] / 2 for p in pads)) + 0.25
    out += _court(-cx, -cy, cx, cy)
    for name, x, y, w, h in pads:
        out.append(_smd(name, x, y, w, h))
    if ep:
        num, w, h = ep
        out.append(_smd(num, 0, 0, w, h))
    out.append(')')
    return "\n".join(out) + "\n"


def _fp_quad(fid, descr, tags, pads, body, ep=None):
    """4변 패드 (LGA/QFN)."""
    bx = body
    out = _fp_open(fid, descr, tags, -(bx + 1.3), bx + 1.3)
    out += _fab_body(-bx, -bx, bx, bx, min(1.0, bx * 0.4))
    ext = max(abs(p[1]) + p[3] / 2 for p in pads)
    s = ext + 0.2 + 0.06
    p1 = pads[0]
    out += _silk_box((s, s), p1[2] - 0.25, p1[2] + 0.25, -s - 0.35)
    c = ext + 0.25
    out += _court(-c, -c, c, c)
    for name, x, y, w, h in pads:
        out.append(_smd(name, x, y, w, h))
    if ep:
        num, w, h = ep
        out.append(_smd(num, 0, 0, w, h))
    out.append(')')
    return "\n".join(out) + "\n"


# ---------- 부품 정의 ----------

def _part_lga16(fid, lib, name, manuf, mpn, ds, dim_src, pad_r, pad_t, radial, kw, addr):
    """QMC5883L/HMC5883L 공용 (핀맵 동일 — 각자 권장 랜드 치수)."""
    pads = quad_pads(4, 0.5, radial * 2, pad_r, pad_t)
    fp = _fp_quad(fid, f"{name}, 3-axis magnetometer, I2C, LGA-16 3x3x0.9mm. "
                       "Land pattern per manufacturer datasheet.",
                  f"{mpn} magnetometer compass 3-axis I2C", pads, 1.5)
    nm = {1: "SCL", 2: "VDD", 3: "NC", 4: "S1", 5: "NC", 6: "NC", 7: "NC", 8: "SETP",
          9: "GND", 10: "C1", 11: "GND", 12: "SETC", 13: "VDDIO", 14: "NC", 15: "DRDY", 16: "SDA"}
    left = [(str(i), nm[i]) for i in range(1, 9)]
    right = [(str(i), nm[i]) for i in range(9, 17)]
    sym = _lr_symbol(fid, left, right)
    meta = _meta(fid, name, "sensor", "magnetometer", manuf, mpn,
                 f"{manuf} {mpn} 3-axis magnetic sensor (compass), I2C address {addr}, "
                 "LGA-16 3x3x0.9mm. Land pattern per manufacturer datasheet. "
                 "S1 must tie to VDDIO; C1 reservoir capacitor required.",
                 {"contacts": 16, "mounting": "SMD", "interface": "I2C",
                  "i2c_address": addr, "supply_voltage": "2.16-3.6V", "body_mm": "3.0x3.0x0.9"},
                 ds, dim_src, kw)
    return fid, lib, fp, sym, meta


def qmc5883l():
    return _part_lga16(
        "qmc5883l", "sensor/qst/qmc5883l", "QMC5883L 3-Axis Magnetometer",
        "QST", "QMC5883L",
        "https://nettigo.pl/attachments/440",
        "QST QMC5883L datasheet 1.0: §3.2 LGA-16 3x3x0.9, Fig.7 recommended land pattern "
        "(16 pads 0.325x0.25, pitch 0.5, radial centers +/-1.2625), Table 5 pinout.",
        0.325, 0.25, 1.2625,
        ["qmc5883l", "qst", "magnetometer", "compass", "3-axis", "i2c", "gy-271", "lga"],
        "0x0D")


def hmc5883l():
    return _part_lga16(
        "hmc5883l", "sensor/honeywell/hmc5883l", "HMC5883L 3-Axis Magnetometer",
        "Honeywell", "HMC5883L",
        "https://cdn-shop.adafruit.com/datasheets/HMC5883L_3-Axis_Digital_Compass_IC.pdf",
        "Honeywell HMC5883L datasheet Rev E: p.4 LCC-16 3x3x0.9, p.5 recommended land "
        "pattern (16 pads 0.45x0.30, pitch 0.5, radial centers +/-1.275), Table 1 pinout.",
        0.45, 0.30, 1.275,
        ["hmc5883l", "honeywell", "magnetometer", "compass", "3-axis", "i2c", "gy-273", "lcc"],
        "0x1E")


def adxl345():
    fid, lib = "adxl345", "sensor/adi/adxl345"
    # 권장 랜드 p36 Fig59: 2열x6 (1.145x0.55, 세로피치 0.8, 열중심 ±1.0975) + 중앙 상하 2패드(90°)
    col = 2.195 / 2
    pads = [(str(i + 1), -col, -2.0 + i * 0.8, 1.145, 0.55) for i in range(6)]      # 1-6 좌 위→아래
    pads.append(("7", 0, (3.05 + 1.145) / 2, 0.55, 1.145))                          # 7 하중앙
    pads += [(str(8 + i), col, 2.0 - i * 0.8, 1.145, 0.55) for i in range(6)]       # 8-13 우 아래→위
    pads.append(("14", 0, -(3.05 + 1.145) / 2, 0.55, 1.145))                        # 14 상중앙
    bx, by = 1.5, 2.5
    out = _fp_open(fid, "Analog Devices ADXL345 3-axis accelerometer, LGA-14 3x5x0.95mm. "
                        "Land pattern per ADI datasheet Fig.59.",
                   "ADXL345 accelerometer 3-axis SPI I2C LGA", -4.2, 4.2)
    out += _fab_body(-bx, -by, bx, by, 0.8)
    # 실크: 패드(x±1.6675, y±2.67)를 피해서 4모서리 L자
    sx, sy = 1.93, 2.93
    for mx in (-1, 1):
        for my in (-1, 1):
            out.append(_line(mx * sx, my * sy, mx * sx, my * (sy - 1.0), "F.SilkS", 0.12))
            out.append(_line(mx * sx, my * sy, mx * (sx - 0.8), my * sy, "F.SilkS", 0.12))
    out.append(_line(-2.2, -2.0 - 0.3, -2.2, -2.0 + 0.3, "F.SilkS", 0.12))  # pin1 틱
    out += _court(-1.92, -2.92, 1.92, 2.92)
    for name, x, y, w, h in pads:
        out.append(_smd(name, x, y, w, h))
    out.append(')')
    fp = "\n".join(out) + "\n"
    nm = {1: "VDD_IO", 2: "GND", 3: "RESERVED", 4: "GND", 5: "GND", 6: "VS", 7: "~CS",
          8: "INT1", 9: "INT2", 10: "NC", 11: "RESERVED", 12: "SDO/ALT_ADDR",
          13: "SDA/SDI/SDIO", 14: "SCL/SCLK"}
    sym = _lr_symbol(fid, [(str(i), nm[i]) for i in range(1, 8)],
                     [(str(i), nm[i]) for i in range(8, 15)])
    meta = _meta(fid, "ADXL345 3-Axis Accelerometer", "sensor", "accelerometer",
                 "Analog Devices", "ADXL345BCCZ",
                 "Analog Devices ADXL345 3-axis digital accelerometer, SPI/I2C "
                 "(0x1D or 0x53), LGA-14 3x5x0.95mm. Land pattern per ADI datasheet. "
                 "CS and ALT_ADDR must not float.",
                 {"contacts": 14, "mounting": "SMD", "interface": "SPI/I2C",
                  "i2c_address": "0x1D/0x53", "supply_voltage": "2.0-3.6V",
                  "body_mm": "3.0x5.0x0.95"},
                 "https://components101.com/sites/default/files/component_datasheet/ADXL345-Datasheet.pdf",
                 "ADI ADXL345 datasheet Rev E: Fig.61 package CC-14-1 (3x5x0.95), Fig.59 "
                 "recommended land pattern (pads 1.145x0.55, pitch 0.8, columns c-c 2.195, "
                 "center pads span 5.34 outer), Table 5 pinout.",
                 ["adxl345", "accelerometer", "3-axis", "spi", "i2c", "adi", "gy-291", "lga"])
    return fid, lib, fp, sym, meta


def _part_esop8(fid, lib, name, manuf, mpn, ds, dim_src, pins, ep, desc_extra, params, kw,
                pitch=1.27, pad=(1.6, 0.61), span=5.4, body=(1.95, 2.45)):
    """eSOP8/SOIC8E 계열 (MP1584 권장 랜드 기하 공유: 0.61x1.6 c-c 5.4)."""
    pads = two_row_pads(8, pitch, span, pad[0], pad[1])
    epn = None
    ep_pin = None
    if ep:
        epn = (ep[0], ep[1], ep[2])
        if ep[3]:
            ep_pin = (ep[0], ep[3])
    fp = _fp_two_row(fid, f"{name}. Land pattern: 8 pads {pad[1]}x{pad[0]}, pitch {pitch}, "
                          f"row centers {span}mm c-c" + (f", exposed pad {ep[1]}x{ep[2]}" if ep else "") + ".",
                     f"{mpn}", pads, body, ep=epn)
    left = [(str(i + 1), pins[i]) for i in range(4)]
    right = [(str(i + 5), pins[i + 4]) for i in range(4)]
    bottom = [ep_pin] if ep_pin else None
    sym = _lr_symbol(fid, left, right, bottom=bottom)
    meta = _meta(fid, name, "ic", lib.split("/")[1], manuf, mpn, desc_extra, params, ds, dim_src, kw)
    return fid, lib, fp, sym, meta


def mp1584():
    return _part_esop8(
        "mp1584", "ic/regulator/mp1584", "MP1584EN 3A Buck Converter",
        "MPS", "MP1584EN",
        "https://datasheet4u.com/pdf/1471577/MP1584.pdf",
        "MPS MP1584 datasheet Rev 1.0 p.17: SOIC8E package (4.9x3.9, EP 3.3x2.41) with "
        "explicit recommended land pattern (8 pads 0.61x1.60, pitch 1.27, rows 5.40 c-c, "
        "EP land 3.51x2.62).",
        ["SW", "EN", "COMP", "FB", "GND", "FREQ", "VIN", "BST"],
        ("5", 3.51, 2.62, None),  # EP=핀5(GND)와 동일넷 → 같은 번호, 심볼 추가핀 없음
        "MPS MP1584EN 3A 1.5MHz step-down converter, 4.5-28V input, SOIC-8E with exposed "
        "pad (EP = GND, same net as pin 5). NOTE: MPS marks MP1584 NRND (successor MP2338) "
        "but it remains ubiquitous on buck modules.",
        {"contacts": 8, "mounting": "SMD", "supply_voltage": "4.5-28V",
         "output_current": "3A", "body_mm": "4.9x3.9x1.6"},
        ["mp1584", "mps", "buck", "step-down", "dc-dc", "regulator", "soic-8"])


def ip5306():
    return _part_esop8(
        "ip5306", "ic/power/ip5306", "IP5306 Power Bank SoC",
        "Injoinic", "IP5306",
        "https://datasheet.lcsc.com/datasheet/pdf/309666add984eaea02a8f06d99102496.pdf",
        "Injoinic IP5306 datasheet V1.10 p.10: eSOP8 4.9x3.9 span 6.0 pitch 1.27, EP 2.09 sq. "
        "No recommended land pattern - pads derived per IPC-7351 (matches MP1584 SOIC8E "
        "recommendation for identical outline); EP land 2.1x2.1.",
        ["VIN", "LED1", "LED2", "LED3", "KEY", "BAT", "SW", "VOUT"],
        ("9", 2.1, 2.1, "EP/GND"),
        "Injoinic IP5306 fully-integrated power bank system-on-chip: 2.1A charger + 2.4A "
        "5V boost output + battery indicator LEDs + key control, eSOP8 (EP = GND).",
        {"contacts": 9, "mounting": "SMD", "supply_voltage": "4.75-5.5V",
         "battery": "3.0-4.4V", "body_mm": "4.9x3.9x1.65"},
        ["ip5306", "injoinic", "power bank", "charger", "boost", "battery", "esop-8"])


def cn3791():
    fid, lib = "cn3791", "ic/power/cn3791"
    pads = two_row_pads(10, 1.0, 5.4, 1.6, 0.6)
    fp = _fp_two_row(fid, "Consonance CN3791 MPPT solar Li-ion charger, SSOP-10 (4.9x3.9, "
                          "span 6.0, pitch 1.0). No recommended land pattern - pads 0.6x1.6 "
                          "at rows 5.4 c-c derived per IPC-7351.",
                     "CN3791 MPPT solar charger li-ion", pads, (1.95, 2.45))
    nm = ["VG", "GND", "~CHRG", "~DONE", "COM", "MPPT", "BAT", "CSP", "VCC", "DRV"]
    sym = _lr_symbol(fid, [(str(i + 1), nm[i]) for i in range(5)],
                     [(str(i + 6), nm[i + 5]) for i in range(5)])
    meta = _meta(fid, "CN3791 MPPT Solar Li-Ion Charger", "ic", "power", "Consonance", "CN3791",
                 "Consonance CN3791 PWM switch-mode Li-ion charger with MPPT for solar "
                 "panels, 4.5-28V input, 4.2V CV, up to 4A, SSOP-10.",
                 {"contacts": 10, "mounting": "SMD", "supply_voltage": "4.5-28V",
                  "body_mm": "4.9x3.9x1.75"},
                 "https://datasheet.lcsc.com/datasheet/pdf/6c2f62f31126495186741f6e77130abd.pdf",
                 "Consonance CN3791 datasheet Rev 1.0 p.11: SSOP-10 body 4.9x3.9, lead span "
                 "5.8-6.2, pitch 1.0 BSC. Land pads 0.6x1.6 rows 5.4 c-c derived per IPC-7351. "
                 "Pinout p.1/p.3.",
                 ["cn3791", "consonance", "mppt", "solar", "charger", "li-ion", "ssop-10"])
    return fid, lib, fp, sym, meta


def w25q64jv():
    fid, lib = "w25q64jv", "ic/memory/w25q64jv"
    pads = two_row_pads(8, 1.27, 7.3, 1.95, 0.65)
    fp = _fp_two_row(fid, "Winbond W25Q64JVSSIQ 64Mbit SPI flash, SOIC-8 208mil (body "
                          "5.23x5.23, lead span 7.9, pitch 1.27). No recommended land "
                          "pattern - pads 0.65x1.95 at rows 7.3 c-c derived per IPC-7351.",
                     "W25Q64 SPI flash SOIC-8 208mil", pads, (2.615, 2.615))
    nm = ["~CS", "DO(IO1)", "~WP(IO2)", "GND", "DI(IO0)", "CLK", "~HOLD(IO3)", "VCC"]
    sym = _lr_symbol(fid, [(str(i + 1), nm[i]) for i in range(4)],
                     [(str(i + 5), nm[i + 4]) for i in range(4)])
    meta = _meta(fid, "W25Q64JV 64Mbit SPI Flash (SOIC-8 208mil)", "ic", "memory",
                 "Winbond", "W25Q64JVSSIQ",
                 "Winbond W25Q64JV 64Mbit (8MB) serial NOR flash, SPI/Dual/Quad, 2.7-3.6V, "
                 "wide-body SOIC-8 208mil (not the 150mil narrow body).",
                 {"contacts": 8, "mounting": "SMD", "supply_voltage": "2.7-3.6V",
                  "body_mm": "5.23x5.23x1.95"},
                 "https://www.winbond.com/resource-files/w25q64jv%20revj%2003272018%20plus.pdf",
                 "Winbond W25Q64JV datasheet Rev J §10.1: SOIC-8 208mil body 5.23x5.23, "
                 "span H 7.9, pitch 1.27, foot 0.65. Land pads 0.65x1.95 rows 7.3 c-c "
                 "derived per IPC-7351. Pinout §3.1.",
                 ["w25q64", "winbond", "spi", "flash", "nor", "memory", "soic-8", "208mil"])
    return fid, lib, fp, sym, meta


def _part_sot23(fid, lib, name, manuf, mpn, ds, dim_src, pins5or6, desc, params, kw, six=False):
    """SOT23-5/6: 패드 0.55x0.8(장축 radial), 피치 0.95, 행중심 c-c 2.4 (Silergy 권장/동계열)."""
    if six:
        pads = two_row_pads(6, 0.95, 2.4, 0.8, 0.55)
    else:
        pads = two_row_pads(5, 0.95, 2.4, 0.8, 0.55, right_ys=[0.95, -0.95])
    # two_row_pads의 pw/ph: 여기선 가로가 radial → w=0.8, h=0.55
    fp = _fp_two_row(fid, f"{name}. SOT-23-{'6' if six else '5'}; land pads 0.55x0.8, "
                          "pitch 0.95, rows 2.4mm c-c.",
                     mpn, pads, (0.85, 1.45))
    n_l = 3
    left = [(str(i + 1), pins5or6[i]) for i in range(n_l)]
    right = [(str(n_l + 1 + i), pins5or6[n_l + i]) for i in range(len(pins5or6) - n_l)]
    sym = _lr_symbol(fid, left, right)
    meta = _meta(fid, name, "ic", lib.split("/")[1], manuf, mpn, desc, params, ds, dim_src, kw)
    return fid, lib, fp, sym, meta


def sy8008():
    return _part_sot23(
        "sy8008", "ic/regulator/sy8008", "SY8008B 1A Buck Converter", "Silergy", "SY8008BAAC",
        "https://mangopi.org/_media/sy8008.pdf",
        "Silergy AN_SY8008 Rev 1.0 p.7: SOT23-5 (body 2.8-3.1x1.5-1.7, span 2.7-3.0, pitch "
        "0.95) with recommended land pattern: pads 0.55x0.80, pitch 0.95, rows 2.40 c-c. "
        "Pinout p.2 (verified: 4=IN bottom-right, 5=FB top-right in column layout).",
        ["EN", "GND", "LX", "IN", "FB"],
        "Silergy SY8008B 1A 1.5MHz synchronous step-down regulator, 2.5-5.5V input, "
        "0.6V reference, SOT23-5.",
        {"contacts": 5, "mounting": "SMD", "supply_voltage": "2.5-5.5V",
         "output_current": "1A", "body_mm": "2.9x1.6x1.1"},
        ["sy8008", "silergy", "buck", "step-down", "dc-dc", "sot23-5"])


def sy8089():
    return _part_sot23(
        "sy8089", "ic/regulator/sy8089", "SY8089A 2A Buck Converter", "Silergy", "SY8089AAAC",
        "https://www.olimex.com/Products/Components/IC/SY8009A/resources/SY8089AAAC.pdf",
        "Silergy AN_SY8089A Rev 0.9A p.9: SOT23-5 outline + recommended land pattern "
        "(pads 0.55x0.80, pitch 0.95, rows 2.40 c-c). Pinout p.2.",
        ["EN", "GND", "LX", "IN", "FB"],
        "Silergy SY8089A 2A (3A peak) 1MHz synchronous step-down regulator, 2.7-5.5V "
        "input, 0.6V reference, SOT23-5.",
        {"contacts": 5, "mounting": "SMD", "supply_voltage": "2.7-5.5V",
         "output_current": "2A", "body_mm": "2.9x1.6x1.1"},
        ["sy8089", "silergy", "buck", "step-down", "dc-dc", "sot23-5", "esp32 power"])


def ttp223():
    return _part_sot23(
        "ttp223", "ic/touch/ttp223", "TTP223-BA6 Touch Key IC", "Tontek", "TTP223-BA6",
        "https://vakits.com/sites/default/files/TTP223B%20Touch%20Switch.pdf",
        "Tontek TTP223-BA6 datasheet V1.0 p.7: SOT-23-6L (body 2.9x1.7, span 2.85, pitch "
        "0.95). No recommended land pattern - pads 0.55x0.8 rows 2.4 c-c (same package "
        "class as Silergy SOT23 recommendation / IPC-7351). Pinout p.2 (verified: bottom "
        "row 1 Q, 2 VSS, 3 I; top row 6 TOG, 5 VDD, 4 AHLB).",
        ["Q", "VSS", "I", "AHLB", "VDD", "TOG"],
        "Tontek TTP223-BA6 single-key capacitive touch detector, 2.0-5.5V, direct/toggle "
        "output modes, SOT-23-6.",
        {"contacts": 6, "mounting": "SMD", "supply_voltage": "2.0-5.5V",
         "body_mm": "2.9x1.7x1.1"},
        ["ttp223", "tontek", "touch", "capacitive", "key", "sot-23-6"], six=True)


def ttp229():
    fid, lib = "ttp229", "ic/touch/ttp229"
    pads = two_row_pads(28, 0.635, 5.4, 1.5, 0.4)
    fp = _fp_two_row(fid, "Tontek TTP229-BSF 16-key touch IC, SSOP-28 150mil MO-137(AF) "
                          "(body 9.91x3.91, span 5.99, pitch 0.635). No recommended land "
                          "pattern - pads 0.4x1.5 at rows 5.4 c-c derived per IPC-7351.",
                     "TTP229 touch 16-key SSOP-28", pads, (1.955, 4.955))
    nm = ["TP3", "TP2", "NC", "SENADJ0", "TP1", "TP0", "TP15", "TP14", "SENADJ3", "TP13",
          "TP12", "SDO", "SCL", "SLPSENB", "TP11", "TP10", "SENADJ2", "TP9", "TP8", "TEST",
          "TP7", "TP6", "SENADJ1", "TP5", "TP4", "VDD", "VSS", "SLPSENA"]
    sym = _lr_symbol(fid, [(str(i + 1), nm[i]) for i in range(14)],
                     [(str(i + 15), nm[i + 14]) for i in range(14)])
    meta = _meta(fid, "TTP229-BSF 16-Key Touch IC", "ic", "touch", "Tontek", "TTP229-BSF",
                 "Tontek TTP229-BSF 16-key capacitive touch detector with serial output, "
                 "2.4-5.5V, SSOP-28 150mil.",
                 {"contacts": 28, "mounting": "SMD", "supply_voltage": "2.4-5.5V",
                  "body_mm": "9.91x3.91x1.63"},
                 "https://www.tontek.com.tw/uploads/product/97/TTP229-BSF_V1.1_EN.pdf",
                 "Tontek TTP229-BSF datasheet V1.1 p.15: SSOP-28 MO-137(AF) body 9.91x3.91, "
                 "span 5.99, pitch 0.635. Land pads 0.4x1.5 rows 5.4 c-c derived per "
                 "IPC-7351. Pinout p.2-4.",
                 ["ttp229", "tontek", "touch", "capacitive", "16-key", "keypad", "ssop-28"])
    return fid, lib, fp, sym, meta


def _part_sot89(fid, name, mpn, ds, dim_src, desc, vmax, current, kw):
    """Holtek SOT-89 LDO: 핀 1 GND, 2 VIN(=탭), 3 VOUT. 리드측 y+, 탭측 y-."""
    lib = f"ic/regulator/{fid}"
    out = _fp_open(fid, f"{name}. SOT-89-3: lead pads 0.8x1.6 at pitch 1.5 (y+1.65), tab pad "
                        "2.0x1.6 (y-1.4, pin 2 net). Derived from Holtek outline per IPC-7351.",
                   f"{mpn} LDO SOT-89", -3.0, 3.0)
    bx, by = 2.275, 1.25
    out += _fab_body(-bx, -by, bx, by, 0.8)
    # 실크: 상단(탭 패드)·하단(리드 패드)을 가로지르지 않게 좌우 수직선만
    out += _rect_lines([(-bx - 0.11, -by, -bx - 0.11, by),
                        (bx + 0.11, -by, bx + 0.11, by)], "F.SilkS", 0.12)
    out.append(_line(-2.6, 1.4, -2.6, 1.9, "F.SilkS", 0.12))  # pin1 틱
    out += _court(-2.53, -2.45, 2.53, 2.7)
    for i, x in enumerate((-1.5, 0.0, 1.5)):
        out.append(_smd(str(i + 1), x, 1.65, 0.8, 1.6))
    out.append(_smd("2", 0, -1.4, 2.0, 1.6))  # 탭 = 핀2
    out.append(')')
    fp = "\n".join(out) + "\n"
    sym = _lr_symbol(fid, [("2", "VIN"), ("1", "GND")], [("3", "VOUT")])
    meta = _meta(fid, name, "ic", "regulator", "Holtek", mpn, desc,
                 {"contacts": 3, "mounting": "SMD", "supply_voltage": vmax,
                  "output_current": current, "output_voltage": "3.3V",
                  "body_mm": "4.55x2.5x1.5"},
                 ds, dim_src, kw)
    return fid, lib, fp, sym, meta


def ht7333():
    return _part_sot89(
        "ht7333", "HT7333-A Low-Power LDO 3.3V", "HT7333-A",
        "https://www.holtek.com/webapi/116711/HT73xxv180.pdf",
        "Holtek HT73xx datasheet Rev 1.80 p.7: SOT-89 body 4.55x2.5, lead pitch 1.5, tab "
        "width 1.35-1.83, overall tab-to-lead 4.17. Land (leads 0.8x1.6 pitch 1.5, tab "
        "2.0x1.6) derived per IPC-7351. Pinout p.2: 1 GND, 2 VIN(tab), 3 VOUT. "
        "NOTE: HT7333-1 is a different 30V family.",
        "Holtek HT7333-A ultra-low-power LDO, 3.3V 250mA output, 2.5uA quiescent, "
        "VIN up to 12V, SOT-89. Battery-project staple.",
        "up to 12V", "250mA",
        ["ht7333", "holtek", "ldo", "regulator", "3.3v", "low quiescent", "sot-89"])


def ht7833():
    return _part_sot89(
        "ht7833", "HT7833 500mA LDO 3.3V", "HT7833",
        "https://www.singsun.com/datasheet/en/HT78XX.pdf",
        "Holtek HT78xx datasheet Rev 1.50 p.8: SOT-89 outline identical to HT73xx "
        "(body 4.55x2.5, pitch 1.5). Land derived per IPC-7351. Pinout p.2: "
        "1 GND, 2 VIN(tab), 3 VOUT.",
        "Holtek HT7833 TinyPower LDO, 3.3V 500mA output, 4uA quiescent, VIN up to 8V, "
        "SOT-89.",
        "up to 8V", "500mA",
        ["ht7833", "holtek", "ldo", "regulator", "3.3v", "500ma", "sot-89"])


def tp5100():
    fid, lib = "tp5100", "ic/power/tp5100"
    pads = quad_pads(4, 0.65, 3.55, 0.85, 0.35)
    fp = _fp_quad(fid, "TopPower TP5100 1/2-cell switching charger, QFN16 4x4x0.8 (pitch "
                       "0.65, pads 0.25-0.35x0.45-0.65, EP 2.0-2.2). No recommended land "
                       "pattern - pads 0.35x0.85 at centers +/-1.775 + EP 2.1 derived per "
                       "IPC-7351. NOTE: QFN16, not ESOP-8.",
                  "TP5100 charger 2-cell QFN16", pads, 2.0, ep=("17", 2.1, 2.1))
    nm = ["VIN", "LX", "LX", "VIN", "VIN", "PWR_ON-", "GND", "VS", "BAT", "VREG", "TS",
          "RTRICK", "CS", "STDBY", "CHRG", "VIN"]
    sym = _lr_symbol(fid, [(str(i + 1), nm[i]) for i in range(8)],
                     [(str(i + 9), nm[i + 8]) for i in range(8)],
                     bottom=[("17", "EP/GND")])
    meta = _meta(fid, "TP5100 1/2-Cell Switching Charger", "ic", "power",
                 "NanJing TopPower", "TP5100",
                 "TopPower TP5100 switch-mode Li-ion charger, single-cell 4.2V or 2-cell "
                 "8.4V (CS pin select), 0.1-2A, VIN 4.5-12V, QFN16 4x4mm (EP = heatsink, "
                 "ground only).",
                 {"contacts": 17, "mounting": "SMD", "supply_voltage": "4.5-12V",
                  "body_mm": "4.0x4.0x0.9"},
                 "https://www.toppwr.com/uploadfile/file/20240913/66e3a293b3c42.pdf",
                 "TopPower TP5100 datasheet REV_2.4 p.16: QFN16 4x4x0.8-0.9, pitch 0.65, "
                 "pad 0.25-0.35 x 0.45-0.65, EP 2.0-2.2 sq. Land pads 0.35x0.85 centers "
                 "+/-1.775 + EP 2.1 derived per IPC-7351. Pinout p.4/p.8-9.",
                 ["tp5100", "toppower", "charger", "li-ion", "2-cell", "8.4v", "qfn"])
    return fid, lib, fp, sym, meta


def a4988():
    fid, lib = "a4988", "ic/driver/a4988"
    # 랜드 벡터 실측(p19): 패드중심 스팬 4.80 c-c (외측 ±2.97, 내측 ±1.82, EP 1.575와 간극 0.25)
    pads = quad_pads(7, 0.5, 4.80, 1.15, 0.30)
    fp = _fp_quad(fid, "Allegro A4988 microstepping driver, QFN-28 5x5x0.9 (ET). Land "
                       "pattern per datasheet p.19 (IPC QFN50P500X500X100-29V1M): pads "
                       "0.30x1.15 pitch 0.5, centers span 4.80 c-c, EP 3.15x3.15.",
                  "A4988 stepper driver QFN-28", pads, 2.5, ep=("29", 3.15, 3.15))
    nm = ["OUT2B", "~ENABLE", "GND", "CP1", "CP2", "VCP", "NC", "VREG", "MS1", "MS2",
          "MS3", "~RESET", "ROSC", "~SLEEP", "VDD", "STEP", "REF", "GND", "DIR", "NC",
          "OUT1B", "VBB1", "SENSE1", "OUT1A", "NC", "OUT2A", "SENSE2", "VBB2"]
    sym = _lr_symbol(fid, [(str(i + 1), nm[i]) for i in range(14)],
                     [(str(i + 15), nm[i + 14]) for i in range(14)],
                     bottom=[("29", "PAD")])
    meta = _meta(fid, "A4988 Microstepping Motor Driver", "ic", "driver",
                 "Allegro MicroSystems", "A4988SETTR-T",
                 "Allegro A4988 DMOS microstepping driver with translator, up to 2A / 35V, "
                 "1/16 microstepping, QFN-28 5x5mm (ET). GND pins tie via exposed PAD "
                 "ground plane.",
                 {"contacts": 29, "mounting": "SMD", "supply_voltage": "8-35V",
                  "output_current": "2A", "body_mm": "5.0x5.0x0.9"},
                 "https://www.allegromicro.com/-/media/files/datasheets/a4988-datasheet.pdf",
                 "Allegro A4988 datasheet p.19: QFN-28 ET 5x5x0.9, pitch 0.5, EP 3.15; PCB "
                 "Layout Reference View (QFN50P500X500X100-29V1M): pads 0.30x1.15, outer "
                 "span 4.80. Pinout p.18 (verified: 1-7 left, 8-14 bottom, 15-21 right, "
                 "22-28 top, CCW).",
                 ["a4988", "allegro", "stepper", "driver", "microstepping", "qfn-28"])
    return fid, lib, fp, sym, meta


def drv8825():
    fid, lib = "drv8825", "ic/driver/drv8825"
    pads = two_row_pads(28, 0.65, 5.8, 1.5, 0.45)
    fp = _fp_two_row(fid, "TI DRV8825 stepper driver, HTSSOP-28 PWP (9.7x4.4, pitch 0.65). "
                          "Land pattern per TI PWP0028C example: pads 0.45x1.5 pitch 0.65 "
                          "columns 5.8 c-c, thermal pad 3.1x5.18.",
                     "DRV8825 stepper driver HTSSOP-28", pads, (2.2, 4.85),
                     ep=("29", 3.1, 5.18))
    nm = ["CP1", "CP2", "VCP", "VMA", "AOUT1", "ISENA", "AOUT2", "BOUT2", "ISENB", "BOUT1",
          "VMB", "AVREF", "BVREF", "GND", "V3P3OUT", "nRESET", "nSLEEP", "nFAULT", "DECAY",
          "DIR", "nENBL", "STEP", "NC", "MODE0", "MODE1", "MODE2", "nHOME", "GND"]
    sym = _lr_symbol(fid, [(str(i + 1), nm[i]) for i in range(14)],
                     [(str(i + 15), nm[i + 14]) for i in range(14)],
                     bottom=[("29", "PPAD")])
    meta = _meta(fid, "DRV8825 Stepper Motor Driver", "ic", "driver",
                 "Texas Instruments", "DRV8825PWP",
                 "TI DRV8825 stepper motor driver, up to 2.5A / 45V, 1/32 microstepping, "
                 "HTSSOP-28 with PowerPAD (PPAD = GND, must be soldered).",
                 {"contacts": 29, "mounting": "SMD", "supply_voltage": "8.2-45V",
                  "output_current": "2.5A", "body_mm": "9.7x4.4x1.2"},
                 "https://www.ti.com/lit/ds/symlink/drv8825.pdf",
                 "TI DRV8825 datasheet SLVSA73F: PWP0028C outline (9.7x4.4, span 6.4, pitch "
                 "0.65, thermal pad 4.48-5.18x2.4-3.1) + TI recommended land pattern "
                 "(0.45x1.5 pads, columns 5.8 c-c, thermal 3.1x5.18). Pinout p.3.",
                 ["drv8825", "ti", "stepper", "driver", "microstepping", "htssop-28"])
    return fid, lib, fp, sym, meta


# ---------- 디스플레이 모듈 (LCDwiki 제조사 도면; THT 헤더+마운팅홀) ----------

def _module_fp(fid, descr, tags, board, pins, pin_names, pin_y, pin1_x, holes, hole_d,
               hole_pad, disp):
    bw, bh = board
    hx, hy = bw / 2, bh / 2
    out = _fp_open(fid, descr, tags, -(hy + 1.5), hy + 1.5, attr="through_hole")
    out += _fab_body(-hx, -hy, hx, hy, 1.5)
    dx0, dy0, dx1, dy1 = disp
    out += _rect_lines([(dx0, dy0, dx1, dy0), (dx1, dy0, dx1, dy1),
                        (dx1, dy1, dx0, dy1), (dx0, dy1, dx0, dy0)], "F.Fab", 0.10)
    out += _rect_lines([(-hx - 0.11, -hy - 0.11, hx + 0.11, -hy - 0.11),
                        (hx + 0.11, -hy - 0.11, hx + 0.11, hy + 0.11),
                        (hx + 0.11, hy + 0.11, -hx - 0.11, hy + 0.11),
                        (-hx - 0.11, hy + 0.11, -hx - 0.11, -hy - 0.11)], "F.SilkS", 0.12)
    out.append(_line(pin1_x - 1.27, pin_y - 1.6, pin1_x + 1.27, pin_y - 1.6, "F.SilkS", 0.12))
    out += _court(-hx - 0.25, -hy - 0.25, hx + 0.25, hy + 0.25)
    for i in range(pins):
        x = pin1_x + i * 2.54
        shape = "rect" if i == 0 else "circle"
        out.append(_tht(str(i + 1), x, pin_y, 1.7, 1.0, shape))
    for x, y in holes:
        out.append(_npth(x, y, hole_d))
    out.append(')')
    return "\n".join(out) + "\n"


def ssd1306_module_096():
    fid, lib = "ssd1306_module_096", "module/display/ssd1306_module_096"
    bw, bh = 27.3, 27.8
    fp = _module_fp(fid,
                    "Generic 0.96 inch 128x64 I2C OLED module (SSD1306), 4-pin header, "
                    "27.3x27.8mm board. Dimensions per LCDwiki MC096VX drawing.",
                    "SSD1306 OLED module 0.96 I2C display", (bw, bh),
                    4, ["VCC", "GND", "SCL", "SDA"], -bh / 2 + 1.5, -3.81,
                    [(-11.65, -11.9), (11.65, -11.9), (-11.65, 11.9), (11.65, 11.9)],
                    2.0, 3.5, (-10.87, -7.53, 10.87, 3.33))
    sym = _lr_symbol(fid, [("1", "VCC"), ("2", "GND"), ("3", "SCL"), ("4", "SDA")], [])
    meta = _meta(fid, "0.96\" SSD1306 I2C OLED Module (128x64)", "module", "display",
                 "Generic (LCDwiki MC096VX)", "MC096VX",
                 "Common 0.96 inch 128x64 OLED display module with SSD1306 controller, "
                 "I2C 4-pin header (VCC GND SCL SDA), 27.3x27.8mm board, four 2.0mm "
                 "mounting holes. Dimensions per LCDwiki vendor drawing - verify against "
                 "your specific module (Chinese modules vary slightly).",
                 {"contacts": 4, "mounting": "THT header", "interface": "I2C",
                  "i2c_address": "0x3C", "supply_voltage": "3.3-5V",
                  "board_mm": "27.3x27.8"},
                 "https://www.lcdwiki.com/0.96inch_OLED_Module_(IIC-4P_SKU:MC096VX)",
                 "LCDwiki MC096VX dimension drawing (MC096-015): board 27.3x27.8, holes "
                 "D2.0/pad 3.5 at 2.0 from edges, 4-pin 2.54 header (pin1 VCC at 9.84 from "
                 "left), active area 21.74x10.86.",
                 ["ssd1306", "oled", "display", "module", "0.96", "128x64", "i2c"])
    return fid, lib, fp, sym, meta


def sh1106_module_13():
    fid, lib = "sh1106_module_13", "module/display/sh1106_module_13"
    bw, bh = 35.4, 33.5
    fp = _module_fp(fid,
                    "Generic 1.3 inch 128x64 I2C OLED module (SH1106), 4-pin header, "
                    "35.4x33.5mm board. Dimensions per LCDwiki MC130VX drawing. "
                    "NOTE pin order GND VCC (opposite of 0.96 inch module).",
                    "SH1106 OLED module 1.3 I2C display", (bw, bh),
                    4, ["GND", "VCC", "SCL", "SDA"], -bh / 2 + 2.0, -6.3,
                    [(-15.2, -14.75), (15.2, -14.75), (-15.2, 13.75), (15.2, 13.75)],
                    3.0, 4.5, (-14.71, -7.15, 14.71, 7.55))
    sym = _lr_symbol(fid, [("1", "GND"), ("2", "VCC"), ("3", "SCL"), ("4", "SDA")], [])
    meta = _meta(fid, "1.3\" SH1106 I2C OLED Module (128x64)", "module", "display",
                 "Generic (LCDwiki MC130VX)", "MC130VX",
                 "Common 1.3 inch 128x64 OLED display module with SH1106 controller, I2C "
                 "4-pin header (GND VCC SCL SDA - note order differs from 0.96\" module!), "
                 "35.4x33.5mm board, four 3.0mm mounting holes. Dimensions per LCDwiki "
                 "vendor drawing - verify against your specific module.",
                 {"contacts": 4, "mounting": "THT header", "interface": "I2C",
                  "i2c_address": "0x3C", "supply_voltage": "3.3-5V",
                  "board_mm": "35.4x33.5"},
                 "https://www.lcdwiki.com/1.3inch_IIC_OLED_Module_SKU:MC130VX",
                 "LCDwiki MC130VX size drawing: board 35.4x33.5, holes D3.0/pad 4.5 "
                 "(x +/-15.2; y top -14.75/bottom +13.75 - drawing has a 0.5mm chain "
                 "conflict, arithmetically exact chain adopted), 4-pin 2.54 header, "
                 "active area 29.42x14.7.",
                 ["sh1106", "oled", "display", "module", "1.3", "128x64", "i2c"])
    return fid, lib, fp, sym, meta


def st7789_module_13():
    fid, lib = "st7789_module_13", "module/display/st7789_module_13"
    bw, bh = 27.78, 39.22
    fp = _module_fp(fid,
                    "Generic 1.3 inch 240x240 IPS TFT module (ST7789), 7-pin SPI header, "
                    "27.78x39.22mm board. Dimensions per LCDwiki MSP1308 drawing.",
                    "ST7789 TFT module 1.3 IPS SPI display", (bw, bh),
                    7, ["GND", "VCC", "SCL", "SDA", "RES", "DC", "BLK"], -bh / 2 + 2.5, -7.62,
                    [(-11.39, -17.11), (11.39, -17.11), (-11.39, 17.11), (11.39, 17.11)],
                    2.0, 3.5, (-11.7, -13.28, 11.7, 10.12))
    sym = _lr_symbol(fid, [("1", "GND"), ("2", "VCC"), ("3", "SCL"), ("4", "SDA"),
                           ("5", "RES"), ("6", "DC"), ("7", "BLK")], [])
    meta = _meta(fid, "1.3\" ST7789 IPS TFT Module (240x240, SPI)", "module", "display",
                 "Generic (LCDwiki MSP1308)", "MSP1308",
                 "Common 1.3 inch 240x240 IPS TFT display module with ST7789 controller, "
                 "SPI 7-pin header (GND VCC SCL SDA RES DC BLK), 27.78x39.22mm board, four "
                 "2.0mm mounting holes. Dimensions per LCDwiki vendor drawing - verify "
                 "against your specific module.",
                 {"contacts": 7, "mounting": "THT header", "interface": "SPI",
                  "supply_voltage": "3.3V", "board_mm": "27.78x39.22"},
                 "https://www.lcdwiki.com/1.3inch_IPS_Module",
                 "LCDwiki MSP1308 size drawing: board 27.78x39.22, holes D2.0 at 2.5 from "
                 "all edges, 7-pin 2.54 header (pin1 GND at 6.27 from left; 6.27x2+6x2.54="
                 "27.78 checks), active area 23.4x23.4.",
                 ["st7789", "tft", "ips", "display", "module", "1.3", "240x240", "spi"])
    return fid, lib, fp, sym, meta


PARTS = [qmc5883l, hmc5883l, adxl345, ip5306, tp5100, cn3791, mp1584, sy8008, sy8089,
         ht7333, ht7833, ttp223, ttp229, w25q64jv, drv8825, a4988,
         ssd1306_module_096, sh1106_module_13, st7789_module_13]


def main():
    for fn in PARTS:
        fid, lib_path, footprint, symbol, meta = fn()
        d = os.path.normpath(os.path.join(LIB_ROOT, lib_path, fid))
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, f"{fid}.kicad_mod"), "w", encoding="utf-8").write(footprint)
        open(os.path.join(d, f"{fid}.kicad_sym"), "w", encoding="utf-8").write(symbol)
        json.dump(meta, open(os.path.join(d, "meta.json"), "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)
        print(f"  {fid}")
    print(f"Done ({len(PARTS)} ICs/modules).")


if __name__ == "__main__":
    main()
