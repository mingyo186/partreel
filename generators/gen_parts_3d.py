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
    # 금속 셸: 풋프린트 fab 범위(8.94 x 7.3) x 높이 3.16
    shell = Part.makeBox(8.94, 7.3, 3.16, App.Vector(-4.47, -3.65, 0))
    # 전면(+Y) 입구 컷
    cav = Part.makeBox(7.6, 3.2, 2.2, App.Vector(-3.8, 1.0, 0.5))
    shell = shell.cut(cav)
    # SMD 접점 스트립 (대표)
    contacts = Part.makeBox(7.0, 0.8, 0.4, App.Vector(-3.5, -4.45, 0))
    Part.makeCompound([shell, contacts]).exportStep("%s/%s.step" % (d, fid))
    shell.exportStl("%s/%s__housing.stl" % (d, fid))
    contacts.exportStl("%s/%s__pins.stl" % (d, fid))
    print("USB-C 3D done")


usb_c_16p()
