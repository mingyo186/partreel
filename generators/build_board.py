"""
보드 생성기 (REQUIREMENTS §25 1단계) — board.json → 루트 회로도.

보드 = 블록 시트들의 조합. 시트는 블록 .kicad_sch를 상대경로로 참조만
한다(복사 없음 — 블록 수정이 모든 보드에 반영). 연결은 시트 핀 +
**전역 라벨** 쌍 — 2026-08-04 커널 실험에서 오류 0으로 실증된 유일 조합
(check_block 하네스 패턴 그대로). 전원(+5V/+3V3/GND 등 power_in)은 블록
내부 전역 전원 심볼이 이름으로 자동 병합되므로 보드 선언이 필요 없다.
미연결 인터페이스 핀은 no_connect를 명시해 ERC 잡음을 0으로 유지한다.

boards/<id>/board.json:
{
  "id": "demo_g431_devkit", "name": "...", "revision": "0.1",
  "blocks": [ {"ref": "B1", "block": "usb_c_5v"}, ... ],
  "nets": { "USB_DP": ["B1.USB_DP", "B3.PA12"], ... }
}

실행: python generators/build_board.py boards/<id> | --all
"""

import glob
import json
import os
import sys
import uuid

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

SHEET_W = 30.48
COL_X0, ROW_Y0 = 38.1, 38.1
COL_DX = 78.74


def uid(*keys):
    return str(uuid.uuid5(NS, "partreel-board:" + ":".join(keys)))


def load_block(block_id):
    hits = glob.glob(os.path.join(ROOT, "blocks", "*", block_id, "block.json"))
    if len(hits) != 1:
        raise SystemExit(f"FAIL: 블록 '{block_id}' 탐색 결과 {len(hits)}건")
    b = json.load(open(hits[0], encoding="utf-8"))
    rel = os.path.relpath(os.path.dirname(hits[0]), ROOT).replace(os.sep, "/")
    return b, f"{rel}/{block_id}.kicad_sch"


def build(board_dir):
    bd = json.load(open(os.path.join(board_dir, "board.json"), encoding="utf-8"))
    for k in ("id", "name", "blocks", "nets"):
        if k not in bd:
            raise SystemExit(f"FAIL: board.json에 {k} 없음")
    bid = bd["id"]
    root_uuid = uid(bid, "root")

    # 핀 -> 네트 역인덱스 + 선언 검증
    pin_net = {}
    for net, pins in bd["nets"].items():
        for p in pins:
            pin_net[p] = net

    sheets, labels, ncs = [], [], []
    seen_pins = set()
    for i, inst in enumerate(bd["blocks"]):
        ref, blk_id = inst["ref"], inst["block"]
        b, sheet_file = load_block(blk_id)
        iface = sorted(b.get("interface", {}).items())
        x = COL_X0 + i * COL_DX
        y0 = ROW_Y0
        h = max(len(iface) * 2.54 + 12.7, 20.32)
        pins_out = []
        for j, (net, direction) in enumerate(iface):
            py = y0 + 5.08 + j * 2.54
            shape = {"input": "input", "output": "output", "bidirectional":
                     "bidirectional", "passive": "passive"}.get(direction,
                                                                "bidirectional")
            key = f"{ref}.{net}"
            seen_pins.add(key)
            pins_out.append(f'''\t\t(pin "{net}" {shape}
\t\t\t(at {x + SHEET_W:g} {py:g} 0)
\t\t\t(uuid "{uid(bid, ref, net, "pin")}")
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left)
\t\t\t)
\t\t)''')
            if key in pin_net:
                labels.append(f'''\t(global_label "{pin_net[key]}"
\t\t(at {x + SHEET_W:g} {py:g} 0)
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.27 1.27)
\t\t\t)
\t\t\t(justify left bottom)
\t\t)
\t\t(uuid "{uid(bid, ref, net, "glabel")}")
\t)''')
            else:
                ncs.append(f'\t(no_connect\n\t\t(at {x + SHEET_W:g} {py:g})\n'
                           f'\t\t(uuid "{uid(bid, ref, net, "nc")}")\n\t)')
        sheets.append(f'''\t(sheet
\t\t(at {x:g} {y0:g})
\t\t(size {SHEET_W:g} {h:g})
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(stroke
\t\t\t(width 0)
\t\t\t(type solid)
\t\t)
\t\t(fill
\t\t\t(color 0 0 0 0.0000)
\t\t)
\t\t(uuid "{uid(bid, ref, "sheet")}")
\t\t(property "Sheetname" "{ref} {blk_id}"
\t\t\t(at {x:g} {y0 - 0.8:g} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left bottom)
\t\t\t)
\t\t)
\t\t(property "Sheetfile" "{'../../' + sheet_file}"
\t\t\t(at {x:g} {y0 + h + 0.8:g} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left top)
\t\t\t)
\t\t)
{chr(10).join(pins_out)}
\t\t(instances
\t\t\t(project "{bid}"
\t\t\t\t(path "/{root_uuid}"
\t\t\t\t\t(page "{i + 2}")
\t\t\t\t)
\t\t\t)
\t\t)
\t)''')

    ghost = [p for p in pin_net if p not in seen_pins]
    if ghost:
        raise SystemExit(f"FAIL: nets가 존재하지 않는 블록 핀을 참조: {ghost}")

    title = bd["name"].replace('"', "'")
    out = f'''(kicad_sch
\t(version 20250114)
\t(generator "partreel-board")
\t(generator_version "1.0")
\t(uuid "{root_uuid}")
\t(paper "A3")
\t(title_block
\t\t(title "{title}")
\t\t(company "PartReel board")
\t\t(rev "{bd.get("revision", "0.1")}")
\t)
{chr(10).join(labels)}
{chr(10).join(ncs)}
{chr(10).join(sheets)}
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
'''
    out_path = os.path.join(board_dir, f"{bid}.kicad_sch")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(out)

    # pins.h (§25 1단계 후반): 보드 네트의 MCU 쪽 끝점이 PXn 형태면 STM32
    # HAL 스타일 #define을 낸다. SWDIO 같은 별칭 핀의 원 포트 역추적과
    # AF 검증은 2단계 (ST XML 신호표).
    defines = []
    for net in sorted(bd["nets"]):
        for e in bd["nets"][net]:
            m = __import__("re").fullmatch(r"[^.]+\.(P([A-K])(\d+))", e)
            if m:
                _, port, num = m.groups()
                defines.append(f"#define {net}_GPIO_Port GPIO{port}")
                defines.append(f"#define {net}_Pin GPIO_PIN_{num}")
    pins_h = (f"/* pins.h — generated by build_board.py from boards/{bid}/board.json\n"
              f" * rev {bd.get('revision', '0.1')} — DO NOT EDIT (source: board.json)\n"
              f" */\n#ifndef PARTREEL_PINS_H\n#define PARTREEL_PINS_H\n\n"
              + "\n".join(defines) + "\n\n#endif /* PARTREEL_PINS_H */\n")
    with open(os.path.join(board_dir, "pins.h"), "w", encoding="utf-8",
              newline="\n") as f:
        f.write(pins_h)
    print(f"OK  {bid}: 블록 {len(bd['blocks'])} / 연결 네트 {len(bd['nets'])} / "
          f"NC {len(ncs)} / pins.h #define {len(defines)} -> {out_path}")
    return out_path


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        targets = [os.path.dirname(p) for p in
                   glob.glob(os.path.join(ROOT, "boards", "*", "board.json"))]
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
