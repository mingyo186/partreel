"""
회로 블록 생성기 (REQUIREMENTS §24) — 선언(block.json) → 자립 .kicad_sch.

블록 1개 = 재사용 시트 1장 (KiCad 데모의 multichannel 패턴):
  - lib_symbols에 파트릴 심볼을 내장해 파일 하나로 자립
  - 인터페이스 = 계층 라벨(hierarchical_label) → 부모에서 시트 핀으로 노출
  - 다핀 네트는 **실제 배선**(핀→세로 스텁→네트별 가로 버스)으로 잇는다.
    라벨 이름 병합에 기대는 방식은 커널 연결 그래프와 안 맞는다 (본문 주석)

문법 근거(1차 사료): KiCad 10 동봉 데모의 실제 .kicad_sch 파일에서 추출
  (complex_hierarchy/ampli_ht, cm5_minima/CM5 — 2026-08-04 확인).
좌표 규약: 회로도 Y축은 아래로 증가, 심볼 라이브러리 Y축은 위로 증가
  → 인스턴스 (X,Y)에 놓인 심볼의 핀 절대좌표 = (X + px, Y - py).
  (kicad-cli sch erc가 미접속 핀을 잡으므로 이 규약은 게이트가 검증한다)

block.json:
{
  "id": "i2c_pullup", "name": "...", "description": "...",
  "circuit_source": "<데이터시트/규격 URL + 페이지·그림 — 필수>",
  "fp_lib": "PCM_PartReel",          # 풋프린트 라이브러리 별명 (기본값)
  "parts": [ {"ref": "R1", "part": "<partreel id>", "value": "1.8k"} ],
  "nets": { "+3V3": ["R1.1", "R2.1"], "SDA": ["R1.2"] },
  "interface": { "+3V3": "input", "SDA": "bidirectional" }
}

실행: python generators/build_block.py blocks/<분류>/<id> | --all
"""

import json
import os
import re
import sys
import uuid

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
BS = chr(92)

GRID_X0, GRID_Y0 = 63.5, 63.5
GRID_DX, GRID_DY, GRID_COLS = 38.1, 38.1, 4


def uid(*keys):
    return str(uuid.uuid5(NS, "partreel-block:" + ":".join(keys)))


def balanced(text, start):
    """start의 '('부터 균형 블록 추출."""
    depth, i, instr = 0, start, False
    while i < len(text):
        c = text[i]
        if instr:
            if c == '"' and text[i - 1] != BS:
                instr = False
        elif c == '"':
            instr = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    raise ValueError("괄호 불균형")


def load_symbol(part_id):
    """부품 심볼 파일에서 최상위 심볼 블록·이름·핀 목록 추출."""
    idx = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    part = next((p for p in idx["parts"] if p["id"] == part_id), None)
    if not part:
        raise SystemExit(f"FAIL: 부품 '{part_id}'가 카탈로그에 없음")
    text = open(os.path.join(ROOT, part["path"], f"{part_id}.kicad_sym"),
                encoding="utf-8").read()
    m = re.search(r'[(]symbol\s+"([^"]+)"', text)
    blk = balanced(text, m.start())
    name = m.group(1)
    pins = []  # (number, x, y)
    for pm in re.finditer(r"[(]pin\s+\w+\s+\w+", blk):
        pblk = balanced(blk, pm.start())
        at = re.search(r"[(]at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)[)]", pblk)
        num = re.search(r'[(]number\s+"([^"]+)"', pblk)
        if at and num:
            pins.append((num.group(1), float(at.group(1)), float(at.group(2))))
    return name, blk, pins, part


def prop(name, value, x, y, hide=False, left=False):
    h = "\n\t\t\t\t(hide yes)" if hide else ""
    # 왼쪽 정렬 (R12): 짝의 왼쪽 끝을 맞춰 긴 값이 삐져나오지 않게
    j = "\n\t\t\t\t(justify left)" if left else ""
    return (f'\t\t(property "{name}" "{value}"\n'
            f"\t\t\t(at {x:g} {y:g} 0)\n"
            f"\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t){j}{h}\n\t\t\t)\n\t\t)")


def build(block_dir):
    bj = os.path.join(block_dir, "block.json")
    b = json.load(open(bj, encoding="utf-8"))
    for k in ("id", "name", "description", "circuit_source", "parts", "nets"):
        if not b.get(k):
            raise SystemExit(f"FAIL: block.json에 {k} 없음 (circuit_source는 필수 — §24)")
    bid = b["id"]
    fp_lib = b.get("fp_lib", "PCM_PartReel")
    root_uuid = uid(bid, "root")

    # 핀 -> 네트 역인덱스
    pin_net = {}
    for net, pins in b["nets"].items():
        for p in pins:
            pin_net[p] = net
    iface = b.get("interface", {})

    lib_entries, inst_blocks, labels, noconnects = {}, [], [], []
    pin_pos, wires = {}, []
    layout = b.get("layout") or {}
    lay_parts = layout.get("parts") or {}

    def rot_xy(px, py, rot):
        """심볼 좌표(Y위) -> 인스턴스 회전(CCW) 후 회로도 오프셋(Y아래)."""
        c, s = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[rot % 360]
        rx, ry = px * c - py * s, px * s + py * c
        return rx, -ry

    for i, part in enumerate(b["parts"]):
        ref, pid = part["ref"], part["part"]
        sym_name, sym_blk, pins, meta = load_symbol(pid)
        if sym_name not in lib_entries:
            cached = sym_blk.replace(f'(symbol "{sym_name}"',
                                     f'(symbol "PartReel:{sym_name}"', 1)
            lib_entries[sym_name] = "\t\t" + cached.replace("\n", "\n\t\t")
        lp = lay_parts.get(ref) or {}
        rot = int(lp.get("rot", 0))
        if "at" in lp:
            X, Y = float(lp["at"][0]), float(lp["at"][1])
        else:
            X = GRID_X0 + (i % GRID_COLS) * GRID_DX
            Y = GRID_Y0 + (i // GRID_COLS) * GRID_DY
        pin_uuid_lines = "\n".join(
            f'\t\t(pin "{n}"\n\t\t\t(uuid "{uid(bid, ref, "pin", n)}")\n\t\t)'
            for n, _, _ in pins)
        inst_blocks.append(f'''\t(symbol
\t\t(lib_id "PartReel:{sym_name}")
\t\t(at {X:g} {Y:g} {rot})
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "{uid(bid, ref)}")
{prop("Reference", ref, *(lp.get("ref_at") or [X, Y - 7.62]), hide=bool(lp.get("ref_at")))}
{prop("Value", part.get("value") or meta.get("name") or pid, *(lp.get("value_at") or [X, Y + 7.62]), hide=bool(lp.get("value_at")))}
{prop("Footprint", f"{fp_lib}:{pid}", X, Y, hide=True)}
{prop("Datasheet", f"https://partreel.com/p/{pid}/", X, Y, hide=True)}
{prop("PartReel", pid, X, Y, hide=True)}
{pin_uuid_lines}
\t\t(instances
\t\t\t(project "{bid}"
\t\t\t\t(path "/{root_uuid}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)''')
        # 표기(R12): 회전 심볼의 속성 텍스트는 커널이 정렬·위치를 재계산해
        # 예측 불가 (2026-08-09 실측) — 속성은 숨기고 자유 텍스트로 그린다.
        # 왼쪽 정렬 고정: 짝의 왼쪽 끝이 맞아 긴 값이 삐져나오지 않는다.
        if lp.get("ref_at"):
            for txt, (tx, ty) in ((ref, lp["ref_at"]),
                                  (part.get("value") or "", lp.get("value_at") or lp["ref_at"])):
                if not txt:
                    continue
                # 색 고정: 자유 텍스트는 기본 테마에서 파란 '노트' 색이 되므로
                # 부품 필드 관례색(진홍 #840000)으로 지정 (2026-08-09 지적)
                labels.append(
                    f'\t(text "{txt}"\n\t\t(exclude_from_sim no)\n'
                    f"\t\t(at {tx:g} {ty:g} 0)\n"
                    f"\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n"
                    f"\t\t\t\t(color 132 0 0 1)\n\t\t\t)\n"
                    f"\t\t\t(justify left)\n\t\t)\n"
                    f'\t\t(uuid "{uid(bid, ref, "fx", txt)}")\n\t)')

        # 핀 절대좌표 기록 + 미접속 표시. (라벨/배선은 전체 배치 후 일괄)
        for num, px, py in pins:
            dx, dy = rot_xy(px, py, rot)
            ax, ay = round(X + dx, 4), round(Y + dy, 4)
            key = f"{ref}.{num}"
            if key not in pin_net:
                noconnects.append(
                    f'\t(no_connect\n\t\t(at {ax:g} {ay:g})\n\t\t(uuid "{uid(bid, key, "nc")}")\n\t)')
            else:
                pin_pos[key] = (ax, ay)

    # === 네트 배선 (2026-08-04 커널 실험의 결론) ===
    # 라벨 이름 병합에 기대면 안 된다: 핀 2개 이상인 네트를 라벨로만 이으면
    # (계층 2장이든, 계층 1장+로컬이든, 배선 브리지든) 부모 시트의 라벨이
    # label_dangling으로 죽는다 — 실패는 항상 '다핀 네트'를 따라감을 변수
    # 격리(이름/자리/모양/라벨 구성)로 확정했다. 그래서 **실제 배선**으로
    # 물리적으로 잇는다: 핀→세로 스텁→네트별 가로 버스(고유 y), 모든 접속은
    # 끝점-끝점(연쇄 구간)이라 교차-비접속 문제도 없다. 계층 라벨은 배선
    # 끝점에 네트당 1장 (단핀 네트는 핀 위에 직접 — 실험으로 검증된 형태).
    def w(x1, y1, x2, y2, *k):
        wires.append(f'\t(wire\n\t\t(pts\n\t\t\t(xy {x1:g} {y1:g}) (xy {x2:g} {y2:g})\n\t\t)'
                     f'\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type solid)\n\t\t)'
                     f'\n\t\t(uuid "{uid(bid, "w", *k)}")\n\t)')

    def hlabel(net, x, y):
        shape = {"input": "input", "output": "output", "bidirectional": "bidirectional",
                 "passive": "passive"}.get(iface.get(net), "bidirectional")
        return (f'\t(hierarchical_label "{net}"\n\t\t(shape {shape})\n'
                f'\t\t(at {x:g} {y:g} 0)\n\t\t(effects\n\t\t\t(font\n'
                f'\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left)\n\t\t)\n'
                f'\t\t(uuid "{uid(bid, net, "hlabel")}")\n\t)')

    def llabel(net, x, y):
        return (f'\t(label "{net}"\n\t\t(at {x:g} {y:g} 0)\n\t\t(effects\n'
                f'\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n'
                f'\t\t\t(justify left bottom)\n\t\t)\n'
                f'\t\t(uuid "{uid(bid, net, "llabel")}")\n\t)')

    # === 명시 배치 모드 (§24 가독 규칙): layout이 있으면 자동 버스 대신
    #     선언된 배선·라벨·전원 심볼을 그대로 그린다 ===
    if layout:
        import block_power
        for pts in layout.get("wires", []):
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                w(x1, y1, x2, y2, f"{x1}_{y1}_{x2}_{y2}")
        for lab in layout.get("labels", []):
            net, (x, y) = lab["net"], lab["at"]
            if lab.get("kind") == "local":
                labels.append(llabel(net, x, y))
            else:
                labels.append(hlabel(net, x, y))
        pwr_defs, pwr_insts = {}, []
        for j, pw in enumerate(layout.get("power", [])):
            kind, (x, y) = pw["symbol"], pw["at"]
            if kind == "gnd":
                name, text = "PR_GND", block_power.gnd_symbol()
            elif kind == "flag":
                name, text = "PR_FLAG", block_power.flag_symbol()
            else:
                name, text = block_power.rail_symbol(pw["net"])
            pwr_defs.setdefault(name, "\t\t" + text.replace("\n", "\n\t\t"))
            ref = f"#PWR{j + 1:02d}" if kind != "flag" else f"#FLG{j + 1:02d}"
            pwr_insts.append(f'''\t(symbol
\t\t(lib_id "PartReelPwr:{name}")
\t\t(at {x:g} {y:g} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "{uid(bid, "pwr", str(j))}")
{prop("Reference", ref, x, y + 5.08, hide=True)}
{prop("Value", pw.get("net", "flag"), x,
      y + 4.445 if kind == "gnd" else y - 3.81, hide=(kind == "flag"))}
\t\t(pin "1"
\t\t\t(uuid "{uid(bid, "pwrpin", str(j))}")
\t\t)
\t\t(instances
\t\t\t(project "{bid}"
\t\t\t\t(path "/{root_uuid}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)''')
        for name, textdef in pwr_defs.items():
            lib_entries[name] = textdef.replace(f'(symbol "{name}"',
                                                f'(symbol "PartReelPwr:{name}"', 1)
        inst_blocks.extend(pwr_insts)

        # 자동 junction (커널 규칙, 2026-08-08 ERC로 확정): 배선 '끝점'끼리는
        # 암묵 연결되지만, 끝점/핀/전원심볼이 다른 배선의 **중간**에 닿는
        # T자 접합은 (junction) 요소가 있어야 전기적으로 연결된다 —
        # 편집기가 자동으로 찍는 점이 파일 포맷에서는 필수 요소다.
        segs = []
        for pts in layout.get("wires", []):
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                segs.append((x1, y1, x2, y2))

        def interior(px, py, seg):
            x1, y1, x2, y2 = seg
            if (px, py) in ((x1, y1), (x2, y2)):
                return False
            if x1 == x2 == px:
                return min(y1, y2) < py < max(y1, y2)
            if y1 == y2 == py:
                return min(x1, x2) < px < max(x1, x2)
            return False

        touch_pts = set()
        for x1, y1, x2, y2 in segs:
            touch_pts.add((x1, y1)); touch_pts.add((x2, y2))
        touch_pts.update(pin_pos.values())
        for pw in layout.get("power", []):
            touch_pts.add(tuple(pw["at"]))
        junctions = []
        seen_j = set()
        for px, py in touch_pts:
            if any(interior(px, py, s) for s in segs) and (px, py) not in seen_j:
                seen_j.add((px, py))
                junctions.append(
                    f'\t(junction\n\t\t(at {px:g} {py:g})\n\t\t(diameter 0)\n'
                    f'\t\t(color 0 0 0 0)\n\t\t(uuid "{uid(bid, "junc", f"{px}_{py}")}")\n\t)')
        wires.extend(junctions)

    BUS_Y0 = GRID_Y0 - 25.4
    for k, (net, members) in enumerate(sorted(b["nets"].items())):
        if layout:
            break  # 명시 배치 모드에서는 자동 버스/라벨 생략
        pts = [pin_pos[m] for m in members if m in pin_pos]
        if len(pts) == 1:
            x, y = pts[0]
            labels.append(hlabel(net, x, y) if net in iface else llabel(net, x, y))
            continue
        bus_y = BUS_Y0 - k * 2.54
        pts = sorted(pts)
        for x, y in pts:
            w(x, y, x, bus_y, net, f"v{x:g}")
        for (x1, _), (x2, _) in zip(pts, pts[1:]):
            w(x1, bus_y, x2, bus_y, net, f"h{x1:g}")
        if net in iface:
            labels.append(hlabel(net, pts[0][0], bus_y))
        else:
            labels.append(llabel(net, pts[0][0], bus_y))

    # 네트 선언이 실제 핀을 가리키는지 (오타 방어)
    all_pins = set()
    for part in b["parts"]:
        _, _, pins, _ = load_symbol(part["part"])
        all_pins.update(f"{part['ref']}.{n}" for n, _, _ in pins)
    ghost = [p for p in pin_net if p not in all_pins]
    if ghost:
        raise SystemExit(f"FAIL: nets가 존재하지 않는 핀을 참조: {ghost}")

    title = b["name"].replace('"', "'")
    doc = (f'{b["description"]} | source: {b["circuit_source"]}').replace('"', "'")
    out = f'''(kicad_sch
\t(version 20250114)
\t(generator "partreel-block")
\t(generator_version "1.0")
\t(uuid "{root_uuid}")
\t(paper "A4")
\t(title_block
\t\t(title "{title}")
\t\t(company "PartReel block")
\t\t(comment 1 "{doc[:200]}")
\t)
\t(lib_symbols
{chr(10).join(lib_entries.values())}
\t)
{chr(10).join(wires)}
{chr(10).join(labels)}
{chr(10).join(noconnects)}
{chr(10).join(inst_blocks)}
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
'''
    out_path = os.path.join(block_dir, f"{bid}.kicad_sch")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    print(f"OK  {bid}: 부품 {len(b['parts'])} / 계층라벨 "
          f"{sum(1 for l in labels if 'hierarchical' in l)} / 로컬라벨 "
          f"{sum(1 for l in labels if l.startswith(chr(9) + '(label'))} / NC {len(noconnects)}"
          f" -> {out_path}")
    return out_path


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        targets = [os.path.dirname(p) for p in
                   __import__("glob").glob(os.path.join(ROOT, "blocks", "*", "*", "block.json"))]
    else:
        targets = sys.argv[1:]
    if not targets:
        print(__doc__)
        return 2
    for t in targets:
        build(os.path.join(ROOT, t) if not os.path.isabs(t) else t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
