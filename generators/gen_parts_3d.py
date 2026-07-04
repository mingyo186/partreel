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
    contacts = Part.makeBox(9.5, 1.2, 0.3, App.Vector(-6.2, -8.3, 0))  # 접점 스트립
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


usb_c_16p()
microsd_hc()
esp32_wroom32()
