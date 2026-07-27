"""
Antmicro hardware-components 수입기 (REQUIREMENTS §21-C 물결, docs/next-wave-sources.md 1순위).
실행: python generators/import_antmicro.py docs/antmicro-pilot.json
     (ANTMICRO_COMMIT env = 고정 커밋 sha; 없으면 config의 commit 사용)

- 14GB 레포 통클론 없이 파일 단위 수집: 텍스트는 GitHub contents API(심링크 해석),
  glTF는 raw 실경로 (웹용은 LOD2 → LOD1 → 원본 순으로 경량판 우선).
- glTF+bin → 단일 메시 GLB (메시명 "imported" — 수입 GLB 정책 §21-6ⓒ③과 동일,
  merged-pins 게이트 자연 면제).
- 라이선스 Apache-2.0 유지 + provenance 기록. 공식 KiCad 라이브러리와 풋프린트
  이름이 충돌하는 부품은 config에서 미리 제외돼 있어야 함 (감사 §next-wave).
"""
import base64
import json
import os
import re
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
LIB_ROOT = os.path.join(ROOT, "library")
REPO = "antmicro/hardware-components"
ATTR = "Antmicro (Apache-2.0)"


SRC_LOCAL = os.environ.get("ANTMICRO_SRC", "").strip()


def _resolve_local(path):
    """sparse 클론에서 파일 읽기. Windows는 심링크가 '대상 경로 텍스트 파일'로
    체크아웃되므로(core.symlinks=false) 짧은 텍스트가 경로처럼 보이면 따라간다."""
    fp = os.path.join(SRC_LOCAL, *path.split("/"))
    if not os.path.exists(fp):
        return None
    raw = open(fp, "rb").read()
    if len(raw) < 300 and (b"\n" not in raw.strip()) and (b"../" in raw or b".." == raw[:2]):
        target = os.path.normpath(os.path.join(os.path.dirname(fp),
                                               raw.decode("utf-8").strip()))
        if os.path.exists(target):
            return open(target, "rb").read()
        return None
    return raw


def gh_api_file(path, ref):
    """contents API로 파일 획득 (심링크를 따라 실제 내용 반환). ANTMICRO_SRC 있으면 로컬."""
    if SRC_LOCAL:
        return _resolve_local(path)
    r = subprocess.run(["gh", "api", f"repos/{REPO}/contents/{path}?ref={ref}",
                        "--jq", ".content"],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        return None
    return base64.b64decode(r.stdout)


def raw_file(path, ref, dest):
    url = f"https://raw.githubusercontent.com/{REPO}/{ref}/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "partreel-import"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as f:
            f.write(resp.read())
        return True
    except Exception:
        return False


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


def flatten_extends(sym_text, want_name):
    """Antmicro 심볼은 파일 안에 템플릿+파생(extends) 구조 — 파생엔 핀이 없어
    렌더러가 빈/부분 심볼을 그림. 템플릿 블록을 파생 이름으로 개명하고 파생의
    property(Reference/Value/Footprint/Datasheet 등)로 덮어써 단일 심볼로 평탄화."""
    syms = top_symbols(sym_text)
    blk = syms.get(want_name)
    if not blk:
        return None
    m = re.search(r'\(extends\s+"([^"]+)"\)', blk)
    if not m:
        return ('(kicad_symbol_lib\n\t(version 20260206)\n'
                '\t(generator "partreel-import")\n'
                "\t" + blk.replace("\n", "\n\t").rstrip() + "\n)\n")
    tpl = syms.get(m.group(1))
    if not tpl:
        return None
    merged = tpl.replace(f'"{m.group(1)}', f'"{want_name}')
    # 파생의 property로 템플릿 property 교체 (같은 키가 템플릿에 있으면 대체, 없으면 유지)
    for pm in re.finditer(r'\(property\s+"([^"]+)"', blk):
        pblk = balanced_block(blk, pm.start())
        key = pm.group(1)
        tm = re.search(r'\(property\s+"' + re.escape(key) + r'"', merged)
        if tm:
            told = balanced_block(merged, tm.start())
            merged = merged.replace(told, pblk, 1)
    return ('(kicad_symbol_lib\n\t(version 20260206)\n'
            '\t(generator "partreel-import")\n'
            "\t" + merged.replace("\n", "\n\t").rstrip() + "\n)\n")


def slugify(s):
    t = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return re.sub(r"_+", "_", t)


def gltf_to_glb(gltf_path, glb_path):
    import trimesh
    scene = trimesh.load(gltf_path)
    geoms = list(scene.geometry.values()) if hasattr(scene, "geometry") else [scene]
    m = trimesh.util.concatenate(geoms)
    m.visual = trimesh.visual.ColorVisuals(m, face_colors=[178, 180, 186, 255])
    out = trimesh.Scene()
    out.add_geometry(m, node_name="imported", geom_name="imported")
    out.export(glb_path)
    return os.path.getsize(glb_path)


def guess_category(data, fp_name):
    """키워드/설명 기반 카테고리 추정 (본대 배치용)."""
    kw = ((data.get("keywords") or "") + " " + (data.get("description") or "")).lower()
    def has(*words):
        return any(w in kw for w in words)
    if has("dimm", " socket", "m.2", "sim card", "sd card", "microsd"):
        return "socket"
    if has("connector", "header", "receptacle", "plug", " jack", "usb", "rj45",
           "ffc", "fpc", "terminal block", "btb", "board-to-board"):
        return "connector"
    if has("resistor", "capacitor", "inductor", "ferrite", "choke", "bead",
           "crystal", "oscillator", "resonator", "varistor", "thermistor"):
        return "passive"
    if has("led"):
        return "discrete"
    if has("diode", " tvs", "esd", "rectifier", "zener", "transistor", "mosfet"):
        return "discrete"
    if has("fuse", " ptc"):
        return "fuse"
    if has("relay"):
        return "relay"
    if has("switch", "button", "tactile"):
        return "switch"
    if has("transformer"):
        return "transformer"
    if has("antenna", " module"):
        return "module"
    if has("sensor", "accelerometer", "gyro", "magnetometer", "temperature"):
        return "sensor"
    if has("regulator", "converter", "pmic", " ldo", " buck", " boost",
           "power management", "efuse", "load switch"):
        return "power"
    return "ic"


# IPC-7351 밀도 레벨 B(공칭) 칩 랜드패턴 — 수치 출처: KEMET C1002 X7R SMD 카탈로그
# Table 3 (치수=사실). C=패드 간격, Y=패드 길이(x), X=패드 폭(y), V1/V2=코트야드.
# KiCad 공식 카피로 판정된 풋프린트 4종의 대체용 (§21-C 대체 수입 규칙).
CHIP_LAND = {
    "1005": {"C": 0.45, "Y": 0.62, "X": 0.62, "V1": 1.90, "V2": 1.00,
             "body": (1.0, 0.5)},
    "3216": {"C": 1.50, "Y": 1.15, "X": 1.80, "V1": 4.70, "V2": 2.30,
             "body": (3.2, 1.6)},
}
FP_REPLACEMENTS = {
    "C_0402_1005Metric": "1005", "D_0402_1005Metric": "1005",
    "L_0402_1005Metric": "1005", "C_1206_3216Metric": "3216",
}


def chip_footprint(pid, size_key):
    """자체 생성 2패드 칩 풋프린트 (SMD, IPC-7351 밀도 B 공칭)."""
    p = CHIP_LAND[size_key]
    cx = round((p["C"] + p["Y"]) / 2, 4)          # 패드 중심 x
    hx, hy = p["body"][0] / 2, p["body"][1] / 2   # 몸체 반폭
    vx, vy = p["V1"] / 2, p["V2"] / 2             # 코트야드 반폭
    ty = round(vy + 1.1, 2)                       # 참조/값 텍스트 y
    L = [f'(footprint "{pid}"',
         '  (version 20240108) (generator "partreel")',
         '  (layer "F.Cu")',
         f'  (descr "Chip {size_key} metric 2-terminal SMD. Land pattern per '
         'IPC-7351 density level B (nominal), values as tabulated in KEMET '
         'C1002 X7R SMD datasheet Table 3")',
         '  (attr smd)',
         f'  (fp_text reference "REF**" (at 0 {-ty}) (layer "F.SilkS")'
         ' (effects (font (size 1 1) (thickness 0.15))))',
         f'  (fp_text value "VAL**" (at 0 {ty}) (layer "F.Fab")'
         ' (effects (font (size 1 1) (thickness 0.15))))']
    # 몸체 외곽 (Fab)
    for a, b, c, d in ((-hx, -hy, hx, -hy), (hx, -hy, hx, hy),
                       (hx, hy, -hx, hy), (-hx, hy, -hx, -hy)):
        L.append(f'  (fp_line (start {a} {b}) (end {c} {d})'
                 ' (stroke (width 0.1) (type solid)) (layer "F.Fab"))')
    # 실크 (패드 사이 상하 라인 — 1005는 공간이 없어 생략, KiCad 관행과 동일)
    if size_key != "1005":
        sy = round(p["X"] / 2 + 0.16, 3)
        sx = round(cx - p["Y"] / 2 - 0.2, 3)
        for s in (-sy, sy):
            L.append(f'  (fp_line (start {-sx} {s}) (end {sx} {s})'
                     ' (stroke (width 0.12) (type solid)) (layer "F.SilkS"))')
    # 코트야드
    for a, b, c, d in ((-vx, -vy, vx, -vy), (vx, -vy, vx, vy),
                       (vx, vy, -vx, vy), (-vx, vy, -vx, -vy)):
        L.append(f'  (fp_line (start {a} {b}) (end {c} {d})'
                 ' (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))')
    for num, x in (("1", -cx), ("2", cx)):
        L.append(f'  (pad "{num}" smd rect (at {x} 0) (size {p["Y"]} {p["X"]})'
                 ' (layers "F.Cu" "F.Paste" "F.Mask"))')
    L.append(f'  (model "{pid}.glb" (offset (xyz 0 0 0)) (scale (xyz 1 1 1))'
             ' (rotate (xyz 0 0 0)))')
    L.append(')')
    return "\n".join(L) + "\n"


def excluded_footprints():
    """판별 리포트에서 IDENTICAL/NEAR 풋프린트 이름 집합 (수입 제외 — §21-C)."""
    try:
        rep = json.load(open(os.path.join(ROOT, "docs", "provenance-report.json"),
                             encoding="utf-8"))
    except OSError:
        return set()
    out = set()
    for r in rep:
        if r.get("verdict") in ("IDENTICAL", "NEAR"):
            out.add(os.path.splitext(os.path.basename(r["file"]))[0])
    return out


def main():
    if sys.argv[1] == "--all":
        return main_all()
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    ref = os.environ.get("ANTMICRO_COMMIT") or cfg["commit"]
    import_loop(cfg, ref)


def import_loop(cfg, ref):
    tmp = os.path.join(ROOT, "..", "_antmicro_tmp")
    tmp = os.path.abspath(tmp)
    os.makedirs(tmp, exist_ok=True)
    accepted, skipped = [], []
    for ent in cfg["parts"]:
        slug, category = ent["slug"], ent["category"]
        try:
            data = json.loads(gh_api_file(f"components/{slug}/data.json", ref))
            sym_name, fp_name = data["symbol"], data["footprint"]
            replaced_fp = fp_name in FP_REPLACEMENTS
            sym = gh_api_file(f"components/{slug}/{sym_name}.kicad_sym", ref)
            fp = None if replaced_fp else \
                gh_api_file(f"components/{slug}/{fp_name}.kicad_mod", ref)
            if not sym or (not replaced_fp and not fp):
                skipped.append((slug, "symbol/footprint fetch failed")); continue
            sym_text = flatten_extends(sym.decode("utf-8"), sym_name)
            if not sym_text:
                skipped.append((slug, f"symbol '{sym_name}' not found/flatten failed")); continue

            mpn = data.get("mpn") or slug
            pid = "antmicro_" + slugify(mpn)
            if replaced_fp:
                # §21-C 대체 수입: 공식 카피 판정 풋프린트 → 자체 생성 랜드패턴
                fp_text = chip_footprint(pid, FP_REPLACEMENTS[fp_name])
            else:
                fp_text = fp.decode("utf-8")
            if '"F.CrtYd"' not in fp_text:
                skipped.append((slug, "no courtyard")); continue
            d = os.path.join(LIB_ROOT, category, "antmicro", pid)
            os.makedirs(d, exist_ok=True)

            # glTF: LOD2 → LOD1 → 원본 (경량판 우선, 웹 프리뷰 용도)
            glb_size = None
            gname = data.get("gltf_model")
            if gname:
                # gltf-models 디렉토리명은 부품 슬러그가 아니라 "모델명 슬러그"
                gdir = re.sub(r"[^a-z0-9]+", "-", gname.lower()).strip("-")
                for lod in ("LOD2/", "LOD1/", ""):
                    gp = f"gltf-models/{gdir}/{lod}{gname}"
                    g_local = os.path.join(tmp, f"{pid}.gltf")
                    b_local = os.path.join(tmp, f"{gname}.bin")
                    if raw_file(gp + ".gltf", ref, g_local) and \
                       raw_file(gp + ".bin", ref, b_local):
                        try:
                            glb_size = gltf_to_glb(g_local, os.path.join(d, f"{pid}.glb"))
                            break
                        except Exception:
                            continue

            # 3D 모델 경로 제거 (glb만 제공, step 없음)
            fp_text = re.sub(r'\(model\s+"[^"]*"', '(model "%s.glb"' % pid, fp_text)
            mods = ["converted glTF (LOD) to single-mesh GLB preview"]
            if replaced_fp:
                mods.append(
                    f"footprint replaced: source used '{fp_name}' (KiCad-official-"
                    "derived, license-incompatible); PartReel generated its own "
                    "IPC-7351 density-B nominal land pattern instead (values per "
                    "KEMET C1002 X7R SMD datasheet Table 3)")
            open(os.path.join(d, f"{pid}.kicad_mod"), "w", encoding="utf-8",
                 newline="\n").write(fp_text)
            open(os.path.join(d, f"{pid}.kicad_sym"), "w", encoding="utf-8",
                 newline="\n").write(sym_text)

            kw = [w.strip().lower() for w in (data.get("keywords") or "").split(",") if w.strip()]
            files = {"footprint": f"{pid}.kicad_mod", "symbol": f"{pid}.kicad_sym",
                     "footprint_svg": f"{pid}.footprint.svg",
                     "symbol_svg": f"{pid}.symbol.svg"}
            formats = ["kicad_mod", "kicad_sym"]
            if glb_size:
                files["preview"] = f"{pid}.glb"
                formats.append("glb")
            meta = {
                "id": pid, "name": mpn, "category": category,
                "family": "Antmicro " + category,
                "manufacturer": data.get("manufacturer") or "",
                "mpn_pattern": mpn,
                "description": (data.get("description") or mpn) +
                               " Imported from Antmicro hardware-components "
                               "(Apache-2.0, attribution: Antmicro); passed PartReel "
                               "quality gates.",
                "parameters": {"contacts": len(data.get("pads") or []) or None,
                               "mounting": "SMD"},
                "files": files, "formats": formats,
                "datasheet": data.get("datasheet") or "",
                "dimensions_source": f"antmicro/hardware-components@{ref[:12]} "
                                     f"(components/{slug})" +
                                     ("; footprint land pattern: IPC-7351 density "
                                      "level B nominal (KEMET C1002 X7R SMD "
                                      "datasheet Table 3)" if replaced_fp else ""),
                "verified": True, "origin": "imported", "license": "Apache-2.0",
                "generated_by": "generators/import_antmicro.py",
                "keywords": ["antmicro"] + kw[:8],
                "import": {
                    "source_repo": f"https://github.com/{REPO}",
                    "source_commit": ref,
                    "source_files": {"component": f"components/{slug}"},
                    "attribution": ATTR, "modifications": mods,
                },
            }
            if not glb_size:
                meta["tier"] = "verified-2d"
            json.dump(meta, open(os.path.join(d, "meta.json"), "w", encoding="utf-8"),
                      indent=2, ensure_ascii=False)
            accepted.append((pid, glb_size))
            print("등록:", pid, f"(glb {glb_size or '-'} bytes)")
        except Exception as e:
            skipped.append((slug, f"error: {e}"))
    json.dump({"commit": ref,
               "accepted": [{"id": a, "glb_bytes": s} for a, s in accepted],
               "skipped": [{"slug": n, "reason": r} for n, r in skipped]},
              open(os.path.join(ROOT, "docs", "import-antmicro-log.json"), "w",
                   encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"accepted {len(accepted)}, skipped {len(skipped)}")


def main_all():
    ref = os.environ.get("ANTMICRO_COMMIT", "main")
    comp_dir = os.path.join(SRC_LOCAL, "components")
    slugs = sorted(os.listdir(comp_dir))
    excl = excluded_footprints()
    print(f"components: {len(slugs)}, excluded footprints: {len(excl)}")
    cfg = {"commit": ref, "parts": []}
    skipped_pre = []
    for slug in slugs:
        raw = _resolve_local(f"components/{slug}/data.json")
        if not raw:
            skipped_pre.append((slug, "no data.json")); continue
        try:
            data = json.loads(raw)
        except ValueError:
            skipped_pre.append((slug, "bad data.json")); continue
        if data.get("public") is False:
            skipped_pre.append((slug, "not public")); continue
        if data.get("footprint") in excl:
            skipped_pre.append((slug, f"excluded footprint {data.get('footprint')}")); continue
        cfg["parts"].append({"slug": slug,
                             "category": guess_category(data, data.get("footprint"))})
    print(f"eligible: {len(cfg['parts'])}, pre-skipped: {len(skipped_pre)}")
    json.dump({"commit": ref, "parts": cfg["parts"]},
              open(os.path.join(ROOT, "docs", "antmicro-wave.json"), "w",
                   encoding="utf-8"), indent=1)
    json.dump([{"slug": a, "reason": b} for a, b in skipped_pre],
              open(os.path.join(ROOT, "docs", "antmicro-wave-preskip.json"), "w",
                   encoding="utf-8"), indent=1)
    import_loop(cfg, ref)


if __name__ == "__main__":
    main()
