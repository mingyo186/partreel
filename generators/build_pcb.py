"""
PCB 초기화 (REQUIREMENTS §25 2단계) — 보드 회로도 → .kicad_pcb.

KiCad 동봉 파이썬(pcbnew)으로 실행해야 한다:
  "D:/Program Files/KiCad/10.0/bin/python.exe" generators/build_pcb.py boards/<id>

배치 규칙은 rules/pcb-layout.md (P1~P7, 사용자와 확정):
  P1 외곽 = 부품+배선 여유 최소, 용지 중앙 / P2 커넥터 가장자리, 삽입구 밖
  P3 디버그는 MCU 근처 / P4 층수 board.json 선언
  P6 가장자리 접면은 부품 meta(parameters.edge_face)가 근거, 실크=외곽 일치
  P7 기능 군집: 메인 IC 군집 중앙(IC 가운데+수동 사이드), 블록 군집 사방
     밀착, 빈공간 최소화

배선은 하지 않는다 — 게이트는 check_board.py E (kicad-cli pcb drc,
unconnected_items만 허용).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
KICAD_CLI = os.environ.get(
    "KICAD_CLI", r"D:\Program Files\KiCad\10.0\bin\kicad-cli.exe")

import pcbnew  # noqa: E402  (KiCad 파이썬 전용)

MARGIN = 1.0     # 부품 간 여백 (mm)
GAP = 2.0        # 군집 간 여백 (배선 지나갈 폭)
EDGE = 2.0       # 외곽선-부품 여백
# KiCad 회전(화면 반시계) — 삽입구 방향을 -x(왼쪽 밖)로 보내는 각 (실측 검증)
FACE_TO_LEFT = {"+y": 270, "-y": 90, "+x": 180, "-x": 0}


def mm(v):
    return pcbnew.FromMM(v)


def netlist(board_dir, bid):
    out = os.path.join(tempfile.mkdtemp(prefix="pcb_"), "net.xml")
    r = subprocess.run([KICAD_CLI, "sch", "export", "netlist", "--format",
                       "kicadxml", "--output", out,
                       os.path.join(board_dir, f"{bid}.kicad_sch")],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
    if not os.path.exists(out):
        raise SystemExit(f"FAIL: 넷리스트 실패 — {(r.stdout + r.stderr)[-200:]}")
    return ET.parse(out).getroot()


def catalog():
    idx = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    return {p["id"]: os.path.join(ROOT, p["path"]) for p in idx["parts"]}


def body_bb(fp):
    bb = fp.GetBoundingBox(False, False)
    return (pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
            pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()))


def move_center(fp, cx, cy):
    """몸체(글자 제외) 중심을 (cx, cy)로."""
    x1, y1, x2, y2 = body_bb(fp)
    p = fp.GetPosition()
    fp.SetPosition(pcbnew.VECTOR2I(p.x + mm(cx - (x1 + x2) / 2),
                                   p.y + mm(cy - (y1 + y2) / 2)))


def silk_min_x(fp):
    """실크 그래픽의 왼쪽 끝 (P6: 실크=외곽 일치 스냅용). 없으면 몸체."""
    xs = []
    for g in fp.GraphicalItems():
        if g.GetLayer() == pcbnew.F_SilkS:
            xs.append(pcbnew.ToMM(g.GetBoundingBox().GetLeft()))
    return min(xs) if xs else body_bb(fp)[0]


def pack_main_ic(items):
    """P7: 메인 IC 가운데 + 수동소자를 좌우 열로 번갈아. items=(ref,fp,w,h)
    면적 내림차순. 반환: [(fp, cx, cy)] 로컬 중심좌표."""
    main = items[0]
    out = [(main[1], 0.0, 0.0)]
    mw, mh = main[2], main[3]
    state = {1: {"x": mw / 2 + MARGIN, "y": -mh / 2, "w": 0.0},
             -1: {"x": -mw / 2 - MARGIN, "y": -mh / 2, "w": 0.0}}
    side = 1
    for ref, fp, w, h in items[1:]:
        s = state[side]
        if s["y"] + h > mh / 2 + 0.1:
            o = state[-side]
            if o["y"] + h <= mh / 2 + 0.1:
                side = -side
                s = o
            else:  # 양쪽 다 참 — 이 변에 새 열
                s["x"] += (s["w"] + MARGIN) * side
                s["y"], s["w"] = -mh / 2, 0.0
        out.append((fp, s["x"] + (w / 2) * side, s["y"] + h / 2))
        s["y"] += h + MARGIN
        s["w"] = max(s["w"], w)
        side = -side
    return out


def pack_wrap(items, hmax):
    """단순 세로 감기 배치. 반환 [(fp, cx, cy)] (좌상 기준 0,0)."""
    out = []
    x0 = y = colw = 0.0
    for ref, fp, w, h in items:
        if y > 0 and y + h > hmax:
            x0 += colw + MARGIN
            y, colw = 0.0, 0.0
        out.append((fp, x0 + w / 2, y + h / 2))
        y += h + MARGIN
        colw = max(colw, w)
    return out


def cluster_bbox(pos):
    xs1 = [c - f_w(fp) / 2 for fp, c, _ in pos]
    xs2 = [c + f_w(fp) / 2 for fp, c, _ in pos]
    ys1 = [c - f_h(fp) / 2 for fp, _, c in pos]
    ys2 = [c + f_h(fp) / 2 for fp, _, c in pos]
    return min(xs1), min(ys1), max(xs2), max(ys2)


def f_w(fp):
    x1, _, x2, _ = body_bb(fp)
    return x2 - x1


def f_h(fp):
    _, y1, _, y2 = body_bb(fp)
    return y2 - y1


def build(board_dir):
    bid = os.path.basename(os.path.normpath(board_dir))
    root = netlist(board_dir, bid)
    dirs = catalog()
    bd = json.load(open(os.path.join(board_dir, "board.json"), encoding="utf-8"))

    comps = []  # (ref, pid, block)
    for c in root.iter("comp"):
        ref = c.get("ref")
        pid = (c.findtext("footprint") or "").split(":", 1)[-1]
        sheet = c.find("sheetpath")
        block = (sheet.get("names", "/") if sheet is not None else "/").strip("/") or "root"
        comps.append((ref, pid, block))
    comps.sort(key=lambda t: (t[2], t[0]))

    pretty = os.path.join(tempfile.mkdtemp(prefix="pcblib_"), "PartReel.pretty")
    os.makedirs(pretty)
    metas = {}
    for _, pid, _ in comps:
        if pid not in dirs:
            raise SystemExit(f"FAIL: 풋프린트 '{pid}' 카탈로그에 없음")
        shutil.copy(os.path.join(dirs[pid], f"{pid}.kicad_mod"),
                    os.path.join(pretty, f"{pid}.kicad_mod"))
        if pid not in metas:
            metas[pid] = json.load(open(os.path.join(dirs[pid], "meta.json"),
                                        encoding="utf-8"))

    board = pcbnew.CreateEmptyBoard()
    board.SetCopperLayerCount(int(bd.get("layers", 2)))  # P4

    nets = {}
    for net in root.iter("net"):
        item = pcbnew.NETINFO_ITEM(board, net.get("name"))
        board.Add(item)
        nets[net.get("name")] = item
    pad_net = {}
    for net in root.iter("net"):
        for node in net.findall("node"):
            pad_net[(node.get("ref"), node.get("pin"))] = net.get("name")

    # 풋프린트 로드 + 회전(P6) + 블록별 군집 구성
    blocks = {}   # block -> [(ref, fp, w, h)]
    edge_fps = []  # (block, fp) — 실크=외곽 스냅 대상
    order = []
    for ref, pid, block in comps:
        fp = pcbnew.FootprintLoad(pretty, pid)
        if fp is None:
            raise SystemExit(f"FAIL: FootprintLoad 실패 '{pid}'")
        face = (metas[pid].get("parameters") or {}).get("edge_face")
        if face:
            fp.SetOrientationDegrees(FACE_TO_LEFT[face])
            edge_fps.append((block, fp))
        fp.SetReference(ref)
        fp.Reference().SetLayer(pcbnew.F_Fab)  # P5 후보: 초기화 REF는 Fab
        for pad in fp.Pads():
            key = (ref, pad.GetNumber())
            if key in pad_net:
                pad.SetNet(nets[pad_net[key]])
        board.Add(fp)
        if block not in blocks:
            blocks[block] = []
            order.append(block)
        blocks[block].append((ref, fp, f_w(fp), f_h(fp)))

    # 메인 군집 = 가장 핀 많은 부품이 속한 블록 (MCU)
    def max_pads(blk):
        return max(fp.Pads().size() if hasattr(fp.Pads(), "size") else len(list(fp.Pads()))
                   for _, fp, _, _ in blocks[blk])
    main_block = max(order, key=max_pads)

    # 군집 내부 배치 (로컬 좌표)
    placed_local = {}  # block -> [(fp, cx, cy)]
    for blk in order:
        items = sorted(blocks[blk], key=lambda t: -(t[2] * t[3]))
        if blk == main_block and len(items) >= 4:
            placed_local[blk] = pack_main_ic(items)
        else:
            hmax = max(12.0, max(h for _, _, _, h in items))
            placed_local[blk] = pack_wrap(items, hmax)

    def local_bbox(blk):
        pos = placed_local[blk]
        x1 = min(c - f_w(fp) / 2 for fp, c, _ in pos)
        x2 = max(c + f_w(fp) / 2 for fp, c, _ in pos)
        y1 = min(cy - f_h(fp) / 2 for fp, _, cy in pos)
        y2 = max(cy + f_h(fp) / 2 for fp, _, cy in pos)
        return x1, y1, x2, y2

    # 군집 배치: 메인 중앙, 가장자리 군집은 왼쪽/오른쪽 변, 나머지 사방 (P7)
    CX, CY = 148.5, 105.0  # A4 중앙
    offsets = {main_block: (0.0, 0.0)}
    edge_blocks = [b for b, _ in edge_fps]
    others = [b for b in order if b != main_block]
    sides = {}
    side_seq = ["left", "right", "bottom", "top"]
    for b in others:
        if b in edge_blocks and "left" not in sides.values():
            sides[b] = "left"
        else:
            for s in side_seq:
                if s not in sides.values():
                    sides[b] = s
                    break
            else:
                sides[b] = "bottom"
    mx1, my1, mx2, my2 = local_bbox(main_block)
    for b in others:
        x1, y1, x2, y2 = local_bbox(b)
        s = sides[b]
        if s == "left":
            offsets[b] = (mx1 - GAP - x2, (my1 + my2) / 2 - (y1 + y2) / 2)
        elif s == "right":
            offsets[b] = (mx2 + GAP - x1, (my1 + my2) / 2 - (y1 + y2) / 2)
        elif s == "bottom":
            offsets[b] = ((mx1 + mx2) / 2 - (x1 + x2) / 2, my2 + GAP - y1)
        else:
            offsets[b] = ((mx1 + mx2) / 2 - (x1 + x2) / 2, my1 - GAP - y2)

    # 절대 배치 (일단 원점 기준) 후 전체 범위 산출
    for blk in order:
        ox, oy = offsets[blk]
        for fp, cx, cy in placed_local[blk]:
            move_center(fp, ox + cx, oy + cy)
    all_fp = [fp for blk in order for fp, _, _ in placed_local[blk]]
    ex1 = min(body_bb(fp)[0] for fp in all_fp)
    ey1 = min(body_bb(fp)[1] for fp in all_fp)
    ex2 = max(body_bb(fp)[2] for fp in all_fp)
    ey2 = max(body_bb(fp)[3] for fp in all_fp)

    # P6: 가장자리 부품의 실크 왼끝 = 외곽 왼변 (그 변은 여백 0)
    flush_x = min((silk_min_x(fp) for _, fp in edge_fps), default=None)
    x1 = flush_x if flush_x is not None else ex1 - EDGE
    y1, x2, y2 = ey1 - EDGE, ex2 + EDGE, ey2 + EDGE

    # 용지 중앙으로 평행이동 (P1)
    dx, dy = CX - (x1 + x2) / 2, CY - (y1 + y2) / 2
    for fp in all_fp:
        p = fp.GetPosition()
        fp.SetPosition(pcbnew.VECTOR2I(p.x + mm(dx), p.y + mm(dy)))
    x1, x2, y1, y2 = x1 + dx, x2 + dx, y1 + dy, y2 + dy

    rect = pcbnew.PCB_SHAPE(board)
    rect.SetShape(pcbnew.SHAPE_T_RECT)
    rect.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    rect.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    rect.SetLayer(pcbnew.Edge_Cuts)
    rect.SetWidth(mm(0.1))
    board.Add(rect)

    out = os.path.join(board_dir, f"{bid}.kicad_pcb")
    board.Save(out)
    print(f"OK  {bid}: 부품 {len(comps)} / 네트 {len(nets)} / "
          f"{bd.get('layers', 2)}층 / 외곽 {x2 - x1:.0f}x{y2 - y1:.0f}mm "
          f"(메인 군집: {main_block.split()[0]}) -> {out}")
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    for t in sys.argv[1:]:
        build(os.path.join(ROOT, t) if not os.path.isabs(t) else t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
