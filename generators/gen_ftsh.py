"""
Samtec FTSH 1.27mm 2열 SMD 헤더 생성기 (STDC14 = FTSH-107, UM2448 명기).

치수 근거 (2026-08-10, 공식 도면 미확보 상태의 3중 교차):
  - 피치 1.27 / 2열: Samtec FTSH 계열 공통 (UM2448 Rev 9 §8.1.2가
    "SAMTEC FTSH-107-01-L-DV-K-A"로 형번 명기).
  - 몸체: FTSH-105가 6.35 x 4.78mm (Arm ULINKplus UG 101636 실측 명기:
    0.25" x 0.188") -> 길이 = (자리수+1) x 1.27 파라메트릭, 폭 4.78.
  - 랜드: 0.76 x 2.4, 행간 ±1.95 — antmicro/hardware-components
    samtec-ftsh-105-01-f-dv-k (양산 보드 레퍼런스) 실측치 재사용.
  - Samtec 공식 print PDF는 다운로드 차단(403) — 확보되면 대조 예정
    (meta.dimensions_source에 미확보 사실 기록).

실행: python generators/gen_ftsh.py <자리수/열> <mpn>
예:   python generators/gen_ftsh.py 7 FTSH-107-01-L-DV-K
"""

import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

PITCH = 1.27
PAD_W, PAD_H = 0.76, 2.4
ROW_Y = 1.95
BODY_W = 4.78


def footprint(fid, npos):
    half = (npos - 1) * PITCH / 2
    body_l = (npos + 1) * PITCH
    bx, by = body_l / 2, BODY_W / 2
    cx, cy = bx + 0.25, ROW_Y + PAD_H / 2 + 0.25
    pads = []
    for k in range(npos):
        x = round(-half + k * PITCH, 3)
        for row, y in ((1, ROW_Y), (2, -ROW_Y)):
            num = 2 * k + row
            pads.append(
                f'  (pad "{num}" smd rect (at {x:g} {y if row == 1 else -ROW_Y:g}) '
                f"(size {PAD_W:g} {PAD_H:g}) (layers \"F.Cu\" \"F.Paste\" \"F.Mask\"))")
    silk_y = by + 0.11
    return f'''(footprint "{fid}"
  (version 20231120)
  (generator "partreel-gen-ftsh")
  (layer "F.Cu")
  (attr smd)
  (property "Reference" "REF**" (at 0 {-cy - 1:g} 0) (layer "F.SilkS")
    (effects (font (size 1 1) (thickness 0.15))))
  (property "Value" "{fid}" (at 0 {cy + 1:g} 0) (layer "F.Fab")
    (effects (font (size 1 1) (thickness 0.15))))
  (fp_rect (start {-bx:g} {-by:g}) (end {bx:g} {by:g})
    (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))
  (fp_line (start {-bx:g} {-by:g}) (end {-bx:g} {by:g})
    (stroke (width 0.12) (type solid)) (layer "F.SilkS"))
  (fp_line (start {bx:g} {-by:g}) (end {bx:g} {by:g})
    (stroke (width 0.12) (type solid)) (layer "F.SilkS"))
  (fp_circle (center {-half - 1.0:g} {ROW_Y + PAD_H / 2 + 0.5:g}) (end {-half - 0.75:g} {ROW_Y + PAD_H / 2 + 0.5:g})
    (stroke (width 0.25) (type solid)) (fill solid) (layer "F.SilkS"))
  (fp_rect (start {-cx:g} {-cy:g}) (end {cx:g} {cy:g})
    (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
  (fp_rect (start {-bx:g} {-by:g}) (end {bx:g} {by:g})
    (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))
{chr(10).join(pads)}
)
'''


def symbol(fid, npos):
    rows = []
    for k in range(npos):
        y = -2.54 * k
        for col, (x, ang) in ((1, (0, 0)), (2, (10.16, 180))):
            num = 2 * k + col
            rows.append(
                f'''      (pin passive line (at {x:g} {y:g} {ang}) (length 2.54)
        (name "Pin_{num}" (effects (font (size 1.27 1.27))))
        (number "{num}" (effects (font (size 1.27 1.27)))))''')
    top, bot = 1.27, -2.54 * (npos - 1) - 1.27
    return f'''(kicad_symbol_lib (version 20231120) (generator "partreel-gen-ftsh")
  (symbol "{fid}" (pin_names hide) (in_bom yes) (on_board yes)
    (property "Reference" "J" (at 2.54 {top + 1.27:g} 0) (effects (font (size 1.27 1.27)) (justify left)))
    (property "Value" "{fid}" (at 2.54 {bot - 1.9:g} 0) (effects (font (size 1.27 1.27)) (justify left)))
    (symbol "{fid}_1_1"
      (rectangle (start 2.54 {top:g}) (end 7.62 {bot:g})
        (stroke (width 0.254) (type solid)) (fill (type background)))
{chr(10).join(rows)}
    )))'''


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    npos, mpn = int(sys.argv[1]), sys.argv[2]
    pid = "samtec_" + mpn.lower().replace("-", "_")
    d = os.path.join(ROOT, "library", "connector", "samtec", pid)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{pid}.kicad_mod"), "w", encoding="utf-8", newline="\n") as f:
        f.write(footprint(pid, npos))
    with open(os.path.join(d, f"{pid}.kicad_sym"), "w", encoding="utf-8", newline="\n") as f:
        f.write(symbol(pid, npos))
    meta = {
        "id": pid,
        "name": f"{mpn} 1.27mm 2x{npos} SMD header (Samtec)",
        "category": "connector",
        "family": f"ftsh_127_2x{npos}",
        "manufacturer": "Samtec",
        "mpn_pattern": mpn,
        "description": f"Samtec FTSH series 1.27mm dual-row SMD header, 2x{npos} "
                       f"({npos * 2} pins). FTSH-107 is the STDC14 debug connector "
                       f"(ST UM2448).",
        "keywords": ["connector", "header", "1.27mm", "samtec", "ftsh", "stdc14"],
        "parameters": {"pins": npos * 2, "mounting": "smd"},
        "formats": ["kicad_mod", "kicad_sym"],
        "tier": "verified-2d",
        "license": "CC-BY-4.0",
        "datasheet": f"https://www.samtec.com/products/{mpn.lower()}",
        "dimensions_source": "Pitch 1.27 dual-row per Samtec FTSH series (MPN named "
                             "in ST UM2448 Rev 9 sec 8.1.2). Body L=(pos+1)*1.27, "
                             "W=4.78 from FTSH-105 = 6.35x4.78mm (Arm ULINKplus UG "
                             "101636). Land 0.76x2.4 rows +-1.95 from "
                             "antmicro/hardware-components samtec-ftsh-105 "
                             "production reference. Samtec official print PDF "
                             "blocked (HTTP 403) - to be cross-checked when "
                             "obtainable.",
        "files": {
            "footprint": f"{pid}.kicad_mod",
            "symbol": f"{pid}.kicad_sym",
        },
    }
    with open(os.path.join(d, "meta.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(f"OK {pid} -> {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
