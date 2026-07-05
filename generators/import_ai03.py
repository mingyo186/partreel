"""
ai03 MX_V2 검증-수입 Wave A (REQUIREMENTS §21-6ⓒ ③, docs/ai03-import-plan.md).
실행: AI03_SRC=<클론경로> python generators/import_ai03.py
그 후: build_index → render_svg → build_site → build_api → qa (실패분 드롭 후 재실행)

- 소스: 라이브러리별 .pretty (심볼 업스트림 부재 → 우리가 2핀 심볼 저작)
- 수정(전부 기록): Dwgs.User→F.Fab 재매핑, 실크 핀1 마커, 자동 코트야드,
  model 참조 제거(소켓 STEP만 있어 부품 3D 아님 → verified-2D)
- 라이선스 MIT 유지 ((c) ai03 — 재라이선스 금지)
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
LIB_ROOT = os.path.join(ROOT, "library")
SRC = os.environ.get("AI03_SRC", "").strip()
COMMIT = "0b379ee"
REPO = "https://github.com/ai03-2725/MX_V2"
IMPORT_DATE = "2026-07-05"

# 라이브러리 → (family, manufacturer, 유형설명)
WAVE_A = {
    "MX_Solderable": ("ai03 MX Solderable", "Cherry MX compatible",
                      "Cherry MX-type mechanical keyboard switch, soldered"),
    "MX_Hotswap": ("ai03 MX Hotswap", "Cherry MX compatible",
                   "Cherry MX-type mechanical keyboard switch, Kailh hotswap socket"),
    "MX_Alps_Hybrid": ("ai03 MX/Alps Hybrid", "Cherry MX / Alps compatible",
                       "Hybrid MX+Alps compatible keyboard switch, soldered"),
    "Alps_Solderable": ("ai03 Alps Solderable", "Alps SKCM/SKCL compatible",
                        "Alps SKCM/SKCL-type keyboard switch, soldered"),
    "Gateron_KS33_Solderable": ("ai03 Gateron KS-33 Solderable", "Gateron",
                                "Gateron low-profile KS-27/KS-33 switch, soldered"),
    "Gateron_KS33_Hotswap": ("ai03 Gateron KS-33 Hotswap", "Gateron",
                             "Gateron low-profile KS-27/KS-33 switch, hotswap socket"),
    "Kailh_PG1353_Solderable": ("ai03 Kailh Choc V2 Solderable", "Kailh",
                                "Kailh Choc V2 (PG1353) low-profile switch, soldered"),
    "Kailh_PG1353_Hotswap": ("ai03 Kailh Choc V2 Hotswap", "Kailh",
                             "Kailh Choc V2 (PG1353) low-profile switch, hotswap socket"),
    "Switch_Misc": ("ai03 Switch LED", "Generic",
                    "In-switch indicator LED aligned to the switch footprint"),
}

LAYER_TOKENS = ("F.Cu", "B.Cu", "*.Cu", "F&B.Cu", "*.Mask", "F.Mask", "B.Mask",
                "F.Paste", "B.Paste", "F.SilkS", "B.SilkS", "Dwgs.User",
                "Cmts.User", "F.CrtYd", "B.CrtYd", "F.Fab", "B.Fab", "Edge.Cuts")


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return re.sub(r"_+", "_", s)


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


def quote_layers(fp_text):
    """구포맷(v20211014)의 비인용 레이어 토큰을 인용으로 정규화."""
    def q(m):
        toks = m.group(2).split()
        return "(" + m.group(1) + " " + " ".join(
            t if t.startswith('"') else f'"{t}"' for t in toks) + ")"
    return re.sub(r"\((layers?)\s+([^()\"]+)\)", q, fp_text)


def modernize_lines(fp_text):
    """구포맷 fp_line `(layer X) (width w)` → 신포맷 `(stroke ...) (layer X)`.
    render_svg LINE_RE가 width→layer 순서를 요구하므로 필수."""
    def sub(m):
        return (f'\n  (fp_line {m.group(1)} {m.group(2)} '
                f'(stroke (width {m.group(4)}) (type solid)) (layer {m.group(3)}))')
    fp_text = re.sub(r'\(fp_line\s+(\(start\s+[-\d. ]+\))\s+(\(end\s+[-\d. ]+\))\s+'
                     r'\(layer\s+("[^"]+")\)\s+\(width\s+([-\d.]+)\)'
                     r'(?:\s+\(tstamp\s+[^)]*\))?\s*\)', sub, fp_text)
    # check_render가 줄 단위로 세므로 도형 요소는 반드시 줄마다 하나씩
    for tok in ("(fp_line", "(fp_arc", "(fp_circle", "(fp_text", "(pad"):
        fp_text = fp_text.replace(tok, "\n  " + tok)
    return fp_text


def geo_bbox(fp_text):
    x0 = y0 = 1e9
    x1 = y1 = -1e9
    for m in re.finditer(r'\(pad\s+"[^"]*"\s+\w+\s+\w+\s*\(at\s+([-\d.]+)\s+([-\d.]+)'
                         r'[^)]*\)\s*\(size\s+([-\d.]+)\s+([-\d.]+)', fp_text):
        x, y, w, h = map(float, m.groups())
        r = max(w, h) / 2
        x0, y0, x1, y1 = min(x0, x - r), min(y0, y - r), max(x1, x + r), max(y1, y + r)
    for m in re.finditer(r'\(fp_line\s*\(start\s+([-\d.]+)\s+([-\d.]+)\)\s*'
                         r'\(end\s+([-\d.]+)\s+([-\d.]+)\)', fp_text):
        a, b, c, d = map(float, m.groups())
        x0, y0, x1, y1 = min(x0, a, c), min(y0, b, d), max(x1, a, c), max(y1, b, d)
    for m in re.finditer(r'\(xy\s+([-\d.]+)\s+([-\d.]+)\)', fp_text):
        a, b = float(m.group(1)), float(m.group(2))
        x0, y0, x1, y1 = min(x0, a), min(y0, b), max(x1, a), max(y1, b)
    return (x0, y0, x1, y1) if x1 > x0 else None


def add_courtyard(fp_text, bbox):
    x0, y0, x1, y1 = [round(v + s * 0.25, 2) for v, s in zip(bbox, (-1, -1, 1, 1))]
    lines = ""
    for (a, b, c, d) in [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1),
                         (x0, y1, x0, y0)]:
        lines += (f'  (fp_line (start {a} {b}) (end {c} {d})'
                  f' (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))\n')
    i = fp_text.rstrip().rfind(")")
    return fp_text.rstrip()[:i] + lines + ")\n"


def pad1_pos(fp_text):
    m = re.search(r'\(pad\s+"1"\s+\w+\s+\w+\s*\(at\s+([-\d.]+)\s+([-\d.]+)'
                  r'[^)]*\)\s*\(size\s+([-\d.]+)\s+([-\d.]+)', fp_text)
    if not m:
        return None
    x, y, w, h = map(float, m.groups())
    return x, y, w, h


def add_silk_pin1(fp_text, x, y, w, h):
    cy = round(y - h / 2 - 0.6, 2)
    mark = (f'  (fp_circle (center {x} {cy}) (end {round(x + 0.2, 2)} {cy})'
            f' (stroke (width 0.2) (type solid)) (fill none) (layer "F.SilkS"))\n')
    i = fp_text.rstrip().rfind(")")
    return fp_text.rstrip()[:i] + mark + ")\n"


def make_symbol(pid, is_led, datasheet):
    if is_led:
        pins = [("A", "1", 1.27), ("K", "2", -1.27)]
        ref = "D"
    else:
        pins = [("1", "1", 1.27), ("2", "2", -1.27)]
        ref = "SW"
    pin_txt = ""
    for name, num, py in pins:
        pin_txt += (f'      (pin passive line (at -5.08 {py} 0) (length 2.54)\n'
                    f'        (name "{name}" (effects (font (size 1.27 1.27))))\n'
                    f'        (number "{num}" (effects (font (size 1.27 1.27)))))\n')
    return f'''(kicad_symbol_lib (version 20211014) (generator partreel-import)
  (symbol "{pid}" (in_bom yes) (on_board yes)
    (property "Reference" "{ref}" (at 3.54 2.54 0)
      (effects (font (size 1.27 1.27)) (justify left)))
    (property "Value" "{pid}" (at 3.54 -2.54 0)
      (effects (font (size 1.27 1.27)) (justify left)))
    (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "Datasheet" "{datasheet}" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (symbol "{pid}_1_1"
      (rectangle (start -2.54 2.54) (end 2.54 -2.54)
        (stroke (width 0.254) (type solid)) (fill (type background)))
{pin_txt}    )
  )
)
'''


def keysize(fpname):
    m = re.search(r"(\d+(?:\.\d+)?)U", fpname)
    return f"{m.group(1)}u" if m else None


def main():
    if not SRC or not os.path.exists(os.path.join(SRC, "LICENSE")):
        print("AI03_SRC not set or LICENSE missing")
        sys.exit(2)
    accepted, skipped = [], []
    for libname, (family, manuf, typedesc) in WAVE_A.items():
        pretty = os.path.join(SRC, libname + ".pretty")
        for fn in sorted(os.listdir(pretty)):
            if not fn.endswith(".kicad_mod"):
                continue
            fpname = fn[:-len(".kicad_mod")]
            fp_text = open(os.path.join(pretty, fn), encoding="utf-8").read()
            mods = ["symbol authored by PartReel (upstream pairs with stock "
                    "KiCad symbols by design)"]
            # (model ...) 제거 — 균형 추출 (§14-H: 중첩 괄호에 정규식 금지)
            had_model = False
            while True:
                mm = re.search(r"\(model\s", fp_text)
                if not mm:
                    break
                blk = balanced_block(fp_text, mm.start())
                if blk is None:
                    break
                fp_text = fp_text.replace(blk, "", 1)
                had_model = True
            if had_model:
                mods.append("removed 3D model reference (socket-only model; part "
                            "published as verified-2D)")
            fp_text = modernize_lines(quote_layers(fp_text))
            if '"Dwgs.User"' in fp_text:
                fp_text = fp_text.replace('"Dwgs.User"', '"F.Fab"')
                mods.append("remapped Dwgs.User outline to F.Fab (keyboard "
                            "libraries avoid silk under the keycap)")
            p1 = pad1_pos(fp_text)
            if p1 is None:
                skipped.append((fpname, "no numbered pad 1"))
                continue
            if '"F.SilkS"' not in fp_text:
                fp_text = add_silk_pin1(fp_text, *p1)
                mods.append("added minimal silk pin-1 marker (hidden under the "
                            "mounted switch)")
            if '"F.CrtYd"' not in fp_text:
                bbox = geo_bbox(fp_text)
                if bbox is None:
                    skipped.append((fpname, "no geometry for courtyard"))
                    continue
                fp_text = add_courtyard(fp_text, bbox)
                mods.append("auto-added courtyard (pads+outline bbox +0.25mm)")

            pid = "ai03_" + slug(fpname)
            is_led = libname == "Switch_Misc"
            npads = len(set(re.findall(r'\(pad\s+"(\d+)"', fp_text)))
            datasheet = f"{REPO}/blob/main/{libname}.pretty/{fn}"
            sym_text = make_symbol(pid, is_led, datasheet)
            size = keysize(fpname)
            variant_bits = []
            if "ReversedStabilizers" in fpname:
                variant_bits.append("reversed stabilizers")
            if "Reversed" in fpname and not variant_bits:
                variant_bits.append("reversed pin order")
            if "PolarityMarked" in fpname:
                variant_bits.append("polarity marked")
            desc = (f"{typedesc}"
                    + (f", {size} keysize" if size else "")
                    + (f" ({', '.join(variant_bits)})" if variant_bits else "")
                    + ". Imported from the ai03 MX_V2 keyboard library (MIT, (c) "
                      "ai03); passed PartReel quality gates. Verified-2D part. "
                      "Official KiCad libraries carry no hotswap / low-profile / "
                      "hybrid switch footprints.")
            meta = {
                "id": pid, "name": f"{fpname} (ai03 MX_V2)", "category": "switch",
                "family": family, "manufacturer": manuf, "mpn_pattern": fpname,
                "description": desc,
                "parameters": {k: v for k, v in {
                    "keysize": size, "pins": npads,
                    "mounting": "SMD" if "(attr smd" in fp_text or
                                 '(attr "smd"' in fp_text else "THT",
                    "type": "LED" if is_led else "keyboard switch"}.items()
                    if v not in (None, "")},
                "files": {"footprint": f"{pid}.kicad_mod", "symbol": f"{pid}.kicad_sym",
                          "footprint_svg": f"{pid}.footprint.svg",
                          "symbol_svg": f"{pid}.symbol.svg"},
                "formats": ["kicad_mod", "kicad_sym"],
                "datasheet": datasheet,
                "dimensions_source": f"ai03 MX_V2@{COMMIT} ({libname}.pretty/{fn}) — "
                                     "designed from scratch from official switch "
                                     "datasheets per upstream README",
                "verified": True, "origin": "imported", "tier": "verified-2d",
                "license": "MIT",
                "generated_by": "generators/import_ai03.py",
                "keywords": ["keyboard", "switch", "ai03"]
                            + [w for w in slug(fpname).split("_") if len(w) > 1][:6],
                "import": {
                    "source_repo": REPO, "source_commit": COMMIT,
                    "source_files": {"footprint": f"{libname}.pretty/{fn}"},
                    "attribution": "(c) ai03 (ai03-2725/MX_V2), MIT",
                    "import_date": IMPORT_DATE, "modifications": mods,
                },
            }
            d = os.path.join(LIB_ROOT, "switch", "ai03", pid)
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, f"{pid}.kicad_mod"), "w", encoding="utf-8").write(fp_text)
            open(os.path.join(d, f"{pid}.kicad_sym"), "w", encoding="utf-8").write(sym_text)
            json.dump(meta, open(os.path.join(d, "meta.json"), "w", encoding="utf-8"),
                      indent=2, ensure_ascii=False)
            accepted.append(pid)
    log = {"commit": COMMIT, "wave": "A", "accepted": accepted,
           "skipped": [{"part": k, "reason": v} for k, v in skipped]}
    json.dump(log, open(os.path.join(ROOT, "docs", "import-ai03-log.json"), "w",
                        encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"accepted {len(accepted)}, skipped {len(skipped)}")


if __name__ == "__main__":
    main()
