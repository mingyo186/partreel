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


# Silergy SY8008 등급 변형 (같은 AN 데이터시트: A=0.6A, B=1A, C=1.2A)
SY8008_GRADES = {"a": ("SY8008AAAC", "0.6A"), "b": ("SY8008BAAC", "1A"),
                 "c": ("SY8008CAAC", "1.2A")}


def _sy8008_grade(g):
    mpn, amps = SY8008_GRADES[g]
    fid = "sy8008" if g == "b" else f"sy8008{g}"
    return _part_sot23(
        fid, f"ic/regulator/{fid}", f"SY8008{g.upper()} {amps} Buck Converter",
        "Silergy", mpn,
        "https://mangopi.org/_media/sy8008.pdf",
        "Silergy AN_SY8008 Rev 1.0 p.7: SOT23-5 (body 2.8-3.1x1.5-1.7, span 2.7-3.0, pitch "
        "0.95) with recommended land pattern: pads 0.55x0.80, pitch 0.95, rows 2.40 c-c. "
        "Pinout p.2 (verified: 4=IN bottom-right, 5=FB top-right in column layout).",
        ["EN", "GND", "LX", "IN", "FB"],
        f"Silergy SY8008{g.upper()} {amps} 1.5MHz synchronous step-down regulator, "
        "2.5-5.5V input, 0.6V reference, SOT23-5.",
        {"contacts": 5, "mounting": "SMD", "supply_voltage": "2.5-5.5V",
         "output_current": amps, "body_mm": "2.9x1.6x1.1"},
        [fid, "silergy", "buck", "step-down", "dc-dc", "sot23-5"])


def sy8008():
    return _sy8008_grade("b")


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


# Holtek LDO 전압변형 (§21-6ⓐ 온디맨드 변형 패밀리 — 데이터시트 셀렉션 테이블 실존 품번만)
HT73XX_CODES = {"7318": "1.8V", "7325": "2.5V", "7327": "2.7V", "7330": "3.0V",
                "7333": "3.3V", "7335": "3.5V", "7341": "4.15V", "7350": "5.0V"}
HT78XX_CODES = {"7818": "1.8V", "7825": "2.5V", "7827": "2.7V", "7830": "3.0V",
                "7833": "3.3V", "7850": "5.0V"}


def _ht73xx(code):
    v = HT73XX_CODES[code]
    return _part_sot89(
        f"ht{code}", f"HT{code}-A Low-Power LDO {v}", f"HT{code}-A",
        "https://www.holtek.com/webapi/116711/HT73xxv180.pdf",
        "Holtek HT73xx datasheet Rev 1.80 p.7: SOT-89 body 4.55x2.5, lead pitch 1.5, tab "
        "width 1.35-1.83, overall tab-to-lead 4.17. Land (leads 0.8x1.6 pitch 1.5, tab "
        "2.0x1.6) derived per IPC-7351. Pinout p.2: 1 GND, 2 VIN(tab), 3 VOUT. "
        f"Selection table covers HT{code} ({v}). NOTE: HT73xx-1 is a different 30V family.",
        f"Holtek HT{code}-A ultra-low-power LDO, {v} 250mA output, 2.5uA quiescent, "
        "VIN up to 12V, SOT-89. Battery-project staple.",
        "up to 12V", "250mA",
        [f"ht{code}", "holtek", "ldo", "regulator", v.lower(), "low quiescent", "sot-89"])


def _ht78xx(code):
    v = HT78XX_CODES[code]
    return _part_sot89(
        f"ht{code}", f"HT{code} 500mA LDO {v}", f"HT{code}",
        "https://www.singsun.com/datasheet/en/HT78XX.pdf",
        "Holtek HT78xx datasheet Rev 1.50 p.8: SOT-89 outline identical to HT73xx "
        "(body 4.55x2.5, pitch 1.5). Land derived per IPC-7351. Pinout p.2: "
        f"1 GND, 2 VIN(tab), 3 VOUT. Selection table covers HT{code} ({v}).",
        f"Holtek HT{code} TinyPower LDO, {v} 500mA output, 4uA quiescent, VIN up to 8V, "
        "SOT-89.",
        "up to 8V", "500mA",
        [f"ht{code}", "holtek", "ldo", "regulator", v.lower(), "500ma", "sot-89"])


def ht7333():
    return _ht73xx("7333")


def ht7833():
    return _ht78xx("7833")


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


# ================= 배치 3차 (§21-4 라운드2, 18종) =================

def _soic8(fid, lib, name, manuf, mpn, ds, dim_src, pins, desc, params, kw):
    """협폭 SOIC-8 (MAX6675/AS5600): MP1584 권장 기하 재사용 (0.61x1.6, c-c 5.4)."""
    pads = two_row_pads(8, 1.27, 5.4, 1.6, 0.61)
    fp = _fp_two_row(fid, f"{name}. SOIC-8 narrow (4.9x3.9); pads 0.61x1.6 rows 5.4 c-c "
                          "per IPC-7351.", mpn, pads, (1.95, 2.45))
    sym = _lr_symbol(fid, [(str(i + 1), pins[i]) for i in range(4)],
                     [(str(i + 5), pins[i + 4]) for i in range(4)])
    return fid, lib, fp, sym, _meta(fid, name, "ic", lib.split("/")[1], manuf, mpn,
                                    desc, params, ds, dim_src, kw)


def max6675():
    return _soic8(
        "max6675", "ic/sensor_if/max6675", "MAX6675 Thermocouple-to-Digital Converter",
        "Maxim Integrated", "MAX6675ISA",
        "https://cdn-shop.adafruit.com/datasheets/MAX6675.pdf",
        "Maxim MAX6675 datasheet 19-2235 p.8: SOIC .150 (MS012-A) body 4.9x3.9, span 6.0, "
        "pitch 1.27. Land pads 0.61x1.6 rows 5.4 c-c per IPC-7351. Pinout p.1.",
        ["GND", "T-", "T+", "VCC", "SCK", "~CS", "SO", "N.C."],
        "Maxim MAX6675 cold-junction-compensated K-thermocouple to digital converter, "
        "12-bit SPI read-only, 3.0-5.5V, SOIC-8. The entry-level thermocouple interface "
        "on K-type breakouts (MAX31855 is 3.3V-only, not a drop-in).",
        {"contacts": 8, "mounting": "SMD", "supply_voltage": "3.0-5.5V",
         "interface": "SPI", "body_mm": "4.9x3.9x1.55"},
        ["max6675", "thermocouple", "k-type", "spi", "temperature", "soic-8"])


def as5600():
    return _soic8(
        "as5600", "ic/sensor_if/as5600", "AS5600 Magnetic Angle Sensor",
        "ams-OSRAM", "AS5600-ASOT",
        "https://look.ams-osram.com/m/7059eac7531a86fd/original/AS5600-DS000365.pdf",
        "ams AS5600 datasheet v1-06 Fig.42: SOIC-8 (MS-012) body 4.9x3.9, span 6.0, pitch "
        "1.27. Land pads 0.61x1.6 rows 5.4 c-c per IPC-7351. Pinout Fig.3/4.",
        ["VDD5V", "VDD3V3", "OUT", "GND", "PGO", "SDA", "SCL", "DIR"],
        "ams AS5600 12-bit contactless magnetic rotary position sensor (on-axis), I2C "
        "0x36 + analog/PWM out, 3.3V or 5V mode, SOIC-8. SimpleFOC/robotics encoder staple.",
        {"contacts": 8, "mounting": "SMD", "supply_voltage": "3.0-3.6V or 4.5-5.5V",
         "interface": "I2C", "i2c_address": "0x36", "body_mm": "4.9x3.9x1.75"},
        ["as5600", "ams", "magnetic", "encoder", "rotary", "angle", "i2c", "soic-8"])


def tm1637():
    fid, lib = "tm1637", "ic/driver/tm1637"
    pads = two_row_pads(20, 1.27, 9.6, 1.9, 0.6)
    fp = _fp_two_row(fid, "Titan Micro TM1637 LED display driver, SOP-20 (body 12.7x7.65, "
                          "span 10.45, pitch 1.27). Pads 0.6x1.9 rows 9.6 c-c per IPC-7351.",
                     "TM1637 LED driver SOP-20", pads, (3.825, 6.35))
    nm = ["GND", "SG1", "SG2", "SG3", "SG4", "SG5", "SG6", "SG7", "SG8", "GRID6",
          "GRID5", "GRID4", "GRID3", "GRID2", "GRID1", "VDD", "DIO", "CLK", "K1", "K2"]
    sym = _lr_symbol(fid, [(str(i + 1), nm[i]) for i in range(10)],
                     [(str(i + 11), nm[i + 10]) for i in range(10)])
    meta = _meta(fid, "TM1637 LED Display Driver", "ic", "driver", "Titan Micro", "TM1637",
                 "Titan Micro TM1637 6-digit LED display driver with keyscan, proprietary "
                 "2-wire interface (CLK/DIO, not I2C), 4.5-5.5V, SOP-20. The chip behind "
                 "ubiquitous 4-digit clock display modules.",
                 {"contacts": 20, "mounting": "SMD", "supply_voltage": "4.5-5.5V",
                  "body_mm": "12.7x7.65x2.35"},
                 "https://m5stack.oss-cn-shenzhen.aliyuncs.com/resource/docs/datasheet/unit/digi_clock/TM1637.pdf",
                 "Titan Micro TM1637 datasheet V2.4 p.12: SOP20 body 12.7x7.65, span 10.45, "
                 "pitch 1.27, foot 0.8. Land pads 0.6x1.9 rows 9.6 c-c per IPC-7351. "
                 "Pinout p.2 (10=GRID6..15=GRID1 reversed order per datasheet).",
                 ["tm1637", "led", "display", "driver", "7-segment", "sop-20"])
    return fid, lib, fp, sym, meta


def inmp441():
    fid, lib = "inmp441", "ic/audio/inmp441"
    # 랜드 p17 Fig14 (1:1 필수): 열 2개 c-c 2.66, 세로피치 1.05, 패드 0.6x0.4.
    # 바텀뷰 미러(탑뷰): 우열 아래→위 1-4, 좌열 위→아래 6-9, 5=포트링(핀4/6 행, 중앙)
    ys = [1.575, 0.525, -0.525, -1.575]
    pads = [(str(i + 1), 1.33, ys[i], 0.6, 0.4) for i in range(4)]
    pads += [(str(6 + i), -1.33, -ys[3 - i] * -1, 0.6, 0.4) for i in range(4)]
    # 좌열 6,7,8,9 = y -1.575,-0.525,0.525,1.575
    pads = [(str(i + 1), 1.33, ys[i], 0.6, 0.4) for i in range(4)] + \
           [(str(6 + i), -1.33, [-1.575, -0.525, 0.525, 1.575][i], 0.6, 0.4) for i in range(4)]
    out = _fp_open(fid, "TDK InvenSense INMP441 I2S MEMS microphone, bottom-port LGA_CAV "
                        "4.72x3.76x0.98. Land pattern per datasheet Fig.14 (MANDATORY 1:1 - "
                        "do not oversize): 8 pads 0.4x0.6, port ring pad D1.56 with PCB "
                        "sound hole (0.5-1.0mm) at ring center.",
                   "INMP441 I2S MEMS microphone bottom port", -3.3, 3.3)
    out += _fab_body(-1.88, -2.36, 1.88, 2.36, 0.8)
    out += _silk_box((2.14, 2.62), 1.575 - 0.25, 1.575 + 0.25, 2.5)  # pin1 우측 → 틱 x>0
    out += _court(-2.13, -2.61, 2.13, 2.61)
    for name, x, y, w, h in pads:
        out.append(_smd(name, x, y, w, h))
    out.append(_smd("5", 0, -1.575, 1.56, 1.56, shape="circle"))  # 포트 링 (GND)
    out.append(_npth(0, -1.575, 0.8))  # PCB 사운드홀
    out.append(')')
    fp = "\n".join(out) + "\n"
    sym = _lr_symbol(fid, [("1", "SCK"), ("2", "SD"), ("3", "WS"), ("4", "L/R"), ("5", "GND")],
                     [("6", "GND"), ("7", "VDD"), ("8", "CHIPEN"), ("9", "GND")])
    meta = _meta(fid, "INMP441 I2S MEMS Microphone", "ic", "audio",
                 "TDK InvenSense", "INMP441ACEZ-R7",
                 "TDK InvenSense INMP441 omnidirectional bottom-port MEMS microphone with "
                 "24-bit I2S output, 1.8-3.3V. The default ESP32 I2S mic. Footprint "
                 "includes the required PCB sound hole (0.8mm NPTH) under the port ring - "
                 "keep solder paste off the hole.",
                 {"contacts": 9, "mounting": "SMD", "supply_voltage": "1.8-3.3V",
                  "interface": "I2S", "body_mm": "4.72x3.76x0.98"},
                 "https://www.farnell.com/datasheets/1824785.pdf",
                 "TDK DS-INMP441-00 Rev1.0: Fig.16 LGA_CAV 4.72x3.76x0.98; Fig.14 "
                 "recommended land (1:1): 8 pads 0.4x0.6, columns 2.66 c-c, pitch 1.05, "
                 "port ring ID0.96/OD1.56, PCB hole 0.5-1.0. Pinout Fig.3 (bottom view, "
                 "mirrored for footprint).",
                 ["inmp441", "invensense", "mems", "microphone", "i2s", "esp32", "audio"])
    return fid, lib, fp, sym, meta


def bh1750():
    fid, lib = "bh1750", "ic/sensor_if/bh1750"
    # WSOF6I: 하단행 1,2,3(좌→우, 그리드 중심 오프셋 0.025), 상단행 6,5,4(좌→우)
    xs = [-0.525, -0.025, 0.475]
    out = _fp_open(fid, "Rohm BH1750FVI ambient light sensor, WSOF6I 1.6x3.0x0.75. Pads "
                        "0.3x0.8 at rows +/-1.5 (pin row offset 0.025 per drawing). "
                        "CAUTION: exposed center back pad must have NO copper/paste.",
                   "BH1750 light sensor lux I2C WSOF6I", -2.6, 2.6)
    out += _fab_body(-0.775, -1.5, 0.825, 1.5, 0.4)
    out += _rect_lines([(-0.95, -1.05, -0.95, 1.05), (1.0, -1.05, 1.0, 1.05)], "F.SilkS", 0.12)
    out.append(_line(-0.9, 1.75, -0.5, 1.75, "F.SilkS", 0.12))  # pin1 틱 (하단좌)
    out += _court(-1.05, -2.15, 1.1, 2.15)
    for i, x in enumerate(xs):
        out.append(_smd(str(i + 1), x, 1.5, 0.3, 0.8))
    for i, x in enumerate(xs):
        out.append(_smd(str(6 - i), x, -1.5, 0.3, 0.8))
    out.append(')')
    fp = "\n".join(out) + "\n"
    sym = _lr_symbol(fid, [("1", "VCC"), ("2", "ADDR"), ("3", "GND")],
                     [("4", "SDA"), ("5", "DVI"), ("6", "SCL")])
    meta = _meta(fid, "BH1750FVI Ambient Light Sensor", "ic", "sensor_if",
                 "Rohm", "BH1750FVI-TR",
                 "Rohm BH1750FVI digital 16-bit ambient light sensor (1-65535 lx), I2C "
                 "(ADDR H=0x5C / L=0x23), 2.4-3.6V, WSOF6I. DVI pin needs 1uS low reset "
                 "after power-up. Exposed back pad: leave unconnected (no copper).",
                 {"contacts": 6, "mounting": "SMD", "supply_voltage": "2.4-3.6V",
                  "interface": "I2C", "i2c_address": "0x23/0x5C", "body_mm": "1.6x3.0x0.75"},
                 "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/1811081611_ROHM-Semicon-BH1750FVI-TR_C78960.pdf",
                 "Rohm BH1750FVI Technical Note Rev.D p.14: WSOF6I 1.6x3.0x0.75, 6 leads "
                 "pitch 0.5 (row offset 0.025), foot 0.3. Pads 0.3x0.8 derived per IPC-7351; "
                 "center back pad no-connect per p.16 caution 10. Pinout p.13 + package "
                 "drawing numbering (bottom row 1-3, top row 6-4).",
                 ["bh1750", "rohm", "light", "lux", "ambient", "i2c", "gy-302"])
    return fid, lib, fp, sym, meta


def xl6009():
    fid, lib = "xl6009", "ic/regulator/xl6009"
    out = _fp_open(fid, "XLSEMI XL6009 4A boost converter, TO-263-5 (body 8.64x10.16, "
                        "pitch 1.7). Lead pads 1.05x2.8, tab pad 10.4x7.0. "
                        "CAUTION: tab is SW (switch node), NOT ground.",
                   "XL6009 boost step-up TO-263", -9.2, 9.2)
    out += _fab_body(-5.08, -4.32, 5.08, 4.32, 1.0)
    out += _rect_lines([(-5.19, -4.32, -5.19, 4.32), (5.19, -4.32, 5.19, 4.32)], "F.SilkS", 0.12)
    out.append(_line(-4.3, 8.8, -3.7, 8.8, "F.SilkS", 0.12))  # pin1 틱
    out += _court(-5.45, -5.55, 5.45, 8.85)
    for i in range(5):
        out.append(_smd(str(i + 1), -3.4 + i * 1.7, 7.2, 1.05, 2.8))
    out.append(_smd("3", 0, -1.8, 10.4, 7.0))  # 탭 = SW = 핀3
    out.append(')')
    fp = "\n".join(out) + "\n"
    sym = _lr_symbol(fid, [("4", "VIN"), ("2", "EN"), ("1", "GND")],
                     [("3", "SW"), ("5", "FB")])
    meta = _meta(fid, "XL6009 4A Boost Converter", "ic", "regulator", "XLSEMI", "XL6009E1",
                 "XLSEMI XL6009 400kHz 4A step-up (boost) DC-DC converter, 5-32V input, "
                 "TO-263-5. WARNING: the metal tab is the SW switch node, not GND - do "
                 "not pour ground under it.",
                 {"contacts": 5, "mounting": "SMD", "supply_voltage": "5-32V",
                  "body_mm": "8.64x10.16x4.55"},
                 "https://components101.com/sites/default/files/component_datasheet/XL6009-Datasheet_0.pdf",
                 "XLSEMI XL6009 datasheet Rev1.1 p.8: TO263-5L body 8.64x10.16x4.55, "
                 "overall 14.35 incl leads, pitch 1.7, lead 0.84, tab ext 1.27. Land "
                 "derived per IPC (leads 1.05x2.8, tab 10.4x7.0). Pinout p.2 (tab=SW).",
                 ["xl6009", "xlsemi", "boost", "step-up", "dc-dc", "to-263"])
    return fid, lib, fp, sym, meta


def mlx90614():
    fid, lib = "mlx90614", "sensor/melexis/mlx90614"
    # TO-39: 리드 4 Ø0.45 @ 리드서클 Ø5.08 (탑뷰: 1 좌상, 2 좌하, 3 우하, 4 우상, 탭 상단)
    r = 5.08 / 2 * 0.7071068
    pos = [("1", -r, -r), ("2", -r, r), ("3", r, r), ("4", r, -r)]
    out = _fp_open(fid, "Melexis MLX90614 IR thermometer, TO-39 can (flange D9.12, leads "
                        "D0.45 on D5.08 circle). THT drill 0.8, pad D1.4. Tab at top "
                        "(between pins 4 and 1). Can must only connect via VSS.",
                   "MLX90614 IR thermometer contactless TO-39", -6.2, 6.2, attr="through_hole")
    import math
    R = 9.12 / 2
    pts = [(R * math.cos(a * math.pi / 8), R * math.sin(a * math.pi / 8)) for a in range(17)]
    for i in range(16):
        out.append(_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], "F.Fab", 0.10))
    Rs = R + 0.15
    pts = [(Rs * math.cos(a * math.pi / 8), Rs * math.sin(a * math.pi / 8)) for a in range(17)]
    for i in range(16):
        out.append(_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], "F.SilkS", 0.12))
    out.append(_line(-0.4, -5.3, 0.4, -5.3, "F.SilkS", 0.12))  # 탭 마커 (상단)
    out += _court(-4.87, -5.5, 4.87, 4.87)
    for name, x, y in pos:
        shape = "rect" if name == "1" else "circle"
        out.append(_tht(name, x, y, 1.4, 0.8, shape))
    out.append(')')
    fp = "\n".join(out) + "\n"
    sym = _lr_symbol(fid, [("3", "VDD"), ("4", "VSS")], [("1", "SCL/Vz"), ("2", "SDA/PWM")])
    meta = _meta(fid, "MLX90614 IR Thermometer (TO-39)", "sensor", "temperature",
                 "Melexis", "MLX90614ESF-BAA",
                 "Melexis MLX90614 contactless infrared thermometer, SMBus (default 0x5A) "
                 "or PWM output, factory-calibrated, TO-39 metal can. GY-906 module chip. "
                 "Metal can: no electrical connection except via VSS.",
                 {"contacts": 4, "mounting": "THT", "supply_voltage": "3.0V (BAA) / 5V (Axx)",
                  "interface": "SMBus", "body_mm": "D9.12x4.1"},
                 "https://www.melexis.com/-/media/files/documents/datasheets/mlx90614-datasheet-melexis.pdf",
                 "Melexis MLX90614 datasheet Rev021 p.47 Fig.41 (xxA can): flange D9.12, "
                 "height 4.1, 4 leads D0.45 on D5.08 circle at 90deg, tab at 45deg between "
                 "pins 4-1. Pinout Table 2/Fig.1 p.6 (bottom view, mirrored for footprint).",
                 ["mlx90614", "melexis", "infrared", "thermometer", "contactless", "smbus",
                  "gy-906", "to-39"])
    return fid, lib, fp, sym, meta


MAX1704X_CODES = {"17048": "1-cell", "17049": "2-cell"}


def _max1704x(code):
    cells = MAX1704X_CODES[code]
    fid, lib = f"max{code}", f"ic/power/max{code}"
    pads = two_row_pads(8, 0.5, 1.98, 0.70, 0.30)
    fp = _fp_two_row(fid, f"Maxim MAX{code} LiPo fuel gauge, TDFN-8 2x2x0.75 (T822+3). Land "
                          "per official 90-0065: pads 0.30x0.70 pitch 0.5 rows 1.98 c-c, "
                          "EP 0.8x1.38.", f"MAX{code} fuel gauge TDFN", pads, (1.0, 1.0),
                     ep=("9", 0.8, 1.38))
    nm = ["CTG", "CELL", "VDD", "GND", "ALRT", "QSTRT", "SCL", "SDA"]
    sym = _lr_symbol(fid, [(str(i + 1), nm[i]) for i in range(4)],
                     [(str(i + 5), nm[i + 4]) for i in range(4)],
                     bottom=[("9", "EP/GND")])
    tail = (" CELL pin senses the 2-cell stack." if code == "17049" else
            " The battery-percentage chip on modern ESP32 dev boards.")
    meta = _meta(fid, f"MAX{code} LiPo Fuel Gauge ({cells})", "ic", "power",
                 "Maxim Integrated", f"MAX{code}G+T10",
                 f"Maxim MAX{code} {cells} Li-ion fuel gauge with ModelGauge, I2C 0x36 "
                 "fixed, 2.5-4.5V, TDFN-8 2x2 (EP=GND)." + tail,
                 {"contacts": 9, "mounting": "SMD", "supply_voltage": "2.5-4.5V",
                  "interface": "I2C", "i2c_address": "0x36", "body_mm": "2.0x2.0x0.75"},
                 "https://cdn.sparkfun.com/assets/5/2/7/6/6/MAX17048-MAX17049.pdf",
                 "Maxim 19-6171 Rev7 + official outline 21-0168 RevM (TDFN 2x2, pitch 0.5, "
                 "EP 0.8x1.2) + official land 90-0065 RevE (pads 0.30x0.70, rows 1.98 c-c "
                 "vector-verified, EP land 0.8x1.38). Pinout p.6 (datasheet covers both "
                 "MAX17048/MAX17049).",
                 [fid, "maxim", "fuel gauge", "lipo", "battery", "i2c", "tdfn"])
    return fid, lib, fp, sym, meta


def max17048():
    return _max1704x("17048")


def sgp40():
    fid, lib = "sgp40", "sensor/sensirion/sgp40"
    # Fig.14의 2.3은 중심간 스팬 (외측으로 읽으면 센터패드와 0.025 겹침 = 불가능 설계;
    # 중심간이면 간극 0.25 정합 — A4988과 동일 함정)
    pads = two_row_pads(6, 0.8, 2.3, 0.55, 0.4)
    fp = _fp_two_row(fid, "Sensirion SGP40 VOC sensor, DFN-6 2.44x2.44x0.85. Land per "
                          "datasheet Fig.14: pads 0.4x0.55 pitch 0.8, centers 2.3 c-c, "
                          "center die pad 1.25x1.7 (GND, solder recommended).",
                     "SGP40 VOC gas sensor DFN", pads, (1.22, 1.22), ep=("7", 1.25, 1.7))
    sym = _lr_symbol(fid, [("1", "VDD"), ("2", "VSS"), ("3", "SDA")],
                     [("4", "n/a(GND)"), ("5", "VDDH"), ("6", "SCL")],
                     bottom=[("7", "DIE/GND")])
    meta = _meta(fid, "SGP40 VOC Air Quality Sensor", "sensor", "gas", "Sensirion",
                 "SGP40-D-R4",
                 "Sensirion SGP40 digital VOC sensor for air quality, I2C 0x59, 1.7-3.6V "
                 "(VDD and VDDH must share one supply), DFN-6 with sensing opening on top "
                 "(do not cover). Die pad = GND, soldering recommended.",
                 {"contacts": 7, "mounting": "SMD", "supply_voltage": "1.7-3.6V",
                  "interface": "I2C", "i2c_address": "0x59", "body_mm": "2.44x2.44x0.85"},
                 "https://sensirion.com/media/documents/296373BB/6203C5DF/Sensirion_Gas_Sensors_Datasheet_SGP40.pdf",
                 "Sensirion SGP40 datasheet v1.2: Fig.13 DFN-6 2.44x2.44x0.85 (pitch 0.8, "
                 "terminal 0.4x0.35, die pad 1.25x1.64); Fig.14 recommended land (pads "
                 "0.4x0.55, centers 2.3 c-c - geometry-verified vs center pad clearance, "
                 "center 1.25x1.7). Pinout Table 6 p.7.",
                 ["sgp40", "sensirion", "voc", "gas", "air quality", "i2c", "dfn"])
    return fid, lib, fp, sym, meta


def veml7700():
    fid, lib = "veml7700", "sensor/vishay/veml7700"
    out = _fp_open(fid, "Vishay VEML7700 ambient light sensor, side-view 6.8x2.35x3.0 SMD. "
                        "Land per datasheet p.10 (-TR side view): 4 pads 0.7x1.4 pitch 1.27.",
                   "VEML7700 ambient light sensor lux I2C", -2.6, 2.6)
    out += _fab_body(-3.4, -1.175, 3.4, 1.175, 0.8)
    out += _rect_lines([(-3.51, -1.29, 3.51, -1.29)], "F.SilkS", 0.12)
    out.append(_line(-2.3, 1.6, -1.5, 1.6, "F.SilkS", 0.12))  # pin1 틱
    out += _court(-3.65, -1.42, 3.65, 1.55)
    for i in range(4):
        out.append(_smd(str(i + 1), -1.905 + i * 1.27, 0.6, 0.7, 1.4))
    out.append(')')
    fp = "\n".join(out) + "\n"
    sym = _lr_symbol(fid, [("1", "SCL"), ("2", "VDD")], [("3", "GND"), ("4", "SDA")])
    meta = _meta(fid, "VEML7700 Ambient Light Sensor", "sensor", "optical", "Vishay",
                 "VEML7700-TR",
                 "Vishay VEML7700 high-accuracy 16-bit ambient light sensor, 0-140klx, "
                 "I2C 0x10 fixed, 2.5-3.6V, transparent side-view SMD package.",
                 {"contacts": 4, "mounting": "SMD", "supply_voltage": "2.5-3.6V",
                  "interface": "I2C", "i2c_address": "0x10", "body_mm": "6.8x2.35x3.0"},
                 "https://www.vishay.com/docs/84286/veml7700.pdf",
                 "Vishay VEML7700 datasheet Rev1.8 p.10: package 6.8(6.6 body)x3.0x2.35, "
                 "4 leads 0.5 wide pitch 1.27; proposed pad layout (side view mount): "
                 "pads 0.7x1.4 pitch 1.27. Pinout p.1.",
                 ["veml7700", "vishay", "light", "lux", "ambient", "i2c"])
    return fid, lib, fp, sym, meta


# ---------- 배치3 모듈 (THT 보드) ----------

def _tht_row(names, x0, y, pitch, horiz=True, start=1, dia=1.7, drill=1.0):
    out = []
    for i, _ in enumerate(names):
        x = x0 + i * pitch if horiz else x0
        yy = y if horiz else y + i * pitch
        shape = "rect" if (start + i) == 1 else "circle"
        out.append(_tht(str(start + i), x, yy, dia, drill, shape))
    return out


def hc_sr04():
    fid, lib = "hc_sr04", "module/sensor/hc_sr04"
    import math
    out = _fp_open(fid, "HC-SR04 ultrasonic distance sensor module, 45x20mm board, two "
                        "D16 transducers (27.0 c-c), 4-pin right-angle header at bottom "
                        "edge. 4x D2.0 mounting holes 40x15 grid (2-hole variants exist). "
                        "Dimensions per Elecfreaks/Cytron drawings + photo measurement.",
                   "HC-SR04 ultrasonic sensor module", -11.5, 11.5, attr="through_hole")
    out += _fab_body(-22.5, -10, 22.5, 10, 1.5)
    for cx in (-13.5, 13.5):
        R = 8.0
        pts = [(cx + R * math.cos(a * math.pi / 8), R * math.sin(a * math.pi / 8))
               for a in range(17)]
        for i in range(16):
            out.append(_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], "F.Fab", 0.10))
    out += _rect_lines([(-22.61, -10.11, 22.61, -10.11), (22.61, -10.11, 22.61, 10.11),
                        (22.61, 10.11, -22.61, 10.11), (-22.61, 10.11, -22.61, -10.11)],
                       "F.SilkS", 0.12)
    out.append(_line(-5.2, 9.6, -4.4, 9.6, "F.SilkS", 0.12))  # pin1(VCC) 틱
    out += _court(-22.75, -10.25, 22.75, 10.25)
    out += _tht_row(["VCC", "Trig", "Echo", "GND"], -3.81, 8.0, 2.54)
    for hx, hy in ((-20, -7.5), (20, -7.5), (-20, 7.5), (20, 7.5)):
        out.append(_npth(hx, hy, 2.0))
    out.append(')')
    fp = "\n".join(out) + "\n"
    sym = _lr_symbol(fid, [("1", "VCC"), ("2", "Trig"), ("3", "Echo"), ("4", "GND")], [])
    meta = _meta(fid, "HC-SR04 Ultrasonic Distance Sensor Module", "module", "sensor",
                 "Generic", "HC-SR04",
                 "Classic HC-SR04 ultrasonic ranging module (2-400cm), 5V, 4-pin header "
                 "(VCC Trig Echo GND). Footprint is the module board with mounting holes; "
                 "HC-SR04P (3.3-5.5V) and RCWL clones are mechanically identical. Some "
                 "units have only 2 diagonal mounting holes.",
                 {"contacts": 4, "mounting": "THT header", "supply_voltage": "5V",
                  "board_mm": "45x20"},
                 "https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf",
                 "Elecfreaks HC-SR04 datasheet (45x20x15) + Cytron manual drawing (4 holes, "
                 "40mm spacing) + calibrated photo measurement: holes D2.0 at 2.5 corner "
                 "insets (40.0x15.0 grid), transducers D16 at 27.0 c-c, header 2.54 pitch "
                 "centered 2.0 above bottom edge.",
                 ["hc-sr04", "ultrasonic", "distance", "sonar", "module", "arduino"])
    return fid, lib, fp, sym, meta


def dfplayer_mini():
    fid, lib = "dfplayer_mini", "module/audio/dfplayer_mini"
    out = _fp_open(fid, "DFRobot DFPlayer Mini MP3 module (DFR0299), 20.32x20.32mm, 16 pins "
                        "2.54 pitch, row spacing 18.03mm (official drawing - NOT 17.78).",
                   "DFPlayer Mini MP3 module DFR0299", -11.7, 11.7, attr="through_hole")
    out += _fab_body(-10.16, -10.16, 10.16, 10.16, 1.5)
    out += _rect_lines([(-10.27, -10.27, 10.27, -10.27), (10.27, -10.27, 10.27, 10.27),
                        (10.27, 10.27, -10.27, 10.27), (-10.27, 10.27, -10.27, -10.27)],
                       "F.SilkS", 0.12)
    out.append(_line(-11.0, -9.14, -11.0, -8.64, "F.SilkS", 0.12))  # pin1 틱
    out += _court(-10.41, -10.41, 10.41, 10.41)
    L = ["VCC", "RX", "TX", "DAC_R", "DAC_L", "SPK_1", "GND", "SPK_2"]
    R = ["IO_1", "GND", "IO_2", "ADKEY_1", "ADKEY_2", "USB+", "USB-", "BUSY"]
    for i in range(8):
        out.append(_tht(str(i + 1), -9.015, -8.89 + i * 2.54, 1.7, 1.0,
                        "rect" if i == 0 else "circle"))
    for i in range(8):
        out.append(_tht(str(9 + i), 9.015, 8.89 - i * 2.54, 1.7, 1.0, "circle"))
    out.append(')')
    fp = "\n".join(out) + "\n"
    sym = _lr_symbol(fid, [(str(i + 1), L[i]) for i in range(8)],
                     [(str(16 - i), R[7 - i]) for i in range(8)])
    meta = _meta(fid, "DFPlayer Mini MP3 Player Module", "module", "audio",
                 "DFRobot", "DFR0299",
                 "DFRobot DFPlayer Mini serial MP3 player module with microSD slot and "
                 "3W amp, 3.2-5V, UART control. Clones (MP3-TF-16P) share the identical "
                 "footprint. Row spacing is 18.03mm per the official drawing.",
                 {"contacts": 16, "mounting": "THT", "supply_voltage": "3.2-5V",
                  "board_mm": "20.32x20.32"},
                 "https://wiki.dfrobot.com/DFPlayer_Mini_SKU_DFR0299",
                 "DFRobot DFR0299 official dimension drawing v1.1: board 20.32x20.32, "
                 "16 pins 2.54 pitch, columns 18.03 c-c, pin1 1.27 below top edge. Pin "
                 "names per official wiki pinout.",
                 ["dfplayer", "mp3", "audio", "module", "dfrobot", "microsd"])
    return fid, lib, fp, sym, meta


def hc05():
    fid, lib = "hc05", "module/rf/hc05"
    nm = ["STATE", "RXD", "TXD", "GND", "VCC", "EN"]
    out = _fp_open(fid, "HC-05 bluetooth module on ZS-040 carrier, 37x16mm, 6-pin "
                        "right-angle header (STATE RXD TXD GND VCC EN). Also fits HC-06 "
                        "(same board). Dimensions per ProtoSupplies measurement, "
                        "pitch-calibrated photos.",
                   "HC-05 HC-06 bluetooth module ZS-040", -9.5, 9.5, attr="through_hole")
    out += _fab_body(-18.5, -8, 18.5, 8, 1.5)
    out += _rect_lines([(-18.61, -8.11, 18.61, -8.11), (18.61, -8.11, 18.61, 8.11),
                        (18.61, 8.11, -18.61, 8.11), (-18.61, 8.11, -18.61, -8.11)],
                       "F.SilkS", 0.12)
    out.append(_line(-17.6, -7.0, -17.6, -6.4, "F.SilkS", 0.12))  # pin1 틱
    out += _court(-18.75, -8.25, 18.75, 8.25)
    for i in range(6):
        out.append(_tht(str(i + 1), -16.5, -6.35 + i * 2.54, 1.7, 1.0,
                        "rect" if i == 0 else "circle"))
    out.append(')')
    fp = "\n".join(out) + "\n"
    sym = _lr_symbol(fid, [(str(i + 1), nm[i]) for i in range(6)], [])
    meta = _meta(fid, "HC-05 Bluetooth Module (ZS-040)", "module", "rf",
                 "Generic (ZS-040)", "HC-05",
                 "HC-05 bluetooth serial (SPP) module on the common ZS-040 carrier board, "
                 "3.6-6V supply / 3.3V logic, 6-pin right-angle header. HC-06 ships on "
                 "the same board (4 of 6 pins used).",
                 {"contacts": 6, "mounting": "THT", "supply_voltage": "3.6-6V",
                  "board_mm": "37x16"},
                 "https://protosupplies.com/product/hc-05-bluetooth-module/",
                 "ZS-040 carrier: 37x16 board (ProtoSupplies measured), 6-pin 2.54 "
                 "right-angle header inset 2.0 from edge, group centered; daughterboard "
                 "27x13. Pin names verbatim from board silkscreen.",
                 ["hc-05", "hc-06", "bluetooth", "serial", "module", "zs-040"])
    return fid, lib, fp, sym, meta


def sim800l():
    fid, lib = "sim800l", "module/rf/sim800l"
    L = ["NET", "VCC", "RST", "RXD", "TXD", "GND"]
    R = ["RING", "DTR", "MIC+", "MIC-", "SPK+", "SPK-"]
    out = _fp_open(fid, "SIM800L GSM breakout (red coreboard), 24.9x22.7mm, 2x6 pins 2.54 "
                        "pitch columns 20.0 c-c. NOT the blue SIM800L EVB v2.0 (different "
                        "board). Photo-measured, 2.54-pitch calibrated.",
                   "SIM800L GSM GPRS module breakout", -13.2, 13.2, attr="through_hole")
    out += _fab_body(-12.45, -11.35, 12.45, 11.35, 1.5)
    out += _rect_lines([(-12.56, -11.46, 12.56, -11.46), (12.56, -11.46, 12.56, 11.46),
                        (12.56, 11.46, -12.56, 11.46), (-12.56, 11.46, -12.56, -11.46)],
                       "F.SilkS", 0.12)
    out.append(_line(-11.4, -5.9, -11.4, -5.4, "F.SilkS", 0.12))  # pin1(NET) 틱
    out += _court(-12.7, -11.6, 12.7, 11.6)
    for i in range(6):
        out.append(_tht(str(i + 1), -10.0, -5.65 + i * 2.54, 1.7, 1.0,
                        "rect" if i == 0 else "circle"))
    for i in range(6):
        out.append(_tht(str(7 + i), 10.0, -5.65 + i * 2.54, 1.7, 1.0, "circle"))
    out.append(')')
    fp = "\n".join(out) + "\n"
    sym = _lr_symbol(fid, [(str(i + 1), L[i]) for i in range(6)],
                     [(str(7 + i), R[i]) for i in range(6)])
    meta = _meta(fid, "SIM800L GSM/GPRS Module (Red Breakout)", "module", "rf",
                 "SIMCom (generic breakout)", "SIM800L",
                 "SIM800L quad-band GSM/GPRS module on the common red coreboard, 3.4-4.4V "
                 "(2A bursts!), UART, u.FL + solder antenna pads, micro-SIM on back. "
                 "Do not confuse with the larger blue SIM800L EVB v2.0.",
                 {"contacts": 12, "mounting": "THT", "supply_voltage": "3.4-4.4V",
                  "board_mm": "24.9x22.7"},
                 "https://www.haoyuelectronics.com/Attachment/SIM800L/SIM800L_Coreboard.jpg",
                 "HAOYU coreboard photos, pitch-calibrated: board 24.9x22.7, 2x6 pins "
                 "2.54 pitch, columns 20.0 c-c (off-grid), first pin 5.7 below top edge. "
                 "Pin names verbatim from silkscreen (NET has square pad).",
                 ["sim800l", "gsm", "gprs", "sms", "module", "simcom"])
    return fid, lib, fp, sym, meta


def max7219_matrix_module():
    fid, lib = "max7219_matrix_module", "module/display/max7219_matrix_module"
    IN = ["VCC", "GND", "DIN", "CS", "CLK"]
    OUT = ["VCC", "GND", "DOUT", "CS", "CLK"]
    out = _fp_open(fid, "MAX7219 8x8 LED matrix module (FC-16, cascadable), 32x32mm, 5-pin "
                        "headers on both edges (IN left, OUT right), 4x M3 holes 26x20 grid.",
                   "MAX7219 8x8 LED matrix module FC-16", -17.5, 17.5, attr="through_hole")
    out += _fab_body(-16, -16, 16, 16, 1.5)
    out += _rect_lines([(-16.11, -16.11, 16.11, -16.11), (16.11, -16.11, 16.11, 16.11),
                        (16.11, 16.11, -16.11, 16.11), (-16.11, 16.11, -16.11, -16.11)],
                       "F.SilkS", 0.12)
    out.append(_line(-15.9, -5.6, -15.4, -5.6, "F.SilkS", 0.12))  # pin1 틱
    out += _court(-16.25, -16.25, 16.25, 16.25)
    for i in range(5):
        out.append(_tht(str(i + 1), -14.73, -5.08 + i * 2.54, 1.7, 1.0,
                        "rect" if i == 0 else "circle"))
    for i in range(5):
        out.append(_tht(str(6 + i), 14.73, -5.08 + i * 2.54, 1.7, 1.0, "circle"))
    for hx, hy in ((-13, -10), (13, -10), (-13, 10), (13, 10)):
        out.append(_npth(hx, hy, 3.0))
    out.append(')')
    fp = "\n".join(out) + "\n"
    sym = _lr_symbol(fid, [(str(i + 1), IN[i]) for i in range(5)],
                     [(str(6 + i), OUT[i]) for i in range(5)])
    meta = _meta(fid, "MAX7219 8x8 LED Matrix Module (FC-16)", "module", "display",
                 "Generic (FC-16)", "FC-16 MAX7219",
                 "Cascadable 8x8 LED dot matrix module driven by MAX7219, SPI-like 3-wire, "
                 "5V, IN/OUT headers for daisy-chaining, 32x32mm. The bare MAX7219 chip is "
                 "in the official KiCad library; this is the module board.",
                 {"contacts": 10, "mounting": "THT", "supply_voltage": "5V",
                  "board_mm": "32x32"},
                 "https://components101.com/sites/default/files/component_datasheet/MAX7219%208x8%20LED%20Matrix%20Module%20Datasheet.pdf",
                 "Components101 FC-16 module datasheet p.9 dimension drawing: 32x32 board, "
                 "4x D3.0 holes 26x20 grid centered; 5-pin 2.54 headers both edges, group "
                 "centered (span 10.16), inset 1.27 (photo-estimated 1.0-1.3). Pin order "
                 "verified: VCC GND DIN/DOUT CS CLK.",
                 ["max7219", "led matrix", "8x8", "module", "fc-16", "cascadable"])
    return fid, lib, fp, sym, meta


def gc9a01_module_128():
    fid, lib = "gc9a01_module_128", "module/display/gc9a01_module_128"
    import math
    nm = ["BLK", "CS", "DC", "RES", "SDA", "SCL", "VCC", "GND"]
    cy = -3.9  # 원 중심 (전고 45.8, 하단 탭)
    out = _fp_open(fid, "GC9A01 1.28 inch round LCD module (240x240 IPS, SPI), round PCB "
                        "D38 + 23mm bottom tab (45.8 overall), 8-pin header. Dimensions "
                        "per lcdwiki MSP1281 vendor drawing. 7-pin variants drop BLK.",
                   "GC9A01 round LCD 1.28 240x240 SPI module", -25.5, 25.5,
                   attr="through_hole")
    R = 19.0
    pts = [(R * math.cos(a * math.pi / 12), cy + R * math.sin(a * math.pi / 12))
           for a in range(25)]
    for i in range(24):
        out.append(_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], "F.Fab", 0.10))
    out += _rect_lines([(-11.5, 11.4, -11.5, 22.9), (-11.5, 22.9, 11.5, 22.9),
                        (11.5, 22.9, 11.5, 11.4)], "F.Fab", 0.10)  # 탭
    Ra = 16.2
    pts = [(Ra * math.cos(a * math.pi / 12), cy + Ra * math.sin(a * math.pi / 12))
           for a in range(25)]
    for i in range(24):
        out.append(_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], "F.Fab", 0.10))
    Rs = 19.15
    pts = [(Rs * math.cos(a * math.pi / 12), cy + Rs * math.sin(a * math.pi / 12))
           for a in range(25)]
    for i in range(24):
        out.append(_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], "F.SilkS", 0.12))
    out.append(_line(-9.7, 23.3, -8.1, 23.3, "F.SilkS", 0.12))  # pin1(BLK) 틱
    out += _court(-19.25, -23.15, 19.25, 23.15)
    for i in range(8):
        out.append(_tht(str(i + 1), -8.89 + i * 2.54, 21.43, 1.7, 1.0,
                        "rect" if i == 0 else "circle"))
    for hx in (-9.7, 9.7):
        out.append(_npth(hx, 17.08, 2.0))
    out.append(')')
    fp = "\n".join(out) + "\n"
    sym = _lr_symbol(fid, [(str(i + 1), nm[i]) for i in range(8)], [])
    meta = _meta(fid, "1.28\" GC9A01 Round LCD Module (240x240, SPI)", "module", "display",
                 "Generic (lcdwiki MSP1281)", "MSP1281",
                 "Common 1.28 inch round IPS LCD module with GC9A01 controller, 240x240, "
                 "SPI 8-pin header (BLK CS DC RES SDA SCL VCC GND), round PCB D38 with "
                 "23mm bottom tab. Smartwatch-project staple; pairs with CST816S touch "
                 "variants. Verify against your vendor - clones vary.",
                 {"contacts": 8, "mounting": "THT header", "interface": "SPI",
                  "supply_voltage": "3.3V", "board_mm": "D38.03x45.8"},
                 "https://www.lcdwiki.com/res/MSP1281/MSP1281_Size.pdf",
                 "lcdwiki MSP1281 size drawing: round D38.03 + tab 23.0 wide, overall "
                 "45.8; 8-pin 2.54 header (span 17.78, row 1.47 above bottom); 2x D2.0 "
                 "holes 19.4 c-c at 5.82 above bottom; active area D32.4 concentric.",
                 ["gc9a01", "round lcd", "1.28", "240x240", "spi", "module", "smartwatch"])
    return fid, lib, fp, sym, meta


def ld2410c():
    fid, lib = "ld2410c", "module/sensor/ld2410c"
    nm = ["TX", "RX", "OUT", "GND", "VCC"]
    out = _fp_open(fid, "Hi-Link HLK-LD2410C 24GHz mmWave human presence radar module, "
                        "22x16mm, 5-pin 2.54 header (TX RX OUT GND VCC - official "
                        "datasheet; the 1.27 pitch applies to LD2410/B, not C). Keep the "
                        "antenna face unobstructed.",
                   "LD2410C mmWave radar presence sensor module", -9.5, 9.5,
                   attr="through_hole")
    out += _fab_body(-11, -8, 11, 8, 1.5)
    out += _rect_lines([(-11.11, -8.11, 11.11, -8.11), (11.11, -8.11, 11.11, 8.11),
                        (11.11, 8.11, -11.11, 8.11), (-11.11, 8.11, -11.11, -8.11)],
                       "F.SilkS", 0.12)
    out.append(_line(-5.8, -6.5, -5.8, -5.9, "F.SilkS", 0.12))  # pin1(TX) 틱
    out += _court(-11.25, -8.25, 11.25, 8.25)
    for i in range(5):
        out.append(_tht(str(i + 1), -5.08 + i * 2.54, -5.46, 1.6, 0.9,
                        "rect" if i == 0 else "circle"))
    out.append(')')
    fp = "\n".join(out) + "\n"
    sym = _lr_symbol(fid, [(str(i + 1), nm[i]) for i in range(5)], [])
    meta = _meta(fid, "HLK-LD2410C 24GHz mmWave Presence Radar", "module", "sensor",
                 "Hi-Link", "HLK-LD2410C",
                 "Hi-Link LD2410C 24GHz FMCW radar for human presence detection, UART + "
                 "presence OUT pin (3.3V logic), 5-12V supply (5V advised, 200mA). "
                 "ESPHome/Home Assistant staple. Antenna side must face the room.",
                 {"contacts": 5, "mounting": "THT", "supply_voltage": "5-12V",
                  "board_mm": "22x16"},
                 "https://d.hlktech.net/download/HLK-LD2410C/1/",
                 "Hi-Link HLK-LD2410C datasheet V1.00 pp.6-8: board 22x16, 5 pin holes "
                 "D0.9 at 2.54 pitch (verbatim: 'pin spacing is 2.54mm'), row ~2.54 from "
                 "edge, centered. Pin order TX RX OUT GND VCC per silkscreen/table.",
                 ["ld2410", "mmwave", "radar", "presence", "human sensor", "hi-link",
                  "esphome"])
    return fid, lib, fp, sym, meta


def esp32_devkitc_v4():
    fid, lib = "esp32_devkitc_v4", "module/devboard/esp32_devkitc_v4"
    L = ["3V3", "EN", "VP", "VN", "IO34", "IO35", "IO32", "IO33", "IO25", "IO26", "IO27",
         "IO14", "IO12", "GND", "IO13", "D2", "D3", "CMD", "5V"]
    R = ["GND", "IO23", "IO22", "TX", "RX", "IO21", "GND", "IO19", "IO18", "IO5", "IO17",
         "IO16", "IO4", "IO0", "IO2", "IO15", "D1", "D0", "CLK"]
    out = _fp_open(fid, "Espressif ESP32-DevKitC V4 development board, 48.26x27.94mm "
                        "(54.3 incl. antenna overhang), 2x19 pins 2.54 pitch rows 25.4 "
                        "c-c. Dimensions from the official Espressif drawing.",
                   "ESP32 DevKitC V4 devboard WROOM-32", -27.5, 27.5, attr="through_hole")
    out += _fab_body(-13.97, -24.13, 13.97, 24.13, 2.0)
    out += _rect_lines([(-9, -30.17, 9, -30.17), (9, -30.17, 9, -24.13),
                        (-9, -30.17, -9, -24.13)], "F.Fab", 0.10)  # WROOM 안테나 오버행
    out += _rect_lines([(-4, 20.13, 4, 20.13), (4, 20.13, 4, 24.6),
                        (-4, 20.13, -4, 24.6)], "F.Fab", 0.10)     # Micro-USB
    out += _rect_lines([(-14.08, -24.24, 14.08, -24.24), (14.08, -24.24, 14.08, 24.24),
                        (14.08, 24.24, -14.08, 24.24), (-14.08, 24.24, -14.08, -24.24)],
                       "F.SilkS", 0.12)
    out.append(_line(-13.4, -23.15, -13.4, -22.55, "F.SilkS", 0.12))  # pin1(3V3) 틱
    out += _court(-14.22, -30.3, 14.22, 24.85)
    for i in range(19):
        out.append(_tht(str(i + 1), -12.7, -22.86 + i * 2.54, 1.7, 1.0,
                        "rect" if i == 0 else "circle"))
    for i in range(19):
        out.append(_tht(str(20 + i), 12.7, -22.86 + i * 2.54, 1.7, 1.0, "circle"))
    out.append(')')
    fp = "\n".join(out) + "\n"
    sym = _lr_symbol(fid, [(str(i + 1), L[i]) for i in range(19)],
                     [(str(20 + i), R[i]) for i in range(19)])
    meta = _meta(fid, "ESP32-DevKitC V4 Development Board", "module", "devboard",
                 "Espressif", "ESP32-DevKitC-32E",
                 "Espressif ESP32-DevKitC V4 dev board (ESP32-WROOM-32E), 38-pin 2.54 "
                 "headers at 25.4mm row spacing - drop it onto a carrier PCB with two "
                 "1x19 sockets. WROOM antenna overhangs the board edge by 6mm: keep that "
                 "zone copper-free.",
                 {"contacts": 38, "mounting": "THT", "supply_voltage": "5V (USB) / 3.3V",
                  "board_mm": "48.26x27.94"},
                 "https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32/esp32-devkitc/user_guide.html",
                 "Espressif official ESP32-DevKitC V4 dimension drawing: board 48.26x27.94, "
                 "rows 25.40 c-c, pitch 2.54, end pins 1.29 from USB edge, WROOM overhang "
                 "6.04. Pin order verbatim from the official board pinout.",
                 ["esp32", "devkitc", "devboard", "wroom-32", "espressif", "development"])
    return fid, lib, fp, sym, meta


# ================= 배치 4차 (§21-6ⓑ 새 종류) =================

def qmc5883p():
    fid, lib = "qmc5883p", "sensor/qst/qmc5883p"
    # 랜드(권장 Fig7, 픽셀 실측): 16패드 0.40x0.25, 피치 0.5, 반대행 c-c 2.60
    pads = quad_pads(4, 0.5, 2.60, 0.40, 0.25)
    fp = _fp_quad(fid, "QST QMC5883P 3-axis magnetometer, LGA-16 3x3x0.9. Land per "
                       "datasheet Fig.7 (pixel-measured): 16 pads 0.40x0.25, pitch 0.5, "
                       "rows 2.60 c-c. PINOUT DIFFERS FROM QMC5883L (6 active pads only).",
                  "QMC5883P magnetometer compass I2C", pads, 1.5)
    nm = {1: "SCK", 2: "VDD", 9: "GND", 10: "C1", 11: "GND", 16: "SDA"}
    left = [(str(i), nm.get(i, "NC")) for i in range(1, 9)]
    right = [(str(i), nm.get(i, "NC")) for i in range(9, 17)]
    sym = _lr_symbol(fid, left, right)
    meta = _meta(fid, "QMC5883P 3-Axis Magnetometer", "sensor", "magnetometer",
                 "QST", "QMC5883P",
                 "QST QMC5883P 3-axis magnetic sensor - the chip on NEW GY-271 boards, "
                 "I2C address 0x2C, LGA-16 3x3x0.9mm. NOT register- or pinout-compatible "
                 "with QMC5883L (only 6 active pads: SCK/VDD/GND/C1/GND/SDA). C1 4.7uF "
                 "reservoir capacitor required.",
                 {"contacts": 16, "mounting": "SMD", "interface": "I2C",
                  "i2c_address": "0x2C", "supply_voltage": "2.5-3.6V",
                  "body_mm": "3.0x3.0x0.9"},
                 "https://www.qstcorp.com/upload/pdf/202202/%EF%BC%88%E5%B7%B2%E4%BC%A0%EF%BC%8913-52-19%20QMC5883P%20Datasheet%20Rev.C(1).pdf",
                 "QST QMC5883P datasheet Rev.C: p.6 LGA-16 3x3x0.9 (pitch 0.5, pad "
                 "0.325x0.25); Fig.7 recommended footprint pixel-measured (pads 0.40x0.25, "
                 "per-side span 1.5 c-c, rows 2.60 c-c, pad outer edges flush with body). "
                 "Table 5 pinout.",
                 ["qmc5883p", "qst", "magnetometer", "compass", "i2c", "gy-271", "lga"])
    return fid, lib, fp, sym, meta


def dht20():
    fid, lib = "dht20", "sensor/asair/dht20"
    out = _fp_open(fid, "ASAIR DHT20 temperature/humidity sensor in DHT-style 4-pin THT "
                        "housing (12.6x5.8 base, 16.1 tall). Pins in line, 2.54 pitch, "
                        "span 7.62. AHT20 die, I2C 0x38 (not DHT22 1-wire protocol!).",
                   "DHT20 temperature humidity I2C DHT housing", -4.6, 4.6,
                   attr="through_hole")
    out += _fab_body(-6.3, -2.55, 6.3, 3.25, 1.0)
    out += _rect_lines([(-6.41, -2.66, 6.41, -2.66), (6.41, -2.66, 6.41, 3.36),
                        (6.41, 3.36, -6.41, 3.36), (-6.41, 3.36, -6.41, -2.66)],
                       "F.SilkS", 0.12)
    out.append(_line(-4.5, -3.0, -3.1, -3.0, "F.SilkS", 0.12))
    out += _court(-6.55, -2.8, 6.55, 3.5)
    for i, n in enumerate(["VDD", "SDA", "GND", "SCL"]):
        out.append(_tht(str(i + 1), -3.81 + i * 2.54, 0, 1.6, 0.9,
                        "rect" if i == 0 else "circle"))
    out.append(')')
    fp = "\n".join(out) + "\n"
    sym = _lr_symbol(fid, [("1", "VDD"), ("2", "SDA"), ("3", "GND"), ("4", "SCL")], [])
    meta = _meta(fid, "DHT20 Temperature & Humidity Sensor (DHT Housing)", "sensor",
                 "humidity", "Aosong (ASAIR)", "DHT20",
                 "ASAIR DHT20 - the AHT20 die in a classic DHT-style 4-pin housing. "
                 "I2C interface (address 0x38), 2.2-5.5V. Drop-in mechanical replacement "
                 "for DHT11/DHT22 boards but NOT protocol-compatible (I2C, not 1-wire).",
                 {"contacts": 4, "mounting": "THT", "interface": "I2C",
                  "i2c_address": "0x38", "supply_voltage": "2.2-5.5V",
                  "body_mm": "12.6x5.8x16.1"},
                 "https://aqicn.org/air/sensor/spec/asair-dht20.pdf",
                 "ASAIR DHT20 datasheet V1.0 Fig.13: housing 12.6x16.1x5.8, 4 pins in "
                 "line pitch 2.54 (span 7.62), pin 0.5x0.3 length 7.2, pin row 2.55 from "
                 "front face. Table 5 pinout (1 VDD, 2 SDA, 3 GND, 4 SCL).",
                 ["dht20", "asair", "aht20", "humidity", "temperature", "i2c", "dht22"])
    return fid, lib, fp, sym, meta


def aht25():
    fid, lib = "aht25", "sensor/asair/aht25"
    out = _fp_open(fid, "ASAIR AHT25 humidity/temperature sensor - dumbbell PCB module "
                        "17.7mm long with 4 gold-finger solder tabs (pitch 1.27, exposed "
                        "3mm). Pads 0.8x3.4 SMD.",
                   "AHT25 humidity temperature sensor module I2C", -10.6, 10.6)
    out += _rect_lines([(-2.5, -8.85, 2.5, -8.85), (2.5, -8.85, 2.5, 0.15),
                        (2.5, 0.15, 3.0, 0.15), (3.0, 0.15, 3.0, 8.85),
                        (3.0, 8.85, -3.0, 8.85), (-3.0, 8.85, -3.0, 0.15),
                        (-3.0, 0.15, -2.5, 0.15), (-2.5, 0.15, -2.5, -8.85)], "F.Fab", 0.10)
    out += _rect_lines([(-3.11, -8.96, 3.11, -8.96), (-3.11, 4.5, -3.11, -8.96),
                        (3.11, 4.5, 3.11, -8.96)], "F.SilkS", 0.12)
    out.append(_line(-2.5, 9.3, -1.4, 9.3, "F.SilkS", 0.12))
    out += _court(-3.25, -9.1, 3.25, 9.1)
    for i, n in enumerate(["VDD", "SDA", "GND", "SCL"]):
        out.append(_smd(str(i + 1), -1.905 + i * 1.27, 7.15, 0.8, 3.4))
    out.append(')')
    fp = "\n".join(out) + "\n"
    sym = _lr_symbol(fid, [("1", "VDD"), ("2", "SDA"), ("3", "GND"), ("4", "SCL")], [])
    meta = _meta(fid, "AHT25 Humidity and Temperature Sensor Module", "sensor", "humidity",
                 "Aosong (ASAIR)", "AHT25",
                 "ASAIR AHT25 humidity/temperature sensor - a small dumbbell-shaped PCB "
                 "module with 4 gold-finger solder tabs (not a molded IC). I2C 0x38, "
                 "2.2-5.5V.",
                 {"contacts": 4, "mounting": "SMD", "interface": "I2C",
                  "i2c_address": "0x38", "supply_voltage": "2.2-5.5V",
                  "body_mm": "17.7x6x2"},
                 "https://www.aosong.com/userfiles/files/media/Data%20Sheet%20AHT25%20A2.pdf",
                 "ASAIR AHT25 datasheet V1.0 Fig.12: overall 17.7 long, head 5x9, tail "
                 "6 wide, 4 gold fingers pitch 1.27 exposed 3mm (0.4x0.4 section). "
                 "Pinout printed on Fig.12: 1 VDD, 2 SDA, 3 GND, 4 SCL.",
                 ["aht25", "asair", "humidity", "temperature", "i2c", "module"])
    return fid, lib, fp, sym, meta


def tp4054():
    return _part_sot23(
        "tp4054", "ic/power/tp4054", "TP4054 500mA Li-Ion Charger", "TopPower/UTD",
        "TP4054",
        "https://media.digikey.com/pdf/Data%20Sheets/UTD%20Semi%20PDFs/TP4054.pdf",
        "TP4054 datasheet p.11: SOT23-5L body 2.92x1.6, span 2.8, pitch 0.95. Land pads "
        "0.55x0.8 rows 2.4 c-c (same package class as Silergy recommendation). Pinout "
        "p.3: bottom 1 ~CHRG, 2 GND, 3 BAT; top 5 PROG, 4 VCC.",
        ["~CHRG", "GND", "BAT", "VCC", "PROG"],
        "TP4054 single-cell Li-ion linear charger, 4.2V CV, up to 500mA "
        "(Ichg=1000V/Rprog), VCC 4.25-6.5V, SOT23-5. The tiny-charger staple.",
        {"contacts": 5, "mounting": "SMD", "supply_voltage": "4.25-6.5V",
         "output_current": "up to 500mA", "body_mm": "2.9x1.6x1.15"},
        ["tp4054", "charger", "li-ion", "lipo", "battery", "sot23-5"])


def tm1638():
    fid, lib = "tm1638", "ic/driver/tm1638"
    pads = two_row_pads(28, 1.27, 9.2, 1.9, 0.7)
    fp = _fp_two_row(fid, "Titan Micro TM1638 LED driver with keyscan, SOP-28 (body "
                          "17.93x7.52, span 10.2, pitch 1.27). Pads 0.7x1.9 rows 9.2 c-c "
                          "per IPC-7351.", "TM1638 LED driver keyscan SOP-28",
                     pads, (3.76, 8.965))
    L = ["K1", "K2", "K3", "VDD", "SEG1/KS1", "SEG2/KS2", "SEG3/KS3", "SEG4/KS4",
         "SEG5/KS5", "SEG6/KS6", "SEG7/KS7", "SEG8/KS8", "SEG9", "SEG10"]
    R = ["VDD", "GRID8", "GRID7", "GND", "GRID6", "GRID5", "GRID4", "GRID3", "GRID2",
         "GRID1", "GND", "DIO", "CLK", "STB"]
    sym = _lr_symbol(fid, [(str(i + 1), L[i]) for i in range(14)],
                     [(str(i + 15), R[i]) for i in range(14)])
    meta = _meta(fid, "TM1638 LED Driver with Key Scan", "ic", "driver",
                 "Titan Micro", "TM1638",
                 "Titan Micro TM1638 LED display driver (10 segments x 8 grids) with "
                 "8x3 key scan, 3-wire serial (STB/CLK/DIO), 5V, SOP-28. The chip on "
                 "LED&KEY modules.",
                 {"contacts": 28, "mounting": "SMD", "supply_voltage": "5V",
                  "body_mm": "17.93x7.52x2.34"},
                 "https://www.handsontec.com/dataspecs/display/TM1638.pdf",
                 "Titan Micro TM1638 datasheet p.18: SOP28 body 17.93x7.52, overall span "
                 "9.9-10.5, pitch 1.27, lead 0.41. Pads 0.7x1.9 rows 9.2 c-c per "
                 "IPC-7351. Pinout p.1.",
                 ["tm1638", "led", "driver", "keyscan", "7-segment", "sop-28"])
    return fid, lib, fp, sym, meta


def ttp224():
    fid, lib = "ttp224", "ic/touch/ttp224"
    pads = two_row_pads(16, 0.635, 5.4, 1.5, 0.4)
    fp = _fp_two_row(fid, "Tontek TTP224N-BSB 4-key touch IC, SSOP-16 150mil MO-137(AB) "
                          "(body 4.9x3.91, span 5.99, pitch 0.635). Pads 0.4x1.5 rows "
                          "5.4 c-c per IPC-7351.", "TTP224 touch 4-key SSOP-16",
                     pads, (1.955, 2.45))
    nm = ["TP0", "TP1", "TP2", "TP3", "AHLB", "VDD", "TOG", "LPMB",
          "MOT0", "VSS", "OD", "SM", "TPQ3", "TPQ2", "TPQ1", "TPQ0"]
    sym = _lr_symbol(fid, [(str(i + 1), nm[i]) for i in range(8)],
                     [(str(i + 9), nm[i + 8]) for i in range(8)])
    meta = _meta(fid, "TTP224N-BSB 4-Key Touch IC", "ic", "touch", "Tontek",
                 "TTP224N-BSB",
                 "Tontek TTP224N 4-key capacitive touch detector with direct outputs "
                 "(TPQ0-3), option straps for output mode, 2.4-5.5V, SSOP-16.",
                 {"contacts": 16, "mounting": "SMD", "supply_voltage": "2.4-5.5V",
                  "body_mm": "4.9x3.91x1.63"},
                 "https://www.lcsc.com/product-detail/Touch-Screen-Controller-ICs_TTP224N-BSB_C90399.html",
                 "Tontek TTP224N-BSB datasheet Ver3.1 p.8: SSOP-16 MO-137(AB) body "
                 "4.9x3.91, span 5.99, pitch 0.635. Pads 0.4x1.5 rows 5.4 c-c per "
                 "IPC-7351. Pinout p.3 (CCW from pin-1 dot).",
                 ["ttp224", "tontek", "touch", "capacitive", "4-key", "ssop-16"])
    return fid, lib, fp, sym, meta


def ttp226():
    fid, lib = "ttp226", "ic/touch/ttp226"
    pads = two_row_pads(28, 0.635, 5.4, 1.5, 0.4)
    fp = _fp_two_row(fid, "Tontek TTP226-809SN 8-key touch IC, SSOP-28 150mil MO-137(AF) "
                          "- same package as TTP229. Pads 0.4x1.5 rows 5.4 c-c per "
                          "IPC-7351.", "TTP226 touch 8-key SSOP-28", pads, (1.955, 4.955))
    nm = ["OSC2/TOPAD", "I7", "I6", "I5", "I4", "I3", "I2", "I1", "I0", "OSC1", "VSS",
          "VDD", "OPS1", "OPS0", "AHL", "Q0", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7",
          "DV", "SLSE1", "SLSE2", "SLSE3", "SLSE4"]
    sym = _lr_symbol(fid, [(str(i + 1), nm[i]) for i in range(14)],
                     [(str(i + 15), nm[i + 14]) for i in range(14)])
    meta = _meta(fid, "TTP226-809SN 8-Key Touch IC", "ic", "touch", "Tontek",
                 "TTP226-809SN",
                 "Tontek TTP226 8-key capacitive touch detector with direct outputs "
                 "(Q0-7), 2.4-5.5V, SSOP-28.",
                 {"contacts": 28, "mounting": "SMD", "supply_voltage": "2.4-5.5V",
                  "body_mm": "9.91x3.91x1.63"},
                 "https://www.lcsc.com/product-detail/Touch-Screen-Controller-ICs_TTP226-809SN_C183531.html",
                 "Tontek TTP226-809SN datasheet Ver1.0 p.13: SSOP-28 MO-137(AF) - "
                 "dimension-identical to TTP229 package. Pads 0.4x1.5 rows 5.4 c-c per "
                 "IPC-7351. Pinout p.14.",
                 ["ttp226", "tontek", "touch", "capacitive", "8-key", "ssop-28"])
    return fid, lib, fp, sym, meta


def _disp_board(fid, title, mpn, iface, tags, bw, bh, holes, hole_d, header, fab_rects,
                desc, ds, dim_src, kw, chamfer=1.5, extra_headers=()):
    hx, hy = bw / 2, bh / 2
    out = _fp_open(fid, desc, tags, -(hy + 1.5), hy + 1.5, attr="through_hole")
    out += _fab_body(-hx, -hy, hx, hy, chamfer)
    for (x0, y0, x1, y1) in fab_rects:
        out += _rect_lines([(x0, y0, x1, y0), (x1, y0, x1, y1),
                            (x1, y1, x0, y1), (x0, y1, x0, y0)], "F.Fab", 0.10)
    out += _rect_lines([(-hx - 0.11, -hy - 0.11, hx + 0.11, -hy - 0.11),
                        (hx + 0.11, -hy - 0.11, hx + 0.11, hy + 0.11),
                        (hx + 0.11, hy + 0.11, -hx - 0.11, hy + 0.11),
                        (-hx - 0.11, hy + 0.11, -hx - 0.11, -hy - 0.11)], "F.SilkS", 0.12)
    n1, pins = header
    p1 = pins[0]
    out.append(_line(p1[1] - 0.6, p1[2] - 1.55, p1[1] + 0.6, p1[2] - 1.55, "F.SilkS", 0.12))
    out += _court(-hx - 0.25, -hy - 0.25, hx + 0.25, hy + 0.25)
    num = n1
    for name, x, y in pins:
        out.append(_tht(str(num), x, y, 1.7, 1.0, "rect" if num == n1 else "circle"))
        num += 1
    for (start, gpins) in extra_headers:
        num = start
        for name, x, y in gpins:
            out.append(_tht(str(num), x, y, 1.7, 1.0, "circle"))
            num += 1
    for x, y in holes:
        out.append(_npth(x, y, hole_d))
    out.append(')')
    fp = "\n".join(out) + "\n"
    left = [(str(n1 + i), pins[i][0]) for i in range(len(pins))]
    right = []
    for (start, gpins) in extra_headers:
        right += [(str(start + i), gpins[i][0]) for i in range(len(gpins))]
    sym = _lr_symbol(fid, left, right)
    contacts = len(pins) + sum(len(g) for _, g in extra_headers)
    meta = _meta(fid, title, "module", "display", "Generic (lcdwiki)", mpn, desc,
                 {"contacts": contacts, "mounting": "THT header", "interface": iface,
                  "board_mm": str(bw) + "x" + str(bh)},
                 ds, dim_src, kw)
    return fid, "module/display/" + fid, fp, sym, meta


def mc091gx():
    pins = [("GND", -17.5, -3.81), ("VCC", -17.5, -1.27), ("SCL", -17.5, 1.27),
            ("SDA", -17.5, 3.81)]
    return _disp_board(
        "mc091gx", '0.91" SSD1306 I2C OLED Module (128x32, MC091GX)', "MC091GX", "I2C",
        "SSD1306 OLED 0.91 128x32 module I2C", 38.0, 12.0, [], 2.0, (1, pins),
        [(-11.9, -2.79, 10.48, 2.79)],
        "Generic 0.91 inch 128x32 I2C OLED module (SSD1306, lcdwiki MC091GX), 4-pin "
        "header (GND VCC SCL SDA), 38x12mm board, no mounting holes. NOTE: different "
        "board from the official library ER_OLEDM0.91 bare glass.",
        "https://www.lcdwiki.com/res/MC091GX/0.91inch_IIC_OLED_Module_MC091GX_User_Manual_EN.pdf",
        "lcdwiki MC091GX drawing+manual: board 38x12, 4-pin 2.54 header on short edge "
        "(column 1.5 inset, end pins 2.19 from long edges), glass 30x11.5 (5.0 from "
        "header edge), AA 22.38x5.58 at 7.10.",
        ["ssd1306", "oled", "0.91", "128x32", "i2c", "module"])


def msp0961():
    pins = [(n, -8.89 + i * 2.54, -10.58) for i, n in
            enumerate(["GND", "VCC", "SCL", "SDA", "RES", "DC", "CS", "BLK"])]
    return _disp_board(
        "msp0961", '0.96" ST7735S IPS Module (80x160, SPI, MSP0961)', "MSP0961", "SPI",
        "ST7735 IPS 0.96 80x160 SPI module", 30.0, 24.04,
        [(-12.4, -9.4), (12.4, -9.4), (-12.4, 9.4), (12.4, 9.4)], 2.0,
        (1, pins), [(-11.3, -5.42, 10.4, 5.38)],
        "Generic 0.96 inch 80x160 IPS TFT module (ST7735S, lcdwiki MSP0961), SPI 8-pin "
        "header (GND VCC SCL SDA RES DC CS BLK), 30x24mm board, four 2.0mm holes.",
        "https://www.lcdwiki.com/0.96inch_IPS_Module",
        "lcdwiki MSP0961 drawing+manual: board 30x24.04, holes D2.0/pad3.5 at 2.6 "
        "insets (24.8x18.8), 8-pin 2.54 header row 1.44 from top (pin1 6.11 from left), "
        "AA 21.7x10.8 (3.7 from left, 6.6 from top).",
        ["st7735", "ips", "0.96", "80x160", "spi", "module"])


def msp1541():
    pins = [(n, -8.89 + i * 2.54, -20.36) for i, n in
            enumerate(["GND", "VCC", "SCL", "SDA", "RES", "DC", "CS", "BLK"])]
    return _disp_board(
        "msp1541", '1.54" ST7789 IPS Module (240x240, SPI, MSP1541)', "MSP1541", "SPI",
        "ST7789 IPS 1.54 240x240 SPI module", 32.0, 43.72,
        [(-13.86, -19.36), (13.86, -19.36), (-13.86, 19.36), (13.86, 19.36)], 2.0,
        (1, pins), [(-13.86, -15.41, 13.86, 12.31)],
        "Generic 1.54 inch 240x240 IPS TFT module (ST7789, lcdwiki MSP1541), SPI 8-pin "
        "header (GND VCC SCL SDA RES DC CS BLK), 32x43.7mm board, four 2.0mm holes.",
        "https://www.lcdwiki.com/1.54inch_IPS_Module",
        "lcdwiki MSP1541 drawing+manual: board 32x43.72, holes D2.0 (x +/-13.86, y "
        "+/-19.36), 8-pin 2.54 header row 1.5 from top (pin1 7.11 from left), glass "
        "31.52x35.1, AA 27.72 sq centered (top 6.45).",
        ["st7789", "ips", "1.54", "240x240", "spi", "module"])


def msp1803():
    j2 = [("VCC", 8.89, 26.5), ("GND", 6.35, 26.5), ("CS", 3.81, 26.5),
          ("RESET", 1.27, 26.5), ("AO", -1.27, 26.5), ("SDA", -3.81, 26.5),
          ("SCK", -6.35, 26.5), ("LED", -8.89, 26.5)]
    j4 = [("SD_CS", 3.81, -26.5), ("SD_MOSI", 1.27, -26.5),
          ("SD_MISO", -1.27, -26.5), ("SD_SCK", -3.81, -26.5)]
    return _disp_board(
        "msp1803", '1.8" ST7735 TFT Module (128x160, SPI, MSP1803)', "MSP1803", "SPI",
        "ST7735 TFT 1.8 128x160 SPI module SD", 34.5, 58.0,
        [(-14.25, -26.0), (14.25, -26.0), (-14.25, 26.0), (14.25, 26.0)], 3.2,
        (1, j2), [],
        "Generic 1.8 inch 128x160 TFT module (ST7735, lcdwiki MSP1803), SPI 8-pin main "
        "header + 4-pin SD header, 34.5x58mm board, four 3.2mm holes. Main header "
        "pin1=VCC is on the RIGHT in front view (vendor drawing is back-view).",
        "https://www.lcdwiki.com/1.8inch_SPI_Module_ST7735S_SKU:MSP1803",
        "lcdwiki MSP1803 back-view drawing (pixel-verified): board 34.5x58, holes D3.2 "
        "at 3.0 insets (28.5x52), J2 8-pin 2.54 bottom (row 2.5, centered, back-view "
        "L-R VCC GND CS RESET AO SDA SCK LED - mirrored for front), J4 SD 4-pin top "
        "centered. Glass dims not in drawing (footprint-complete).",
        ["st7735", "tft", "1.8", "128x160", "spi", "sd", "module"],
        extra_headers=[(9, j4)])


def msp2008():
    pins = [(n, -8.89 + i * 2.54, -29.06) for i, n in
            enumerate(["GND", "VCC", "SCL", "SDA", "RES", "DC", "CS", "BLK"])]
    return _disp_board(
        "msp2008", '2.0" ST7789V IPS Module (240x320, SPI, MSP2008)', "MSP2008", "SPI",
        "ST7789V IPS 2.0 240x320 SPI module", 36.48, 61.12,
        [(-15.74, -28.06), (15.74, -28.06), (-15.74, 28.4), (15.74, 28.4)], 2.0,
        (1, pins), [(-15.3, -23.1, 15.3, 17.7)],
        "Generic 2.0 inch 240x320 IPS TFT module (ST7789V, lcdwiki MSP2008-class), SPI "
        "8-pin header (GND VCC SCL SDA RES DC CS BLK), 36.5x61mm board, four 2.0mm holes.",
        "https://www.lcdwiki.com/2.0inch_IPS_Module",
        "lcdwiki 2.0inch IPS drawing (pixel-verified): board 36.48x61.12, holes D2.0 "
        "(top 2.5/2.5 insets; bottom 2.5 sides, 2.16 bottom), 8-pin 2.54 header row 1.5 "
        "(pin1 9.35 from left), glass 36x51.8, AA 30.6x40.8 (top 7.46).",
        ["st7789", "ips", "2.0", "240x320", "spi", "module"])


def mc01506():
    pins = [(n, -3.81 + i * 2.54, -21.0) for i, n in
            enumerate(["GND", "VCC", "SCL", "SDA"])]
    return _disp_board(
        "mc01506", '1.5" OLED Module (128x128, I2C, MC01506)', "MC01506", "I2C",
        "OLED 1.5 128x128 I2C module", 34.0, 47.0,
        [(-14.5, -21.0), (14.5, -21.0), (-14.5, 21.0), (14.5, 21.0)], 2.2,
        (1, pins), [(-13.43, -16.25, 13.43, 10.6)],
        "Generic 1.5 inch 128x128 OLED module (SH1107-class controller per lcdwiki; "
        "lcdwiki MC01506), I2C 4-pin header (GND VCC SCL SDA), 34x47mm board, four "
        "2.2mm holes.",
        "https://www.lcdwiki.com/1.5inch_OLED_Module_SKU:MC01506",
        "lcdwiki MC01506 size drawing: board 34x47 t1.2, holes D2.2 at 2.5 insets "
        "(29x42), 4-pin 2.54 header top centered (pin1 13.19 from left, row ~2.5), "
        "glass 33.9x37.3 (top 4.85), AA 26.855 sq (top 7.25).",
        ["sh1107", "oled", "1.5", "128x128", "i2c", "module"])


def msp2807():
    j2 = [(n, -16.51 + i * 2.54, 41.0) for i, n in enumerate(
        ["VCC", "GND", "CS", "RESET", "DC", "SDI(MOSI)", "SCK", "LED", "SDO(MISO)",
         "T_CLK", "T_CS", "T_DIN", "T_DO", "T_IRQ"])]
    j4 = [("SD_CS", -3.81, -40.0), ("SD_MOSI", -1.27, -40.0),
          ("SD_MISO", 1.27, -40.0), ("SD_SCK", 3.81, -40.0)]
    return _disp_board(
        "msp2807", '2.8" ILI9341 TFT Module (240x320, SPI+Touch+SD, MSP2807)', "MSP2807",
        "SPI", "ILI9341 TFT 2.8 240x320 SPI touch SD module", 50.0, 86.0,
        [(-22.0, -40.0), (22.0, -40.0), (-22.0, 36.08), (22.0, 36.08)], 3.2,
        (1, j2), [(-21.6, -33.7, 21.6, 23.9)],
        "Classic 2.8 inch 240x320 TFT module (ILI9341V + resistive touch + microSD, "
        "lcdwiki MSP2807), 14-pin SPI/touch header + 4-pin SD header, 50x86mm board, "
        "four 3.2mm holes.",
        "https://www.lcdwiki.com/2.8inch_SPI_Module_ILI9341_SKU:MSP2807",
        "lcdwiki MSP2807 factory outline V1.0 (2024-04-11): board 50x86 t1.6, holes "
        "D3.2/pad4.7 (top 3.0/3.0, pitch 44x76.08), J2 14-pin 2.54 bottom row 2.0 "
        "(pin1 8.49 from left), J4 SD 4-pin top centered, touch glass 50x69.2, AA "
        "43.2x57.6 (top 9.3). Official lib has only the 2.4-inch CR2013 sibling.",
        ["ili9341", "tft", "2.8", "240x320", "spi", "touch", "sd", "module"],
        extra_headers=[(15, j4)])


# ================= 배치 5차 칩 (§21-6ⓑ) =================

def wm8960():
    fid, lib = "wm8960", "ic/audio/wm8960"
    pads = quad_pads(8, 0.5, 4.7, 0.7, 0.28)
    fp = _fp_quad(fid, "Cirrus/Wolfson WM8960 stereo codec with class-D speaker driver, "
                       "QFN-32 5x5x0.9 (pitch 0.5, EP 3.45 = analogue ground). Land pads "
                       "0.28x0.7 centers 4.7 c-c per IPC-7351.",
                  "WM8960 audio codec I2S class-D", pads, 2.5, ep=("33", 3.45, 3.45))
    nm = ["MICBIAS", "LINPUT3/JD2", "LINPUT2", "LINPUT1", "RINPUT1", "RINPUT2",
          "RINPUT3/JD3", "DCVDD", "DGND", "DBVDD", "MCLK", "BCLK", "DACLRC", "DACDAT",
          "ADCLRC/GPIO1", "ADCDAT", "SCLK", "SDIN", "SPK_RN", "SPKGND2", "SPKVDD2",
          "SPK_RP", "SPK_LN", "SPKGND1", "SPK_LP", "SPKVDD1", "VMID", "AGND", "HP_R",
          "OUT3", "HP_L", "AVDD"]
    sym = _lr_symbol(fid, [(str(i + 1), nm[i]) for i in range(16)],
                     [(str(i + 17), nm[i + 16]) for i in range(16)],
                     bottom=[("33", "EP/AGND")])
    meta = _meta(fid, "WM8960 Stereo Audio Codec", "ic", "audio",
                 "Cirrus Logic (Wolfson)", "WM8960CGEFL/RV",
                 "Cirrus/Wolfson WM8960 stereo CODEC with 1W class-D speaker drivers and "
                 "headphone amp, I2S audio + 2-wire control (write-only, addr 0x1A), "
                 "QFN-32 5x5. Raspberry Pi / ESP32 audio HAT staple. EP = analogue GND.",
                 {"contacts": 33, "mounting": "SMD", "interface": "I2S + I2C(0x1A)",
                  "supply_voltage": "1.71-3.6V (SPKVDD to 5.5V)", "body_mm": "5.0x5.0x0.9"},
                 "https://wiki.geekworm.com/images/5/58/WM8960-Datasheet.pdf",
                 "Wolfson WM8960 datasheet (QFN-32 DM033.D / MO-220 VHHD-5): body 5x5x0.9, "
                 "pitch 0.5, lead 0.25x0.4, EP 3.45 sq. Land pads 0.28x0.7 centers 4.7 c-c "
                 "derived per IPC-7351 (EP clearance 0.275). Pinout p.6 (CCW from pin-1).",
                 ["wm8960", "wolfson", "cirrus", "codec", "audio", "i2s", "class-d", "qfn"])
    return fid, lib, fp, sym, meta


def _qfn20_3x3(fid, lib, name, manuf, mpn, ds, dim_src, nm, ep_name, desc, params, kw):
    """ES8311/CST816S 공용: QFN-20 3x3 P0.4 (ES8311 권장 랜드)."""
    pads = quad_pads(5, 0.4, 2.9, 0.7, 0.22)
    fp = _fp_quad(fid, f"{name}. QFN-20 3x3x0.55 (pitch 0.4). Land per ES8311 datasheet "
                       "p.14 pattern (same mechanical family): pads 0.22x0.7 centers 2.9 "
                       "c-c, center pad 1.8 sq, EP clearance 0.2.",
                  mpn, pads, 1.5, ep=("21", 1.8, 1.8))
    sym = _lr_symbol(fid, [(str(i + 1), nm[i]) for i in range(10)],
                     [(str(i + 11), nm[i + 10]) for i in range(10)],
                     bottom=[("21", ep_name)])
    meta = _meta(fid, name, "ic", lib.split("/")[1], manuf, mpn, desc, params, ds,
                 dim_src, kw)
    return fid, lib, fp, sym, meta


def es8311():
    return _qfn20_3x3(
        "es8311", "ic/audio/es8311", "ES8311 Mono Audio Codec", "Everest Semi", "ES8311",
        "http://www.everest-semi.com/pdf/ES8311%20PB.pdf",
        "Everest ES8311 datasheet Rev 17.0: QFN-20 3x3x0.55 pitch 0.4, EP 1.7; "
        "recommended land p.14 (pads 0.22x0.7 centers 2.9 c-c geometry-verified, center "
        "1.8 sq). Pinout p.3 (CCW).",
        ["CCLK", "MCLK", "PVDD", "DVDD", "DGND", "SCLK/DMIC_SCL", "ASDOUT", "LRCK",
         "DSDIN", "AGND", "AVDD", "OUTP", "OUTN", "DACVREF", "ADCVREF", "VMID", "MIC1N",
         "MIC1P/DMIC_SDA", "CDATA", "CE"],
        "EP/GND",
        "Everest ES8311 low-power mono audio codec - Espressif's reference codec "
        "(ESP32-S3-Box, Korvo, most ESP32 voice kits). I2S/PCM + I2C (0x18/0x19 via CE), "
        "1.6-3.6V, QFN-20 3x3.",
        {"contacts": 21, "mounting": "SMD", "interface": "I2S + I2C(0x18/0x19)",
         "supply_voltage": "1.6-3.6V", "body_mm": "3.0x3.0x0.55"},
        ["es8311", "everest", "codec", "audio", "i2s", "esp32", "qfn"])


def cst816s():
    return _qfn20_3x3(
        "cst816s", "ic/touch/cst816s", "CST816S Capacitive Touch Controller",
        "Hynitron", "CST816S",
        "https://www.waveshare.com/w/upload/5/51/CST816S_Datasheet_EN.pdf",
        "Hynitron CST816S datasheet V1.4: QFN-20 3x3x0.55 pitch 0.4, EP 1.7 (GND). "
        "No vendor land pattern - ES8311's recommended QFN-20 3x3 P0.4 pattern reused "
        "(dimensionally identical package). Pinout p.4 (CCW).",
        ["CMOD0", "S1L", "S2L", "S3L", "S4L", "S5L", "S6L", "S7R", "S8R", "S9R",
         "S10R", "S11R", "S12R", "S13R", "CMOD1/S14", "VDDA", "RST", "SCL", "SDA", "IRQ"],
        "EP/GND",
        "Hynitron CST816S self-capacitance touch controller - the touch chip paired "
        "with GC9A01 round LCDs in smartwatch projects. I2C 0x15, 2.7-3.6V, QFN-20 3x3. "
        "CMOD needs 1-5.6nF C0G cap.",
        {"contacts": 21, "mounting": "SMD", "interface": "I2C", "i2c_address": "0x15",
         "supply_voltage": "2.7-3.6V", "body_mm": "3.0x3.0x0.55"},
        ["cst816s", "hynitron", "touch", "capacitive", "smartwatch", "gc9a01", "qfn"])


def vs1053b():
    fid, lib = "vs1053b", "ic/audio/vs1053b"
    pads = quad_pads(12, 0.5, 8.5, 1.5, 0.3)
    fp = _fp_quad(fid, "VLSI VS1053B MP3/Ogg/AAC codec, LQFP-48 7x7 (overall 9.0 incl "
                       "leads, pitch 0.5). Land pads 0.3x1.5 centers 8.5 c-c per IPC-7351 "
                       "(foot centers 4.2, body clearance ok).",
                  "VS1053B MP3 codec LQFP-48", pads, 3.5)
    nm = ["MICP/LINE1", "MICN", "XRESET", "DGND0", "CVDD0", "IOVDD0", "CVDD1", "DREQ",
          "GPIO2/DCLK", "GPIO3/SDATA", "GPIO6/I2S_SCLK", "GPIO7/I2S_SDATA",
          "XDCS/BSYNC", "IOVDD1", "VCO", "DGND1", "XTALO", "XTALI", "IOVDD2", "DGND2",
          "DGND3", "DGND4", "XCS", "CVDD2",
          "GPIO5/I2S_MCLK", "RX", "TX", "SCLK", "SI", "SO", "CVDD3", "XTEST", "GPIO0",
          "GPIO1", "GND", "GPIO4/I2S_LROUT",
          "AGND0", "AVDD0", "RIGHT", "AGND1", "AGND2", "GBUF", "AVDD1", "RCAP", "AVDD2",
          "LEFT", "AGND3", "LINE2"]
    sym = _lr_symbol(fid, [(str(i + 1), nm[i]) for i in range(24)],
                     [(str(i + 25), nm[i + 24]) for i in range(24)])
    meta = _meta(fid, "VS1053B MP3/Ogg Audio Codec", "ic", "audio",
                 "VLSI Solution", "VS1053B-L",
                 "VLSI VS1053B MP3/Ogg Vorbis/AAC/WMA/MIDI audio codec with headphone "
                 "driver, SPI control/data, LQFP-48. The Adafruit Music Maker chip. "
                 "GBUF must never be grounded; CVDD 1.8V core.",
                 {"contacts": 48, "mounting": "SMD", "interface": "SPI",
                  "supply_voltage": "IOVDD 1.8-3.6V / AVDD 2.8V / CVDD 1.8V",
                  "body_mm": "7.0x7.0x1.5"},
                 "https://www.vlsi.fi/fileadmin/datasheets/vs1053.pdf",
                 "VLSI VS1053B datasheet v1.33 + official LQFP-48 outline DG4966 rev M "
                 "(body 7.0 sq, overall 9.0, pitch 0.5, foot 0.6). Land pads 0.3x1.5 "
                 "centers 8.5 c-c per IPC-7351. Pinout ch.6 (CCW).",
                 ["vs1053", "vlsi", "mp3", "ogg", "codec", "audio", "spi", "lqfp"])
    return fid, lib, fp, sym, meta


def icm42688():
    fid, lib = "icm42688", "sensor/tdk/icm42688"
    # LGA-14 2.5(x)x3.0(y): 좌열 4 (x-0.9125), 하행 3 (y+1.1625), 우열 4, 상행 3
    pads = []
    for i in range(4):
        pads.append((str(i + 1), -0.9125, -0.75 + i * 0.5, 0.6, 0.3))
    for i in range(3):
        pads.append((str(5 + i), -0.5 + i * 0.5, 1.1625, 0.3, 0.6))
    for i in range(4):
        pads.append((str(8 + i), 0.9125, 0.75 - i * 0.5, 0.6, 0.3))
    for i in range(3):
        pads.append((str(12 + i), 0.5 - i * 0.5, -1.1625, 0.3, 0.6))
    out = _fp_open(fid, "TDK InvenSense ICM-42688-P 6-axis IMU, LGA-14 2.5x3.0x0.91 "
                        "(pitch 0.5). Pads 1:1 with package terminals +0.1 toe "
                        "(0.3x0.6). The standard FPV flight-controller IMU.",
                   "ICM-42688-P IMU 6-axis gyro accel SPI", -2.6, 2.6)
    out += _fab_body(-1.25, -1.5, 1.25, 1.5, 0.6)
    out += _silk_box((1.51, 1.76), -1.0, -0.5, -1.85)
    out += _court(-1.5, -1.75, 1.5, 1.75)
    for name, x, y, w, h in pads:
        out.append(_smd(name, x, y, w, h))
    out.append(')')
    fp = "\n".join(out) + "\n"
    nm = ["AP_SDO/AD0", "RESV", "RESV", "INT1", "VDDIO", "GND", "RESV(GND!)",
          "VDD", "INT2/FSYNC/CLKIN", "RESV", "RESV", "AP_CS", "AP_SCL/SCLK",
          "AP_SDA/SDIO/SDI"]
    sym = _lr_symbol(fid, [(str(i + 1), nm[i]) for i in range(7)],
                     [(str(i + 8), nm[i + 7]) for i in range(7)])
    meta = _meta(fid, "ICM-42688-P 6-Axis IMU", "sensor", "motion",
                 "TDK InvenSense", "ICM-42688-P",
                 "TDK InvenSense ICM-42688-P 6-axis gyroscope+accelerometer - the "
                 "standard modern FPV flight-controller IMU (Betaflight/ArduPilot). "
                 "SPI 24MHz / I2C 0x68-0x69 / I3C, 1.71-3.6V, LGA-14 2.5x3. Pin 7 "
                 "RESV must connect to GND.",
                 {"contacts": 14, "mounting": "SMD", "interface": "SPI/I2C/I3C",
                  "i2c_address": "0x68/0x69", "supply_voltage": "1.71-3.6V",
                  "body_mm": "2.5x3.0x0.91"},
                 "https://www.cdiweb.com/datasheets/invensense/ds-000347-icm-42688-p-v1.2.pdf",
                 "TDK DS-000347 v1.2: LGA-14 2.5x3.0x0.91, terminals 0.25x0.475 pitch "
                 "0.5, 4-pin columns centers +/-0.9125, 3-pin rows +/-1.1625 "
                 "(cross-checked vs body/edge-gap arithmetic). Pads 1:1 +0.1 toe. "
                 "Pinout Table 9.",
                 ["icm-42688", "icm42688", "imu", "gyroscope", "accelerometer", "fpv",
                  "betaflight", "spi", "tdk"])
    return fid, lib, fp, sym, meta


def bno085():
    fid, lib = "bno085", "sensor/ceva/bno085"
    # 탑뷰(도면 직접 판독): 상단행 좌→우 = 1,28..20 / 좌열 2-5 / 하단행 6-15 / 우열 16-19
    pads = []
    top_nums = [1, 28, 27, 26, 25, 24, 23, 22, 21, 20]
    for i, n in enumerate(top_nums):
        pads.append((str(n), -2.25 + i * 0.5, -1.5625, 0.25, 0.675))
    for i in range(4):
        pads.append((str(2 + i), -2.3125, -0.75 + i * 0.5, 0.575, 0.25))
    for i in range(10):
        pads.append((str(6 + i), -2.25 + i * 0.5, 1.5625, 0.25, 0.675))
    for i in range(4):
        pads.append((str(16 + i), 2.3125, 0.75 - i * 0.5, 0.575, 0.25))
    out = _fp_open(fid, "CEVA/Hillcrest BNO085 9-DOF sensor-fusion IMU, LGA-28 "
                        "5.2x3.8x1.18. Land per datasheet Fig.7-2 (vector-verified, "
                        "spans are outer-edge): 20 pads 0.25x0.675 + 8 pads 0.575x0.25, "
                        "pitch 0.5.",
                   "BNO085 IMU 9-DOF fusion quaternion", -3.4, 3.4)
    out += _fab_body(-2.6, -1.9, 2.6, 1.9, 0.8)
    out += _rect_lines([(-2.71, -2.01, -2.71, 2.01), (2.71, -2.01, 2.71, 2.01)],
                       "F.SilkS", 0.12)
    out.append(_line(-2.5, -2.25, -2.0, -2.25, "F.SilkS", 0.12))  # pin1 틱
    out += _court(-2.85, -2.15, 2.85, 2.15)
    for name, x, y, w, h in pads:
        out.append(_smd(name, x, y, w, h))
    out.append(')')
    fp = "\n".join(out) + "\n"
    nm = {1: "RESV_NC", 2: "GND", 3: "VDD", 4: "BOOTN", 5: "PS1", 6: "PS0/WAKE",
          7: "RESV_NC", 8: "RESV_NC", 9: "CAP", 10: "CLKSEL0", 11: "NRST",
          12: "RESV_NC", 13: "RESV_NC", 14: "H_INTN", 15: "ENV_SCL", 16: "ENV_SDA",
          17: "SA0/H_MOSI", 18: "H_CSN", 19: "H_SCL/SCK/RX", 20: "H_SDA/H_MISO/TX",
          21: "RESV_NC", 22: "RESV_NC", 23: "RESV_NC", 24: "RESV_NC", 25: "GND",
          26: "XOUT32/CLKSEL1", 27: "XIN32", 28: "VDDIO"}
    sym = _lr_symbol(fid, [(str(i), nm[i]) for i in range(1, 15)],
                     [(str(i), nm[i]) for i in range(15, 29)])
    meta = _meta(fid, "BNO085 9-DOF Sensor Fusion IMU", "sensor", "motion",
                 "CEVA (Hillcrest Labs)", "BNO085",
                 "CEVA BNO085 9-DOF IMU with on-chip sensor fusion (quaternion output) - "
                 "Adafruit/SparkFun flagship IMU. Host interface selected by PS1/PS0: "
                 "I2C 0x4A/0x4B, SPI, or UART. VDD 2.4-3.6V, LGA-28 5.2x3.8. Needs "
                 "32.768kHz crystal or CLKSEL strap.",
                 {"contacts": 28, "mounting": "SMD", "interface": "I2C/SPI/UART",
                  "i2c_address": "0x4A/0x4B", "supply_voltage": "2.4-3.6V",
                  "body_mm": "5.2x3.8x1.18"},
                 "https://www.ceva-ip.com/wp-content/uploads/BNO080_085-Datasheet.pdf",
                 "CEVA BNO08X datasheet v1.17: Fig.7-1 LGA-28 5.2x3.8 (pads 0.25x0.475 "
                 "x20 + 0.375x0.25 x8, pitch 0.5, bottom-view CW numbering mirrored for "
                 "footprint - verified by direct drawing read); Fig.7-2 recommended land "
                 "(0.675x0.25 rows flush 3.8, 0.575x0.25 cols flush 5.2 - outer-edge "
                 "spans, vector-verified). Pinout Table 1-2.",
                 ["bno085", "bno080", "ceva", "hillcrest", "imu", "9-dof", "fusion",
                  "quaternion", "lga"])
    return fid, lib, fp, sym, meta


def tcs34725():
    fid, lib = "tcs34725", "sensor/ams/tcs34725"
    pads = two_row_pads(6, 0.65, 1.5, 1.0, 0.4)
    fp = _fp_two_row(fid, "ams-OSRAM (TAOS) TCS34725 RGBC color sensor, DFN-6 2.0x2.4 "
                          "(clear mold). Land per datasheet Fig.11: pads 1.0x0.4 pitch "
                          "0.65, columns 1.5 c-c (outer 2.5).",
                     "TCS34725 color sensor RGB I2C", pads, (1.0, 1.2))
    sym = _lr_symbol(fid, [("1", "VDD"), ("2", "SCL"), ("3", "GND")],
                     [("4", "NC"), ("5", "INT"), ("6", "SDA")])
    meta = _meta(fid, "TCS34725 RGBC Color Sensor", "sensor", "optical",
                 "ams-OSRAM (TAOS)", "TCS34725FN",
                 "TAOS/ams TCS34725 RGB+clear color sensor with IR blocking filter, "
                 "I2C 0x29, 2.7-3.6V, clear DFN-6 2.0x2.4. The Adafruit color sensor "
                 "(GY-33 boards). Pin 4 NC: do not connect.",
                 {"contacts": 6, "mounting": "SMD", "interface": "I2C",
                  "i2c_address": "0x29", "supply_voltage": "2.7-3.6V",
                  "body_mm": "2.0x2.4x0.65"},
                 "https://cdn-shop.adafruit.com/datasheets/TCS34725.pdf",
                 "TAOS TCS3472 datasheet (TAOS135): FN package 2.0x2.4x0.65, contacts "
                 "0.3 pitch 0.65; Fig.11 suggested layout (pads 1.0x0.4, pitch 0.65, "
                 "columns outer-to-outer 2.5 = centers 1.5 c-c). Pinout p.3.",
                 ["tcs34725", "taos", "ams", "color", "rgb", "sensor", "i2c", "gy-33"])
    return fid, lib, fp, sym, meta


# ---------- 배치 5차 모듈 (Waveshare 공식 도면/STEP + WeAct 공식 레포) ----------

def ssd1331_module_095():
    # 핀1=VCC 우측 (매뉴얼 넘버링), 행 y = 상단에서 ~2.4 (도면 픽셀실측 2.2-2.6)
    names = ["VCC", "GND", "NC", "DIN", "CLK", "CS", "D/C", "RES"]
    pins = [(names[i], 8.89 - i * 2.54, -16.1) for i in range(8)]
    return _disp_board(
        "ssd1331_module_095", '0.95" SSD1331 RGB OLED Module (96x64, SPI, Waveshare)',
        "Waveshare 0.95inch RGB OLED", "SPI",
        "SSD1331 RGB OLED 0.95 96x64 SPI module", 31.7, 37.0,
        [(-13.35, -16.0), (13.35, -16.0), (-13.35, 16.0), (13.35, 16.0)], 3.0,
        (1, pins), [(-10.07, -7.0, 10.07, 6.4)],
        "Waveshare 0.95 inch 96x64 RGB OLED module (SSD1331), SPI 8-pin header (pin 1 "
        "= VCC at the right per vendor numbering: VCC GND NC DIN CLK CS D/C RES), "
        "31.7x37mm board, four 3.0mm holes. (A)=bent pins, (B)=straight - same PCB.",
        "https://www.waveshare.com/wiki/0.95inch_RGB_OLED_(A)",
        "Waveshare official size drawing + user manual: board 31.7x37, holes D3.0 at "
        "2.5 insets (26.7x32.0 spans, arithmetic-verified), 1x8 2.54 header centered "
        "(span 17.78, row ~2.4 from top - pixel-measured), glass 25.7x22.2 (top 7.1), "
        "AA 20.14x13.42.",
        ["ssd1331", "rgb", "oled", "0.95", "96x64", "spi", "module", "waveshare"])


def ssd1351_module_15():
    # 좌측 에지 세로 컬럼 헤더 (STEP 좌표 검증), 핀1=VCC 상단
    names = ["VCC", "GND", "DIN", "CLK", "CS", "DC", "RST"]
    pins = [(names[i], -20.0, -7.62 + i * 2.54) for i in range(7)]
    return _disp_board(
        "ssd1351_module_15", '1.5" SSD1351 RGB OLED Module (128x128, SPI, Waveshare)',
        "Waveshare 1.5inch RGB OLED Module", "SPI",
        "SSD1351 RGB OLED 1.5 128x128 SPI module", 44.5, 37.0,
        [(-19.75, -16.0), (19.75, -16.0), (-19.75, 16.0), (19.75, 16.0)], 2.0,
        (1, pins), [(-14.05, -14.6, 12.75, 12.2)],
        "Waveshare 1.5 inch 128x128 RGB OLED module (SSD1351), SPI 7-pin vertical "
        "header on the left edge (VCC GND DIN CLK CS DC RST top to bottom), 44.5x37mm "
        "board, four 2.0mm holes. Second 1.25mm SMD wafer on back carries the same "
        "signals.",
        "https://www.waveshare.com/wiki/1.5inch_RGB_OLED_Module",
        "Waveshare official size drawing + 3D STEP (parsed): board 44.5x37 R1.5, holes "
        "D2.0 at 2.5 insets (39.5x32.0 STEP-exact), 1x7 2.54 header column 2.25 from "
        "left edge (pins y-centered, STEP-exact), glass 33.8x34.0, AA 26.855 sq.",
        ["ssd1351", "rgb", "oled", "1.5", "128x128", "spi", "module", "waveshare"])


def weact_epaper_213():
    # 2x4 듀얼로우 (1x8 아님!) — 홀수열이 에지쪽 (x -34.07), 행 위→아래 (1,2)(3,4)(5,6)(7,8)
    nm = ["BUSY", "RES", "D/C", "CS", "SCL", "SDA", "GND", "VCC"]
    pins = []
    for r in range(4):
        pins.append((nm[2 * r], -34.07, -3.81 + r * 2.54))
        pins.append((nm[2 * r + 1], -31.53, -3.81 + r * 2.54))
    return _disp_board(
        "weact_epaper_213", '2.13" WeAct E-Paper Module (SSD1680, 122x250, SPI)',
        "WeAct EpaperModule 2.13", "SPI",
        "SSD1680 epaper eink 2.13 122x250 SPI module WeAct", 72.0, 30.0,
        [(-33.2, -12.2), (33.2, -12.2), (-33.2, 12.2), (33.2, 12.2)], 3.2,
        (1, pins), [(-27.1, -11.85, 21.45, 11.85)],
        "WeAct Studio 2.13 inch black/white e-paper module (SSD1680 driver, 122x250, "
        "YRD0213 panel), SPI via a 2x4 (dual-row!) 2.54 header near the left edge "
        "(1 BUSY 2 RES 3 D/C 4 CS 5 SCL 6 SDA 7 GND 8 VCC, odd pins in the edge-side "
        "column), 72x30mm board, four 3.2mm holes. The official KiCad library has no "
        "e-paper content at all.",
        "https://github.com/WeActStudio/WeActStudio.EpaperModule",
        "WeAct official Board Shape PDF + Board 3D STEP (both parsed): board 72x30 "
        "R1.5, holes D3.2/pad5.6 at 2.8 insets (66.4x24.4 STEP-exact; PDF's 3.60 label "
        "is not the hole offset), 2x4 2.54 header (odd column 1.93 from edge, rows "
        "mid-height centered, drill 0.81), glass 59.2x29.2, AA 48.55x23.7.",
        ["ssd1680", "epaper", "e-ink", "eink", "2.13", "weact", "spi", "module"])


# ---------- 온디맨드 변형 패밀리 (§21-6ⓐ: 변형은 봇/요청이 만든다) ----------

VARIANT_FAMILIES = {
    "ht73xx": {"codes": sorted(HT73XX_CODES), "build": _ht73xx},
    "ht78xx": {"codes": sorted(HT78XX_CODES), "build": _ht78xx},
    "sy8008": {"codes": sorted(SY8008_GRADES), "build": _sy8008_grade},
    "max1704x": {"codes": sorted(MAX1704X_CODES), "build": _max1704x},
}


def write_part(t):
    fid, lib_path, footprint, symbol, meta = t
    d = os.path.normpath(os.path.join(LIB_ROOT, lib_path, fid))
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, f"{fid}.kicad_mod"), "w", encoding="utf-8").write(footprint)
    open(os.path.join(d, f"{fid}.kicad_sym"), "w", encoding="utf-8").write(symbol)
    json.dump(meta, open(os.path.join(d, "meta.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    return fid


def build_variant(family, code):
    fam = VARIANT_FAMILIES.get(family)
    if fam is None or code not in fam["codes"]:
        raise ValueError(f"unknown variant {family}:{code}")
    return write_part(fam["build"](code))


PARTS = [qmc5883l, hmc5883l, adxl345, ip5306, tp5100, cn3791, mp1584, sy8008, sy8089,
         ht7333, ht7833, ttp223, ttp229, w25q64jv, drv8825, a4988,
         ssd1306_module_096, sh1106_module_13, st7789_module_13,
         max6675, as5600, tm1637, inmp441, bh1750, xl6009, mlx90614, max17048, sgp40,
         veml7700, hc_sr04, dfplayer_mini, hc05, sim800l, max7219_matrix_module,
         gc9a01_module_128, ld2410c, esp32_devkitc_v4,
         qmc5883p, dht20, aht25, tp4054, tm1638, ttp224, ttp226,
         mc091gx, msp0961, msp1541, msp1803, msp2008, mc01506, msp2807,
         wm8960, es8311, cst816s, vs1053b, icm42688, bno085, tcs34725,
         ssd1331_module_095, ssd1351_module_15, weact_epaper_213]


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
