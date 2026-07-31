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


def _prop(name, value, y=0):
    """KiCad 10 표준 property 블록 (숨김) — 공식 라이브러리와 동일 형식."""
    v = str(value or "").replace("\\", "\\\\").replace('"', '\\"')
    return (f'      (property "{name}" "{v}"\n'
            f'        (at 0 {y} 0)\n'
            f'        (show_name no)\n'
            f'        (do_not_autoplace no)\n'
            f'        (hide yes)\n'
            f'        (effects (font (size 1.27 1.27)))\n'
            f'      )')


def enrich(blk, pid, meta):
    """심볼에 Footprint/Datasheet/Description/ki_keywords 주입.

    이걸 넣어야 로컬 라이브러리만으로 자립한다 — 선택창 검색(설명·키워드),
    배치 시 풋프린트 자동 지정, 데이터시트 링크가 네트워크 없이 동작
    (§18-A 3단계: KiCad의 전량 선주입 때문에 온라인 의존을 줄이는 방향).
    """
    props = [
        _prop("Footprint", f"PartReel:{pid}"),
        _prop("Datasheet", meta.get("datasheet")),
        _prop("Description", meta.get("description")),
        _prop("ki_keywords", " ".join(meta.get("keywords") or [])),
        _prop("PartReel", f"https://partreel.com/p/{pid}/"),
    ]
    # 원본에 이미 있는 동명 property 제거 (중복이면 KiCad가 빈 쪽을 쓸 수 있음)
    for name in ("Footprint", "Datasheet", "Description", "ki_keywords", "PartReel"):
        while True:
            m = re.search(r'\n[ \t]*\(property "' + re.escape(name) + r'"', blk)
            if not m:
                break
            start = blk.index("(property", m.start())
            end = start + len(balanced_block(blk, start) or "")
            blk = blk[:m.start()] + blk[end:]
    # Value property 블록 뒤에 삽입 (없으면 심볼 헤더 다음 줄)
    m = re.search(r'^\s*\(property "Value".*?\)\)\)\s*$', blk, re.M)
    if m:
        return blk[:m.end()] + "\n" + "\n".join(props) + blk[m.end():]
    head, _, rest = blk.partition("\n")
    return head + "\n" + "\n".join(props) + "\n" + rest


def merge_symbol(pid, sym_text):
    """부품 심볼 파일 → 최상위 심볼을 pid로 개명한 블록 (서브유닛 접두 포함)."""
    tops = top_symbols(sym_text)
    if not tops:
        return None
    name, blk = tops[0]  # 우리 부품 파일은 심볼 1개 (멀티유닛 CERN은 엄선판 제외)
    if name != pid:
        blk = blk.replace(f'"{name}', f'"{pid}')
    # 방어: 부모와 접두가 다른 "내부" 서브유닛만 pid로 정규화 (aht30 사건).
    # 주의: 부품 id 자체가 _N_M로 끝날 수 있어(sparkfun_..._jps_3_1) 이름
    # 패턴만으로 상위/서브를 구분하면 안 됨 — 첫 심볼 헤더(상위)는 제외하고
    # 나머지 영역에만 적용 + 접두==pid면 그대로 둔다.
    head, _, rest = blk.partition("\n")
    rest = re.sub(
        r'\(symbol\s+"([^"]+?)_(\d+)_(\d+)"',
        lambda m: (m.group(0) if m.group(1) == pid
                   else f'(symbol "{pid}_{m.group(2)}_{m.group(3)}"'),
        rest)
    return head + "\n" + rest


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
            meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
            blk = enrich(blk, pid, meta)
            blocks.append("  " + blk.replace("\n", "\n  ").rstrip())
            z.write(mod_p, f"PartReel.pretty/{pid}.kicad_mod")
            included.append(pid)

    lib = ("(kicad_symbol_lib (version 20231120) (generator \"partreel-bundle\")\n"
           + PLACEHOLDER + "\n" + "\n".join(blocks) + "\n)\n")
    open(os.path.join(ASSETS, "PartReel.kicad_sym"), "w", encoding="utf-8",
         newline="\n").write(lib)
    json.dump({"symbols": included, "count": len(included)},
              open(os.path.join(ASSETS, "kicad-bundle-manifest.json"), "w",
                   encoding="utf-8"), indent=1)
    print(f"번들: 심볼 {len(included)} + 풋프린트 zip + manifest / 스킵 {len(skipped)}")
    for s in skipped[:10]:
        print("  skip:", s)


if __name__ == "__main__":
    main()
