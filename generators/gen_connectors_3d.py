"""
커넥터 패밀리 3D 생성기 (FreeCAD 헤드리스, config 공용).
실행: freecadcmd generators/gen_connectors_3d.py

gen_connectors.FAMILIES 설정을 그대로 써서 패밀리별 STEP/STL 생성.
하우징 치수 = 풋프린트 fab 박스 (REQUIREMENTS §14 C: 본체=fab 일치).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_connectors import FAMILIES  # noqa: E402

import FreeCAD as App  # noqa: E402
import Part  # noqa: E402

LIB = (os.path.dirname(os.path.abspath(__file__)) + "/../library").replace("\\", "/")


def build(cfg, n):
    pitch = cfg["pitch"]
    A = (n - 1) * pitch
    fab = cfg["fab"]
    x0, x1 = fab["x0"], A + fab["x1"]
    y0, y1 = fab["y0"], fab["y1"]
    L, W, HZ = x1 - x0, y1 - y0, cfg["housing_h"]
    housing = Part.makeBox(L, W, HZ, App.Vector(x0, y0, 0))
    cav = Part.makeBox(L - 1.6, W - 1.6, HZ - 1.0, App.Vector(x0 + 0.8, y0 + 0.8, 1.0))
    housing = housing.cut(cav)
    ps, below, into = cfg["pin_sq"], cfg["pin_below"], cfg["pin_into"]
    pin_shapes = []
    for i in range(n):
        x = i * pitch
        pin_shapes.append(Part.makeBox(ps, ps, below + into, App.Vector(x - ps / 2, -ps / 2, -below)))
    pins_solid = pin_shapes[0]
    for p in pin_shapes[1:]:
        pins_solid = pins_solid.fuse(p)
    return housing, pins_solid


def main():
    cnt = 0
    for cfg in FAMILIES:
        for n in cfg["pins"]:
            fid = "%s_%dpin" % (cfg["key"], n)
            d = "%s/%s/%s" % (LIB, cfg["lib_path"], fid)
            housing, pins_solid = build(cfg, n)
            Part.makeCompound([housing, pins_solid]).exportStep("%s/%s.step" % (d, fid))
            housing.exportStl("%s/%s__housing.stl" % (d, fid))
            pins_solid.exportStl("%s/%s__pins.stl" % (d, fid))
            cnt += 1
    print("STEP+STL generated:", cnt, "parts")


main()
