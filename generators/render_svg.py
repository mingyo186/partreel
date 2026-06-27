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
PIN_RE = re.compile(
    r'\(pin\s+\w+\s+\w+\s+\(at\s+([-\d.]+)\s+([-\d.]+)\s+(\d+)\)\s+\(length\s+([-\d.]+)\)'
    r'.*?\(name\s+"([^"]+)".*?\(number\s+"([^"]+)"', re.S)


def svg_header(minx, miny, w, h, m):
    vb = f"{minx - m:.2f} {miny - m:.2f} {w + 2 * m:.2f} {h + 2 * m:.2f}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" '
            f'preserveAspectRatio="xMidYMid meet" style="width:100%;height:100%">'
            f'<rect x="{minx - m:.2f}" y="{miny - m:.2f}" width="{w + 2 * m:.2f}" '
            f'height="{h + 2 * m:.2f}" fill="{BG}"/>')


def render_footprint(text):
    pads, lines = [], []
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
                out.append(f'<ellipse cx="{x:.3f}" cy="{y:.3f}" rx="{float(d[1])/2:.3f}" '
                           f'ry="{float(d[2])/2:.3f}" fill="{BG}"/>')
            else:
                out.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{float(d[0])/2:.3f}" fill="{BG}"/>')
    # 핀1 마커: 패드 "1"(일렬 커넥터)일 때만, 패드 아래 빈 공간에 위를 가리키는 삼각형
    p1 = next((pd for pd in pads if pd[0] == "1"), None)
    if p1:
        _, _, _, x, y, pw, ph, _ = p1
        tip = y + ph / 2 + 0.45
        base = y + ph / 2 + 1.05
        out.append(f'<polygon points="{x-0.45:.2f},{base:.2f} {x+0.45:.2f},{base:.2f} '
                   f'{x:.2f},{tip:.2f}" fill="{COL["label"]}"/>')
    out.append("</svg>")
    return "".join(out)


def render_symbol(text):
    rm = RECT_RE.search(text)
    pins = list(PIN_RE.finditer(text))
    if not rm or not pins:
        return None
    rx1, ry1, rx2, ry2 = map(float, rm.groups())
    # KiCad 심볼 Y는 위쪽이 +. SVG는 아래가 + → y 부호 반전.
    def ty(y):
        return -y

    xs = [rx1, rx2]; ys = [ty(ry1), ty(ry2)]
    pin_data = []
    for m in pins:
        px, py, ang, length, name, num = m.groups()
        px, py, ang, length = float(px), float(py), int(ang), float(length)
        # ang 0 = +x 방향으로 핀이 뻗음(본체 쪽). 연결점은 (px,py).
        ex = px + (length if ang == 0 else -length if ang == 180 else 0)
        ey = py + (length if ang == 90 else -length if ang == 270 else 0)
        pin_data.append((px, ty(py), ex, ty(ey), num, name))
        xs += [px, ex]; ys += [ty(py), ty(ey)]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)

    out = [svg_header(minx, miny, maxx - minx, maxy - miny, 1.5)]
    bx, by = min(rx1, rx2), min(ty(ry1), ty(ry2))
    out.append(f'<rect x="{bx:.3f}" y="{by:.3f}" width="{abs(rx2-rx1):.3f}" '
               f'height="{abs(ty(ry2)-ty(ry1)):.3f}" fill="{COL["body"]}" '
               f'stroke="{COL["bodyline"]}" stroke-width="0.25"/>')
    for px, py, ex, ey, num, name in pin_data:
        out.append(f'<line x1="{px:.3f}" y1="{py:.3f}" x2="{ex:.3f}" y2="{ey:.3f}" '
                   f'stroke="{COL["pin"]}" stroke-width="0.2"/>')
        out.append(f'<circle cx="{px:.3f}" cy="{py:.3f}" r="0.4" fill="{COL["bodyline"]}"/>')
        # 핀 번호: 핀선 위, 본체 가까이
        out.append(f'<text x="{ex - 0.4:.3f}" y="{ey - 0.4:.3f}" fill="{COL["num"]}" '
                   f'font-size="1.1" text-anchor="end" font-family="sans-serif">{num}</text>')
        # 핀 이름: 본체 안쪽
        out.append(f'<text x="{ex + 0.6:.3f}" y="{ey + 0.4:.3f}" fill="{COL["name"]}" '
                   f'font-size="1.1" text-anchor="start" font-family="sans-serif">{name}</text>')
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
