"""
칩 캐패시터 생성기 (값-파라메트릭) — §24/§25 블록 작업에서 없는 값이 나올 때마다
부품 우선 원칙대로 정식 등록하기 위한 도구.

풋프린트: import_antmicro.chip_footprint (IPC-7351 밀도 B, §21-C 근거 그대로 —
  1005(0402)는 KEMET 권장 랜드, provenance DIFFERENT 검증 이력 있음).
심볼: 자체 작성 IEC 사각형 저항 (공식 라이브러리 카피 아님).
치수 근거: Samsung CL 시리즈 데이터시트 (몸체 1.0x0.5mm @0402) + KEMET 랜드.

실행: python generators/gen_chip_c.py <mpn> <값표시> <크기키>
                [<벤더> <유전체> <정격전압> <데이터시트URL>]
예:   python generators/gen_chip_c.py CL05A105KA5NNNC 1uF 1005
      python generators/gen_chip_c.py C0805C222K1RACTU 2.2nF 2012 kemet X7R 100V              https://content.kemet.com/datasheets/KEM_C1002_X7R_SMD.pdf
"""

import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from import_antmicro import chip_footprint  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SIZE_NAME = {"1005": "0402", "2012": "0805", "3216": "1206"}
VENDOR_NAME = {"samsung": "Samsung Electro-Mechanics", "kemet": "KEMET"}
VENDOR_SHORT = {"samsung": "Samsung", "kemet": "KEMET"}  # 표시 이름용 짧은 이름
BODY_MM = {"1005": "1.0x0.5mm", "2012": "2.0x1.25mm", "3216": "3.2x1.6mm"}
VENDOR_DS = {
    "samsung": "https://weblib.samsungsem.com/mlcc/mlcc-ec-data-sheet.do?partNumber={mpn}",
    "kemet": "https://content.kemet.com/datasheets/KEM_C1002_X7R_SMD.pdf",
}


def r_symbol(pid, value):
    """평행판 캐패시터 심볼 (자체 작성): 핀1 좌, 핀2 우, 판 2장."""
    return f"""(kicad_symbol_lib (version 20231120) (generator "partreel-gen-chip-c")
  (symbol "{pid}" (pin_numbers hide) (pin_names (offset 0) hide) (in_bom yes) (on_board yes)
    (property "Reference" "C" (at 0 2.54 0) (effects (font (size 1.27 1.27))))
    (property "Value" "{value}" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))
    (symbol "{pid}_1_1"
      (polyline (pts (xy -0.508 1.524) (xy -0.508 -1.524))
        (stroke (width 0.3048) (type solid)) (fill (type none)))
      (polyline (pts (xy 0.508 1.524) (xy 0.508 -1.524))
        (stroke (width 0.3048) (type solid)) (fill (type none)))
      (pin passive line (at -3.81 0 0) (length 3.302)
        (name "~" (effects (font (size 1.27 1.27))))
        (number "1" (effects (font (size 1.27 1.27)))))
      (pin passive line (at 3.81 0 180) (length 3.302)
        (name "~" (effects (font (size 1.27 1.27))))
        (number "2" (effects (font (size 1.27 1.27)))))
    )))"""


def main():
    if len(sys.argv) not in (4, 7, 8):
        print(__doc__)
        return 2
    mpn, value, size_key = sys.argv[1], sys.argv[2], sys.argv[3]
    vendor = sys.argv[4] if len(sys.argv) > 4 else "samsung"
    dielectric = sys.argv[5] if len(sys.argv) > 5 else "X5R"
    voltage = sys.argv[6] if len(sys.argv) > 6 else "25V"
    datasheet = sys.argv[7] if len(sys.argv) > 7 else         VENDOR_DS[vendor].format(mpn=mpn)
    size = SIZE_NAME[size_key]
    pid = mpn.lower().replace("-", "_")
    pid = f"{vendor}_{pid}"
    d = os.path.join(ROOT, "library", "passive", vendor, pid)
    os.makedirs(d, exist_ok=True)

    fp = chip_footprint(pid, size_key)
    with open(os.path.join(d, f"{pid}.kicad_mod"), "w", encoding="utf-8", newline="\n") as f:
        f.write(fp)
    with open(os.path.join(d, f"{pid}.kicad_sym"), "w", encoding="utf-8", newline="\n") as f:
        f.write(r_symbol(pid, value))

    meta = {
        "id": pid,
        # Samsung CL 코드: CL05 A 105 K A5: A=X5R, K=±10%, A5=25V
        "name": f"{value} 10% {size} MLCC ({VENDOR_SHORT[vendor]} {mpn})",
        "category": "passive",
        "family": f"chip_capacitor_{size}",
        "manufacturer": VENDOR_NAME[vendor],
        "mpn_pattern": mpn,
        "description": f"MLCC ceramic capacitor {value} +-10% {size} "
                       f"({size_key} metric), {dielectric} {voltage}. "
                       f"Generated for PartReel circuit blocks.",
        "keywords": ["capacitor", value, size, "chip", "smd",
                     dielectric.lower(), voltage.lower()],
        "parameters": {"pins": 2, "mounting": "smd"},
        "formats": ["kicad_mod", "kicad_sym"],
        "tier": "verified-2d",
        "license": "CC-BY-4.0",
        "datasheet": datasheet,
        "dimensions_source": "Land: IPC-7351 density B nominal for chip "
                             f"{size_key} metric (KEMET C1002 X7R SMD Table 3, see "
                             "generators/import_antmicro.CHIP_LAND, §21-C). Body "
                             f"{BODY_MM[size_key]} per the same catalog Dimensions "
                             f"table ({size}/{size_key} metric); part {mpn} = "
                             f"{value} {dielectric} {voltage}.",
        "files": {
            "footprint": f"{pid}.kicad_mod",
            "symbol": f"{pid}.kicad_sym",
        },
    }
    with open(os.path.join(d, "meta.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    print(f"OK {pid} -> {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
