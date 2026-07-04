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
    y0, y1 = cfg.get("body_y0", -2.5), cfg.get("body_y1", 1.75)  # 공식 fab 외곽
    L, W, H = x1 - x0, y1 - y0, cfg["body_h"]
    # standoff: 리드 두께(0.15)만큼 하우징을 띄움 — 리드 밑면과 공면(z-fighting) 방지 (§14-C)
    Z0 = 0.12
    housing = Part.makeBox(L, W, H - Z0, App.Vector(x0, y0, Z0))
    # 수직 모서리 필렛
    try:
        vedges = [e for e in housing.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 0.1]
        housing = housing.makeFillet(0.25, vedges)
    except Exception:
        pass
    # 상부 캐비티
    cav = Part.makeBox(L - 1.6, W - 1.6, H - 1.0, App.Vector(x0 + 0.8, y0 + 0.8, 1.0))
    housing = housing.cut(cav)
    # 전면 중앙 래치 창
    try:
        ww = max(R * 0.5, 1.2)
        win = Part.makeBox(ww, 1.0, 1.4, App.Vector(R / 2 - ww / 2, y1 - 0.9, H - 1.4))
        housing = housing.cut(win)
    except Exception:
        pass
    # 금속부(금색): SMD 리드 — 하우징 앞(y1)에서 패드 끝(2.8)까지 노출 + 전면 위로 꺾임
    metal = []
    for i in range(n):
        x = i * p
        metal.append(Part.makeBox(0.3, 2.8 - (y1 - 0.6), 0.15,
                                  App.Vector(x - 0.15, y1 - 0.6, 0)))      # 수평 발 (노출 1.05)
        metal.append(Part.makeBox(0.3, 0.2, 1.2,
                                  App.Vector(x - 0.15, y1 - 0.05, 0)))     # 전면 상향 꺾임 (공면 방지 0.05 겹침)
    for mx in (x0 - 0.35, x1 - 0.65):  # 마운팅 탭 (뒤쪽, 하우징 밖 0.3)
        metal.append(Part.makeBox(1.0, 2.8, 1.6, App.Vector(mx, -2.8, 0)))
    pins = metal[0]
    for m in metal[1:]:
        pins = pins.fuse(m)
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
