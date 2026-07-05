# -*- coding: utf-8 -*-
"""IPC명 기반 파라메트릭 3D 파일럿 (CERN verified-2D → 풀 3D 승격, §21-6).
실행: freecadcmd generators/gen_ipc3d_pilot.py
치수: 높이=IPC명(X175=1.75mm), 리드 좌표=부품 자신의 kicad_mod 패드(감사로 검증된 값)."""
import json
import os
import re
import FreeCAD as App
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
LIB = (ROOT + "/library").replace("\\", "/")

PILOT = ["ic/cern/cern_opa2196id", "ic/cern/cern_drv8803dw", "ic/cern/cern_sn74lv244apw"]


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


def gullwing(path, fid, bw, bl, bh, pad_xy, lead_w, lead_l):
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
        fx0 = bw / 2 + 0.02 if sx > 0 else -bw / 2 - 0.02 - lead_l
        feet.append(Part.makeBox(lead_l, lead_w, 0.12, App.Vector(fx0, y - lead_w / 2, 0)))
        rx0 = bw / 2 - 0.03 if sx > 0 else -bw / 2 - 0.12 + 0.03
        feet.append(Part.makeBox(0.12, lead_w, bh * 0.55, App.Vector(rx0, y - lead_w / 2, 0.06)))
    pins = _fuse(feet)
    Part.makeCompound([pins, body]).exportStep("%s/%s.step" % (d, fid))
    pins.exportStl("%s/%s__pins.stl" % (d, fid))
    body.exportStl("%s/%s__extra.stl" % (d, fid))
    print(fid, "3D done")


for rel in PILOT:
    d = os.path.join(ROOT, "library", *rel.split("/"))
    fid = rel.split("/")[-1]
    meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
    mod = open(os.path.join(d, fid + ".kicad_mod"), encoding="utf-8").read()
    pads = []
    for m in re.finditer(r'\(pad\s+"(\d+)"\s+\w+\s+\w+\s*\(at\s+([-\d.]+)\s+([-\d.]+)'
                         r'[^)]*\)\s*\(size\s+([-\d.]+)\s+([-\d.]+)', mod):
        pads.append((float(m.group(2)), float(m.group(3)),
                     float(m.group(4)), float(m.group(5))))
    # IPC명에서 높이 (예: SOIC127P600X175-8 → 1.75)
    mh = re.search(r"P\d+X(\d+)-\d+", meta.get("dimensions_source", ""))
    bh = int(mh.group(1)) / 100.0 if mh else 1.6
    xs = sorted({round(p[0], 2) for p in pads})
    span = xs[-1] - xs[0]                     # 패드 중심 간 스팬
    pad_len = max(p[2] for p in pads)         # 패드 x 길이
    bw = round(span - pad_len - 0.9, 2)       # 몸체 폭 (SOIC-8: 5.4-1.55-0.9≈2.95→3.9 보정)
    bw = max(bw, span * 0.62)
    ys = sorted(p[1] for p in pads)
    bl = round(ys[-1] - ys[0] + 1.1, 2)       # 몸체 길이 = 핀 스팬 + 마진
    # 다리 폭 = 패드의 짧은 변 기준 + 피치의 55% 상한 (뭉침 방지 — "핀 뭉탱이" 재발 사건)
    pitch = min(b - a for a, b in zip(ys, ys[1:]) if b - a > 0.01)
    lead_w = min(min(p[2], p[3]) for p in pads) * 0.75
    lead_w = min(lead_w, pitch * 0.55)
    lead_l = round((span - bw) / 2 - 0.15, 2)
    pad_xy = [(p[0], p[1]) for p in pads]
    gullwing(rel, fid, bw, bl, bh, pad_xy, lead_w, max(lead_l, 0.5))
print("pilot done")
