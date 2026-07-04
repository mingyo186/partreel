"""
SparkFun 라이브러리 검증-수입 파일럿 (REQUIREMENTS §21-6ⓒ). 오프라인 1회 실행.
실행: SPARKFUN_SRC=<클론경로> python generators/import_sparkfun.py
그 후: freecadcmd generators/import_steps_mesh.py && python generators/imported_stl_to_glb.py
      → build_index → render_svg → build_site → build_api → qa (실패 부품은 드롭 후 재실행)

원칙: 원 라이선스 CC-BY-4.0 유지(재라이선스 금지), 출처·커밋·수정목록을 meta.import에 기록,
게이트 통과분만 공개. 실크 부재 부품은 드롭(게이트 완화 대신).
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
LIB_ROOT = os.path.join(ROOT, "library")
SRC = os.environ.get("SPARKFUN_SRC", "").strip()
COMMIT = "2423e36aead98c5756ae09366e0388ff21a82808"
REPO = "https://github.com/sparkfun/SparkFun-KiCad-Libraries"
ATTR = "SparkFun Electronics (CC-BY-4.0)"

# 1차 물결: SparkFun 고유 가치 구간 (패시브/Aesthetic/멀티유닛 제외 — §21-6ⓒ②⑤)
WAVE1 = {"SparkFun-Sensor": "sensor", "SparkFun-GPS": "module", "SparkFun-RF": "module",
         "SparkFun-Connector": "connector", "SparkFun-GNSS": "module"}


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return re.sub(r"_+", "_", s)


def balanced_block(text, start):
    """start 위치의 '('부터 균형 잡힌 블록 추출 (문자열 리터럴 인지)."""
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
    """라이브러리의 최상위 심볼 블록들 {이름: 블록}."""
    out = {}
    for m in re.finditer(r'\n\t?\(symbol\s+"([^"]+)"', lib_text):
        # 최상위(들여쓰기 1레벨)만: kicad_symbol_lib 바로 아래
        blk = balanced_block(lib_text, m.start() + 1 if lib_text[m.start()] == "\n" else m.start())
        if blk:
            out[m.group(1)] = blk
    return out


def prop(block, name):
    m = re.search(r'\(property\s+"' + re.escape(name) + r'"\s+"((?:[^"\\]|\\.)*)"', block)
    return m.group(1) if m else ""


def pad_stats(fp_text):
    """(numbered_pad_count, all_smd, any_tht, bbox) — 코트야드 생성/메타용."""
    nums, smd, tht = set(), 0, 0
    x0 = y0 = 1e9
    x1 = y1 = -1e9
    for m in re.finditer(r'\(pad\s+"([^"]*)"\s+(\w+)\s+\w+\s*\(at\s+([-\d.]+)\s+([-\d.]+)'
                         r'[^)]*\)\s*\(size\s+([-\d.]+)\s+([-\d.]+)', fp_text):
        n, typ, x, y, w, h = m.groups()
        if n:
            nums.add(n)
        if typ == "smd":
            smd += 1
        elif typ == "thru_hole":
            tht += 1
        x, y, w, h = float(x), float(y), float(w), float(h)
        r = max(w, h) / 2
        x0, y0 = min(x0, x - r), min(y0, y - r)
        x1, y1 = max(x1, x + r), max(y1, y + r)
    for m in re.finditer(r'\(fp_line\s*\(start\s+([-\d.]+)\s+([-\d.]+)\)\s*\(end\s+([-\d.]+)\s+([-\d.]+)\)', fp_text):
        a, b, c, d = map(float, m.groups())
        x0, y0 = min(x0, a, c), min(y0, b, d)
        x1, y1 = max(x1, a, c), max(y1, b, d)
    return len(nums), smd, tht, (x0, y0, x1, y1)


def add_courtyard(fp_text, bbox):
    x0, y0, x1, y1 = [round(v + s * 0.25, 2) for v, s in
                      zip(bbox, (-1, -1, 1, 1))]
    lines = ""
    for (a, b, c, d) in [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]:
        lines += (f'  (fp_line (start {a} {b}) (end {c} {d})'
                  f' (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))\n')
    i = fp_text.rstrip().rfind(")")
    return fp_text.rstrip()[:i] + lines + ")\n"


def main():
    if not SRC or not os.path.isdir(SRC):
        print("SPARKFUN_SRC not set or missing")
        sys.exit(2)
    accepted, skipped = [], []
    for libname, category in WAVE1.items():
        sym_path = os.path.join(SRC, "symbols", libname + ".kicad_sym")
        if not os.path.exists(sym_path):
            continue
        lib_text = open(sym_path, encoding="utf-8").read()
        for name, blk in top_symbols(lib_text).items():
            reason = None
            if re.search(r'\(extends\s', blk):
                reason = "derived symbol (extends)"
            elif re.search(r'\(symbol\s+"' + re.escape(name) + r'_2_', blk):
                reason = "multi-unit"
            fp_ref = prop(blk, "Footprint")
            if not reason and (":" not in fp_ref):
                reason = "no footprint property"
            if reason:
                skipped.append((name, reason))
                continue
            fp_lib, fp_name = fp_ref.split(":", 1)
            fp_path = os.path.join(SRC, "footprints", fp_lib + ".pretty", fp_name + ".kicad_mod")
            if not os.path.exists(fp_path):
                skipped.append((name, f"footprint file missing ({fp_ref})"))
                continue
            fp_text = open(fp_path, encoding="utf-8").read()
            mm = re.search(r'\(model\s+"([^"]+)"', fp_text)
            step_path = None
            if mm:
                rel = mm.group(1).replace("${SPARKFUN_KICAD_LIBRARY}/", "")
                cand = os.path.join(SRC, *rel.split("/"))
                cand = os.path.splitext(cand)[0] + ".step"
                if os.path.exists(cand):
                    step_path = cand
            if not step_path:
                skipped.append((name, "no STEP model"))
                continue
            if '"F.SilkS"' not in fp_text:
                skipped.append((name, "no silkscreen (dropped per §21-6ⓒ④)"))
                continue
            if '"F.Fab"' not in fp_text:
                skipped.append((name, "no fab layer"))
                continue

            pid = "sparkfun_" + slug(name)
            mods = ["extracted single symbol from library",
                    "rewrote 3D model path to per-part relative"]
            npads, smd, tht, bbox = pad_stats(fp_text)
            if npads < 1:
                skipped.append((name, "no numbered pads"))
                continue
            if '"F.CrtYd"' not in fp_text:
                fp_text = add_courtyard(fp_text, bbox)
                mods.append("auto-added courtyard (pads+fab bbox +0.25mm, IPC-7351)")
            fp_text = fp_text.replace(mm.group(1), f"{pid}.step")

            sym_text = ('(kicad_symbol_lib (version 20211014) (generator partreel-import)\n'
                        + "  " + blk.replace("\n", "\n  ").rstrip() + "\n)\n")

            ds = prop(blk, "Datasheet")
            if not ds.startswith("http"):
                ds = f"{REPO}/blob/{COMMIT[:12]}/symbols/{libname}.kicad_sym"
            desc = prop(blk, "Description") or name
            prod = prop(blk, "PROD_ID")
            mounting = "SMD" if smd and not tht else ("THT" if tht and not smd else "SMD+THT")
            meta = {
                "id": pid, "name": f"{name} (SparkFun)", "category": category,
                "family": "SparkFun " + libname.split("-", 1)[1],
                "manufacturer": "SparkFun Electronics", "mpn_pattern": name,
                "description": f"{desc} Imported from the SparkFun KiCad library "
                               f"(CC-BY-4.0, attribution: SparkFun Electronics); passed "
                               f"PartReel quality gates.",
                "parameters": {"contacts": npads, "mounting": mounting},
                "files": {"footprint": f"{pid}.kicad_mod", "symbol": f"{pid}.kicad_sym",
                          "model_3d": f"{pid}.step", "preview": f"{pid}.glb",
                          "footprint_svg": f"{pid}.footprint.svg",
                          "symbol_svg": f"{pid}.symbol.svg"},
                "formats": ["kicad_mod", "kicad_sym", "step", "glb"],
                "datasheet": ds,
                "dimensions_source": f"SparkFun-KiCad-Libraries@{COMMIT[:12]} "
                                     f"({fp_lib}.pretty/{fp_name}.kicad_mod)",
                "verified": True, "origin": "imported", "license": "CC-BY-4.0",
                "generated_by": "generators/import_sparkfun.py",
                "keywords": ["sparkfun"] + [w for w in
                                            re.split(r"[\s,]+", prop(blk, "ki_keywords"))
                                            if w][:8],
                "import": {
                    "source_repo": REPO, "source_commit": COMMIT,
                    "source_files": {"symbol": f"symbols/{libname}.kicad_sym#{name}",
                                     "footprint": f"footprints/{fp_lib}.pretty/{fp_name}.kicad_mod",
                                     "model": os.path.relpath(step_path, SRC).replace("\\", "/")},
                    "attribution": ATTR, "sparkfun_prod_id": prod or None,
                    "modifications": mods,
                },
            }
            d = os.path.join(LIB_ROOT, category, "sparkfun", pid)
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, f"{pid}.kicad_mod"), "w", encoding="utf-8").write(fp_text)
            open(os.path.join(d, f"{pid}.kicad_sym"), "w", encoding="utf-8").write(sym_text)
            import shutil
            shutil.copyfile(step_path, os.path.join(d, f"{pid}.step"))
            json.dump(meta, open(os.path.join(d, "meta.json"), "w", encoding="utf-8"),
                      indent=2, ensure_ascii=False)
            accepted.append(pid)

    log = {"commit": COMMIT, "accepted": accepted,
           "skipped": [{"symbol": n, "reason": r} for n, r in skipped]}
    json.dump(log, open(os.path.join(ROOT, "docs", "import-sparkfun-log.json"), "w",
                        encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"accepted {len(accepted)}, skipped {len(skipped)} "
          f"(log: docs/import-sparkfun-log.json)")


if __name__ == "__main__":
    main()
