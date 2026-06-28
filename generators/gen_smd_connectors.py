"""
SMD 커넥터 패밀리 생성기 (config 기반) — JST-GH 등.
실행: python generators/gen_smd_connectors.py
신호패드(핀1=원점, +X, 피치) + 마운팅탭(MP) + 자체 외곽선. 심볼은 gen_connectors.gen_symbol 재사용.
패드 치수=KiCad 공식/데이터시트 사실, 외곽선=자체작성(CC-BY 클린).
"""
import json
import os
from gen_connectors import _line, gen_symbol, LIB_ROOT  # 헬퍼/심볼 재사용

GH = dict(
    key="jst_gh", name="JST GH", manufacturer="JST", mpn="BM{n:02d}B-GHS-TBT",
    desc="JST GH series 1.25mm pitch {n}-pin SMD connector, vertical top entry. "
         "Common in drones/RC (Pixhawk) and compact signal links.",
    datasheet="https://www.jst-mfg.com/product/pdf/eng/eGH.pdf",
    lib_path="connector/jst/gh", pitch=1.25, pins=list(range(2, 13)),
    sig=(0.6, 1.7), sig_y=1.95, mp=(1.0, 2.8), mp_y=-1.4, mp_out=1.85,
    body_h=3.4,
)
FAMILIES = [GH]


def _box(x0, y0, x1, y1, layer, w):
    return [_line(x0, y0, x1, y0, layer, w), _line(x1, y0, x1, y1, layer, w),
            _line(x1, y1, x0, y1, layer, w), _line(x0, y1, x0, y0, layer, w)]


def gen_footprint(cfg, n, fid):
    p = cfg["pitch"]
    R = (n - 1) * p
    sw, sh = cfg["sig"]
    sy = cfg["sig_y"]
    mw, mh = cfg["mp"]
    my = cfg["mp_y"]
    mo = cfg["mp_out"]
    cx = R / 2.0
    out = [f'(footprint "{fid}" (version 20221018) (generator opencad-lib)',
           '  (layer "F.Cu")',
           f'  (descr "{cfg["name"]} {cfg["pitch"]}mm {n}-pin SMD vertical. '
           f'Pad land pattern per KiCad official Connector_JST (datasheet); body outline original.")',
           f'  (tags "{cfg["name"]} connector {cfg["pitch"]}mm {n}pin SMD")',
           '  (attr smd)',
           f'  (fp_text reference "REF**" (at {cx:.3f} -3.6) (layer "F.SilkS")'
           '\n    (effects (font (size 1 1) (thickness 0.15))))',
           f'  (fp_text value "{fid}" (at {cx:.3f} 3.6) (layer "F.Fab")'
           '\n    (effects (font (size 1 1) (thickness 0.15))))']
    # 자체 외곽선 (패드 비침범 계산됨)
    out += _box(-2.5, -2.5, R + 2.5, 1.5, "F.Fab", 0.10)
    out += _box(-1.0, -2.0, R + 1.0, 0.9, "F.SilkS", 0.12)
    out.append(_line(-0.9, 1.5, -0.9, 2.4, "F.SilkS", 0.12))  # pin1 틱
    out += _box(-2.85, -3.05, R + 2.85, 3.05, "F.CrtYd", 0.05)
    # 신호 패드 (핀1=원점, +X)
    for i in range(n):
        out.append(f'  (pad "{i+1}" smd roundrect (at {i*p:.3f} {sy}) (size {sw} {sh}) '
                   f'(layers "F.Cu" "F.Mask" "F.Paste") (roundrect_rratio 0.25))')
    # 마운팅 탭
    for mx in (-mo, R + mo):
        out.append(f'  (pad "MP" smd roundrect (at {mx:.3f} {my}) (size {mw} {mh}) '
                   f'(layers "F.Cu" "F.Mask" "F.Paste") (roundrect_rratio 0.25))')
    out.append(')')
    return "\n".join(out) + "\n"


def gen_meta(cfg, n, fid):
    mpn = cfg["mpn"].format(n=n)
    return {
        "id": fid, "name": f"{cfg['name']} {n}-pin ({mpn})",
        "category": "connector", "family": cfg["name"], "manufacturer": cfg["manufacturer"],
        "mpn_pattern": mpn, "description": cfg["desc"].format(n=n),
        "parameters": {"pitch_mm": cfg["pitch"], "pins": n, "mounting": "SMD", "orientation": "vertical"},
        "files": {"footprint": f"{fid}.kicad_mod", "symbol": f"{fid}.kicad_sym",
                  "model_3d": f"{fid}.step", "preview": f"{fid}.glb",
                  "footprint_svg": f"{fid}.footprint.svg", "symbol_svg": f"{fid}.symbol.svg"},
        "formats": ["kicad_mod", "kicad_sym", "step", "glb"],
        "datasheet": cfg["datasheet"],
        "dimensions_source": "Pad land pattern per KiCad official Connector_JST (datasheet); outline original.",
        "verified": True, "license": "CC-BY-4.0", "generated_by": "generators/gen_smd_connectors.py",
        "keywords": [cfg["key"].split("_")[0], cfg["key"].split("_")[1], f"{cfg['pitch']}mm",
                     "connector", "smd", f"{n}pin"],
    }


def main():
    for cfg in FAMILIES:
        for n in cfg["pins"]:
            fid = f"{cfg['key']}_{n}pin"
            d = os.path.normpath(os.path.join(LIB_ROOT, cfg["lib_path"], fid))
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, f"{fid}.kicad_mod"), "w", encoding="utf-8").write(gen_footprint(cfg, n, fid))
            open(os.path.join(d, f"{fid}.kicad_sym"), "w", encoding="utf-8").write(gen_symbol(cfg, n, fid))
            json.dump(gen_meta(cfg, n, fid), open(os.path.join(d, "meta.json"), "w", encoding="utf-8"),
                      indent=2, ensure_ascii=False)
        print(f"  {cfg['name']}: {len(cfg['pins'])} parts")
    print("Done.")


if __name__ == "__main__":
    print("Generating SMD connector families...")
    main()
