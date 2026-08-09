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

import glob as globmod
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

MARGIN = 0.6     # 부품 간 여백 — 선 1가닥 + 클리어런스 (P11)
GAP = 2.0        # 군집 간 여백 (배선 지나갈 폭)
EDGE = 2.0       # 외곽선-부품 여백
REF_W = 2.6      # P5: 소형 부품 옆 실크 REF 자리 (열 폭에 예약)
# KiCad 회전각 a의 좌표 변환 (실측 검증: 270이 -y를 +x로 보냄)
ROT = {0: lambda x, y: (x, y), 90: lambda x, y: (y, -x),
       180: lambda x, y: (-x, -y), 270: lambda x, y: (-y, x)}
FACE_VEC = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}
OUTWARD = {"left": (-1, 0), "right": (1, 0), "top": (0, -1), "bottom": (0, 1)}


def face_rotation(face, side):
    """edge_face 방향을 side의 바깥 방향으로 보내는 KiCad 회전각 (P6+P8)."""
    fx, fy = FACE_VEC[face]
    for a, f in ROT.items():
        if f(fx, fy) == OUTWARD[side]:
            return a
    return 0


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


def pack_main_ic(items, hints=None):
    """P7+P10: 메인 IC 가운데 + 수동소자를 좌우 열로. items=(ref,fp,w,h)
    면적 내림차순. hints[ref] = (선호변 ±1|None, 정렬 y) — 신호 부품은
    물린 핀의 변·순서대로(P10), 전원 전용은 빈 쪽 채움(P9).
    반환: [(fp, cx, cy)] 로컬 중심좌표."""
    hints = hints or {}
    main = items[0]
    out = [(main[1], 0.0, 0.0)]
    mw, mh = main[2], main[3]
    state = {1: {"x": mw / 2 + MARGIN, "y": -mh / 2, "w": 0.0},
             -1: {"x": -mw / 2 - MARGIN, "y": -mh / 2, "w": 0.0}}

    def put(side, ref, fp, w, h):
        s = state[side]
        if s["y"] + h > mh / 2 + 0.1:
            o = state[-side]
            if hints.get(ref, (None,))[0] is None and o["y"] + h <= mh / 2 + 0.1:
                side = -side
                s = o
            else:
                s["x"] += (s["w"] + MARGIN) * side
                s["y"], s["w"] = -mh / 2, 0.0
        out.append((fp, s["x"] + (w / 2) * side, s["y"] + h / 2))
        s["y"] += h + MARGIN
        s["w"] = max(s["w"], w + REF_W)  # P5: 옆 REF 자리 예약

    rest = items[1:]
    # 1) 신호 부품: 물린 핀의 변에, 핀 y 순서대로 (P10 꼬임 방지)
    sig = sorted((it for it in rest if hints.get(it[0], (None,))[0] is not None),
                 key=lambda it: hints[it[0]][1])
    for ref, fp, w, h in sig:
        put(hints[ref][0], ref, fp, w, h)
    # 2) 전원 전용: 양쪽 잔여 공간을 번갈아 채움 (P9)
    side = 1
    for ref, fp, w, h in (it for it in rest if hints.get(it[0], (None,))[0] is None):
        if state[side]["y"] > state[-side]["y"]:
            side = -side
        put(side, ref, fp, w, h)
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
        # 소형 부품은 옆 REF 자리 예약 (P5); 대형은 몸체 위 REF라 불필요
        colw = max(colw, w + (REF_W if h < 4.0 else 0.0))
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

    # 풋프린트 로드 + 블록별 군집 구성 (회전은 변 결정 후 — P8)
    blocks = {}   # block -> [(ref, pid, fp)]
    order = []
    for ref, pid, block in comps:
        fp = pcbnew.FootprintLoad(pretty, pid)
        if fp is None:
            raise SystemExit(f"FAIL: FootprintLoad 실패 '{pid}'")
        fp.SetReference(ref)
        for pad in fp.Pads():
            key = (ref, pad.GetNumber())
            if key in pad_net:
                pad.SetNet(nets[pad_net[key]])
        board.Add(fp)
        if block not in blocks:
            blocks[block] = []
            order.append(block)
        blocks[block].append((ref, pid, fp))

    # 메인 군집 = 가장 핀 많은 부품(MCU)이 속한 블록
    def pad_count(fp):
        return len(list(fp.Pads()))
    main_block = max(order, key=lambda b: max(pad_count(fp) for _, _, fp in blocks[b]))
    mcu_fp = max((fp for _, _, fp in blocks[main_block]), key=pad_count)

    # P15: 메인 IC 방향은 보드 선언 (orient: {"B3.U1": 90}) — 회전 후 핀
    # 변을 다시 계산하므로 군집 투표(P8)·근접 배치(P13)가 전부 따라온다.
    ref_map_pre = {}
    rmp0 = os.path.join(board_dir, "ref_map.json")
    if os.path.exists(rmp0):
        ref_map_pre = json.load(open(rmp0, encoding="utf-8"))
    for key, deg in (bd.get("orient") or {}).items():
        board_ref = ref_map_pre.get(key, key.split(".", 1)[-1])
        for blk in order:
            for ref, _, fp in blocks[blk]:
                if ref == board_ref:
                    fp.SetOrientationDegrees(int(deg))

    # P8: MCU 패드의 변(좌/우/상/하) — 네트별로 기록 (전원 네트 제외)
    def is_power(name):
        return name.startswith("+") or name == "GND"
    mx1b, my1b, mx2b, my2b = body_bb(mcu_fp)
    mcx, mcy = (mx1b + mx2b) / 2, (my1b + my2b) / 2
    net_side = {}
    for pad in mcu_fp.Pads():
        name = pad.GetNetname()
        if not name or is_power(name):
            continue
        px, py = pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)
        dx, dy = px - mcx, py - mcy
        side = ("left" if dx < 0 else "right") if abs(dx) > abs(dy) else \
               ("top" if dy < 0 else "bottom")
        net_side[name] = side
    TIE = ["right", "top", "left", "bottom"]

    def net_pad_avg(fp):
        """이 부품의 신호 네트가 물린 MCU 패드들의 평균 좌표 (P10 정렬용)."""
        pts = []
        for pad in fp.Pads():
            n = pad.GetNetname()
            if not n or is_power(n):
                continue
            for mp in mcu_fp.Pads():
                if mp.GetNetname() == n:
                    pts.append((pcbnew.ToMM(mp.GetPosition().x),
                                pcbnew.ToMM(mp.GetPosition().y)))
        if not pts:
            return None
        return (sum(p[0] for p in pts) / len(pts),
                sum(p[1] for p in pts) / len(pts))

    def vote_side(blk):
        votes = {}
        for _, _, fp in blocks[blk]:
            for pad in fp.Pads():
                s = net_side.get(pad.GetNetname())
                if s:
                    votes[s] = votes.get(s, 0) + 1
        if not votes:
            return None
        best = max(votes.values())
        return next(s for s in TIE if votes.get(s, 0) == best)

    others = [b for b in order if b != main_block]
    sides = {}
    for b in others:
        sides[b] = vote_side(b)
    # P14: 전원 사슬 — 변환기(신호 연고 없음)는 자기 입력 전원의 공급원
    # 군집 옆에. 블록 선언으로 판단: 깃발(layout.power flag) = 공급원,
    # power_in = 소비.
    producers = {}  # 전원넷 -> block key
    consumers = {}  # block key -> [전원넷]
    bref_of = {}
    for inst in bd.get("blocks", []):
        hits = globmod.glob(os.path.join(ROOT, "blocks", "*", inst["block"], "block.json"))
        if not hits:
            continue
        bj = json.load(open(hits[0], encoding="utf-8"))
        blk_key = next((k for k in order if k.split()[0] == inst["ref"]), None)
        if blk_key is None:
            continue
        bref_of[blk_key] = inst["ref"]
        for pw in (bj.get("layout") or {}).get("power", []):
            if pw.get("symbol") == "flag":
                producers.setdefault(pw.get("net"), blk_key)
        consumers[blk_key] = bj.get("power_in", [])
    chain_avg = {}
    for b in others:
        if sides[b] is None:
            for net in consumers.get(b, []):
                src = producers.get(net)
                if src and src != b and sides.get(src):
                    sides[b] = sides[src]
                    chain_avg[b] = src  # 옆에 서도록 정렬 키 공유
                    break
    used = [s for s in sides.values() if s]
    for b in others:  # 그래도 못 정한 군집은 빈 변부터
        if sides[b] is None:
            sides[b] = next((s for s in TIE if s not in used), "left")
            used.append(sides[b])

    # P6+P8: 가장자리 부품은 자기 군집 변의 바깥으로 삽입구 회전
    edge_fps = []  # (side, fp)
    edge_ids = set()
    for blk in order:
        for _, pid, fp in blocks[blk]:
            face = (metas[pid].get("parameters") or {}).get("edge_face")
            if face:
                side = sides.get(blk) or "left"
                fp.SetOrientationDegrees(face_rotation(face, side))
                edge_fps.append((side, fp))
                edge_ids.add(id(fp))

    # P12: 신호 패드가 메인 IC를 향하는 회전 선택 (가장자리 부품 제외 —
    # 삽입구 방향(P6)이 우선). 0/90/180/270 중 신호 패드 무게중심 방향이
    # IC 방향과 가장 일치하는 각.
    TOWARD = {"top": (0, 1), "bottom": (0, -1), "left": (1, 0), "right": (-1, 0)}

    def orient_toward(fp, want):
        best, best_score = None, None
        for a in (0, 90, 180, 270):
            fp.SetOrientationDegrees(a)
            bb = fp.GetBoundingBox(False, False)
            cx = (bb.GetLeft() + bb.GetRight()) / 2
            cy = (bb.GetTop() + bb.GetBottom()) / 2
            pts = [(pad.GetPosition().x - cx, pad.GetPosition().y - cy)
                   for pad in fp.Pads()
                   if pad.GetNetname() and not is_power(pad.GetNetname())]
            if not pts:
                fp.SetOrientationDegrees(0)
                return
            dx = sum(p[0] for p in pts) / len(pts)
            dy = sum(p[1] for p in pts) / len(pts)
            norm = (dx * dx + dy * dy) ** 0.5 or 1.0
            score = (dx * want[0] + dy * want[1]) / norm
            if best_score is None or score > best_score:
                best, best_score = a, score
        fp.SetOrientationDegrees(best)

    for blk in order:
        if blk == main_block:
            continue
        want = TOWARD[sides[blk]]
        for _, pid, fp in blocks[blk]:
            if id(fp) not in edge_ids:
                orient_toward(fp, want)

    # === P13: place 지시 (block.json parts[].place) — "이 부품의 역할과
    # 자리"를 선언이 말해준다. near가 "<로컬ref>.<핀>"이면 그 핀 옆에 고정
    # 배치 (ref_map으로 보드 참조로 번역). near가 부품만("J1")이면 군집
    # 근접으로 충분해 통상 배치. ===
    ref_map = {}
    rmp = os.path.join(board_dir, "ref_map.json")
    if os.path.exists(rmp):
        ref_map = json.load(open(rmp, encoding="utf-8"))
    place_dir = {}  # 보드ref -> (대상 보드ref, 핀번호, 역할)
    for inst in bd.get("blocks", []):
        bref, blk_id = inst["ref"], inst["block"]
        hits = globmod.glob(os.path.join(ROOT, "blocks", "*", blk_id, "block.json"))
        if not hits:
            continue
        bj = json.load(open(hits[0], encoding="utf-8"))
        for part in bj.get("parts", []):
            pl = part.get("place")
            if not pl or "." not in str(pl.get("near", "")):
                continue
            tgt_local, pad_no = pl["near"].split(".", 1)
            my = ref_map.get(f"{bref}.{part['ref']}", part["ref"])
            tgt = ref_map.get(f"{bref}.{tgt_local}", tgt_local)
            place_dir[my] = (tgt, pad_no, pl.get("role", ""))

    def near_local_pos(fp_part, pad_no, taken):
        """MCU 핀 pad_no 옆 로컬 좌표 (MCU 몸체중심=원점). 연결 패드가 핀을
        향하게 회전, 겹치면 법선 방향으로 밀어냄. 반환 (cx, cy)."""
        tb = body_bb(mcu_fp)
        tcx, tcy = (tb[0] + tb[2]) / 2, (tb[1] + tb[3]) / 2
        tpad = next(p for p in mcu_fp.Pads() if p.GetNumber() == pad_no)
        px = pcbnew.ToMM(tpad.GetPosition().x) - tcx
        py = pcbnew.ToMM(tpad.GetPosition().y) - tcy
        if abs(px) > abs(py):
            n = (-1, 0) if px < 0 else (1, 0)
            angles = (0, 180)
        else:
            n = (0, -1) if py < 0 else (0, 1)
            angles = (90, 270)
        tnet = tpad.GetNetname()
        # 연결 패드(같은 네트)가 MCU 쪽(-n)으로 가는 각 선택
        pick = angles[0]
        for a in angles:
            fp_part.SetOrientationDegrees(a)
            b = body_bb(fp_part)
            ccx, ccy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            for pad in fp_part.Pads():
                if pad.GetNetname() == tnet:
                    ox = pcbnew.ToMM(pad.GetPosition().x) - ccx
                    oy = pcbnew.ToMM(pad.GetPosition().y) - ccy
                    if ox * n[0] + oy * n[1] < 0:
                        pick = a
                    break
        fp_part.SetOrientationDegrees(pick)
        b = body_bb(fp_part)
        w, h = b[2] - b[0], b[3] - b[1]
        half = w / 2 if n[0] else h / 2
        # 패드 크기는 회전을 안 따라온다(GetSize는 로컬) — bbox로 실측
        pbb = tpad.GetBoundingBox()
        phalf = pcbnew.ToMM(pbb.GetWidth() if n[0] else pbb.GetHeight()) / 2
        # 후보: 바깥(k_out) x 옆줄(k_lat) — 인접 핀 캡들은 변을 따라 나란히
        # 퍼진다 (바깥으로만 밀면 후보 소진 시 겹침 — 2026-08-10 C7/C8).
        tv = (-n[1], n[0])
        out_step = (h if n[1] else w) + MARGIN
        lat_step = (w if n[1] else h) + MARGIN
        base = phalf + half + 0.5
        for k_out in range(4):
            dist = base + k_out * out_step
            for k_lat in (0, -1, 1, -2, 2, -3, 3):
                cx = px + n[0] * dist + tv[0] * k_lat * lat_step
                cy = py + n[1] * dist + tv[1] * k_lat * lat_step
                box = (cx - w / 2 - MARGIN, cy - h / 2 - MARGIN,
                       cx + w / 2 + MARGIN, cy + h / 2 + MARGIN)
                if not any(box[0] < t[2] and box[2] > t[0] and
                           box[1] < t[3] and box[3] > t[1] for t in taken):
                    taken.append(box)
                    return cx, cy
        taken.append(box)
        return cx, cy

    # 군집 내부 배치 (로컬 좌표) — 회전 반영된 크기로.
    # 가장자리 부품은 자기 변의 최외곽 열에: 오른변이면 마지막 열(오른쪽),
    # 왼변이면 첫 열 — 아니면 소형 부품이 부품 뒤(보드 밖)로 감긴다
    # (2026-08-10 USB CC 저항 이탈로 확인).
    edge_set = {id(fp) for _, fp in edge_fps}
    placed_local = {}
    near_taken = []
    for blk in order:
        # P13 고정 배치 대상 분리 (대상이 메인 IC(mcu_fp)인 경우만 —
        # 다른 대상은 아직 미지원, 통상 배치로 폴백)
        fixed = []
        rest_items = []
        for ref, _, fp in blocks[blk]:
            tgt = place_dir.get(ref)
            if tgt and blk == main_block and fp is not mcu_fp:
                fixed.append((ref, fp, tgt[1]))
            else:
                rest_items.append((ref, fp))
        items = sorted(((ref, fp, f_w(fp), f_h(fp)) for ref, fp in rest_items),
                       key=lambda t: -(t[2] * t[3]))
        eside = sides.get(blk)
        edge_items = [it for it in items if id(it[1]) in edge_set]
        if edge_items and eside in ("right", "bottom"):
            items = [it for it in items if id(it[1]) not in edge_set] + edge_items
        elif edge_items:
            items = edge_items + [it for it in items if id(it[1]) not in edge_set]
        if fixed and blk == main_block:
            pos = []
            for ref, fp, pad_no in fixed:
                cx, cy = near_local_pos(fp, pad_no, near_taken)
                pos.append((fp, cx, cy))
            hints = {}
            for ref, _, fp in blocks[blk]:
                if fp is mcu_fp or any(f[1] is fp for f in fixed):
                    continue
                avg = net_pad_avg(fp)
                if avg:
                    hints[ref] = (1 if avg[0] >= mcx else -1, avg[1])
            placed_local[blk] = pack_main_ic(items, hints) + pos if items else \
                [(mcu_fp, 0.0, 0.0)] + pos
            continue
        if blk == main_block and len(items) >= 4:
            # P10: 신호 부품(C7 NRST, R1 BOOT0 등)은 물린 핀의 변·순서대로
            hints = {}
            for ref, _, fp in blocks[blk]:
                if fp is mcu_fp:
                    continue
                avg = net_pad_avg(fp)
                if avg:
                    hints[ref] = (1 if avg[0] >= mcx else -1, avg[1])
            placed_local[blk] = pack_main_ic(items, hints)
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

    # 군집 배치 (P7+P8): 메인 중앙, 각 군집은 투표된 변에 — 같은 변 여러
    # 군집은 그 변을 따라 차례로
    CX, CY = 148.5, 105.0  # A4 중앙
    offsets = {main_block: (0.0, 0.0)}
    mx1, my1, mx2, my2 = local_bbox(main_block)
    lateral = {s: [] for s in TIE}
    for b in others:
        lateral[sides[b]].append(b)
    for s, blks in lateral.items():
        if not blks:
            continue
        # P10: 같은 변의 군집은 물린 MCU 핀 좌표 순서로 (꼬임 방지)
        def blk_avg(b, axis):
            if b in chain_avg:   # P14: 전원 사슬은 공급원 옆 정렬
                b = chain_avg[b]
            pts = [net_pad_avg(fp) for _, _, fp in blocks[b]]
            pts = [p for p in pts if p]
            if not pts:
                return 0.0
            return sum(p[axis] for p in pts) / len(pts)
        blks.sort(key=lambda b: blk_avg(b, 0 if s in ("top", "bottom") else 1))
        sizes = [local_bbox(b) for b in blks]
        # 가장자리 군집이 있는 변: 벽(외곽선) 기준 정렬 — 깊은 이웃 군집이
        # 있으면 벽을 그만큼 안쪽으로 내려 띠 폭을 확보한다 (이웃이 메인과
        # 겹쳐 옆으로 튕겨나가던 문제의 기하적 해법, 2026-08-10 LDO 사건).
        edge_ids2 = {id(e) for _, e in edge_fps}
        edge_here = [b for b in blks
                     if any(id(f) in edge_ids2 for _, _, f in blocks[b])]
        depth = (lambda sz: (sz[3] - sz[1]) if s in ("top", "bottom")
                 else (sz[2] - sz[0]))
        d_extra = 0.0
        if edge_here:
            h_edge = max(depth(local_bbox(b)) for b in edge_here)
            non = [depth(local_bbox(b)) for b in blks if b not in edge_here]
            d_extra = max(0.0, (max(non) + EDGE - h_edge) if non else 0.0)
        if s in ("left", "right"):
            total = sum(y2 - y1 for _, y1, _, y2 in sizes) + GAP * (len(blks) - 1)
            cur = (my1 + my2) / 2 - total / 2
            for b, (x1, y1, x2, y2) in zip(blks, sizes):
                if s == "left":
                    ox = mx1 - GAP - x2 - (d_extra if b in edge_here else 0.0)
                    if edge_here and b not in edge_here:
                        ox = (mx1 - GAP - h_edge - d_extra) + EDGE - x1
                else:
                    ox = mx2 + GAP - x1 + (d_extra if b in edge_here else 0.0)
                    if edge_here and b not in edge_here:
                        ox = (mx2 + GAP + h_edge + d_extra) - EDGE - x2
                offsets[b] = (ox, cur - y1)
                cur += (y2 - y1) + GAP
        else:
            total = sum(x2 - x1 for x1, _, x2, _ in sizes) + GAP * (len(blks) - 1)
            cur = (mx1 + mx2) / 2 - total / 2
            for b, (x1, y1, x2, y2) in zip(blks, sizes):
                if s == "top":
                    oy = my1 - GAP - y2 - (d_extra if b in edge_here else 0.0)
                    if edge_here and b not in edge_here:
                        oy = (my1 - GAP - h_edge - d_extra) + EDGE - y1
                else:
                    oy = my2 + GAP - y1 + (d_extra if b in edge_here else 0.0)
                    if edge_here and b not in edge_here:
                        oy = (my2 + GAP + h_edge + d_extra) - EDGE - y2
                offsets[b] = (cur - x1, oy)
                cur += (x2 - x1) + GAP

    # 절대 배치 후 전체 범위 산출
    for blk in order:
        ox, oy = offsets[blk]
        for fp, cx, cy in placed_local[blk]:
            move_center(fp, ox + cx, oy + cy)
    all_fp = [fp for blk in order for fp, _, _ in placed_local[blk]]

    # === 마감 정렬: 군집 분리(옆으로 밀기) ↔ 플러시 클램프를 수렴까지 ===
    # 분리는 항상 '자기 변의 접선 방향'으로만 민다 — 플러시 벽(외곽선)을
    # 다시 넘는 되밀림(진동)이 원리적으로 없다 (2026-08-10: 클램프가 분리
    # 뒤에 돌면서 서로 되물리던 사건의 구조적 해법).
    edge_side_of = {}
    for s, efp in edge_fps:
        for blk in order:
            if any(f is efp for _, _, f in blocks[blk]):
                edge_side_of[blk] = s
    LAT = {"top": "x", "bottom": "x", "left": "y", "right": "y"}

    def blk_box(blk):
        fps = [fp for fp, _, _ in placed_local[blk]]
        return (min(body_bb(f)[0] for f in fps), min(body_bb(f)[1] for f in fps),
                max(body_bb(f)[2] for f in fps), max(body_bb(f)[3] for f in fps))

    def shift_blk(blk, dx, dy):
        if blk in edge_side_of:  # 가장자리 군집은 벽에 수직 이동 금지
            if LAT[edge_side_of[blk]] == "x":
                dy = 0.0
            else:
                dx = 0.0
        if dx == 0.0 and dy == 0.0:
            return
        ox, oy = offsets[blk]
        offsets[blk] = (ox + dx, oy + dy)
        for f, _, _ in placed_local[blk]:
            p = f.GetPosition()
            f.SetPosition(pcbnew.VECTOR2I(p.x + mm(dx), p.y + mm(dy)))

    def separation():
        for _ in range(24):
            moved = False
            for i, a in enumerate(order):
                for b2 in order[i + 1:]:
                    ba, bb_ = blk_box(a), blk_box(b2)
                    # 판정 여유는 GAP(이상적 간격)이 아니라 실겹침 기준 —
                    # 밴드 정렬이 만든 1.7mm 간격을 '겹침'으로 오판해 LDO를
                    # 옆으로 튕겨내던 사건 (2026-08-10). 0.6 = courtyard
                    # 여유(0.25x2) + 선 1가닥 최소.
                    ovx = min(ba[2], bb_[2]) - max(ba[0], bb_[0]) + 0.6
                    ovy = min(ba[3], bb_[3]) - max(ba[1], bb_[1]) + 0.6
                    if ovx <= 0 or ovy <= 0:
                        continue
                    mv = b2 if a == main_block else a if b2 == main_block else b2
                    ot = a if mv is b2 else b2
                    mb, ob = blk_box(mv), blk_box(ot)
                    axis = LAT.get(sides.get(mv) or edge_side_of.get(mv), "x")
                    if axis == "x":
                        sgn = 1 if (mb[0] + mb[2]) >= (ob[0] + ob[2]) else -1
                        shift_blk(mv, sgn * ovx, 0)
                    else:
                        sgn = 1 if (mb[1] + mb[3]) >= (ob[1] + ob[3]) else -1
                        shift_blk(mv, 0, sgn * ovy)
                    moved = True
            if not moved:
                return

    # P6: 가장자리 부품의 실크 = 그 변의 외곽선 (그 변은 여백 0)
    def silk_extreme(fp, side):
        vals = []
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.F_SilkS:
                bb = g.GetBoundingBox()
                vals.append({"left": pcbnew.ToMM(bb.GetLeft()),
                             "right": pcbnew.ToMM(bb.GetRight()),
                             "top": pcbnew.ToMM(bb.GetTop()),
                             "bottom": pcbnew.ToMM(bb.GetBottom())}[side])
        if not vals:
            b = body_bb(fp)
            return {"left": b[0], "right": b[2], "top": b[1], "bottom": b[3]}[side]
        return min(vals) if side in ("left", "top") else max(vals)

    def inward_need(box, side, v):
        """box가 플러시 벽 v를 넘은 양 (안쪽 이동 필요량, 부호 포함 dx/dy)."""
        if side == "top" and box[1] < v + EDGE:
            return 0.0, (v + EDGE) - box[1]
        if side == "bottom" and box[3] > v - EDGE:
            return 0.0, -(box[3] - (v - EDGE))
        if side == "left" and box[0] < v + EDGE:
            return (v + EDGE) - box[0], 0.0
        if side == "right" and box[2] > v - EDGE:
            return -(box[2] - (v - EDGE)), 0.0
        return 0.0, 0.0

    def clamp_flush():
        flush = {}
        for side, efp in edge_fps:
            v = silk_extreme(efp, side)
            eb = edge_side_of and next((b for b in order
                                        if any(f is efp for _, _, f in blocks[b])), None)
            # 가장자리 군집 안의 비가장자리 부품: 최대 필요량만큼 '일괄' 이동
            # (부품별로 밀면 같은 자리에 포개진다 — CC 저항 사건)
            needs = []
            inner = [f for f, _, _ in placed_local[eb] if f is not efp]
            for f in inner:
                needs.append(inward_need(body_bb(f), side, v))
            dxs = [d[0] for d in needs if d[0]] + [0.0]
            dys = [d[1] for d in needs if d[1]] + [0.0]
            dx = max(dxs) if side == "left" else min(dxs) if side == "right" else 0.0
            dy = max(dys) if side == "top" else min(dys) if side == "bottom" else 0.0
            if dx or dy:
                for f in inner:
                    p = f.GetPosition()
                    f.SetPosition(pcbnew.VECTOR2I(p.x + mm(dx), p.y + mm(dy)))
            # 같은 변의 다른 군집: 군집째 클램프
            for blk in order:
                if blk == eb or sides.get(blk) != side:
                    continue
                dx2, dy2 = inward_need(blk_box(blk), side, v)
                if dx2 or dy2:
                    ox, oy = offsets[blk]
                    offsets[blk] = (ox + dx2, oy + dy2)
                    for f, _, _ in placed_local[blk]:
                        p = f.GetPosition()
                        f.SetPosition(pcbnew.VECTOR2I(p.x + mm(dx2), p.y + mm(dy2)))
            flush[side] = v
        return flush

    separation()
    flush = {}
    for _ in range(3):
        flush = clamp_flush()
        separation()
    flush = clamp_flush()

    ex1 = min(body_bb(fp)[0] for fp in all_fp)
    ey1 = min(body_bb(fp)[1] for fp in all_fp)
    ex2 = max(body_bb(fp)[2] for fp in all_fp)
    ey2 = max(body_bb(fp)[3] for fp in all_fp)
    x1 = flush.get("left", ex1 - EDGE)
    x2 = flush.get("right", ex2 + EDGE)
    y1 = flush.get("top", ey1 - EDGE)
    y2 = flush.get("bottom", ey2 + EDGE)

    # 용지 중앙으로 평행이동 (P1)
    dx, dy = CX - (x1 + x2) / 2, CY - (y1 + y2) / 2
    for fp in all_fp:
        p = fp.GetPosition()
        fp.SetPosition(pcbnew.VECTOR2I(p.x + mm(dx), p.y + mm(dy)))
    x1, x2, y1, y2 = x1 + dx, x2 + dx, y1 + dy, y2 + dy

    # P5: 실크 REF 배치 — 후보 위치(옆/위/아래) 중 다른 부품과 안 겹치는
    # 첫 자리. 밀집 배치(P13)에선 고정 방향이 반드시 어딘가와 부딪힌다.
    bcx = (x1 + x2) / 2
    obstacles = [(id(f), body_bb(f)) for f in all_fp]

    def ref_pos(fp):
        bx1, by1, bx2, by2 = body_bb(fp)
        # 글자폭은 실측 보정치 (0.55/자는 과소 — R4 참조가 자기 패드 마스크에
        # 0.02mm 걸린 사건, 2026-08-10)
        tw = 0.85 * len(fp.GetReference()) + 0.5
        small = (by2 - by1) < 4.0 and len(list(fp.Pads())) < 10
        outw = 1 if (bx1 + bx2) / 2 >= bcx else -1
        if small:
            cands = [((bx2 + 0.4 + tw / 2) if outw > 0 else (bx1 - 0.4 - tw / 2),
                      (by1 + by2) / 2),
                     ((bx1 - 0.4 - tw / 2) if outw > 0 else (bx2 + 0.4 + tw / 2),
                      (by1 + by2) / 2),
                     ((bx1 + bx2) / 2, by1 - 0.75),
                     ((bx1 + bx2) / 2, by2 + 0.75)]
        else:
            cands = [((bx1 + bx2) / 2, by1 - 0.9),
                     (bx1 - 0.4 - tw / 2, (by1 + by2) / 2),
                     (bx2 + 0.4 + tw / 2, (by1 + by2) / 2),
                     ((bx1 + bx2) / 2, by2 + 0.9),
                     ((bx1 + bx2) / 2, (by1 + by2) / 2)]  # 최후: 몸체 중앙(LQFP 내부)
        best, best_ov = None, None
        for cx, cy in cands:
            tb = (cx - tw / 2 - 0.15, cy - 0.55, cx + tw / 2 + 0.15, cy + 0.55)
            ov = 0.0
            for oid, o in obstacles:
                if oid == id(fp):
                    continue
                w_ = min(tb[2], o[2]) - max(tb[0], o[0])
                h_ = min(tb[3], o[3]) - max(tb[1], o[1])
                if w_ > 0 and h_ > 0:
                    ov += w_ * h_
            if ov == 0.0:
                obstacles.append((0, tb))  # 놓인 REF도 장애물 (REF끼리 겹침 방지)
                return cx, cy
            if best_ov is None or ov < best_ov:
                best, best_ov = (cx, cy, tb), ov
        # 전 후보가 걸리면 겹침 최소 후보 (1번 고정 폴백은 하필 최악일 수 있음)
        obstacles.append((0, best[2]))
        return best[0], best[1]

    for fp in all_fp:
        r = fp.Reference()
        r.SetLayer(pcbnew.F_SilkS)
        r.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
        r.SetTextThickness(mm(0.12))
        r.SetTextAngleDegrees(0)
        cx, cy = ref_pos(fp)
        r.SetPosition(pcbnew.VECTOR2I(mm(cx), mm(cy)))

    rect = pcbnew.PCB_SHAPE(board)
    rect.SetShape(pcbnew.SHAPE_T_RECT)
    rect.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    rect.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    rect.SetLayer(pcbnew.Edge_Cuts)
    rect.SetWidth(mm(0.1))
    board.Add(rect)

    out = os.path.join(board_dir, f"{bid}.kicad_pcb")
    board.Save(out)

    # PW1/PW2 (rules/pcb-study-kicad-demos.md — StickHub 2층 실측 기준):
    # 신호 0.15 / 전원 0.3 / 비아 0.5x0.3 / 클리어런스 0.15. 넷클래스는
    # 프로젝트(.kicad_pro)에 산다 — 저장 후 JSON을 보강한다.
    pro = os.path.join(board_dir, f"{bid}.kicad_pro")
    if os.path.exists(pro):
        pj = json.load(open(pro, encoding="utf-8"))
        ns = pj.setdefault("net_settings", {})
        base = {"bus_width": 12, "diff_pair_gap": 0.15, "diff_pair_via_gap": 0.25,
                "diff_pair_width": 0.15, "line_style": 0, "microvia_diameter": 0.3,
                "microvia_drill": 0.1, "pcb_color": "rgba(0, 0, 0, 0.000)",
                "schematic_color": "rgba(0, 0, 0, 0.000)", "tuning_profile": "",
                "wire_width": 6}
        ns["classes"] = [
            dict(base, name="Default", clearance=0.15, track_width=0.15,
                 via_diameter=0.5, via_drill=0.3, priority=2147483647),
            dict(base, name="Power", clearance=0.15, track_width=0.3,
                 via_diameter=0.5, via_drill=0.3, priority=0),
        ]
        ns["netclass_patterns"] = [
            {"netclass": "Power", "pattern": "+*"},
            {"netclass": "Power", "pattern": "GND"},
        ]
        with open(pro, "w", encoding="utf-8", newline="\n") as f:
            json.dump(pj, f, indent=2, ensure_ascii=False)
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
