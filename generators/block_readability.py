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


def wire_body_hits(layout, parts_geo):
    """R3: 배선이 심볼 몸체 내부를 지나는가.
    parts_geo: [(ref, X, Y, rot, bbox_lib)]"""
    segs = _segments(layout)
    bad = []
    for ref, X, Y, rot, bb in parts_geo:
        if not bb:
            continue
        corners = []
        for px, py in ((bb[0], bb[1]), (bb[0], bb[3]), (bb[2], bb[1]), (bb[2], bb[3])):
            c, s = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[rot % 360]
            rx, ry = px * c - py * s, px * s + py * c
            corners.append((X + rx, Y - ry))
        x1 = min(c[0] for c in corners) + EPS
        y1 = min(c[1] for c in corners) + EPS
        x2 = max(c[0] for c in corners) - EPS
        y2 = max(c[1] for c in corners) - EPS
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
