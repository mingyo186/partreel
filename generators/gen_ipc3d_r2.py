# -*- coding: utf-8 -*-
"""파라메트릭 3D 백필 2라운드 (§21-6): 칩패시브/MELF몰드/QFN·SON/SOT/QFP/DIP/BGA/래디얼캡.
실행: freecadcmd generators/gen_ipc3d_r2.py     (PILOT=1이면 클래스당 1개만)
원칙: 치수=IPC명, 리드 좌표=자기 kicad_mod 패드. 애매하면 스킵+로그 (무리한 생성 금지).
교훈 반영: 핀은 거대 fuse 대신 핀단위 fuse→compound(뭉침·속도), 재개 가능(기존 산출물 스킵).
"""
import json
import os
import re
import FreeCAD as App
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
PILOT = os.environ.get("PILOT") == "1"


def pads_of(mod):
    out = []
    for m in re.finditer(r'\(pad\s+"([^"]*)"\s+(\w+)\s+\w+\s*\(at\s+([-\d.]+)\s+([-\d.]+)'
                         r'[^)]*\)\s*\(size\s+([-\d.]+)\s+([-\d.]+)', mod):
        out.append((m.group(1), m.group(2), float(m.group(3)), float(m.group(4)),
                    float(m.group(5)), float(m.group(6))))
    return out


def export(d, fid, pins_solids, body):
    pins = Part.makeCompound(pins_solids)
    Part.makeCompound([pins, body]).exportStep("%s/%s.step" % (d, fid))
    pins.exportStl("%s/%s__pins.stl" % (d, fid))
    body.exportStl("%s/%s__extra.stl" % (d, fid))


def box(w, l, h, x, y, z):
    return Part.makeBox(w, l, h, App.Vector(x, y, z))


def chip(d, fid, name, pads):
    """RESC/CAPC/INDC/DIOM####X##: 몸체 + 양끝 금속캡."""
    m = re.match(r"(?:RESC|CAPC|INDC|DIOM)(\d\d)(\d\d)X(\d+)", name)
    if not m:
        return False
    L, W, H = int(m.group(1)) / 10.0, int(m.group(2)) / 10.0, int(m.group(3)) / 100.0
    nums = [p for p in pads if p[0].isdigit()]
    if len(nums) != 2:
        return False
    xs = sorted(p[2] for p in nums)
    if abs(xs[1] - xs[0]) < 0.05:  # 세로 배치면 회전 대신 스킵(드묾)
        return False
    if W > L:
        L, W = W, L  # 패드축=길이축 정렬
    cap = max(L * 0.22, 0.1)
    body = box(L - 2 * cap + 0.04, W, H, -(L - 2 * cap + 0.04) / 2, -W / 2, 0)
    caps = [box(cap, W, H, -L / 2, -W / 2, 0), box(cap, W, H, L / 2 - cap, -W / 2, 0)]
    export(d, fid, caps, body)
    return True


def qfn(d, fid, name, pads):
    """QFN/SON ..P<bx>X<by>X<h>: 플랫 노리드 — 몸체 + 바닥 패드판 + EP."""
    m = re.match(r"(?:QFN|SON)\d+P(\d+)X(\d+)X(\d+)", name)
    if not m:
        return False
    bx, by, H = int(m.group(1)) / 100.0, int(m.group(2)) / 100.0, int(m.group(3)) / 100.0
    nums = [p for p in pads if p[0].isdigit()]
    if len(nums) < 4:
        return False
    body = box(bx, by, H - 0.05, -bx / 2, -by / 2, 0.05)
    try:
        ve = [e for e in body.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 0.03]
        body = body.makeFillet(0.05, ve)
    except Exception:
        pass
    x1 = min(nums, key=lambda p: (p[3], p[2]))
    body = body.cut(Part.makeCylinder(min(0.2, bx * 0.06), 0.1,
                                      App.Vector(-bx * 0.32, -by * 0.32, H - 0.1)))
    plates = []
    for _, _, x, y, w, h in nums:
        w2, h2 = min(w, bx * 0.45) * 0.9, min(h, by * 0.45) * 0.9
        plates.append(box(w2, h2, 0.1, x - w2 / 2, y - h2 / 2, 0))
    export(d, fid, plates, body)
    return True


def sot(d, fid, name, pads):
    """SOT..P<span>X<h>: 걸윙, 피치 불균일 허용(SOT23-3 등)."""
    m = re.match(r"SOT\d+P(\d+)X(\d+)", name)
    if not m:
        return False
    span, H = int(m.group(1)) / 100.0, int(m.group(2)) / 100.0
    nums = [p for p in pads if p[0].isdigit()]
    cols = sorted({round(p[2], 1) for p in nums})
    if len(nums) < 3 or len(cols) != 2:
        return False
    bw = max(span - max(p[4] for p in nums) - 0.7, span * 0.5)
    ys = sorted(p[3] for p in nums)
    bl = ys[-1] - ys[0] + 1.4
    gaps = [b - a for a, b in zip(ys, ys[1:]) if b - a > 0.05]
    lead_w = min(min(p[4], p[5]) for p in nums) * 0.75
    if gaps:
        lead_w = min(lead_w, min(gaps) * 0.55)
    lead_l = max((span - bw) / 2 - 0.1, 0.4)
    body = box(bw, bl, H - 0.12, -bw / 2, -bl / 2, 0.12)
    try:
        ve = [e for e in body.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 0.05]
        body = body.makeFillet(0.06, ve)
    except Exception:
        pass
    feet = []
    for _, _, x, y, w, h in nums:
        sx = 1 if x > 0 else -1
        fx0 = bw / 2 + 0.02 if sx > 0 else -bw / 2 - 0.02 - lead_l
        foot = box(lead_l, lead_w, 0.12, fx0, y - lead_w / 2, 0)
        rx0 = bw / 2 - 0.03 if sx > 0 else -bw / 2 - 0.09
        feet.append(foot.fuse(box(0.12, lead_w, (H - 0.12) * 0.5, rx0, y - lead_w / 2, 0.06)))
    export(d, fid, feet, body)
    return True


def qfp(d, fid, name, pads):
    """QFP..P<sx>X<sy>X<h>: 4면 걸윙. 스팬=리드끝간, 몸체=스팬-2."""
    m = re.match(r"QFP\d+P(\d+)X(\d+)X(\d+)", name)
    if not m:
        return False
    sx_, sy_, H = int(m.group(1)) / 100.0, int(m.group(2)) / 100.0, int(m.group(3)) / 100.0
    nums = [p for p in pads if p[0].isdigit()]
    if len(nums) < 8:
        return False
    bw, bl = sx_ - 2.0, sy_ - 2.0
    lead_l = 0.85
    lead_w = min(min(p[4], p[5]) for p in nums) * 0.75
    body = box(bw, bl, H - 0.12, -bw / 2, -bl / 2, 0.12)
    try:
        ve = [e for e in body.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 0.05]
        body = body.makeFillet(0.1, ve)
    except Exception:
        pass
    body = body.cut(Part.makeCylinder(0.4, 0.15, App.Vector(-bw / 2 + 1.2, -bl / 2 + 1.2, H - 0.14)))
    feet = []
    for _, _, x, y, w, h in nums:
        if abs(x) >= abs(y):  # 좌/우변
            f0 = bw / 2 + 0.02 if x > 0 else -bw / 2 - 0.02 - lead_l
            foot = box(lead_l, lead_w, 0.12, f0, y - lead_w / 2, 0)
            r0 = bw / 2 - 0.03 if x > 0 else -bw / 2 - 0.09
            feet.append(foot.fuse(box(0.12, lead_w, (H - 0.12) * 0.5, r0, y - lead_w / 2, 0.06)))
        else:  # 상/하변
            f0 = bl / 2 + 0.02 if y > 0 else -bl / 2 - 0.02 - lead_l
            foot = box(lead_w, lead_l, 0.12, x - lead_w / 2, f0, 0)
            r0 = bl / 2 - 0.03 if y > 0 else -bl / 2 - 0.09
            feet.append(foot.fuse(box(lead_w, 0.12, (H - 0.12) * 0.5, x - lead_w / 2, r0, 0.06)))
    export(d, fid, feet, body)
    return True


def dip(d, fid, name, pads):
    """DIP<n>-300: 표준 몰드 DIP — 몸체 부양 + 수직 다리."""
    if not re.match(r"DIP\d+-\d+", name):
        return False
    nums = [p for p in pads if p[0].isdigit() and p[1] == "thru_hole"]
    if len(nums) < 4:
        return False
    xs = sorted({round(p[2], 1) for p in nums})
    if len(xs) != 2:
        return False
    row = xs[1] - xs[0]
    ys = sorted(p[3] for p in nums)
    bw, bl, bh, lift = row - 1.4, ys[-1] - ys[0] + 2.2, 3.2, 0.35
    body = box(bw, bl, bh, -bw / 2, (ys[0] + ys[-1]) / 2 - bl / 2, lift)
    body = body.cut(Part.makeCylinder(0.5, 0.2, App.Vector(0, (ys[0] + ys[-1]) / 2 - bl / 2 + 1.0, lift + bh - 0.18)))
    legs = []
    for _, _, x, y, w, h in nums:
        sx = 1 if x > 0 else -1
        legs.append(box(0.5, 0.28, lift + 0.6, x - 0.25 - sx * 0.35, y - 0.14, 0)
                    .fuse(box(1.1, 0.28, 0.25, min(x - sx * 0.85, x) if sx > 0 else x - 0.25, y - 0.14, lift + 0.35)))
    export(d, fid, legs, body)
    return True


def bga(d, fid, name, pads):
    """BGA...C<p>P<nx>X<ny>_<bx>X<by>X<h>: 몸체 + 볼(퓨즈 없이 컴파운드)."""
    m = re.match(r"BGA\d+C(\d+)P\d+X\d+_(\d+)X(\d+)X(\d+)", name)
    if not m:
        return False
    pitch = int(m.group(1)) / 100.0
    bx, by, H = int(m.group(2)) / 100.0, int(m.group(3)) / 100.0, int(m.group(4)) / 100.0
    nums = [p for p in pads if p[0].strip()]
    if len(nums) < 9:
        return False
    ball_r, ball_h = pitch * 0.28, 0.22
    body = box(bx, by, H - ball_h, -bx / 2, -by / 2, ball_h)
    body = body.cut(Part.makeCylinder(min(0.5, bx * 0.04), 0.15,
                                      App.Vector(-bx * 0.4, -by * 0.4, H - 0.14)))
    balls = [Part.makeCylinder(ball_r, ball_h, App.Vector(p[2], p[3], 0)) for p in nums]
    export(d, fid, balls, body)
    return True


def radial(d, fid, name, pads):
    """CAPPR/CAPRD<ls>-<D>X<H> 원통 | CAPRR<ls>-<W>X<L>X<H> 박스 래디얼."""
    nums = [p for p in pads if p[0].isdigit()]
    if len(nums) < 2:
        return False
    cx = sum(p[2] for p in nums) / len(nums)
    cy = sum(p[3] for p in nums) / len(nums)
    m = re.match(r"(?:CAPPR|CAPRD)\d+-(\d+)X(\d+)", name)
    if m:
        D, H = int(m.group(1)) / 100.0, int(m.group(2)) / 100.0
        body = Part.makeCylinder(D / 2, H, App.Vector(cx, cy, 0.4))
    else:
        m = re.match(r"CAPRR\d+-(\d+)X(\d+)X(\d+)", name)
        if not m:
            return False
        W, L, H = int(m.group(1)) / 100.0, int(m.group(2)) / 100.0, int(m.group(3)) / 100.0
        body = box(W, L, H, cx - W / 2, cy - L / 2, 0.4)
    legs = [Part.makeCylinder(max(min(p[4], p[5]) * 0.3, 0.25), 0.42,
                              App.Vector(p[2], p[3], 0)) for p in nums]
    export(d, fid, legs, body)
    return True


BUILDERS = [("chip", re.compile(r"^(?:RESC|CAPC|INDC|DIOM)\d"), chip),
            ("qfn", re.compile(r"^(?:QFN|SON)\d+P\d+X\d+X\d+"), qfn),
            ("sot", re.compile(r"^SOT\d+P\d+X\d+"), sot),
            ("qfp", re.compile(r"^QFP\d+P\d+X\d+X\d+"), qfp),
            ("dip", re.compile(r"^DIP\d+-\d+"), dip),
            ("bga", re.compile(r"^BGA\d+C\d+P"), bga),
            ("radial", re.compile(r"^(?:CAPPR|CAPRD|CAPRR)\d+-\d+X\d+"), radial)]


def main():
    idx = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    done = {}
    skipped = []
    for p in idx["parts"]:
        d = os.path.join(ROOT, p["path"]).replace("\\", "/")
        fid = p["id"]
        try:
            meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
            if meta.get("tier") != "verified-2d":
                continue
            fpname = meta.get("dimensions_source", "").split("(")[-1].rstrip(")")
            fpname = fpname.split("/")[-1].replace(".kicad_mod", "")
            builder = next(((k, f) for k, rx, f in BUILDERS if rx.match(fpname)), None)
            if not builder:
                continue
            kind, fn = builder
            if PILOT and done.get(kind):
                continue
            if (os.path.exists(os.path.join(d, fid + ".glb"))
                    or os.path.exists(os.path.join(d, fid + "__pins.stl"))):
                continue
            mod = open(os.path.join(d, fid + ".kicad_mod"), encoding="utf-8").read()
            if fn(d, fid, fpname, pads_of(mod)):
                done[kind] = done.get(kind, 0) + 1
                if sum(done.values()) % 200 == 0:
                    print("progress", sum(done.values()))
            else:
                skipped.append((fid, kind + " guard"))
        except Exception as e:
            skipped.append((fid, "error: %s" % e))
    json.dump([{"part": k, "reason": v} for k, v in skipped],
              open(os.path.join(ROOT, "docs", "ipc3d-r2-skip-log.json"), "w",
                   encoding="utf-8"), indent=1, ensure_ascii=False)
    print("r2 generated", done, "| skipped", len(skipped))


main()
