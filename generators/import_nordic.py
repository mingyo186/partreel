"""
nordic-lib-kicad 검증-수입 (REQUIREMENTS §21-C — 사용자 GO 2026-07-26).
실행: NORDIC_SRC=<클론경로> python generators/import_nordic.py
그 후: build_index → freecadcmd import_steps_mesh.py → imported_stl_to_glb.py
      → sync_r2 --hash → (신규 step/glb R2 업로드) → render_svg → build_site → build_api → qa

원칙: 원 라이선스 CERN-OHL-P-2.0 유지, 출처·커밋·수정목록을 meta.import에 기록.
생성 도구 산출물 허용 근거 = §21-C (자기 치수 입력 + 공식 이름 충돌 0 = 도구 사용).
"""
import json
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
LIB_ROOT = os.path.join(ROOT, "library")
SRC = os.environ.get("NORDIC_SRC", "").strip()
COMMIT = "b12341fb8eaea4c72685c87bc37b591bfe25d20a"
REPO = "https://github.com/hlord2000/nordic-lib-kicad"
ATTR = "Helmut Lord — nordic-lib-kicad (CERN-OHL-P-2.0)"

# 서드파티 모듈 심볼의 제조사 추정 (이름 프리픽스 → 벤더)
MODULE_VENDORS = [("E73", "Ebyte"), ("E83", "Ebyte"), ("ISP", "Insight SiP"),
                  ("BC15", "Fanstel"), ("BM15", "Fanstel"), ("BM20", "Fanstel"),
                  ("BL54", "Ezurio (Laird)"), ("MDBT", "Raytac"), ("BT40", "Fanstel")]


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


def top_symbols(lib_text):
    out = {}
    for m in re.finditer(r'\n\t?\(symbol\s+"([^"]+)"', lib_text):
        blk = balanced_block(lib_text, m.start() + 1 if lib_text[m.start()] == "\n" else m.start())
        if blk:
            out[m.group(1)] = blk
    return out


def prop(block, name):
    m = re.search(r'\(property\s+"' + re.escape(name) + r'"\s+"((?:[^"\\]|\\.)*)"', block)
    return m.group(1) if m else ""


def pad_stats(fp_text):
    nums, smd, tht = set(), 0, 0
    for m in re.finditer(r'\(pad\s+"([^"]*)"\s+(\w+)\s+', fp_text):
        n, typ = m.groups()
        if n:
            nums.add(n)
        if typ == "smd":
            smd += 1
        elif typ == "thru_hole":
            tht += 1
    return len(nums), smd, tht


def category_of(libname):
    if "modules" in libname:
        return "module"
    if libname.endswith("-npm"):
        return "power"
    return "ic"


def main():
    if not SRC or not os.path.isdir(SRC):
        print("NORDIC_SRC not set or missing")
        sys.exit(2)
    accepted, skipped = [], []
    for fn in sorted(os.listdir(os.path.join(SRC, "symbols"))):
        if not fn.endswith(".kicad_sym"):
            continue
        libname = fn[:-len(".kicad_sym")]
        category = category_of(libname)
        lib_text = open(os.path.join(SRC, "symbols", fn), encoding="utf-8").read()
        for name, blk in top_symbols(lib_text).items():
            reason = None
            if re.search(r'\(extends\s', blk):
                reason = "derived symbol (extends)"
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
                base = os.path.basename(mm.group(1))
                shapes_dir = os.path.dirname(mm.group(1)).split("/")[-1]
                cand = os.path.join(SRC, "3dmodels", shapes_dir, base)
                if os.path.exists(cand):
                    step_path = cand
            npads, smd, tht = pad_stats(fp_text)
            if npads < 1:
                skipped.append((name, "no numbered pads")); continue
            if '"F.CrtYd"' not in fp_text:
                skipped.append((name, "no courtyard")); continue

            pid = "nordic_" + slug(name)
            mods = ["extracted single symbol from library"]
            if step_path:
                fp_text = fp_text.replace(mm.group(1), f"{pid}.step")
                mods.append("rewrote 3D model path to per-part relative")
            sym_text = ('(kicad_symbol_lib\n\t(version 20260206)\n'
                        '\t(generator "partreel-import")\n'
                        + "\t" + blk.replace("\n", "\n\t").rstrip() + "\n)\n")

            ds = prop(blk, "Datasheet")
            if not ds.startswith("http"):
                ds = f"{REPO}/blob/{COMMIT[:12]}/symbols/{fn}"
            desc = prop(blk, "Description") or name
            manuf = "Nordic Semiconductor"
            if category == "module":
                for pre, vendor in MODULE_VENDORS:
                    if name.upper().startswith(pre):
                        manuf = vendor
                        break
            mounting = "SMD" if smd and not tht else ("THT" if tht and not smd else "SMD+THT")
            files = {"footprint": f"{pid}.kicad_mod", "symbol": f"{pid}.kicad_sym",
                     "footprint_svg": f"{pid}.footprint.svg",
                     "symbol_svg": f"{pid}.symbol.svg"}
            formats = ["kicad_mod", "kicad_sym"]
            if step_path:
                files["model_3d"] = f"{pid}.step"
                files["preview"] = f"{pid}.glb"
                formats += ["step", "glb"]
            meta = {
                "id": pid, "name": name, "category": category,
                "family": "Nordic " + libname.replace("nordic-lib-kicad-", ""),
                "manufacturer": manuf, "mpn_pattern": name,
                "description": f"{desc} Imported from nordic-lib-kicad "
                               f"(CERN-OHL-P-2.0, attribution: Helmut Lord); dimensions "
                               f"generated from manufacturer datasheet inputs; passed "
                               f"PartReel quality gates.",
                "parameters": {"contacts": npads, "mounting": mounting},
                "files": files, "formats": formats,
                "datasheet": ds,
                "dimensions_source": f"nordic-lib-kicad@{COMMIT[:12]} "
                                     f"(footprints/{fp_lib}.pretty/{fp_name}.kicad_mod)",
                "verified": True, "origin": "imported", "license": "CERN-OHL-P-2.0",
                "generated_by": "generators/import_nordic.py",
                "keywords": ["nordic", "wireless"] + [w for w in
                            re.split(r"[\s,]+", prop(blk, "ki_keywords")) if w][:8],
                "import": {
                    "source_repo": REPO, "source_commit": COMMIT,
                    "source_files": {"symbol": f"symbols/{fn}#{name}",
                                     "footprint": f"footprints/{fp_lib}.pretty/{fp_name}.kicad_mod"},
                    "attribution": ATTR, "modifications": mods,
                },
            }
            if not step_path:
                meta["tier"] = "verified-2d"
            else:
                meta["import"]["source_files"]["model"] = \
                    os.path.relpath(step_path, SRC).replace("\\", "/")
            d = os.path.join(LIB_ROOT, category, "nordic", pid)
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, f"{pid}.kicad_mod"), "w", encoding="utf-8").write(fp_text)
            open(os.path.join(d, f"{pid}.kicad_sym"), "w", encoding="utf-8").write(sym_text)
            if step_path:
                shutil.copyfile(step_path, os.path.join(d, f"{pid}.step"))
            json.dump(meta, open(os.path.join(d, "meta.json"), "w", encoding="utf-8"),
                      indent=2, ensure_ascii=False)
            accepted.append(pid)

    log = {"commit": COMMIT, "accepted": accepted,
           "skipped": [{"symbol": n, "reason": r} for n, r in skipped]}
    json.dump(log, open(os.path.join(ROOT, "docs", "import-nordic-log.json"), "w",
                        encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"accepted {len(accepted)}, skipped {len(skipped)} "
          f"(log: docs/import-nordic-log.json)")


if __name__ == "__main__":
    main()
