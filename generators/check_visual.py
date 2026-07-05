"""
시각 품질 자동검수 (REQUIREMENTS §16 — "사용자가 일일이 지적하기 전에 기계가").
렌더된 SVG의 기하 이상을 휴리스틱으로 검출:

  V1 뷰박스 퇴화/극단 종횡비  (그림이 찌그러져 보이는 클래스)      → FAIL
  V2 미아 요소: 패드 무리에서 비정상적으로 멀리 떨어진 도형        → WARN
  V3 심볼 텍스트가 뷰박스 밖으로 넘침 (라벨 잘림 클래스)           → WARN
  V4 그릴 게 없는 풋프린트 (패드만 있고 외곽 요소 0)               → WARN

FAIL은 비0 종료(게이트), WARN은 docs/visual-audit-report.json에 기록만.
실행: python generators/check_visual.py
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

VB_RE = re.compile(r'viewBox="([-\d. ]+)"')
LINE_RE = re.compile(r'<line x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"')
CIRC_RE = re.compile(r'<circle cx="([-\d.]+)" cy="([-\d.]+)" r="([-\d.]+)"[^>]*?(?:fill="([^"]*)")?')
RECT_RE = re.compile(r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([-\d.]+)" height="([-\d.]+)"[^>]*?fill="([^"]*)"')
TEXT_RE = re.compile(r'<text x="([-\d.]+)" y="([-\d.]+)"[^>]*?font-size="([\d.]+)"[^>]*?'
                     r'text-anchor="(\w+)"[^>]*?>([^<]*)</text>')
COPPER = "#c79b5c"


def fp_checks(svg):
    errs, warns = [], []
    m = VB_RE.search(svg)
    if not m:
        return ["뷰박스 없음"], warns
    vx, vy, vw, vh = map(float, m.group(1).split())
    if vw <= 0 or vh <= 0:
        errs.append(f"뷰박스 퇴화 ({vw}x{vh})")
        return errs, warns
    ratio = max(vw / vh, vh / vw)
    if ratio > 30:
        errs.append(f"극단 종횡비 {ratio:.0f}:1 (미아 요소로 뷰박스 폭발 의심)")
    # 구리(패드) 무리 bbox
    pads = []
    for mm in RECT_RE.finditer(svg):
        if mm.group(5) == COPPER:
            x, y, w, h = map(float, mm.groups()[:4])
            pads.append((x, y, x + w, y + h))
    for mm in CIRC_RE.finditer(svg):
        if mm.group(4) == COPPER:
            x, y, r = map(float, mm.groups()[:3])
            pads.append((x - r, y - r, x + r, y + r))
    outline_n = svg.count("<line") + svg.count("<path") + svg.count("<polygon")
    if pads:
        px0 = min(p[0] for p in pads); py0 = min(p[1] for p in pads)
        px1 = max(p[2] for p in pads); py1 = max(p[3] for p in pads)
        diag = ((px1 - px0) ** 2 + (py1 - py0) ** 2) ** 0.5 or 1.0
        cx, cy = (px0 + px1) / 2, (py0 + py1) / 2
        far = 0
        for mm in LINE_RE.finditer(svg):
            x1, y1, x2, y2 = map(float, mm.groups())
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            if ((mx - cx) ** 2 + (my - cy) ** 2) ** 0.5 > 4 * diag:
                far += 1
        if far:
            warns.append(f"패드 무리에서 4x 대각선 밖 선분 {far}개 (미아 좌표 의심)")
        if outline_n <= 4:  # 자동 코트야드 4선뿐 = 외곽 정보 전무
            warns.append("외곽 요소가 코트야드뿐 (몸체 윤곽 없음)")
    return errs, warns


def sym_checks(svg):
    errs, warns = [], []
    m = VB_RE.search(svg)
    if not m:
        return ["뷰박스 없음"], warns
    vx, vy, vw, vh = map(float, m.group(1).split())
    if vw <= 0 or vh <= 0:
        return [f"뷰박스 퇴화 ({vw}x{vh})"], warns
    over = 0
    from check_overlap import _segments  # <g translate> 오프셋 인지 (멀티유닛)
    for seg, dx, dy in _segments(svg):
      for mm in TEXT_RE.finditer(seg):
        x, y, fs = float(mm.group(1)) + dx, float(mm.group(2)) + dy, float(mm.group(3))
        anchor, txt = mm.group(4), mm.group(5)
        w = max(len(txt), 1) * fs * 0.62
        x0 = x - w / 2 if anchor == "middle" else x - w if anchor == "end" else x
        if x0 < vx - 2 or x0 + w > vx + vw + 2 or y < vy - 2 or y > vy + vh + 2:
            over += 1
    if over:
        warns.append(f"뷰박스 밖 텍스트 {over}개 (라벨 잘림 의심)")
    return errs, warns


def main():
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    fails = 0
    report = {}
    for p in index["parts"]:
        d = os.path.join(ROOT, p["path"])
        fid = p["id"]
        entry = []
        for suf, fn in (("fp", f"{fid}.footprint.svg"), ("sym", f"{fid}.symbol.svg")):
            path = os.path.join(d, fn)
            if not os.path.exists(path):
                continue
            svg = open(path, encoding="utf-8").read()
            errs, warns = (fp_checks if suf == "fp" else sym_checks)(svg)
            for e in errs:
                print(f"FAIL {fid} [{suf}]: {e}")
                fails += 1
            entry += [f"[{suf}] {w}" for w in warns]
        if entry:
            report[fid] = entry
    out = os.path.join(ROOT, "docs", "visual-audit-report.json")
    json.dump(report, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{'PASS' if not fails else 'FAIL'}: {len(index['parts'])} parts, "
          f"{fails} fails, {len(report)} warned -> docs/visual-audit-report.json")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
