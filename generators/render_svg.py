"""
KiCad 풋프린트/심볼 -> SVG 미리보기 렌더러.
실행: python generators/render_svg.py

.kicad_mod -> <id>.footprint.svg  (패드 탑뷰 + silk/fab/courtyard)
.kicad_sym -> <id>.symbol.svg     (본체 + 핀 + 번호/이름)
.kicad 표준 요소만 파싱하므로 모든 패밀리에 적용됨. viewBox로 자동 스케일.
"""

import json
import os
import re

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

BG = "#12151c"
COL = dict(courtyard="#d24d4d", fab="#6b7280", silk="#e6e9ef",
           copper="#c79b5c", body="#1e222b", bodyline="#4ea1ff",
           pin="#e6e9ef", num="#9aa3b2", name="#e6e9ef", label="#ffffff")

PAD_RE = re.compile(
    r'\(pad\s+(?:"([^"]*)"|(\S+))\s+(\w+)\s+(\w+)\s+\(at\s+([-\d.]+)\s+([-\d.]+)[^)]*?\)\s*'
    r'\(size\s+([-\d.]+)\s+([-\d.]+)\)(?:\s*\(drill\s+([^)]+)\))?')
LINE_RE = re.compile(
    r'\(fp_line\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\)'
    r'.*?\(width\s+([-\d.]+)\).*?\(layer\s+"([^"]+)"\)')
RECT_RE = re.compile(
    r'\(rectangle\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\)')
POLY_RE = re.compile(r'\(polyline\s+\(pts((?:\s*\(xy\s+[-\d.]+\s+[-\d.]+\))+)', re.S)
XY_RE = re.compile(r'\(xy\s+([-\d.]+)\s+([-\d.]+)\)')
CIRC_RE = re.compile(r'\(circle\s+\(center\s+([-\d.]+)\s+([-\d.]+)\)\s+'
                     r'\(radius\s+([-\d.]+)\)', re.S)
ARC_RE = re.compile(r'\(arc\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+'
                    r'\(mid\s+([-\d.]+)\s+([-\d.]+)\)\s+'
                    r'\(end\s+([-\d.]+)\s+([-\d.]+)\)', re.S)


def arc_path(sx, sy, mx, my, ex, ey):
    """3점(SVG 좌표) → SVG 패스 A 명령. 일직선이면 None."""
    d = 2 * (sx * (my - ey) + mx * (ey - sy) + ex * (sy - my))
    if abs(d) < 1e-9:
        return None
    ux = ((sx * sx + sy * sy) * (my - ey) + (mx * mx + my * my) * (ey - sy)
          + (ex * ex + ey * ey) * (sy - my)) / d
    uy = ((sx * sx + sy * sy) * (ex - mx) + (mx * mx + my * my) * (sx - ex)
          + (ex * ex + ey * ey) * (mx - sx)) / d
    import math
    r = math.hypot(sx - ux, sy - uy)
    # sweep: S→M→E 방향 (SVG y-아래 좌표계에서 시계=1)
    cross = (mx - sx) * (ey - sy) - (my - sy) * (ex - sx)
    sweep = 1 if cross > 0 else 0
    a0, a1, am = (math.atan2(sy - uy, sx - ux), math.atan2(ey - uy, ex - ux),
                  math.atan2(my - uy, mx - ux))
    span = (a1 - a0) % (2 * math.pi) if sweep else (a0 - a1) % (2 * math.pi)
    large = 1 if span > math.pi else 0
    return (f'M {sx:.3f} {sy:.3f} A {r:.3f} {r:.3f} 0 {large} {sweep} '
            f'{ex:.3f} {ey:.3f}')
PIN_RE = re.compile(
    r'\(pin\s+\w+\s+\w+\s+\(at\s+([-\d.]+)\s+([-\d.]+)\s+(\d+)\)\s+\(length\s+([-\d.]+)\)'
    r'((?:\s|hide|\(hide\s+yes\))*)\(name\s+"([^"]+)".*?\(number\s+"([^"]+)"', re.S)


def svg_header(minx, miny, w, h, m):
    vb = f"{minx - m:.2f} {miny - m:.2f} {w + 2 * m:.2f} {h + 2 * m:.2f}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" '
            f'preserveAspectRatio="xMidYMid meet" style="width:100%;height:100%">'
            f'<rect x="{minx - m:.2f}" y="{miny - m:.2f}" width="{w + 2 * m:.2f}" '
            f'height="{h + 2 * m:.2f}" fill="{BG}"/>')


FP_ARC_RE = re.compile(r'\(fp_arc\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+'
                       r'\(mid\s+([-\d.]+)\s+([-\d.]+)\)\s+'
                       r'\(end\s+([-\d.]+)\s+([-\d.]+)\).*?\(layer\s+"([^"]+)"\)', re.S)
FP_CIRC_RE = re.compile(r'\(fp_circle\s+\(center\s+([-\d.]+)\s+([-\d.]+)\)\s+'
                        r'\(end\s+([-\d.]+)\s+([-\d.]+)\).*?\(layer\s+"([^"]+)"\)', re.S)
FP_POLY_RE = re.compile(r'\(fp_poly\s+\(pts((?:\s*\(xy\s+[-\d.]+\s+[-\d.]+\))+)'
                        r'.*?\(layer\s+"([^"]+)"\)', re.S)


def render_footprint(text):
    pads, lines = [], []
    arcs = [tuple(map(float, m.groups()[:6])) + (m.group(7),)
            for m in FP_ARC_RE.finditer(text)]
    fcircs = [tuple(map(float, m.groups()[:4])) + (m.group(5),)
              for m in FP_CIRC_RE.finditer(text)]
    fpolys = [([(float(a), float(b)) for a, b in XY_RE.findall(m.group(1))],
               m.group(2)) for m in FP_POLY_RE.finditer(text)]
    for m in PAD_RE.finditer(text):
        name = m.group(1) if m.group(1) is not None else m.group(2)
        ptype, shape = m.group(3), m.group(4)
        x, y = float(m.group(5)), float(m.group(6))
        pw, ph = float(m.group(7)), float(m.group(8))
        drill = m.group(9)  # None | "0.75" | "oval 0.6 1.2"
        pads.append((name, ptype, shape, x, y, pw, ph, drill))
    for m in LINE_RE.finditer(text):
        x1, y1, x2, y2, w, layer = m.groups()
        lines.append((float(x1), float(y1), float(x2), float(y2), float(w), layer))
    if not pads:
        return None

    xs, ys = [], []
    for _, _, _, x, y, pw, ph, _ in pads:
        xs += [x - pw / 2, x + pw / 2]; ys += [y - ph / 2, y + ph / 2]
    for x1, y1, x2, y2, _, _ in lines:
        xs += [x1, x2]; ys += [y1, y2]
    for sx, sy, mx, my, ex, ey, _ in arcs:
        xs += [sx, mx, ex]; ys += [sy, my, ey]
    for cx, cy, ex, ey, _ in fcircs:
        r = ((ex - cx) ** 2 + (ey - cy) ** 2) ** 0.5
        xs += [cx - r, cx + r]; ys += [cy - r, cy + r]
    for pts, _ in fpolys:
        xs += [p[0] for p in pts]; ys += [p[1] for p in pts]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)

    out = [svg_header(minx, miny, maxx - minx, maxy - miny, 1.0)]
    layer_style = {"F.CrtYd": (COL["courtyard"], "0.7", None),  # KiCad 코트야드는 실선
                   "F.Fab": (COL["fab"], "0.8", None),
                   "F.SilkS": (COL["silk"], "1", None)}
    for x1, y1, x2, y2, w, layer in lines:
        st = layer_style.get(layer)
        if not st:
            continue
        col, op, dash = st
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
                   f'stroke="{col}" stroke-width="{max(w,0.08):.3f}" stroke-linecap="round" '
                   f'opacity="{op}"{dash_attr}/>')
    for sx, sy, mx, my, ex, ey, layer in arcs:
        st = layer_style.get(layer)
        if not st:
            continue
        path = arc_path(sx, sy, mx, my, ex, ey)
        if path:
            out.append(f'<path d="{path}" fill="none" stroke="{st[0]}" '
                       f'stroke-width="0.12" opacity="{st[1]}"/>')
    for cx, cy, ex, ey, layer in fcircs:
        st = layer_style.get(layer)
        if not st:
            continue
        r = ((ex - cx) ** 2 + (ey - cy) ** 2) ** 0.5
        out.append(f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{r:.3f}" fill="none" '
                   f'stroke="{st[0]}" stroke-width="0.12" opacity="{st[1]}"/>')
    for pts, layer in fpolys:
        st = layer_style.get(layer)
        if not st or len(pts) < 2:
            continue
        pstr = " ".join(f"{x:.3f},{y:.3f}" for x, y in pts)
        out.append(f'<polygon points="{pstr}" fill="{st[0]}" opacity="{st[1]}" '
                   f'fill-opacity="0.35" stroke="{st[0]}" stroke-width="0.08"/>')
    for name, ptype, shape, x, y, pw, ph, drill in pads:
        if ptype == "np_thru_hole":  # 마운팅 홀: 링만
            out.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{min(pw,ph)/2:.3f}" '
                       f'fill="none" stroke="{COL["fab"]}" stroke-width="0.1"/>')
            continue
        rx = (min(pw, ph) / 2 if shape in ("oval", "circle")
              else min(pw, ph) * 0.25 if shape == "roundrect" else 0)
        out.append(f'<rect x="{x - pw/2:.3f}" y="{y - ph/2:.3f}" width="{pw:.3f}" height="{ph:.3f}" '
                   f'rx="{rx:.3f}" fill="{COL["copper"]}"/>')
        if drill:  # THT 드릴 홀
            d = drill.split()
            if d[0] == "oval" and len(d) >= 3:
                # 슬롯 = obround(양끝 반원). ellipse 아님(끝이 뾰족해짐).
                dw, dh = float(d[1]), float(d[2])
                out.append(f'<rect x="{x-dw/2:.3f}" y="{y-dh/2:.3f}" width="{dw:.3f}" '
                           f'height="{dh:.3f}" rx="{min(dw,dh)/2:.3f}" fill="{BG}"/>')
            else:
                out.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{float(d[0])/2:.3f}" fill="{BG}"/>')
    # 핀1 마커: 모든 패드가 같은 Y(순수 일렬 커넥터)이고 패드 "1"이 있을 때만.
    p1 = next((pd for pd in pads if pd[0] == "1"), None)
    same_row = len({round(pd[4], 2) for pd in pads}) == 1
    if p1 and same_row:
        _, _, _, x, y, pw, ph, _ = p1
        tip = y + ph / 2 + 0.45
        base = y + ph / 2 + 1.05
        out.append(f'<polygon points="{x-0.45:.2f},{base:.2f} {x+0.45:.2f},{base:.2f} '
                   f'{x:.2f},{tip:.2f}" fill="{COL["label"]}"/>')
    out.append("</svg>")
    return "".join(out)


def render_symbol(text):
    rects = [tuple(map(float, m.groups())) for m in RECT_RE.finditer(text)]
    polys = [[(float(a), float(b)) for a, b in XY_RE.findall(m.group(1))]
             for m in POLY_RE.finditer(text)]
    circs = [tuple(map(float, m.groups())) for m in CIRC_RE.finditer(text)]
    arcs = [tuple(map(float, m.groups())) for m in ARC_RE.finditer(text)]
    pins = list(PIN_RE.finditer(text))
    if not pins or not (rects or polys or circs or arcs):
        return None
    # 심볼 전역 표시 플래그 (구형 인라인 hide / 신형 (hide yes) 둘 다)
    hide_nums = bool(re.search(r"\(pin_numbers\s*(?:\(offset[^)]*\)\s*)?"
                               r"(?:hide|\(hide\s+yes\))", text))
    hide_names = bool(re.search(r"\(pin_names\s*(?:\(offset[^)]*\)\s*)?"
                                r"(?:hide|\(hide\s+yes\))", text))
    # KiCad 심볼 Y는 위쪽이 +. SVG는 아래가 + → y 부호 반전.
    def ty(y):
        return -y

    xs, ys = [], []
    for rx1, ry1, rx2, ry2 in rects:
        xs += [rx1, rx2]; ys += [ty(ry1), ty(ry2)]
    for pts in polys:
        xs += [p[0] for p in pts]; ys += [ty(p[1]) for p in pts]
    for cx, cy, r in circs:
        xs += [cx - r, cx + r]; ys += [ty(cy) - r, ty(cy) + r]
    for sx, sy, mx, my, ex, ey in arcs:
        xs += [sx, mx, ex]; ys += [ty(sy), ty(my), ty(ey)]
    pin_data = []
    for m in pins:
        px, py, ang, length, flags, name, num = m.groups()
        if "hide" in flags:  # 스택/숨김 핀 (벤더 파워핀 관례) — KiCad와 동일하게 미표시
            continue
        px, py, ang, length = float(px), float(py), int(ang), float(length)
        # ang 0 = +x 방향으로 핀이 뻗음(본체 쪽). 연결점은 (px,py).
        ex = px + (length if ang == 0 else -length if ang == 180 else 0)
        ey = py + (length if ang == 90 else -length if ang == 270 else 0)
        pin_data.append((px, ty(py), ex, ty(ey), num, name))
        xs += [px, ex]; ys += [ty(py), ty(ey)]
    # 같은 위치 스택 핀(벤더 쉴드 관례, hide 아님) → 1개로 병합, 번호는 "9-12"
    grouped = {}
    for px, py, ex, ey, num, name in pin_data:
        grouped.setdefault((px, py, ex, ey), []).append((num, name))
    merged = []
    for (px, py, ex, ey), nn in grouped.items():
        nums = [n for n, _ in nn]
        if len(nums) > 1 and all(n.isdigit() for n in nums):
            sn = sorted(map(int, nums))
            num = (f"{sn[0]}-{sn[-1]}" if sn == list(range(sn[0], sn[-1] + 1))
                   else ",".join(map(str, sn)))
        else:
            num = nums[0]
        names = [n for _, n in nn]
        name = num if all(n.isdigit() for n in names) and len(names) > 1 else names[0]
        merged.append((px, py, ex, ey, num, name))
    pin_data = merged
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)

    out = [svg_header(minx, miny, maxx - minx, maxy - miny, 1.5)]
    for rx1, ry1, rx2, ry2 in rects:
        bx, by = min(rx1, rx2), min(ty(ry1), ty(ry2))
        out.append(f'<rect x="{bx:.3f}" y="{by:.3f}" width="{abs(rx2-rx1):.3f}" '
                   f'height="{abs(ty(ry2)-ty(ry1)):.3f}" fill="{COL["body"]}" '
                   f'stroke="{COL["bodyline"]}" stroke-width="0.25"/>')
    for pts in polys:
        pstr = " ".join(f"{x:.3f},{ty(y):.3f}" for x, y in pts)
        closed = len(pts) > 2 and pts[0] == pts[-1]
        fill = COL["body"] if closed else "none"
        out.append(f'<polyline points="{pstr}" fill="{fill}" '
                   f'stroke="{COL["bodyline"]}" stroke-width="0.25" '
                   f'stroke-linejoin="round"/>')
    for cx, cy, r in circs:
        out.append(f'<circle cx="{cx:.3f}" cy="{ty(cy):.3f}" r="{r:.3f}" '
                   f'fill="none" stroke="{COL["bodyline"]}" stroke-width="0.25"/>')
    for sx, sy, mx, my, ex, ey in arcs:
        path = arc_path(sx, ty(sy), mx, ty(my), ex, ty(ey))
        if path:
            out.append(f'<path d="{path}" fill="none" stroke="{COL["bodyline"]}" '
                       f'stroke-width="0.25"/>')
    for px, py, ex, ey, num, name in pin_data:
        out.append(f'<line x1="{px:.3f}" y1="{py:.3f}" x2="{ex:.3f}" y2="{ey:.3f}" '
                   f'stroke="{COL["pin"]}" stroke-width="0.2"/>')
        out.append(f'<circle cx="{px:.3f}" cy="{py:.3f}" r="0.4" fill="{COL["bodyline"]}"/>')
        dx, dy = ex - px, ey - py
        # 이름=본체 안쪽, 번호=핀선 바깥 위. 핀 방향에 맞춰 좌/우/세로 미러링.
        if abs(dx) >= abs(dy):  # 가로 핀
            if dx > 0:  # 좌측 핀(오른쪽으로 뻗음): 안쪽=오른쪽
                nm = (f'<text x="{ex + 0.5:.3f}" y="{ey + 0.35:.3f}" fill="{COL["name"]}" '
                      f'font-size="1.1" text-anchor="start" font-family="sans-serif">{name}</text>')
                nu = (f'<text x="{ex - 0.3:.3f}" y="{ey - 0.35:.3f}" fill="{COL["num"]}" '
                      f'font-size="0.9" text-anchor="end" font-family="sans-serif">{num}</text>')
            else:  # 우측 핀(왼쪽으로 뻗음): 안쪽=왼쪽
                nm = (f'<text x="{ex - 0.5:.3f}" y="{ey + 0.35:.3f}" fill="{COL["name"]}" '
                      f'font-size="1.1" text-anchor="end" font-family="sans-serif">{name}</text>')
                nu = (f'<text x="{ex + 0.3:.3f}" y="{ey - 0.35:.3f}" fill="{COL["num"]}" '
                      f'font-size="0.9" text-anchor="start" font-family="sans-serif">{num}</text>')
        else:  # 세로 핀 (예: 하단 쉴드)
            nm = (f'<text x="{ex:.3f}" y="{ey - 0.6:.3f}" fill="{COL["name"]}" '
                  f'font-size="1.1" text-anchor="middle" font-family="sans-serif">{name}</text>')
            nu = (f'<text x="{ex + 0.6:.3f}" y="{ey + 1.0:.3f}" fill="{COL["num"]}" '
                  f'font-size="0.9" text-anchor="start" font-family="sans-serif">{num}</text>')
        if not hide_names and name != num:  # 이름=번호인 무의미 중복도 생략
            out.append(nm)
        if not hide_nums:
            out.append(nu)
    out.append("</svg>")
    return "".join(out)


def main():
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    n = 0
    for p in index["parts"]:
        d = os.path.join(ROOT, p["path"])
        fid = p["id"]
        mod = open(os.path.join(d, f"{fid}.kicad_mod"), encoding="utf-8").read()
        sym = open(os.path.join(d, f"{fid}.kicad_sym"), encoding="utf-8").read()
        fp_svg = render_footprint(mod)
        sym_svg = render_symbol(sym)
        if not fp_svg or not sym_svg:
            print(f"WARN {fid}: render failed (fp={bool(fp_svg)} sym={bool(sym_svg)})")
            continue
        open(os.path.join(d, f"{fid}.footprint.svg"), "w", encoding="utf-8").write(fp_svg)
        open(os.path.join(d, f"{fid}.symbol.svg"), "w", encoding="utf-8").write(sym_svg)
        n += 1
    print(f"Rendered {n} footprint + symbol SVGs")


if __name__ == "__main__":
    main()
