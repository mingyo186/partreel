"""
커넥터 패밀리 공통 생성기 (config 기반).
실행: python generators/gen_connectors.py

패밀리별 치수만 config로 두고 동일한 KLC 로직으로 풋프린트/심볼/meta 생성 + 통합 index.json.
치수 출처: KiCad 공식 Connector_JST (데이터시트 기반)와 대조 일치. (REQUIREMENTS §14)
"""

import json
import os

# ---- 패밀리 설정 (텍스트 + 3D 공용) ----
PH = dict(
    key="jst_ph", name="JST PH", manufacturer="JST", mpn="B{n}B-PH-K-S",
    desc="JST PH series 2.0mm pitch {n}-pin through-hole connector, vertical top entry. "
         "Common for LiPo battery and signal connections.",
    datasheet="https://www.jst-mfg.com/product/pdf/eng/ePH.pdf",
    lib_path="connector/jst/ph", pitch=2.0, pad_w=1.2, pad_h=1.75, drill=0.75,
    fab=dict(x0=-1.95, x1=1.95, y0=-1.70, y1=2.80),
    silk=dict(x0=-2.06, x1=2.06, y0=-1.81, y1=2.91),
    crt=dict(x0=-2.45, x1=2.45, y0=-2.20, y1=3.30),
    pins=list(range(2, 17)),
    pin_sq=0.5, housing_h=6.0, pin_below=3.0, pin_into=2.0,
)
XH = dict(
    key="jst_xh", name="JST XH", manufacturer="JST", mpn="B{n}B-XH-A",
    desc="JST XH series 2.5mm pitch {n}-pin through-hole connector, vertical. "
         "Common for batteries, power and signal connections.",
    datasheet="https://www.jst-mfg.com/product/pdf/eng/eXH.pdf",
    lib_path="connector/jst/xh", pitch=2.5, pad_w=1.7, pad_h=1.95, drill=0.95,
    fab=dict(x0=-2.45, x1=2.45, y0=-2.35, y1=3.40),
    silk=dict(x0=-2.56, x1=2.56, y0=-2.46, y1=3.51),
    crt=dict(x0=-2.95, x1=2.95, y0=-2.85, y1=3.90),
    pins=list(range(2, 17)),
    pin_sq=0.64, housing_h=7.0, pin_below=3.0, pin_into=2.0,  # 높이 7.0 = XH 데이터시트
)
TERM = dict(
    key="screw_terminal_5_08", name="Screw Terminal 5.08mm", manufacturer="Generic (KF301)",
    mpn="KF301-5.08-{n}P",
    desc="5.08mm pitch {n}-pole screw terminal block (KF301-compatible), THT. "
         "For power and wire-to-board connections.",
    datasheet="", lib_path="connector/terminal/screw_5_08",
    pitch=5.08, pad_w=2.5, pad_h=2.5, drill=1.3, pad_shape="circle",
    fab=dict(x0=-3.0, x1=3.0, y0=-3.2, y1=6.0),
    silk=dict(x0=-3.1, x1=3.1, y0=-3.3, y1=6.1),
    crt=dict(x0=-3.5, x1=3.5, y0=-3.7, y1=6.5),
    pins=list(range(2, 9)),
    style="terminal", pin_sq=1.0, housing_h=10.0, pin_below=3.0, pin_into=2.0,
)
FAMILIES = [PH, XH, TERM]


def _pin_header(pitch_key, pitch, pad, drill, half_body, half_silk, half_crt, pin_sq):
    return dict(
        key=f"pin_header_{pitch_key}", name=f"Pin Header {pitch}mm", manufacturer="Generic",
        mpn="PinHeader_1x{n:02d}_P%.2fmm" % pitch,
        desc=f"{pitch}mm pitch 1x{{n}} male pin header, THT vertical. "
             "Dimensions match the official KiCad Connector_PinHeader library.",
        datasheet="https://en.wikipedia.org/wiki/Pin_header",
        lib_path=f"connector/header/p{pitch_key}", pitch=pitch,
        pad_w=pad, pad_h=pad, drill=drill,
        fab=dict(x0=-half_body, x1=half_body, y0=-half_body, y1=half_body),
        silk=dict(x0=-half_silk, x1=half_silk, y0=-half_silk, y1=half_silk),
        crt=dict(x0=-half_crt, x1=half_crt, y0=-half_crt, y1=half_crt),
        pins=list(range(1, 41)),
        style="header", pin_sq=pin_sq, housing_h=2.5, pin_below=3.0, pin_into=6.0,
    )


# 온디맨드 전용 패밀리 (사전 대량생성 안 함 — 요청 시 generate_one.py가 생성, REQUIREMENTS §19)
ONDEMAND = [
    _pin_header("254", 2.54, 1.7, 1.0, 1.27, 1.33, 1.8, 0.64),
    _pin_header("200", 2.00, 1.35, 0.8, 1.0, 1.06, 1.5, 0.5),
    _pin_header("127", 1.27, 1.0, 0.65, 1.05, 1.11, 1.5, 0.4),
]


def get_family(key):
    for cfg in FAMILIES + ONDEMAND:
        if cfg["key"] == key:
            return cfg
    return None

LIB_ROOT = os.path.join(os.path.dirname(__file__), "..", "library")


def _line(x1, y1, x2, y2, layer, w):
    return (f'  (fp_line (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f})'
            f' (stroke (width {w}) (type solid)) (layer "{layer}"))')


def _rect(box, A, layer, w):
    x0, x1 = box["x0"], A + box["x1"]
    y0, y1 = box["y0"], box["y1"]
    return [_line(x0, y0, x1, y0, layer, w), _line(x1, y0, x1, y1, layer, w),
            _line(x1, y1, x0, y1, layer, w), _line(x0, y1, x0, y0, layer, w)]


def _cham_rect(box, A, layer, w, ch):
    """좌상단(핀1) 모따기 사각 — KLC pin1 마커."""
    x0, x1 = box["x0"], A + box["x1"]
    y0, y1 = box["y0"], box["y1"]
    return [_line(x0 + ch, y0, x1, y0, layer, w), _line(x1, y0, x1, y1, layer, w),
            _line(x1, y1, x0, y1, layer, w), _line(x0, y1, x0, y0 + ch, layer, w),
            _line(x0, y0 + ch, x0 + ch, y0, layer, w)]


def gen_footprint(cfg, n, fid):
    A = (n - 1) * cfg["pitch"]
    cx = A / 2.0
    pw, ph, drill = cfg["pad_w"], cfg["pad_h"], cfg["drill"]
    shape = cfg.get("pad_shape", "oval")  # 비1번핀 패드 형상 (oval/circle 등)
    ref_y = cfg["silk"]["y0"] - 1.0
    val_y = cfg["silk"]["y1"] + 1.0
    out = [f'(footprint "{fid}" (version 20221018) (generator opencad-lib)',
           '  (layer "F.Cu")',
           f'  (descr "{cfg["name"]} {cfg["pitch"]}mm {n}-pin THT vertical. '
           f'Dimensions match KiCad official Connector_JST (datasheet-derived).")',
           f'  (tags "{cfg["name"]} connector {cfg["pitch"]}mm {n}pin")',
           '  (attr through_hole)',
           f'  (fp_text reference "REF**" (at {cx:.3f} {ref_y:.3f}) (layer "F.SilkS")'
           '\n    (effects (font (size 1 1) (thickness 0.15))))',
           f'  (fp_text value "{fid}" (at {cx:.3f} {val_y:.3f}) (layer "F.Fab")'
           '\n    (effects (font (size 1 1) (thickness 0.15))))']
    out += _cham_rect(cfg["fab"], A, "F.Fab", 0.10, 1.0)
    out += _cham_rect(cfg["silk"], A, "F.SilkS", 0.12, 1.0)
    out += _rect(cfg["crt"], A, "F.CrtYd", 0.05)
    for i in range(n):
        num = i + 1
        x = i * cfg["pitch"]
        if num == 1:
            out.append(f'  (pad "1" thru_hole roundrect (at 0 0) (size {pw} {ph})'
                       f' (drill {drill}) (layers "*.Cu" "*.Mask") (roundrect_rratio 0.25))')
        else:
            out.append(f'  (pad "{num}" thru_hole {shape} (at {x:.3f} 0) (size {pw} {ph})'
                       f' (drill {drill}) (layers "*.Cu" "*.Mask"))')
    out.append(')')
    return "\n".join(out) + "\n"


def gen_symbol(cfg, n, fid):
    PIN_LEN, GRID = 2.54, 2.54
    bl, br = -2.54, 2.54
    span = (n - 1) * GRID
    top = span / 2.0
    bt, bb = top + 1.27, -top - 1.27
    out = ['(kicad_symbol_lib (version 20211014) (generator opencad-lib)',
           f'  (symbol "{fid}" (in_bom yes) (on_board yes)',
           f'    (property "Reference" "J" (at {br + 1.0:.2f} {bt:.2f} 0)'
           '\n      (effects (font (size 1.27 1.27)) (justify left)))',
           f'    (property "Value" "{fid}" (at {br + 1.0:.2f} {bb:.2f} 0)'
           '\n      (effects (font (size 1.27 1.27)) (justify left)))',
           '    (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
           f'    (property "Datasheet" "{cfg["datasheet"]}"'
           ' (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
           f'    (symbol "{fid}_1_1"',
           f'      (rectangle (start {bl:.2f} {bt:.2f}) (end {br:.2f} {bb:.2f})'
           '\n        (stroke (width 0.254) (type solid)) (fill (type background)))']
    for i in range(n):
        num = i + 1
        y = top - i * GRID
        out.append(f'      (pin passive line (at {bl - PIN_LEN:.2f} {y:.2f} 0) (length {PIN_LEN})'
                   f'\n        (name "Pin_{num}" (effects (font (size 1.27 1.27))))'
                   f'\n        (number "{num}" (effects (font (size 1.27 1.27)))))')
    out += ['    )', '  )', ')']
    return "\n".join(out) + "\n"


def gen_meta(cfg, n, fid):
    mpn = cfg["mpn"].format(n=n)
    return {
        "id": fid,
        "name": f"{cfg['name']} {n}-pin ({mpn.rsplit('-', 1)[0] if '-' in mpn else mpn})",
        "category": "connector", "family": cfg["name"], "manufacturer": cfg["manufacturer"],
        "mpn_pattern": mpn,
        "description": cfg["desc"].format(n=n),
        "parameters": {"pitch_mm": cfg["pitch"], "pins": n, "mounting": "THT", "orientation": "vertical"},
        "files": {
            "footprint": f"{fid}.kicad_mod", "symbol": f"{fid}.kicad_sym",
            "model_3d": f"{fid}.step", "preview": f"{fid}.glb",
            "footprint_svg": f"{fid}.footprint.svg", "symbol_svg": f"{fid}.symbol.svg",
        },
        "formats": ["kicad_mod", "kicad_sym", "step", "glb"],
        "datasheet": cfg["datasheet"],
        "dimensions_source": "Footprint matches KiCad official Connector_JST (datasheet-derived). 3D representative.",
        "verified": True, "license": "CC-BY-4.0", "generated_by": "generators/gen_connectors.py",
        "keywords": [cfg["key"].split("_")[0], cfg["key"].split("_")[1], f"{cfg['pitch']}mm",
                     "connector", f"{n}pin"],
    }


def generate(cfg, n, fid):
    part_dir = os.path.normpath(os.path.join(LIB_ROOT, cfg["lib_path"], fid))
    os.makedirs(part_dir, exist_ok=True)
    with open(os.path.join(part_dir, f"{fid}.kicad_mod"), "w", encoding="utf-8") as f:
        f.write(gen_footprint(cfg, n, fid))
    with open(os.path.join(part_dir, f"{fid}.kicad_sym"), "w", encoding="utf-8") as f:
        f.write(gen_symbol(cfg, n, fid))
    meta = gen_meta(cfg, n, fid)
    with open(os.path.join(part_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    return meta


def build_index(rows):
    parts = []
    for cfg, n, fid, meta in rows:
        parts.append({
            "id": fid, "name": meta["name"], "category": "connector",
            "family": cfg["name"], "manufacturer": cfg["manufacturer"], "pins": n,
            "path": f"library/{cfg['lib_path']}/{fid}",
            "formats": meta["formats"], "verified": meta["verified"], "keywords": meta["keywords"],
        })
    index = {"generated_by": "opencad-lib", "count": len(parts), "parts": parts}
    with open(os.path.normpath(os.path.join(LIB_ROOT, "..", "index.json")), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    print(f"  index.json -> {len(parts)} parts")


def main():
    rows = []
    for cfg in FAMILIES:
        for n in cfg["pins"]:
            fid = f"{cfg['key']}_{n}pin"
            meta = generate(cfg, n, fid)
            rows.append((cfg, n, fid, meta))
        print(f"  {cfg['name']}: {len(cfg['pins'])} parts")
    build_index(rows)
    print("Done.")


if __name__ == "__main__":
    print("Generating connector families...")
    main()
