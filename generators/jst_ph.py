"""
JST PH series (2.0mm pitch, THT vertical, B*B-PH-K) parametric generator.

핀수(pins)만 받아서 한 부품의 전체 텍스트 자산을 생성:
  - <id>.kicad_mod  (풋프린트)
  - <id>.kicad_sym  (심볼)
  - meta.json       (데이터 계약)
3D(.step/.glb)는 jst_ph_3d.py / stl_to_glb.py 에서 생성.

치수 출처: KiCad 공식 Connector_JST 라이브러리(JST 데이터시트 기반)와 일치.
  - 패드 oval 1.2 x 1.75, drill 0.75, pitch 2.0, 핀1 roundrect
  - Fab  x[-1.95, A+1.95] y[-1.70, 2.80]
  - Silk x[-2.06, A+2.06] y[-1.81, 2.91]
  - Crt  x[-2.45, A+2.45] y[-2.20, 3.30]
  (A = (pins-1)*2.0)
"""

import json
import os

PITCH = 2.0
PAD_W, PAD_H = 1.2, 1.75
DRILL = 0.75

# 본체/외곽 오프셋 (핀1 기준, A 더해서 우측 확장)
FAB = dict(x0=-1.95, x1=1.95, y0=-1.70, y1=2.80)
SILK = dict(x0=-2.06, x1=2.06, y0=-1.81, y1=2.91)
CRT = dict(x0=-2.45, x1=2.45, y0=-2.20, y1=3.30)

LIB_ROOT = os.path.join(os.path.dirname(__file__), "..", "library", "connector", "jst", "ph")

PINS_RANGE = range(2, 17)  # PH 시리즈: 2~16핀


def _line(x1, y1, x2, y2, layer, w):
    return (f'  (fp_line (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f})'
            f' (stroke (width {w}) (type solid)) (layer "{layer}"))')


def _rect(box, A, layer, w):
    x0, x1 = box["x0"], A + box["x1"]
    y0, y1 = box["y0"], box["y1"]
    return [
        _line(x0, y0, x1, y0, layer, w),
        _line(x1, y0, x1, y1, layer, w),
        _line(x1, y1, x0, y1, layer, w),
        _line(x0, y1, x0, y0, layer, w),
    ]


def _cham_rect(box, A, layer, w, ch):
    """좌상단(핀1) 모따기한 사각 — KLC pin1 마커."""
    x0, x1 = box["x0"], A + box["x1"]
    y0, y1 = box["y0"], box["y1"]
    return [
        _line(x0 + ch, y0, x1, y0, layer, w),
        _line(x1, y0, x1, y1, layer, w),
        _line(x1, y1, x0, y1, layer, w),
        _line(x0, y1, x0, y0 + ch, layer, w),
        _line(x0, y0 + ch, x0 + ch, y0, layer, w),
    ]


def gen_footprint(pins, fid):
    A = (pins - 1) * PITCH
    cx = A / 2.0
    out = [f'(footprint "{fid}" (version 20221018) (generator opencad-lib)',
           '  (layer "F.Cu")',
           f'  (descr "JST PH series 2.0mm {pins}-pin THT vertical (B{pins}B-PH-K). '
           f'Dimensions match KiCad official Connector_JST (JST datasheet-derived).")',
           f'  (tags "JST PH connector 2.0mm {pins}pin")',
           '  (attr through_hole)',
           f'  (fp_text reference "REF**" (at {cx:.3f} -3.000) (layer "F.SilkS")'
           '\n    (effects (font (size 1 1) (thickness 0.15))))',
           f'  (fp_text value "{fid}" (at {cx:.3f} 4.000) (layer "F.Fab")'
           '\n    (effects (font (size 1 1) (thickness 0.15))))']

    # KLC: Fab(0.10mm) + Silk(0.12mm) 둘 다 핀1 코너 1mm 모따기로 통일.
    out += _cham_rect(FAB, A, "F.Fab", 0.10, 1.0)
    out += _cham_rect(SILK, A, "F.SilkS", 0.12, 1.0)
    # Courtyard(0.05mm, 커넥터 0.5mm 클리어런스 = CRT 오프셋에 반영됨)
    out += _rect(CRT, A, "F.CrtYd", 0.05)
    # 패드
    for i in range(pins):
        n = i + 1
        x = i * PITCH
        if n == 1:
            out.append(f'  (pad "1" thru_hole roundrect (at 0 0) (size {PAD_W} {PAD_H})'
                       f' (drill {DRILL}) (layers "*.Cu" "*.Mask") (roundrect_rratio 0.25))')
        else:
            out.append(f'  (pad "{n}" thru_hole oval (at {x:.3f} 0) (size {PAD_W} {PAD_H})'
                       f' (drill {DRILL}) (layers "*.Cu" "*.Mask"))')
    out.append(')')
    return "\n".join(out) + "\n"


def gen_symbol(pins, fid):
    PIN_LEN, GRID = 2.54, 2.54
    bl, br = -2.54, 2.54
    span = (pins - 1) * GRID
    top = span / 2.0
    bt, bb = top + 1.27, -top - 1.27
    out = ['(kicad_symbol_lib (version 20211014) (generator opencad-lib)',
           f'  (symbol "{fid}" (in_bom yes) (on_board yes)',
           f'    (property "Reference" "J" (at {br + 1.0:.2f} {bt:.2f} 0)'
           '\n      (effects (font (size 1.27 1.27)) (justify left)))',
           f'    (property "Value" "{fid}" (at {br + 1.0:.2f} {bb:.2f} 0)'
           '\n      (effects (font (size 1.27 1.27)) (justify left)))',
           '    (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
           '    (property "Datasheet" "https://www.jst-mfg.com/product/pdf/eng/ePH.pdf"'
           ' (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
           f'    (symbol "{fid}_1_1"',
           f'      (rectangle (start {bl:.2f} {bt:.2f}) (end {br:.2f} {bb:.2f})'
           '\n        (stroke (width 0.254) (type solid)) (fill (type background)))']
    for i in range(pins):
        n = i + 1
        y = top - i * GRID
        out.append(f'      (pin passive line (at {bl - PIN_LEN:.2f} {y:.2f} 0) (length {PIN_LEN})'
                   f'\n        (name "Pin_{n}" (effects (font (size 1.27 1.27))))'
                   f'\n        (number "{n}" (effects (font (size 1.27 1.27)))))')
    out += ['    )', '  )', ')']
    return "\n".join(out) + "\n"


def gen_meta(pins, fid):
    return {
        "id": fid,
        "name": f"JST PH {pins}-pin (B{pins}B-PH-K)",
        "category": "connector",
        "family": "JST PH",
        "manufacturer": "JST",
        "mpn_pattern": f"B{pins}B-PH-K-S",
        "description": f"JST PH series 2.0mm pitch {pins}-pin through-hole connector, "
                       f"vertical top entry. Common for LiPo battery and signal connections.",
        "parameters": {"pitch_mm": PITCH, "pins": pins, "mounting": "THT", "orientation": "vertical"},
        "files": {
            "footprint": f"{fid}.kicad_mod",
            "symbol": f"{fid}.kicad_sym",
            "model_3d": f"{fid}.step",
            "preview": f"{fid}.glb",
            "footprint_svg": f"{fid}.footprint.svg",
            "symbol_svg": f"{fid}.symbol.svg",
        },
        "formats": ["kicad_mod", "kicad_sym", "step", "glb"],
        "datasheet": "https://www.jst-mfg.com/product/pdf/eng/ePH.pdf",
        "dimensions_source": "Footprint matches KiCad official Connector_JST (JST datasheet-derived). 3D model representative.",
        "verified": True,
        "license": "CC-BY-4.0",
        "generated_by": "generators/jst_ph.py",
        "keywords": ["jst", "ph", "2.0mm", "connector", "battery", "lipo", f"{pins}pin"],
    }


def generate(pins):
    fid = f"jst_ph_{pins}pin"
    part_dir = os.path.normpath(os.path.join(LIB_ROOT, fid))
    os.makedirs(part_dir, exist_ok=True)
    with open(os.path.join(part_dir, f"{fid}.kicad_mod"), "w", encoding="utf-8") as f:
        f.write(gen_footprint(pins, fid))
    with open(os.path.join(part_dir, f"{fid}.kicad_sym"), "w", encoding="utf-8") as f:
        f.write(gen_symbol(pins, fid))
    meta = gen_meta(pins, fid)
    with open(os.path.join(part_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    return meta


def build_index(metas):
    index = {
        "generated_by": "opencad-lib",
        "count": len(metas),
        "parts": [
            {
                "id": m["id"], "name": m["name"], "category": m["category"],
                "family": m["family"], "manufacturer": m["manufacturer"],
                "pins": m["parameters"]["pins"],
                "path": f"library/connector/jst/ph/{m['id']}",
                "formats": m["formats"], "verified": m["verified"], "keywords": m["keywords"],
            }
            for m in metas
        ],
    }
    index_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "index.json"))
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    print(f"  index.json -> {len(metas)} parts")


if __name__ == "__main__":
    print(f"Generating JST-PH full family ({PINS_RANGE.start}..{PINS_RANGE.stop - 1} pin)...")
    metas = [generate(p) for p in PINS_RANGE]
    for m in metas:
        print(f"  {m['id']}")
    build_index(metas)
    print("Done.")
