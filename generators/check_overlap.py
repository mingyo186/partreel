"""
SVG 텍스트 겹침 검출기 (심볼 핀 이름/번호가 서로/겹치는지).
실행: python generators/check_overlap.py
스크린샷 없이 텍스트 bbox 충돌을 계산해 검사. 겹치면 비0 종료(빌드 게이트 가능).
"""
import os
import re
import sys
import glob

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
TEXT_RE = re.compile(
    r'<text x="([-\d.]+)" y="([-\d.]+)"[^>]*?font-size="([\d.]+)"[^>]*?'
    r'text-anchor="(\w+)"[^>]*?>([^<]*)</text>')
TOL = 0.15  # mm, 살짝 닿는 건 허용


def bbox(x, y, fs, anchor, txt):
    w = max(len(txt), 1) * fs * 0.62
    if anchor == "middle":
        x0 = x - w / 2
    elif anchor == "end":
        x0 = x - w
    else:
        x0 = x
    return (x0, y - fs * 0.78, x0 + w, y + fs * 0.22, txt)


def overlaps(a, b):
    return (a[0] < b[2] - TOL and a[2] > b[0] + TOL
            and a[1] < b[3] - TOL and a[3] > b[1] + TOL)


G_RE = re.compile(r'<g transform="translate\(([-\d.]+)\s+([-\d.]+)\)">|</g>')


def _segments(svg):
    """(조각, dx, dy) 목록 — 1단계 <g translate> 그룹만 지원(우리 렌더러 출력 형태)."""
    segs = []
    pos = 0
    dx = dy = 0.0
    for m in G_RE.finditer(svg):
        segs.append((svg[pos:m.start()], dx, dy))
        if m.group(0) == "</g>":
            dx = dy = 0.0
        else:
            dx, dy = float(m.group(1)), float(m.group(2))
        pos = m.end()
    segs.append((svg[pos:], dx, dy))
    return segs


def main():
    files = glob.glob(os.path.join(ROOT, "library", "**", "*.symbol.svg"), recursive=True)
    files += glob.glob(os.path.join(ROOT, "library", "**", "*.footprint.svg"), recursive=True)
    total = 0
    for f in sorted(files):
        svg = open(f, encoding="utf-8").read()
        # <g transform="translate(dx dy)"> 오프셋 반영 (멀티유닛 심볼)
        boxes = []
        for seg, dx, dy in _segments(svg):
            boxes += [bbox(float(m[0]) + dx, float(m[1]) + dy,
                           float(m[2]), m[3], m[4])
                      for m in TEXT_RE.findall(seg)]
        hits = []
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                if overlaps(boxes[i], boxes[j]):
                    hits.append((boxes[i][4], boxes[j][4]))
        name = os.path.relpath(f, ROOT).replace("\\", "/")
        if hits:
            total += len(hits)
            print(f"OVERLAP {name}:")
            for a, b in hits[:8]:
                print(f"   '{a}' <-> '{b}'")
        # else: 조용히 통과
    print(f"\n{'PASS' if total == 0 else 'FAIL'}: {len(files)} SVGs, {total} overlaps")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
