"""
회로도 가독 규칙 기계 검사 (rules/schematic-readability.md R1/R2/R3/R6).

원리:
  R2 (배선-배선 겹침): block.json의 배선 구간끼리 같은 축·같은 좌표에서
      구간이 포개지면 위반. 십자 교차는 허용.
  R3 (배선-심볼 통과): 부품 심볼의 그래픽 범위(핀 제외)를 배치·회전 변환한
      몸체 상자로 보고, 배선이 그 내부를 지나면 위반.
  R1/R6 (텍스트 겹침): 커널 렌더 SVG의 <text> 요소(mm 단위, textLength/
      font-size/anchor)로 글자 상자를 만들어 서로/배선과 겹치면 위반.
      (kicad-cli SVG는 보이는 글자마다 투명 <text>를 함께 내보낸다 —
       숨긴 속성은 아예 안 나오므로 '보이는 글자'의 대리로 정확)
"""

import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
EPS = 0.1  # mm — 닿는 것은 허용, 이만큼 이상 포개지면 위반


def _segments(layout):
    segs = []
    for pts in (layout or {}).get("wires", []):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            segs.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
    return segs


def wire_wire_overlaps(layout):
    """R2: 같은 축에서 포개지는 배선 쌍."""
    segs = _segments(layout)
    bad = []
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            a, b = segs[i], segs[j]
            if a[1] == a[3] == b[1] == b[3]:  # 둘 다 수평, 같은 y
                lo, hi = max(a[0], b[0]), min(a[2], b[2])
                if hi - lo > EPS:
                    bad.append(f"수평 y={a[1]:g} 구간 [{lo:g},{hi:g}] 겹침")
            elif a[0] == a[2] == b[0] == b[2]:  # 둘 다 수직, 같은 x
                lo, hi = max(a[1], b[1]), min(a[3], b[3])
                if hi - lo > EPS:
                    bad.append(f"수직 x={a[0]:g} 구간 [{lo:g},{hi:g}] 겹침")
    return bad


def _body_bbox(sym_blk):
    """심볼 그래픽(핀 제외) 범위 — 라이브러리 좌표(Y 위)."""
    # 핀 블록 제거
    depth = 0
    out = []
    i = 0
    text = sym_blk
    while i < len(text):
        m = re.search(r"[(]pin\s", text[i:])
        if not m:
            out.append(text[i:])
            break
        start = i + m.start()
        out.append(text[i:start])
        d, j, instr = 0, start, False
        while j < len(text):
            c = text[j]
            if instr:
                if c == '"' and text[j - 1] != chr(92):
                    instr = False
            elif c == '"':
                instr = True
            elif c == "(":
                d += 1
            elif c == ")":
                d -= 1
                if d == 0:
                    break
            j += 1
        i = j + 1
    g = "".join(out)
    xs, ys = [], []
    for mm in re.finditer(r"[(](?:xy|start|end|center)\s+([-\d.]+)\s+([-\d.]+)[)]", g):
        xs.append(float(mm.group(1)))
        ys.append(float(mm.group(2)))
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


MARGIN = 1.27  # R8: 배선-몸체 최소 여백 (핀 길이 1칸)
MIN_PARALLEL = 2.54  # R9: 평행 배선 최소 간격 (1그리드)


def parallel_too_close(layout):
    """R9: 평행 배선이 2.54mm 미만 간격으로 나란히 달리는 쌍."""
    segs = _segments(layout)
    bad = []
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            a, b = segs[i], segs[j]
            if a[1] == a[3] and b[1] == b[3]:            # 둘 다 수평
                gap = abs(a[1] - b[1])
                run = min(a[2], b[2]) - max(a[0], b[0])  # 나란한 구간 길이
            elif a[0] == a[2] and b[0] == b[2]:          # 둘 다 수직
                gap = abs(a[0] - b[0])
                run = min(a[3], b[3]) - max(a[1], b[1])
            else:
                continue
            if 0 < gap < MIN_PARALLEL - EPS and run > EPS:
                bad.append(f"평행 간격 {gap:g}mm < 2.54 (나란히 {run:g}mm)")
    return bad


def rot_corners(bb, X, Y, rot):
    corners = []
    for px, py in ((bb[0], bb[1]), (bb[0], bb[3]), (bb[2], bb[1]), (bb[2], bb[3])):
        c, s = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[rot % 360]
        rx, ry = px * c - py * s, px * s + py * c
        corners.append((X + rx, Y - ry))
    return (min(c[0] for c in corners), min(c[1] for c in corners),
            max(c[0] for c in corners), max(c[1] for c in corners))


def text_outline_overlaps(svg_text, parts_geo):
    """R7: 글자가 심볼 외곽선(몸체 상자 4변)과 겹치는가."""
    boxes = _text_boxes(svg_text)
    bad = []
    for ref, X, Y, rot, bb in parts_geo:
        if not bb:
            continue
        x1, y1, x2, y2 = rot_corners(bb, X, Y, rot)
        edges = [(x1, y1, x2, y1), (x1, y2, x2, y2),
                 (x1, y1, x1, y2), (x2, y1, x2, y2)]
        for tx1, ty1, tx2, ty2, label in boxes:
            for ex1, ey1, ex2, ey2 in edges:
                ox = min(tx2, ex2 + EPS) - max(tx1, ex1 - EPS)
                oy = min(ty2, ey2 + EPS) - max(ty1, ey1 - EPS)
                if ox > EPS and oy > EPS:
                    bad.append(f"R7 '{label}'가 {ref} 외곽선과 겹침")
                    break
    return sorted(set(bad))


def wire_body_hits(layout, parts_geo):
    """R3: 배선이 심볼 몸체 내부를 지나는가.
    parts_geo: [(ref, X, Y, rot, bbox_lib)]"""
    segs = _segments(layout)
    bad = []
    for ref, X, Y, rot, bb in parts_geo:
        if not bb:
            continue
        bx1, by1, bx2, by2 = rot_corners(bb, X, Y, rot)
        # R8: 몸체 + 여백까지 금지 영역 (자기 핀 배선은 핀 길이만큼 밖에서
        # 끝나므로 여백 경계에 '닿기만' 하고 EPS 판정으로 통과)
        x1, y1 = bx1 - MARGIN + EPS, by1 - MARGIN + EPS
        x2, y2 = bx2 + MARGIN - EPS, by2 + MARGIN - EPS
        for sx1, sy1, sx2, sy2 in segs:
            if sx1 < x2 and sx2 > x1 and sy1 < y2 and sy2 > y1:
                bad.append(f"{ref} 몸체({x1:.1f},{y1:.1f})~({x2:.1f},{y2:.1f})를 "
                           f"배선 ({sx1:g},{sy1:g})-({sx2:g},{sy2:g})가 통과")
    return bad


def _text_boxes(svg_text):
    boxes = []
    for m in re.finditer(
            r'<text x="([-\d.]+)" y="([-\d.]+)"\s*[^>]*?textLength="([-\d.]+)"'
            r'[^>]*?font-size="([-\d.]+)"[^>]*?>([^<]*)</text>', svg_text):
        x, y, w, fs = (float(m.group(i)) for i in range(1, 5))
        label = m.group(5)
        anchor = "start"
        am = re.search(r'text-anchor="(\w+)"', m.group(0))
        if am:
            anchor = am.group(1)
        if anchor == "end":
            x1, x2 = x - w, x
        elif anchor == "middle":
            x1, x2 = x - w / 2, x + w / 2
        else:
            x1, x2 = x, x + w
        # 글자 상자: 기준선(y) 위로 폰트 높이만큼 — 커널 렌더에서 핀 번호가
        # 배선 위쪽에 살짝 떠 있는 정상 표기를 오탐하지 않도록 실측형 모델
        boxes.append((x1, y - fs, x2, y, label.strip()))
    return boxes


def text_overlaps(svg_text, layout):
    """R1(텍스트-텍스트) + R6(텍스트-배선)."""
    boxes = _text_boxes(svg_text)
    segs = _segments(layout)
    bad = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            # kicad-cli SVG는 같은 글자를 두 번 내보낸다 (겹침 아님 — 동일
            # 문자열이 거의 같은 자리면 렌더 중복으로 보고 건너뜀)
            if a[4] == b[4] and abs(a[0] - b[0]) < 0.35 and abs(a[1] - b[1]) < 0.35:
                continue
            ox = min(a[2], b[2]) - max(a[0], b[0])
            oy = min(a[3], b[3]) - max(a[1], b[1])
            if ox > EPS and oy > EPS:
                bad.append(f"R1 텍스트 겹침: '{a[4]}' x '{b[4]}'")
    for x1, y1, x2, y2, label in boxes:
        for sx1, sy1, sx2, sy2 in segs:
            ox = min(x2, sx2 + EPS) - max(x1, sx1 - EPS)
            oy = min(y2, sy2 + EPS) - max(y1, sy1 - EPS)
            if ox > EPS and oy > EPS:
                bad.append(f"R6 텍스트-배선 겹침: '{label}' @ "
                           f"배선 ({sx1:g},{sy1:g})-({sx2:g},{sy2:g})")
    return bad


def shunt_symmetry(layout, parts_geo):
    """R11: 수직 2핀 부품의 위/아래 배선 길이 차 ≤ 2.54 (상하 라인 중간 배치)."""
    segs = _segments(layout)
    bad = []
    for ref, X, Y, rot, bb in parts_geo:
        if rot % 180 != 90:
            continue
        vert = [s for s in segs if s[0] == s[2] == X]
        ups = [s[3] - s[1] for s in vert if s[3] <= Y - 2.5]
        downs = [s[3] - s[1] for s in vert if s[1] >= Y - 0.1]
        if ups and downs and abs(ups[0] - downs[0]) > 2.54 + EPS:
            bad.append(f"R11 {ref}: 위 배선 {ups[0]:g} vs 아래 {downs[0]:g} — 중간 배치 아님")
    return bad


def ref_value_row(b):
    """R12: 회전(수직) 수동소자의 ref/value가 같은 줄(y)인가."""
    bad = []
    lay = (b.get("layout") or {}).get("parts") or {}
    for part in b["parts"]:
        lp = lay.get(part["ref"]) or {}
        if "ref_at" in lp and "value_at" in lp:
            dx = abs(lp["ref_at"][0] - lp["value_at"][0])
            dy = lp["value_at"][1] - lp["ref_at"][1]
            if dx > EPS or not (0 < dy <= 2.54 + EPS):
                bad.append(f"R12 {part['ref']}: 참조기호 아래 좁은 행간으로 값이 오지 않음 "
                           f"(dx={dx:g}, dy={dy:g})")
    return bad


def gnd_rail_proximity(layout, parts_geo):
    """R13: 최하단 수평 배선(레일)이 최하단 부품 몸체에서 ≤ 7.62."""
    segs = [s for s in _segments(layout) if s[1] == s[3]]
    boxes = [rot_corners(bb, X, Y, rot) for _, X, Y, rot, bb in parts_geo if bb]
    if not segs or not boxes:
        return []
    rail_y = max(s[1] for s in segs)
    body_bot = max(bx[3] for bx in boxes)
    if rail_y - body_bot > 7.62 + EPS:
        return [f"R13 GND 레일 y={rail_y:g}가 최하단 부품({body_bot:.1f})에서 "
                f"{rail_y - body_bot:.1f}mm — 3그리드 초과"]
    return []


def ref_value_gap(b, svg_text):
    """R12 강화: 모든 부품의 참조기호-값 박스 간 거리 ≤ 2.54 (인접)."""
    boxes = _text_boxes(svg_text)
    bad = []
    for part in b["parts"]:
        rb = next((x for x in boxes if x[4] == part["ref"]), None)
        val = part.get("value")
        vbs = [x for x in boxes if val and x[4] == val]
        if not rb or not vbs:
            continue
        # 같은 값 문자열이 여러 부품에 있으므로 참조기호와 가장 가까운 상자와 짝
        def gap_of(vb):
            dx = max(0, max(rb[0], vb[0]) - min(rb[2], vb[2]))
            dy = max(0, max(rb[1], vb[1]) - min(rb[3], vb[3]))
            return (dx * dx + dy * dy) ** 0.5
        gap = min(gap_of(vb) for vb in vbs)
        if gap > 2.54 + EPS:
            bad.append(f"R12 {part['ref']}: 참조기호-값 간격 {gap:.1f}mm > 2.54 (인접 아님)")
    return bad
