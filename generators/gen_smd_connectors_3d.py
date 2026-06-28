"""
SMD 커넥터 패밀리 3D (FreeCAD 헤드리스). 실행: freecadcmd generators/gen_smd_connectors_3d.py
gen_smd_connectors.FAMILIES 설정 사용. 대표 형상(SMD, 관통핀 없음).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_smd_connectors import FAMILIES  # noqa: E402

import FreeCAD as App  # noqa: E402
import Part  # noqa: E402

LIB = (os.path.dirname(os.path.abspath(__file__)) + "/../library").replace("\\", "/")


def build(cfg, n):
    p = cfg["pitch"]
    R = (n - 1) * p
    x0, x1 = -2.5, R + 2.5
    L, W, H = x1 - x0, 5.0, cfg["body_h"]
    housing = Part.makeBox(L, W, H, App.Vector(x0, -2.5, 0))
    cav = Part.makeBox(L - 1.6, W - 2.0, H - 1.0, App.Vector(x0 + 0.8, -1.5, 1.0))
    housing = housing.cut(cav)
    pins = Part.makeBox(R + 0.6, 1.7, 0.25, App.Vector(-0.3, 1.1, 0))
    return housing, pins


def main():
    cnt = 0
    for cfg in FAMILIES:
        for n in cfg["pins"]:
            fid = "%s_%dpin" % (cfg["key"], n)
            d = "%s/%s/%s" % (LIB, cfg["lib_path"], fid)
            housing, pins = build(cfg, n)
            Part.makeCompound([housing, pins]).exportStep("%s/%s.step" % (d, fid))
            housing.exportStl("%s/%s__housing.stl" % (d, fid))
            pins.exportStl("%s/%s__pins.stl" % (d, fid))
            cnt += 1
    print("SMD STEP+STL generated:", cnt)


main()
