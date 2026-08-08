"""
KiCad 디자인 블록 라이브러리 빌더 (§24) — blocks/ -> PartReel.kicad_blocks

형식 근거 (1차 사료: KiCad 소스 common/design_block_io.cpp, 2026-08-10 확인):
  <라이브러리>.kicad_blocks/            <- 라이브러리 = 이 확장자의 디렉터리
    <블록명>.kicad_block/               <- 블록 = 이 확장자의 하위 디렉터리
      <블록명>.kicad_sch                <- 회로도 (필수)
      <블록명>.json                     <- {description, keywords, fields{}}
등록: design-block-lib-table 에 (lib (name ...)(type "KiCad")(uri ...)).
KiCad 회로도 편집기의 디자인 블록 패널에서 드래그해 메인 시트에 붙인다 —
'메인 시트에 부품 시트가 달라붙는' 사용자가 기억한 그 방식.

실행: python generators/build_design_blocks.py
"""

import glob
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "dist", "design_blocks", "PartReel.kicad_blocks")


def main():
    os.makedirs(OUT, exist_ok=True)
    built = []
    for bj in glob.glob(os.path.join(ROOT, "blocks", "*", "*", "block.json")):
        d = os.path.dirname(bj)
        b = json.load(open(bj, encoding="utf-8"))
        bid = b["id"]
        sch = os.path.join(d, f"{bid}.kicad_sch")
        if not os.path.exists(sch):
            print(f"SKIP {bid}: .kicad_sch 없음 (build_block 먼저)")
            continue
        dbd = os.path.join(OUT, f"{bid}.kicad_block")
        os.makedirs(dbd, exist_ok=True)
        shutil.copy(sch, os.path.join(dbd, f"{bid}.kicad_sch"))
        rev = str(b.get("revision", "0.1"))
        meta = {
            "description": f"{b['name']} (rev {rev}) — {b['description'][:120]}",
            "keywords": " ".join([b.get("id", ""), os.path.basename(os.path.dirname(d))]
                                 + b["name"].lower().split()[:4]),
            "fields": {"Revision": rev},
        }
        with open(os.path.join(dbd, f"{bid}.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(meta, f, indent=1, ensure_ascii=False)
        built.append(bid)
    print(f"디자인 블록 {len(built)}개 -> {OUT}")
    print(" ", ", ".join(built))
    return 0


if __name__ == "__main__":
    sys.exit(main())
