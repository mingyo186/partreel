"""
커넥터 패밀리 3D 생성기 (FreeCAD 헤드리스, config 공용).
실행: freecadcmd generators/gen_connectors_3d.py
  - 기본: FAMILIES 전체 배치 생성
  - env PART_FILTER="<family_key>:<pins>" 지정 시 해당 1개만 (ONDEMAND 포함, §19)

하우징 치수 = 풋프린트 fab 박스 (REQUIREMENTS §14 C: 본체=fab 일치).
style="header"면 낮은 베이스 + 위로 솟은 핀 (핀헤더).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_connectors import FAMILIES, ONDEMAND  # noqa: E402

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
    ps, below, above = cfg["pin_sq"], cfg["pin_below"], cfg["pin_into"]

    if cfg.get("style") == "header":
        # 핀헤더: 낮은 플라스틱 베이스 + 관통 핀(아래 below, 위 above)
        housing = Part.makeBox(L, W, HZ, App.Vector(x0, y0, 0))
        pin_shapes = []
        for i in range(n):
            x = i * pitch
            pin_shapes.append(Part.makeBox(ps, ps, below + above,
                                           App.Vector(x - ps / 2, -ps / 2, -below)))
    elif cfg.get("style") == "terminal":
        # 스크류 터미널: 통짜 블록 + 극마다 상면 나사 리세스 + 전면 전선 삽입구
        housing = Part.makeBox(L, W, HZ, App.Vector(x0, y0, 0))
        screw_r = min(pitch * 0.32, 1.8)
        wire_r = min(pitch * 0.28, 1.6)
        for i in range(n):
            x = i * pitch
            # 상면 나사 리세스 (수직 원통 컷, 뒤쪽 열)
            screw = Part.makeCylinder(screw_r, 3.0,
                                      App.Vector(x, y0 + W * 0.35, HZ - 2.5),
                                      App.Vector(0, 0, 1))
            housing = housing.cut(screw)
            # 전면 전선 삽입구 (수평 원통 컷, 중간 높이)
            wire = Part.makeCylinder(wire_r, W * 0.55,
                                     App.Vector(x, y1 + 0.1, HZ * 0.35),
                                     App.Vector(0, -1, 0))
            housing = housing.cut(wire)
        pin_shapes = []
        for i in range(n):
            x = i * pitch
            pin_shapes.append(Part.makeBox(ps, ps, below + above,
                                           App.Vector(x - ps / 2, -ps / 2, -below)))
    else:
        # 쉬라우드형 커넥터 (JST류): 리얼리즘 패스 적용 (§14-C)
        housing = Part.makeBox(L, W, HZ, App.Vector(x0, y0, 0))
        # 1) 수직 4모서리 필렛 (네모반듯함 제거)
        try:
            vedges = [e for e in housing.Edges
                      if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 0.1]
            housing = housing.makeFillet(min(0.35, W * 0.08), vedges)
        except Exception:
            pass
        # 2) 상부 캐비티
        cav = Part.makeBox(L - 1.6, W - 1.6, HZ - 1.0, App.Vector(x0 + 0.8, y0 + 0.8, 1.0))
        housing = housing.cut(cav)
        # 3) 양 끝벽 상단 U자 홈 — JST XH 데이터시트 측면도의 그 슬롯.
        #    (4면 벽은 풀높이 유지 — 앞벽 낮추는 건 실물과 다름, 도면 대조로 정정됨)
        try:
            yc = (y0 + y1) / 2.0
            nw, nd = 2.0, HZ * 0.5  # 홈 폭 ~2mm, 깊이 = 높이의 절반 (도면 비율)
            for nx in (x0 - 0.05, x1 - 0.95):
                notch = Part.makeBox(1.0, nw, nd + 0.1, App.Vector(nx, yc - nw / 2, HZ - nd))
                housing = housing.cut(notch)
        except Exception:
            pass
        # 5) 핀: 끝단 모따기(테이퍼)로 실핀 느낌
        pin_shapes = []
        for i in range(n):
            x = i * pitch
            pin = Part.makeBox(ps, ps, below + above,
                               App.Vector(x - ps / 2, -ps / 2, -below))
            try:
                tip_edges = [e for e in pin.Edges
                             if abs(e.Vertexes[0].Z + below) < 0.01
                             and abs(e.Vertexes[1].Z + below) < 0.01]
                pin = pin.makeChamfer(ps * 0.3, tip_edges)
            except Exception:
                pass
            pin_shapes.append(pin)

    pins_solid = pin_shapes[0]
    for p in pin_shapes[1:]:
        pins_solid = pins_solid.fuse(p)
    return housing, pins_solid


def emit(cfg, n):
    fid = "%s_%dpin" % (cfg["key"], n)
    d = "%s/%s/%s" % (LIB, cfg["lib_path"], fid)
    housing, pins_solid = build(cfg, n)
    Part.makeCompound([housing, pins_solid]).exportStep("%s/%s.step" % (d, fid))
    housing.exportStl("%s/%s__housing.stl" % (d, fid))
    pins_solid.exportStl("%s/%s__pins.stl" % (d, fid))


def main():
    flt = os.environ.get("PART_FILTER", "").strip()
    if flt:
        key, pins = flt.rsplit(":", 1) if ":" in flt else (flt, "*")
        cfg = next((c for c in FAMILIES + ONDEMAND if c["key"] == key), None)
        if cfg is None:
            print("PART_FILTER: unknown family", key)
            raise SystemExit(1)
        targets = cfg["pins"] if pins == "*" else [int(pins)]
        for p in targets:
            emit(cfg, p)
        print("STEP+STL generated: %d part(s) (%s)" % (len(targets), key))
        return
    cnt = 0
    for cfg in FAMILIES:
        for n in cfg["pins"]:
            emit(cfg, n)
            cnt += 1
    print("STEP+STL generated:", cnt, "parts")


main()
