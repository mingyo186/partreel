"""
칩 캐패시터 생성기 (값-파라메트릭) — §24/§25 블록 작업에서 없는 값이 나올 때마다
부품 우선 원칙대로 정식 등록하기 위한 도구.

풋프린트: import_antmicro.chip_footprint (IPC-7351 밀도 B, §21-C 근거 그대로 —
  1005(0402)는 KEMET 권장 랜드, provenance DIFFERENT 검증 이력 있음).
심볼: 자체 작성 IEC 사각형 저항 (공식 라이브러리 카피 아님).
치수 근거: Samsung CL 시리즈 데이터시트 (몸체 1.0x0.5mm @0402) + KEMET 랜드.

실행: python generators/gen_chip_r.py <mpn> <값표시> <크기키>
예:   python generators/gen_chip_r.py CRCW04025K10FKED 5.1k 1005
"""

import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from import_antmicro import chip_footprint  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SIZE_NAME = {"1005": "0402", "3216": "1206"}


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
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    mpn, value, size_key = sys.argv[1], sys.argv[2], sys.argv[3]
    size = SIZE_NAME[size_key]
    pid = mpn.lower().replace("-", "_")
    pid = f"samsung_{pid}"
    d = os.path.join(ROOT, "library", "passive", "samsung", pid)
    os.makedirs(d, exist_ok=True)

    fp = chip_footprint(pid, size_key)
    with open(os.path.join(d, f"{pid}.kicad_mod"), "w", encoding="utf-8", newline="\n") as f:
        f.write(fp)
    with open(os.path.join(d, f"{pid}.kicad_sym"), "w", encoding="utf-8", newline="\n") as f:
        f.write(r_symbol(pid, value))

    meta = {
        "id": pid,
        "name": f"{value} 1% {size} (Vishay {mpn})",
        "category": "passive",
        "family": f"chip_resistor_{size}",
        "manufacturer": "Samsung Electro-Mechanics",
        "mpn_pattern": mpn,
        "description": f"MLCC ceramic capacitor {value} +-1% {size} "
                       f"({'/'.join(size_key)}mm metric), X5R 25V. "
                       f"Generated for PartReel circuit blocks.",
        "keywords": ["capacitor", value, size, "chip", "smd"],
        "parameters": {"pins": 2, "mounting": "smd"},
        "formats": ["kicad_mod", "kicad_sym"],
        "tier": "verified-2d",
        "license": "CC-BY-4.0",
        "datasheet": "https://weblib.samsungsem.com/mlcc/mlcc-ec-data-sheet.do?partNumber=CL05A105KA5NNNC",
        "dimensions_source": "Land: IPC-7351 density B nominal for chip "
                             f"{size_key} metric (KEMET recommended land, see "
                             "generators/import_antmicro.CHIP_LAND, §21-C). Body "
                             "1.0x0.5mm per Vishay CRCW e3 datasheet (doc 20035) "
                             "Dimensions table, 0402 row.",
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
