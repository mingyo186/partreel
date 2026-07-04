"""
배치 IC/모듈 3D (FreeCAD 헤드리스, §21-4). 실행: freecadcmd generators/gen_ics_3d.py
스타일: 다크 몸체(__extra) + 금색 리드/패드(__pins) (+모듈은 표시창 인레이 __housing).
완결 기준 = §14 3D done-bar (외형 정확 + 알아볼 수 있음 + 렌더 아티팩트 0).
"""
import os
import FreeCAD as App
import Part

LIB = (os.path.dirname(os.path.abspath(__file__)) + "/../library").replace("\\", "/")


def _export(d, fid, housing, pins, extra):
    solids = [s for s in (housing, pins, extra) if s is not None]
    Part.makeCompound(solids).exportStep("%s/%s.step" % (d, fid))
    if housing is not None:
        housing.exportStl("%s/%s__housing.stl" % (d, fid))
    pins.exportStl("%s/%s__pins.stl" % (d, fid))
    if extra is not None:
        extra.exportStl("%s/%s__extra.stl" % (d, fid))


def _fuse(parts):
    s = parts[0]
    for p in parts[1:]:
        s = s.fuse(p)
    return s


def _pin1_dot(body, x, y, ztop):
    try:
        return body.cut(Part.makeCylinder(0.22, 0.2, App.Vector(x, y, ztop - 0.08)))
    except Exception:
        return body


def gullwing(path, fid, bw, bl, bh, pad_xy, lead_w, lead_l, ep=None):
    """two-row 걸윙 IC: 몸체(bw=x폭, bl=y길이, 높이 bh, 스탠드오프 0.12) + 개별 리드발.
    pad_xy: (x,y) 리드 중심 목록(풋프린트 좌표). ep=(w,h)면 바닥 노출패드 추가."""
    d = "%s/%s" % (LIB, path)
    body = Part.makeBox(bw, bl, bh, App.Vector(-bw / 2, -bl / 2, 0.12))
    try:
        ve = [e for e in body.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 0.05]
        body = body.makeFillet(0.08, ve)
    except Exception:
        pass
    x1, y1 = pad_xy[0]
    body = _pin1_dot(body, x1 * 0.45, y1, 0.12 + bh)
    feet = []
    for x, y in pad_xy:
        sx = 1 if x > 0 else -1
        # 발: 몸체 밖 수평부 (몸체와 XY 비겹침 → 공면 회피)
        fx0 = bw / 2 + 0.02 if sx > 0 else -bw / 2 - 0.02 - lead_l
        feet.append(Part.makeBox(lead_l, lead_w, 0.12, App.Vector(fx0, y - lead_w / 2, 0)))
        # 라이저: 몸체 옆면에 붙는 수직부 (0.03 몸체 매립)
        rx0 = bw / 2 - 0.03 if sx > 0 else -bw / 2 - 0.12 + 0.03
        feet.append(Part.makeBox(0.12, lead_w, bh * 0.55, App.Vector(rx0, y - lead_w / 2, 0.06)))
    if ep:
        feet.append(Part.makeBox(ep[0], ep[1], 0.13, App.Vector(-ep[0] / 2, -ep[1] / 2, 0)))
    _export(d, fid, None, _fuse(feet), body)
    print(fid, "3D done")


def flatpack(path, fid, bx, by, bh, pads, ep=None):
    """LGA/QFN: 몸체(풀사이즈, z0.1~) + 바닥 금패드(풋프린트 좌표, -0.02~0.05 매립).
    pads: (x,y,w,h) 목록."""
    d = "%s/%s" % (LIB, path)
    body = Part.makeBox(bx * 2, by * 2, bh - 0.1, App.Vector(-bx, -by, 0.1))
    try:
        ve = [e for e in body.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 0.05]
        body = body.makeFillet(0.1, ve)
    except Exception:
        pass
    x1, y1, _, _ = pads[0]
    body = _pin1_dot(body, x1 * 0.6, y1 * 0.6, bh)
    gold = []
    for x, y, w, h in pads:
        gold.append(Part.makeBox(w, h, 0.14, App.Vector(x - w / 2, y - h / 2, -0.02)))
    if ep:
        gold.append(Part.makeBox(ep[0], ep[1], 0.14, App.Vector(-ep[0] / 2, -ep[1] / 2, -0.02)))
    _export(d, fid, None, _fuse(gold), body)
    print(fid, "3D done")


def sot89(path, fid):
    """SOT-89: 몸체 4.55x2.5x1.5 + 리드 3(y+) + 탭(y-). HT7333/7833 공용."""
    d = "%s/%s" % (LIB, path)
    body = Part.makeBox(4.55, 2.5, 1.4, App.Vector(-2.275, -1.25, 0.1))
    try:
        ve = [e for e in body.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 0.05]
        body = body.makeFillet(0.15, ve)
    except Exception:
        pass
    body = _pin1_dot(body, -1.5, 0.6, 1.5)
    gold = []
    for x, w in ((-1.5, 0.42), (0.0, 0.5), (1.5, 0.42)):
        gold.append(Part.makeBox(w, 1.0, 0.12, App.Vector(x - w / 2, 1.23, 0)))  # 리드 (0.02 몸체 하부 매립)
    gold.append(Part.makeBox(1.6, 0.7, 0.12, App.Vector(-0.8, -1.92, 0)))        # 탭
    _export(d, fid, None, _fuse(gold), body)
    print(fid, "3D done")


def display_module(path, fid, bw, bh, pins, pin1_x, pin_y, holes, hole_d, disp, glass_full):
    """디스플레이 모듈: 호스트보드 위 헤더로 서 있는 형태.
    z: 핀 0~8.5, 헤더 플라스틱 6.0~8.54, 모듈PCB 8.5~9.7, 글라스 9.7~11.2.
    disp=(x0,y0,x1,y1) 활성영역(인레이=white), glass_full=(x0,y0,x1,y1) 글라스(다크)."""
    d = "%s/%s" % (LIB, path)
    pcb = Part.makeBox(bw, bh, 1.2, App.Vector(-bw / 2, -bh / 2, 8.5))
    for hx, hy in holes:
        pcb = pcb.cut(Part.makeCylinder(hole_d / 2, 2.0, App.Vector(hx, hy, 8.1)))
    gx0, gy0, gx1, gy1 = glass_full
    glass = Part.makeBox(gx1 - gx0, gy1 - gy0, 1.5, App.Vector(gx0, gy0, 9.7))
    header = Part.makeBox(pins * 2.54, 2.54, 2.54, App.Vector(pin1_x - 1.27, pin_y - 1.27, 6.0))
    dark = _fuse([pcb, glass, header])
    dx0, dy0, dx1, dy1 = disp
    # 활성영역 인레이(white): 글라스 상면에 0.02 매립
    inlay = Part.makeBox(dx1 - dx0, dy1 - dy0, 0.1, App.Vector(dx0, dy0, 11.12))
    gold = []
    for i in range(pins):
        x = pin1_x + i * 2.54
        gold.append(Part.makeBox(0.64, 0.64, 8.5, App.Vector(x - 0.32, pin_y - 0.32, 0)))
    _export(d, fid, inlay, _fuse(gold), dark)
    print(fid, "3D done")


def two_row_xy(n, pitch, span):
    n2 = n // 2
    top = (n2 - 1) * pitch / 2.0
    xy = [(-span / 2, -top + i * pitch) for i in range(n2)]
    xy += [(span / 2, top - i * pitch) for i in range(n2)]
    return xy


def quad_xy(per_side, pitch, span, pw, ph):
    """flatpack용: 4변 패드 (x,y,w,h)."""
    k, top, out = per_side, (per_side - 1) * pitch / 2.0, []
    for i in range(k):
        out.append((-span / 2, -top + i * pitch, pw, ph))
    for i in range(k):
        out.append((-top + i * pitch, span / 2, ph, pw))
    for i in range(k):
        out.append((span / 2, top - i * pitch, pw, ph))
    for i in range(k):
        out.append((top - i * pitch, -span / 2, ph, pw))
    return out


# ---- 실행 ----

# 센서 (LGA/LCC: 바닥패드, 패키지 패드치수 사용)
flatpack("sensor/qst/qmc5883l/qmc5883l", "qmc5883l", 1.5, 1.5, 0.9,
         quad_xy(4, 0.5, 2.75, 0.325, 0.25))
flatpack("sensor/honeywell/hmc5883l/hmc5883l", "hmc5883l", 1.5, 1.5, 0.9,
         quad_xy(4, 0.5, 2.75, 0.325, 0.25))
adxl_pads = [(-1.01, -2.0 + i * 0.8, 0.813, 0.5) for i in range(6)]
adxl_pads += [(0, 1.75, 0.5, 0.813)]
adxl_pads += [(1.01, 2.0 - i * 0.8, 0.813, 0.5) for i in range(6)]
adxl_pads += [(0, -1.75, 0.5, 0.813)]
flatpack("sensor/adi/adxl345/adxl345", "adxl345", 1.5, 2.5, 0.95, adxl_pads)

# 전원/레귤레이터/메모리/터치 (걸윙)
gullwing("ic/power/ip5306/ip5306", "ip5306", 3.9, 4.9, 1.4,
         two_row_xy(8, 1.27, 4.95), 0.42, 1.05, ep=(2.09, 2.09))
gullwing("ic/power/cn3791/cn3791", "cn3791", 3.9, 4.9, 1.5,
         two_row_xy(10, 1.0, 4.95), 0.38, 1.05)
gullwing("ic/regulator/mp1584/mp1584", "mp1584", 3.9, 4.9, 1.5,
         two_row_xy(8, 1.27, 4.95), 0.42, 1.05, ep=(3.3, 2.41))
gullwing("ic/memory/w25q64jv/w25q64jv", "w25q64jv", 5.23, 5.23, 1.85,
         two_row_xy(8, 1.27, 6.55), 0.42, 1.3)
gullwing("ic/regulator/sy8008/sy8008", "sy8008", 1.6, 2.9, 1.0,
         [(-1.4, -0.95), (-1.4, 0), (-1.4, 0.95), (1.4, 0.95), (1.4, -0.95)], 0.4, 0.55)
gullwing("ic/regulator/sy8089/sy8089", "sy8089", 1.6, 2.9, 1.0,
         [(-1.4, -0.95), (-1.4, 0), (-1.4, 0.95), (1.4, 0.95), (1.4, -0.95)], 0.4, 0.55)
gullwing("ic/touch/ttp223/ttp223", "ttp223", 1.7, 2.9, 1.0,
         two_row_xy(6, 0.95, 2.35), 0.4, 0.55)
gullwing("ic/touch/ttp229/ttp229", "ttp229", 3.91, 9.91, 1.5,
         two_row_xy(28, 0.635, 4.95), 0.25, 1.0)
gullwing("ic/driver/drv8825/drv8825", "drv8825", 4.4, 9.7, 1.1,
         two_row_xy(28, 0.65, 5.3), 0.25, 0.85, ep=(3.1, 5.18))

# QFN (flatpack + EP)
flatpack("ic/power/tp5100/tp5100", "tp5100", 2.0, 2.0, 0.85,
         quad_xy(4, 0.65, 3.45, 0.55, 0.3), ep=(2.1, 2.1))
flatpack("ic/driver/a4988/a4988", "a4988", 2.5, 2.5, 0.9,
         quad_xy(7, 0.5, 4.45, 0.55, 0.25), ep=(3.15, 3.15))

# SOT-89 LDO
sot89("ic/regulator/ht7333/ht7333", "ht7333")
sot89("ic/regulator/ht7833/ht7833", "ht7833")

# ================= 배치 3차 =================

# 걸윙 칩
gullwing("ic/sensor_if/max6675/max6675", "max6675", 3.9, 4.9, 1.5,
         two_row_xy(8, 1.27, 4.95), 0.42, 1.05)
gullwing("ic/sensor_if/as5600/as5600", "as5600", 3.9, 4.9, 1.5,
         two_row_xy(8, 1.27, 4.95), 0.42, 1.05)
gullwing("ic/driver/tm1637/tm1637", "tm1637", 7.65, 12.7, 2.2,
         two_row_xy(20, 1.27, 8.6), 0.4, 1.4)
def bh1750_3d():
    """WSOF6I: 리드가 상/하(y) 짧은변 — 커스텀 (풋프린트 방향 일치)."""
    fid = "bh1750"
    d = "%s/ic/sensor_if/bh1750/%s" % (LIB, fid)
    body = Part.makeBox(1.6, 3.0, 0.6, App.Vector(-0.775, -1.5, 0.1))
    body = _pin1_dot(body, -0.4, 0.9, 0.7)
    feet = []
    for x in (-0.525, -0.025, 0.475):
        for sy in (1, -1):
            feet.append(Part.makeBox(0.22, 0.32, 0.12,
                                     App.Vector(x - 0.11, sy * 1.5 - (0.3 if sy > 0 else 0.02), 0)))
    _export(d, fid, None, _fuse(feet), body)
    print(fid, "3D done")


bh1750_3d()

# 플랫팩
flatpack("ic/audio/inmp441/inmp441", "inmp441", 1.88, 2.36, 0.98,
         [(1.33, y, 0.4, 0.6) for y in (1.575, 0.525, -0.525, -1.575)] +
         [(-1.33, y, 0.4, 0.6) for y in (-1.575, -0.525, 0.525, 1.575)] +
         [(0, -1.575, 1.0, 1.0)])
flatpack("ic/power/max17048/max17048", "max17048", 1.0, 1.0, 0.75,
         [(x, y, 0.3, 0.25) for x in (-0.99, 0.99) for y in (-0.75, -0.25, 0.25, 0.75)],
         ep=(0.8, 1.2))
flatpack("sensor/sensirion/sgp40/sgp40", "sgp40", 1.22, 1.22, 0.85,
         [(x, y, 0.35, 0.4) for x in (-1.05, 1.05) for y in (-0.8, 0, 0.8)],
         ep=(1.25, 1.64))


def xl6009_3d():
    fid = "xl6009"
    d = "%s/ic/regulator/xl6009/%s" % (LIB, fid)
    # TO-263-5: 몸체 + 탭(y-) + 리드 5(y+)
    body = Part.makeBox(10.16, 8.64, 4.4, App.Vector(-5.08, -4.32, 0.15))
    try:
        ve = [e for e in body.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 0.05]
        body = body.makeFillet(0.2, ve)
    except Exception:
        pass
    gold = [Part.makeBox(9.6, 1.3, 1.27, App.Vector(-4.8, -5.59, 0))]  # 탭
    for i in range(5):
        x = -3.4 + i * 1.7
        gold.append(Part.makeBox(0.84, 4.4, 0.5, App.Vector(x - 0.42, 4.34, 0)))
    _export(d, fid, None, _fuse(gold), body)
    print(fid, "3D done")


def mlx90614_3d():
    fid = "mlx90614"
    d = "%s/sensor/melexis/mlx90614/%s" % (LIB, fid)
    can = Part.makeCylinder(4.56, 0.9, App.Vector(0, 0, 0.05))       # 플랜지
    can = can.fuse(Part.makeCylinder(4.1, 4.05, App.Vector(0, 0, 0.05)))  # 캡
    win = Part.makeCylinder(2.8, 0.3, App.Vector(0, 0, 3.95))
    can = can.cut(win)
    r = 5.08 / 2 * 0.7071068
    pins = [Part.makeCylinder(0.225, 3.0, App.Vector(x, y, -2.95))
            for x in (-r, r) for y in (-r, r)]
    dark = Part.makeCylinder(2.7, 0.12, App.Vector(0, 0, 3.9))  # 윈도우(다크)
    Part.makeCompound([can, _fuse(pins), dark]).exportStep("%s/%s.step" % (d, fid))
    can.exportStl("%s/%s__housing.stl" % (d, fid))
    _fuse(pins).exportStl("%s/%s__pins.stl" % (d, fid))
    dark.exportStl("%s/%s__extra.stl" % (d, fid))
    print(fid, "3D done")


def veml7700_3d():
    fid = "veml7700"
    d = "%s/sensor/vishay/veml7700/%s" % (LIB, fid)
    body = Part.makeBox(6.6, 2.35, 2.9, App.Vector(-3.3, -1.175, 0.1))
    feet = [Part.makeBox(0.5, 1.0, 0.12, App.Vector(-1.905 + i * 1.27 - 0.25, 0.3, 0))
            for i in range(4)]
    _export(d, fid, body, _fuse(feet), None)  # 투명 패키지 → 밝은 색
    print(fid, "3D done")


def _pcb_module(path, fid, parts_housing, parts_gold, parts_dark):
    d = "%s/%s" % (LIB, path)
    h = _fuse(parts_housing) if parts_housing else None
    _export(d, fid, h, _fuse(parts_gold), _fuse(parts_dark))
    print(fid, "3D done")


def hc_sr04_3d():
    pcb = Part.makeBox(45, 20, 1.6, App.Vector(-22.5, -10, 0))
    cans = []
    for cx in (-13.5, 13.5):
        c = Part.makeCylinder(8.0, 12, App.Vector(cx, 0, 1.6))
        c = c.cut(Part.makeCylinder(6.5, 1.5, App.Vector(cx, 0, 12.6)))
        cans.append(c)
    xtal = Part.makeBox(10, 4, 3.5, App.Vector(-5, 5.2, 1.6))
    pins = [Part.makeBox(0.64, 0.64, 6, App.Vector(-3.81 + i * 2.54 - 0.32, 7.68, -4.0))
            for i in range(4)]
    hdr = Part.makeBox(10.16, 2.54, 2.54, App.Vector(-5.08, 6.73, -2.54))
    _pcb_module("module/sensor/hc_sr04/hc_sr04", "hc_sr04",
                cans + [xtal], pins, [pcb, hdr])


def dfplayer_3d():
    pcb = Part.makeBox(20.32, 20.32, 1.2, App.Vector(-10.16, -10.16, 0))
    sd = Part.makeBox(14.9, 15.2, 2.0, App.Vector(-7.45, -5.06, 1.2))
    pins = []
    for i in range(8):
        pins.append(Part.makeBox(0.64, 0.64, 4.7, App.Vector(-9.335, -8.89 + i * 2.54 - 0.32, -3.0)))
        pins.append(Part.makeBox(0.64, 0.64, 4.7, App.Vector(8.695, -8.89 + i * 2.54 - 0.32, -3.0)))
    _pcb_module("module/audio/dfplayer_mini/dfplayer_mini", "dfplayer_mini",
                [sd], pins, [pcb])


def hc05_3d():
    pcb = Part.makeBox(37, 16, 1.6, App.Vector(-18.5, -8, 0))
    daughter = Part.makeBox(27, 13, 1.2, App.Vector(-10.5, -6.5, 3.0))
    standoff = Part.makeBox(20, 10, 1.4, App.Vector(-6, -5, 1.6))
    btn = Part.makeBox(3, 2, 1.5, App.Vector(-14, 4.5, 1.6))
    pins = [Part.makeBox(0.64, 0.64, 8, App.Vector(-16.82, -6.35 + i * 2.54 - 0.32, -1.5))
            for i in range(6)]
    _pcb_module("module/rf/hc05/hc05", "hc05",
                [btn], pins, [pcb, daughter, standoff])


def sim800l_3d():
    pcb = Part.makeBox(24.9, 22.7, 1.2, App.Vector(-12.45, -11.35, 0))
    can = Part.makeBox(17.8, 15.8, 2.4, App.Vector(-8.9, -7.4, 1.2))
    ufl = Part.makeCylinder(1.5, 1.6, App.Vector(-9.3, -9.3, 1.2))
    pins = []
    for i in range(6):
        pins.append(Part.makeBox(0.64, 0.64, 4.7, App.Vector(-10.32, -5.65 + i * 2.54 - 0.32, -3.0)))
        pins.append(Part.makeBox(0.64, 0.64, 4.7, App.Vector(9.68, -5.65 + i * 2.54 - 0.32, -3.0)))
    _pcb_module("module/rf/sim800l/sim800l", "sim800l",
                [can, ufl], pins, [pcb])


def max7219_module_3d():
    pcb = Part.makeBox(32, 32, 1.2, App.Vector(-16, -16, 0))
    matrix = Part.makeBox(32, 32, 6.5, App.Vector(-16, -16, 3.0))
    try:
        ve = [e for e in matrix.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 0.05]
        matrix = matrix.makeFillet(0.5, ve)
    except Exception:
        pass
    pins = []
    for i in range(5):
        pins.append(Part.makeBox(0.64, 0.64, 6, App.Vector(-15.05, -5.08 + i * 2.54 - 0.32, -3.0)))
        pins.append(Part.makeBox(0.64, 0.64, 6, App.Vector(14.41, -5.08 + i * 2.54 - 0.32, -3.0)))
    _pcb_module("module/display/max7219_matrix_module/max7219_matrix_module",
                "max7219_matrix_module", [], pins, [pcb, matrix])


def gc9a01_3d():
    cy = -3.9
    pcb = Part.makeCylinder(19.0, 1.6, App.Vector(0, cy, 0))
    tab = Part.makeBox(23, 12, 1.6, App.Vector(-11.5, 10.9, 0))
    glass = Part.makeCylinder(17.8, 1.8, App.Vector(0, cy, 1.6))
    aa = Part.makeCylinder(16.2, 0.1, App.Vector(0, cy, 3.32))  # 활성영역(white)
    pins = [Part.makeBox(0.64, 0.64, 4.2, App.Vector(-8.89 + i * 2.54 - 0.32, 21.11, -3.0))
            for i in range(8)]
    _pcb_module("module/display/gc9a01_module_128/gc9a01_module_128",
                "gc9a01_module_128", [aa], pins, [pcb, tab, glass])


def ld2410c_3d():
    pcb = Part.makeBox(22, 16, 1.0, App.Vector(-11, -8, 0))
    ic = Part.makeBox(5, 5, 0.9, App.Vector(-2.5, 2.0, 1.0))
    patches = [Part.makeBox(5.5, 5.5, 0.06, App.Vector(x - 2.75, -6.5, 1.0))
               for x in (-5.5, 5.5)]
    pins = [Part.makeBox(0.5, 0.5, 4.2, App.Vector(-5.08 + i * 2.54 - 0.25, -5.71, -3.0))
            for i in range(5)]
    _pcb_module("module/sensor/ld2410c/ld2410c", "ld2410c",
                [], pins + patches, [pcb, ic])


def devkitc_3d():
    pcb = Part.makeBox(27.94, 48.26, 1.6, App.Vector(-13.97, -24.13, 0))
    wroom_pcb = Part.makeBox(18, 25.5, 0.8, App.Vector(-9, -30.17, 1.6))
    shield = Part.makeBox(17.4, 18.2, 2.3, App.Vector(-8.7, -22.5, 2.4))
    usb = Part.makeBox(8, 5.6, 2.8, App.Vector(-4, 19.5, 1.6))
    btns = [Part.makeBox(3.5, 3.5, 1.8, App.Vector(x - 1.75, 20.0, 1.6))
            for x in (-10.5, 10.5)]
    pins = []
    for i in range(19):
        pins.append(Part.makeBox(0.64, 0.64, 8.5, App.Vector(-13.02, -22.86 + i * 2.54 - 0.32, -6.4)))
        pins.append(Part.makeBox(0.64, 0.64, 8.5, App.Vector(12.38, -22.86 + i * 2.54 - 0.32, -6.4)))
    _pcb_module("module/devboard/esp32_devkitc_v4/esp32_devkitc_v4",
                "esp32_devkitc_v4", [shield, usb], pins, [pcb, wroom_pcb] + btns)


xl6009_3d()
mlx90614_3d()
veml7700_3d()
hc_sr04_3d()
dfplayer_3d()
hc05_3d()
sim800l_3d()
max7219_module_3d()
gc9a01_3d()
ld2410c_3d()
devkitc_3d()

# 디스플레이 모듈
display_module("module/display/ssd1306_module_096/ssd1306_module_096", "ssd1306_module_096",
               27.3, 27.8, 4, -3.81, -12.4,
               [(-11.65, -11.9), (11.65, -11.9), (-11.65, 11.9), (11.65, 11.9)], 2.0,
               (-10.87, -7.53, 10.87, 3.33), (-13.35, -9.63, 13.35, 9.63))
display_module("module/display/sh1106_module_13/sh1106_module_13", "sh1106_module_13",
               35.4, 33.5, 4, -6.3, -14.75,
               [(-15.2, -14.75), (15.2, -14.75), (-15.2, 13.75), (15.2, 13.75)], 3.0,
               (-14.71, -7.15, 14.71, 7.55), (-16.0, -9.5, 16.0, 9.9))
display_module("module/display/st7789_module_13/st7789_module_13", "st7789_module_13",
               27.78, 39.22, 7, -7.62, -17.11,
               [(-11.39, -17.11), (11.39, -17.11), (-11.39, 17.11), (11.39, 17.11)], 2.0,
               (-11.7, -13.28, 11.7, 10.12), (-13.0, -14.61, 13.0, 14.61))
