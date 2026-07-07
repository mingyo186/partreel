# -*- coding: utf-8 -*-
"""IPC명 기반 파라메트릭 3D 백필 — SOIC/SOP/TSSOP류 걸윙 전량 (§21-6, 파일럿 승계).
실행: freecadcmd generators/gen_ipc3d.py
가드: ①IPC명에서 높이 추출 가능 ②번호 패드가 정확히 2열 ③피치 균일(±0.05)
     ④EP 없음(2열 외 패드 발견 시 스킵). 실패는 스킵+로그(무리한 생성 금지).
다리 폭 = min(패드 짧은변*0.75, 피치*0.55)  ← "핀 뭉탱이" 재발 방지 (2026-07-05 사건)
"""
import json
import os
import re
import FreeCAD as App
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
LIB = (ROOT + "/library").replace("\\", "/")


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


def gullwing(d, fid, bw, bl, bh, pad_xy, lead_w, lead_l):
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


def main():
    idx = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    done = skipped = 0
    log = []
    for p in idx["parts"]:
        d = os.path.join(ROOT, p["path"])
        fid = p["id"]
        try:
            meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
            if meta.get("tier") != "verified-2d":
                continue
            ds = meta.get("dimensions_source", "")
            mm = re.search(r"/((?:SOIC|SOP|TSOP|TSSOP|SSOP)\d*P?\d*X(\d+)-\d+[A-Z]*)"
                           r"\.kicad_mod", ds)
            if not mm:
                continue
            if (os.path.exists(os.path.join(d, fid + ".glb"))
                    or os.path.exists(os.path.join(d, fid + "__pins.stl"))):
                continue  # 이미 생성됨 (재실행/중단 재개 안전)
            bh = int(mm.group(2)) / 100.0
            mod = open(os.path.join(d, fid + ".kicad_mod"), encoding="utf-8").read()
            pads = []
            for m in re.finditer(r'\(pad\s+"(\d+)"\s+\w+\s+\w+\s*\(at\s+([-\d.]+)\s+'
                                 r'([-\d.]+)[^)]*\)\s*\(size\s+([-\d.]+)\s+([-\d.]+)', mod):
                pads.append((float(m.group(2)), float(m.group(3)),
                             float(m.group(4)), float(m.group(5))))
            if len(pads) < 4:
                log.append((fid, "pads<4")); skipped += 1; continue
            cols = sorted({round(p[0], 1) for p in pads})
            if len(cols) != 2:  # 정확히 2열 아니면(EP 등) 스킵
                log.append((fid, "not 2 columns")); skipped += 1; continue
            ys = sorted(p[1] for p in pads)
            gaps = [round(b - a, 2) for a, b in zip(ys, ys[1:]) if b - a > 0.01]
            if not gaps or max(gaps) - min(gaps) > 0.05:
                log.append((fid, "pitch not uniform")); skipped += 1; continue
            pitch = gaps[0]
            span = cols[1] - cols[0]
            pad_len = max(p[2] for p in pads)
            bw = max(round(span - pad_len - 0.9, 2), span * 0.62)
            bl = round(ys[-1] - ys[0] + 1.1, 2)
            lead_w = min(min(p[2], p[3]) for p in pads) * 0.75
            lead_w = min(lead_w, pitch * 0.55)
            lead_l = max(round((span - bw) / 2 - 0.15, 2), 0.5)
            gullwing(d.replace("\\", "/"), fid, bw, bl, bh,
                     [(p[0], p[1]) for p in pads], lead_w, lead_l)
            done += 1
            if done % 100 == 0:
                print("progress", done)
        except Exception as e:
            log.append((fid, "error: %s" % e)); skipped += 1
    json.dump([{"part": k, "reason": v} for k, v in log],
              open(os.path.join(ROOT, "docs", "ipc3d-skip-log.json"), "w",
                   encoding="utf-8"), indent=1, ensure_ascii=False)
    print("3D generated %d, skipped %d" % (done, skipped))


main()
