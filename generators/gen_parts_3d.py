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
        feet.append(Part.makeBox(w * 0.8, 0.9, 0.15, App.Vector(x - w * 0.4, -4.5, 0)))
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
    body = Part.makeBox(13.8, 15.9, 1.4, App.Vector(-6.9, -7.8, 0))
    slot = Part.makeBox(12.0, 1.2, 1.0, App.Vector(-6.0, -8.0, 0.3))  # 카드 입구
    body = body.cut(slot)
    contacts = Part.makeBox(9.5, 1.2, 0.3, App.Vector(-6.2, -8.3, 0))  # 접점 스트립
    Part.makeCompound([body, contacts]).exportStep("%s/%s.step" % (d, fid))
    body.exportStl("%s/%s__housing.stl" % (d, fid))
    contacts.exportStl("%s/%s__pins.stl" % (d, fid))
    print("microSD 3D done")


def esp32_wroom32():
    fid = "esp32_wroom32"
    d = "%s/module/espressif/esp32_wroom32/%s" % (LIB, fid)
    body = Part.makeBox(18, 25.5, 3.1, App.Vector(-9, -15.745, 0))      # 금속 쉴드 모듈
    pads = Part.makeBox(17, 18.5, 0.2, App.Vector(-8.5, -9.0, -0.0))     # 패드 영역(대표)
    Part.makeCompound([body, pads]).exportStep("%s/%s.step" % (d, fid))
    body.exportStl("%s/%s__housing.stl" % (d, fid))
    pads.exportStl("%s/%s__pins.stl" % (d, fid))
    print("ESP32 3D done")


usb_c_16p()
microsd_hc()
esp32_wroom32()
