"""
일회성 부품 3D (FreeCAD 헤드리스). 실행: freecadcmd generators/gen_parts_3d.py
대표(representative) 형상. STEP + housing/pins STL (stl_to_glb가 GLB로).
"""
import os
import FreeCAD as App
import Part

LIB = (os.path.dirname(os.path.abspath(__file__)) + "/../library").replace("\\", "/")


def usb_c_16p():
    fid = "usb_c_16p"
    d = "%s/connector/usb/usb_c_16p/%s" % (LIB, fid)
    # 금속 셸: 풋프린트 fab 범위(8.94 x 7.3) x 높이 3.16 — 스타디움 단면(양옆 라운드)
    shell = Part.makeBox(8.94, 7.3, 3.16, App.Vector(-4.47, -3.65, 0))
    try:
        yedges = [e for e in shell.Edges
                  if abs(e.Vertexes[0].Y - e.Vertexes[1].Y) > 0.1]
        shell = shell.makeFillet(1.45, yedges)  # 좌우 끝 라운드 (실물 셸 단면)
    except Exception:
        pass
    # 전면(+Y) 삽입구: 라운드 입구
    cav = Part.makeBox(7.4, 4.5, 2.3, App.Vector(-3.7, -0.6, 0.43))
    try:
        cedges = [e for e in cav.Edges
                  if abs(e.Vertexes[0].Y - e.Vertexes[1].Y) > 0.1]
        cav = cav.makeFillet(1.0, cedges)
    except Exception:
        pass
    shell = shell.cut(cav)
    # 혓바닥(tongue): 삽입구 안 중앙 플레이트 — 실물 내부 구조
    tongue = Part.makeBox(6.4, 6.3, 0.7, App.Vector(-3.2, -3.4, 1.23))  # 입구 0.75mm 안까지 (실물 리세스)
    try:
        tedges = [e for e in tongue.Edges
                  if abs(e.Vertexes[0].Y - e.Vertexes[1].Y) > 0.1]
        tongue = tongue.makeFillet(0.3, tedges)
    except Exception:
        pass
    # SMD 리드: 실제 패드 X좌표대로 16개 개별 발 (통짜 스트립 아님)
    smd_x = [(-0.25, 0.3), (1.75, 0.3), (1.25, 0.3), (0.75, 0.3), (0.25, 0.3),
             (-0.75, 0.3), (-1.25, 0.3), (-1.75, 0.3), (3.25, 0.6), (2.45, 0.6),
             (-2.45, 0.6), (-3.25, 0.6)]
    feet = []
    for x, w in smd_x:
        # y -4.5..-3.7: 셸(y>=-3.65)과 XY 비겹침 → 공면 z-fight 방지 (check_zfight)
        feet.append(Part.makeBox(w * 0.8, 0.8, 0.15, App.Vector(x - w * 0.4, -4.5, 0)))
    contacts = feet[0]
    for f in feet[1:]:
        contacts = contacts.fuse(f)
    Part.makeCompound([shell, contacts, tongue]).exportStep("%s/%s.step" % (d, fid))
    shell.exportStl("%s/%s__housing.stl" % (d, fid))
    contacts.exportStl("%s/%s__pins.stl" % (d, fid))
    tongue.exportStl("%s/%s__extra.stl" % (d, fid))
    print("USB-C 3D done")


def microsd_hc():
    fid = "microsd_hc"
    d = "%s/connector/card/microsd_hc/%s" % (LIB, fid)
    # 바디 z0=0.05 standoff — 접점 밑면과 공면 z-fight 방지 (check_zfight)
    body = Part.makeBox(13.8, 15.9, 1.35, App.Vector(-6.9, -7.8, 0.05))
    slot = Part.makeBox(12.0, 1.2, 1.0, App.Vector(-6.0, -8.0, 0.35))  # 카드 입구 (접점 윗면 0.3과 공면 회피)
    body = body.cut(slot)
    # 접점: 통짜 스트립이 아니라 풋프린트 X좌표 그대로 9개 개별 핑거
    xs = [2.775, 1.675, 0.575, -0.525, -1.625, -2.725, -3.825, -4.925, -5.875]
    fingers = [Part.makeBox(0.6, 1.2, 0.3, App.Vector(x - 0.3, -8.3, 0)) for x in xs]
    contacts = fingers[0]
    for f in fingers[1:]:
        contacts = contacts.fuse(f)
    Part.makeCompound([body, contacts]).exportStep("%s/%s.step" % (d, fid))
    body.exportStl("%s/%s__housing.stl" % (d, fid))
    contacts.exportStl("%s/%s__pins.stl" % (d, fid))
    print("microSD 3D done")


def esp32_wroom32():
    fid = "esp32_wroom32"
    d = "%s/module/espressif/esp32_wroom32/%s" % (LIB, fid)
    # 3부위: PCB(다크) + 금속 쉴드캔(안테나 영역 비움) + 가장자리 캐스텔레이티드 패드(금)
    # 치수 = 풋프린트 fab (18 x 25.505), 총높이 3.1 (Espressif 데이터시트)
    pcb = Part.makeBox(18, 25.505, 0.8, App.Vector(-9, -15.745, 0))
    # 쉴드캔: 부품 영역만 (y -9.4..8.8 — 안테나 구간 y<-9.5는 PCB 노출)
    shield = Part.makeBox(17.4, 18.2, 2.3, App.Vector(-8.7, -9.4, 0.8))
    try:
        vedges = [e for e in shield.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 0.1]
        shield = shield.makeFillet(0.4, vedges)
    except Exception:
        pass
    # 캐스텔레이티드 패드: 풋프린트 패드 좌표 그대로 (좌 14 / 우 14 / 하 10)
    # 패드는 PCB 상·하면을 0.02씩 감싸게 (공면 z-fight 방지 + 실물 캐스텔레이션 랩)
    pads = []
    for i in range(14):
        y = -8.255 + i * 1.27
        pads.append(Part.makeBox(0.7, 0.9, 0.84, App.Vector(-9.05, y - 0.45, -0.02)))
        pads.append(Part.makeBox(0.7, 0.9, 0.84, App.Vector(8.35, y - 0.45, -0.02)))
    for i in range(10):
        x = -5.715 + i * 1.27
        pads.append(Part.makeBox(0.9, 0.7, 0.84, App.Vector(x - 0.45, 9.105, -0.02)))
    gold = pads[0]
    for p in pads[1:]:
        gold = gold.fuse(p)
    Part.makeCompound([shield, gold, pcb]).exportStep("%s/%s.step" % (d, fid))
    shield.exportStl("%s/%s__housing.stl" % (d, fid))
    gold.exportStl("%s/%s__pins.stl" % (d, fid))
    pcb.exportStl("%s/%s__extra.stl" % (d, fid))
    print("ESP32 3D done")


def aht20():
    fid = "aht20"
    d = "%s/sensor/asair/aht20/%s" % (LIB, fid)
    # ASAIR AHT20 데이터시트 Fig.1: 본체 3x3x1.0, 금속 리드 2.8, 상면 타원 벤트홀 1.1x0.7
    # 기판(다크): 3x3, z 0..0.25
    substrate = Part.makeBox(3.0, 3.0, 0.25, App.Vector(-1.5, -1.5, 0))
    # 금속 리드(하우징): 2.8x2.8, z 0.25..1.0, 수직 모서리 라운드
    lid = Part.makeBox(2.8, 2.8, 0.75, App.Vector(-1.4, -1.4, 0.25))
    try:
        vedges = [e for e in lid.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 0.1]
        lid = lid.makeFillet(0.25, vedges)
    except Exception:
        pass
    # 벤트홀: 스타디움 포켓 1.1x0.7 깊이 0.2, 상단(핀1쪽) 에지 근처
    vent = Part.makeBox(1.1, 0.7, 0.4, App.Vector(-0.55, -1.1, 0.8))
    try:
        vv = [e for e in vent.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 0.1]
        vent = vent.makeFillet(0.3, vv)
    except Exception:
        pass
    lid = lid.cut(vent)
    # I/O 패드(금): 본체 패드 0.55x0.4 6개, 풋프린트 좌표 그대로.
    # 기판에 0.05 매립 + 바닥 -0.02 (공면 z-fight 방지, ESP32 패턴)
    pads = []
    for x, y in [(-1.0, -1.0), (-1.0, 0.0), (-1.0, 1.0), (1.0, 1.0), (1.0, 0.0), (1.0, -1.0)]:
        pads.append(Part.makeBox(0.55, 0.4, 0.07, App.Vector(x - 0.275, y - 0.2, -0.02)))
    gold = pads[0]
    for p in pads[1:]:
        gold = gold.fuse(p)
    Part.makeCompound([lid, gold, substrate]).exportStep("%s/%s.step" % (d, fid))
    lid.exportStl("%s/%s__housing.stl" % (d, fid))
    gold.exportStl("%s/%s__pins.stl" % (d, fid))
    substrate.exportStl("%s/%s__extra.stl" % (d, fid))
    print("AHT20 3D done")


def aht21():
    fid = "aht21"
    d = "%s/sensor/asair/aht21/%s" % (LIB, fid)
    # AHT21 데이터시트 Fig.1: 단일 다크 바디 3x3x0.8, 상면 1.0mm 사각(라운드) 센서창
    body = Part.makeBox(3.0, 3.0, 0.8, App.Vector(-1.5, -1.5, 0))
    try:
        vedges = [e for e in body.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 0.1]
        body = body.makeFillet(0.15, vedges)
    except Exception:
        pass
    # 센서창 포켓 1.0x1.0 깊이 0.15, 핀1쪽(상단) 치우침 (Fig.1: 0.95 오프셋)
    win = Part.makeBox(1.0, 1.0, 0.3, App.Vector(-0.5, -1.15, 0.65))
    try:
        wv = [e for e in win.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 0.1]
        win = win.makeFillet(0.25, wv)
    except Exception:
        pass
    body = body.cut(win)
    # 센서창 인서트(밝은 면): 포켓보다 0.02 작게 + 바닥 0.02 매립 (공면 회피)
    inlay = Part.makeBox(0.96, 0.96, 0.1, App.Vector(-0.48, -1.13, 0.63))
    try:
        iv = [e for e in inlay.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 0.05]
        inlay = inlay.makeFillet(0.22, iv)
    except Exception:
        pass
    pads = []
    for x, y in [(-1.0, -1.0), (-1.0, 0.0), (-1.0, 1.0), (1.0, 1.0), (1.0, 0.0), (1.0, -1.0)]:
        pads.append(Part.makeBox(0.55, 0.4, 0.07, App.Vector(x - 0.275, y - 0.2, -0.02)))
    gold = pads[0]
    for p in pads[1:]:
        gold = gold.fuse(p)
    Part.makeCompound([inlay, gold, body]).exportStep("%s/%s.step" % (d, fid))
    inlay.exportStl("%s/%s__housing.stl" % (d, fid))
    gold.exportStl("%s/%s__pins.stl" % (d, fid))
    body.exportStl("%s/%s__extra.stl" % (d, fid))
    print("AHT21 3D done")


def aht10():
    fid = "aht10"
    d = "%s/sensor/asair/aht10/%s" % (LIB, fid)
    # AHT10 매뉴얼 Fig.1: 다크 베이스 4x5 + 흰색 라운드 바디, 총높이 1.6, 상면 원형 홀(핀1쪽)
    base = Part.makeBox(4.0, 5.0, 0.3, App.Vector(-2.0, -2.27, 0))
    body = Part.makeBox(3.7, 4.7, 1.3, App.Vector(-1.85, -2.12, 0.3))
    try:
        vedges = [e for e in body.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 0.1]
        body = body.makeFillet(0.5, vedges)
    except Exception:
        pass
    hole = Part.makeCylinder(0.35, 0.4, App.Vector(-1.0, -1.4, 1.3))
    body = body.cut(hole)
    # 센서 패드 0.8 정방 (열 2.7 → x±1.35), 베이스에 0.05 매립
    pads = []
    for x, y in [(-1.35, -1.27), (-1.35, 0.0), (-1.35, 1.27), (1.35, 1.27), (1.35, 0.0), (1.35, -1.27)]:
        pads.append(Part.makeBox(0.8, 0.8, 0.07, App.Vector(x - 0.4, y - 0.4, -0.02)))
    gold = pads[0]
    for p in pads[1:]:
        gold = gold.fuse(p)
    Part.makeCompound([body, gold, base]).exportStep("%s/%s.step" % (d, fid))
    body.exportStl("%s/%s__housing.stl" % (d, fid))
    gold.exportStl("%s/%s__pins.stl" % (d, fid))
    base.exportStl("%s/%s__extra.stl" % (d, fid))
    print("AHT10 3D done")


usb_c_16p()
microsd_hc()
esp32_wroom32()
aht20()
aht21()
aht10()
