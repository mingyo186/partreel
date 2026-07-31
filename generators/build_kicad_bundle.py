"""
KiCad 로컬 번들 생성기 (REQUIREMENTS §18-A 2단계).

엄선판(수입 물결 antmicro_/cern_ 제외) 부품의:
- 심볼 전부를 assets/PartReel.kicad_sym 한 파일로 병합 (심볼명 = 부품 id,
  서브유닛 "<id>_0_1" 접두까지 일괄 개명 — HTTP lib의 symbolIdStr와 일치)
- 풋프린트 전부를 assets/PartReel-pretty.zip (PartReel.pretty/<id>.kicad_mod)
- 포함 목록을 assets/kicad-bundle-manifest.json (워커가 symbolIdStr 폴백 판단)

실행: python generators/build_kicad_bundle.py
"""
import json
import os
import re
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ASSETS = os.path.join(ROOT, "assets")

CURATED_EXCLUDE = re.compile(r"^(antmicro_|cern_)")

PLACEHOLDER = '''  (symbol "PLACEHOLDER" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
    (property "Reference" "U" (at 0 8.89 0)
      (effects (font (size 1.27 1.27))))
    (property "Value" "PartReel part" (at 0 -8.89 0)
      (effects (font (size 1.27 1.27))))
    (symbol "PLACEHOLDER_0_1"
      (rectangle (start -10.16 6.35) (end 10.16 -6.35)
        (stroke (width 0.254) (type solid)) (fill (type background)))
      (text "PartReel placeholder" (at 0 2.54 0)
        (effects (font (size 1.27 1.27))))
      (text "Real symbol/footprint:" (at 0 0 0)
        (effects (font (size 1.016 1.016))))
      (text "see 'PartReel' field URL" (at 0 -2.54 0)
        (effects (font (size 1.016 1.016))))
    )
  )'''


def balanced_block(text, start):
    depth, i, in_str = 0, start, False
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == '"' and text[i - 1] != "\\":
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    return None


def top_symbols(lib_text):
    out = []
    for m in re.finditer(r'\(symbol\s+"([^"]+)"', lib_text):
        # 최상위만: 블록 시작 앞의 들여쓰기 깊이로 판별하는 대신,
        # 이미 수집한 블록 내부에 포함되는 매치는 건너뛴다.
        if any(s <= m.start() < e for s, e, _, _ in out):
            continue
        blk = balanced_block(lib_text, m.start())
        if blk:
            out.append((m.start(), m.start() + len(blk), m.group(1), blk))
    return [(name, blk) for _, _, name, blk in out]


def merge_symbol(pid, sym_text):
    """부품 심볼 파일 → 최상위 심볼을 pid로 개명한 블록 (서브유닛 접두 포함)."""
    tops = top_symbols(sym_text)
    if not tops:
        return None
    name, blk = tops[0]  # 우리 부품 파일은 심볼 1개 (멀티유닛 CERN은 엄선판 제외)
    if name != pid:
        blk = blk.replace(f'"{name}', f'"{pid}')
    # 방어: 부모와 접두가 다른 서브유닛도 pid로 정규화 (aht30 사건 재발 대비 —
    # 게이트가 소스에서 막지만 번들은 독립적으로도 안전해야 함)
    blk = re.sub(r'\(symbol\s+"(?:[^"]+?)_(\d+)_(\d+)"',
                 lambda m: f'(symbol "{pid}_{m.group(1)}_{m.group(2)}"', blk)
    return blk


def main():
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    parts = [p for p in index["parts"] if not CURATED_EXCLUDE.match(p["id"])]
    print(f"엄선판 대상: {len(parts)}")

    blocks, included, skipped = [], [], []
    zpath = os.path.join(ASSETS, "PartReel-pretty.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in parts:
            pid = p["id"]
            d = os.path.join(ROOT, p["path"])
            sym_p = os.path.join(d, f"{pid}.kicad_sym")
            mod_p = os.path.join(d, f"{pid}.kicad_mod")
            if not (os.path.exists(sym_p) and os.path.exists(mod_p)):
                skipped.append((pid, "files missing")); continue
            blk = merge_symbol(pid, open(sym_p, encoding="utf-8").read())
            if not blk:
                skipped.append((pid, "no symbol block")); continue
            blocks.append("  " + blk.replace("\n", "\n  ").rstrip())
            z.write(mod_p, f"PartReel.pretty/{pid}.kicad_mod")
            included.append(pid)

    lib = ("(kicad_symbol_lib (version 20231120) (generator \"partreel-bundle\")\n"
           + PLACEHOLDER + "\n" + "\n".join(blocks) + "\n)\n")
    open(os.path.join(ASSETS, "PartReel.kicad_sym"), "w", encoding="utf-8",
         newline="\n").write(lib)
    json.dump({"symbols": included, "count": len(