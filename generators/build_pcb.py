"""
PCB 초기화 (REQUIREMENTS §25 2단계 첫 걸음) — 보드 회로도 → .kicad_pcb.

KiCad 동봉 파이썬(pcbnew)으로 실행해야 한다:
  "D:/Program Files/KiCad/10.0/bin/python.exe" generators/build_pcb.py boards/<id>

하는 일:
  1. kicad-cli로 회로도 넷리스트(kicadxml) 추출
  2. 부품마다 파트릴 풋프린트를 불러와 **블록(시트) 단위로 묶어** 격자 배치
     (§25: "블록 단위 배치 보조 — 전원부 모아두기")
  3. 네트 생성 + 패드 연결 (넷리스트 그대로)
  4. Edge.Cuts 외곽 사각형 + 저장

배선은 하지 않는다 — 초기화 산출물은 "부품이 올라가고 랫츠네스트가 걸린
보드"다. 게이트는 check_board.py의 E 단계(kicad-cli pcb drc,
unconnected_items만 허용)가 판정한다.
"""

import json
import os
import re
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

MARGIN = 3.0       # 부품 간 여백 (mm)
BLOCK_GAP = 6.0    # 블록 묶음 간 여백
EDGE = 4.0         # 외곽선 여백


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


def part_dirs():
    idx = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    return {p["id"]: os.path.join(ROOT, p["path"]) for p in idx["parts"]}


def build(board_dir):
    bid = os.path.basename(os.path.normpath(board_dir))
    root = netlist(board_dir, bid)
    dirs = part_dirs()

    comps = []  # (ref, pid, block_name)
    for c in root.iter("comp"):
        ref = c.get("ref")
        fp = (c.findtext("footprint") or "")
        pid = fp.split(":", 1)[-1]
        sheet = c.find("sheetpath")
        block = (sheet.get("names", "/") if sheet is not None else "/").strip("/") or "root"
        comps.append((ref, pid, block))
    comps.sort(key=lambda t: (t[2], t[0]))

    # 풋프린트는 .pretty 폴더에서만 로드된다 — 임시 라이브러리로 모아 복사
    pretty = os.path.join(tempfile.mkdtemp(prefix="pcblib_"), "PartReel.pretty")
    os.makedirs(pretty)
    for _, pid, _ in comps:
        if pid not in dirs:
            raise SystemExit(f"FAIL: 풋프린트 '{pid}' 카탈로그에 없음")
        shutil.copy(os.path.join(dirs[pid], f"{pid}.kicad_mod"),
                    os.path.join(pretty, f"{pid}.kicad_mod"))

    board = pcbnew.CreateEmptyBoard()

    # 네트 등록
    nets = {}
    for net in root.iter("net"):
        name = net.get("name")
        item = pcbnew.NETINFO_ITEM(board, name)
        board.Add(item)
        nets[name] = item
    pad_net = {}
    for net in root.iter("net"):
        for node in net.findall("node"):
            pad_net[(node.get("ref"), node.get("pin"))] = net.get("name")

    # 블록 단위 격자 배치: 블록 = 열, 부품 = 열 안에서 아래로
    x_cursor = EDGE + 8.0
    max_y = 0.0
    cur_block, col_w, y_cursor, x0 = None, 0.0, 0.0, 0.0
    for ref, pid, block in comps:
        fp = pcbnew.FootprintLoad(pretty, pid)
        if fp is None:
            raise SystemExit(f"FAIL: FootprintLoad 실패 '{pid}'")
        if block != cur_block:
            x_cursor += (col_w + BLOCK_GAP) if cur_block else 0.0
            cur_block, col_w, y_cursor, x0 = block, 0.0, EDGE + 8.0, x_cursor
        bb = fp.GetBoundingBox()
        w = pcbnew.ToMM(bb.GetWidth())
        h = pcbnew.ToMM(bb.GetHeight())
        fp.SetReference(ref)
        fp.SetPosition(pcbnew.VECTOR2I(mm(x0 + w / 2), mm(y_cursor + h / 2)))
        for pad in fp.Pads():
            key = (ref, pad.GetNumber())
            if key in pad_net:
                pad.SetNet(nets[pad_net[key]])
        board.Add(fp)
        y_cursor += h + MARGIN
        col_w = max(col_w, w)
        max_y = max(max_y, y_cursor)
    x_end = x_cursor + col_w

    # Edge.Cuts 외곽 (DRC는 외곽 없는 보드를 거부한다)
    rect = pcbnew.PCB_SHAPE(board)
    rect.SetShape(pcbnew.SHAPE_T_RECT)
    rect.SetStart(pcbnew.VECTOR2I(mm(EDGE), mm(EDGE)))
    rect.SetEnd(pcbnew.VECTOR2I(mm(x_end + EDGE), mm(max_y + EDGE)))
    rect.SetLayer(pcbnew.Edge_Cuts)
    rect.SetWidth(mm(0.1))
    board.Add(rect)

    out = os.path.join(board_dir, f"{bid}.kicad_pcb")
    board.Save(out)
    print(f"OK  {bid}: 부품 {len(comps)} / 네트 {len(nets)} / "
          f"외곽 {x_end + EDGE:.0f}x{max_y + EDGE:.0f}mm -> {out}")
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
