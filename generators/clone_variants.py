"""
검증-변형 등록기 (§1-0 "모으기>만들기" + §21-6 변형 원칙).
기존 검증 부품의 풋프린트·심볼을 재사용해 '같은 패키지·핀배치' 형제 품번을 등록.
근거: Opus 조사(제조사 패밀리 데이터시트) — pin_renames로 핀명 차이 반영.
실행: python generators/clone_variants.py docs/variants-ti-power.json
"""
import json
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def slug(s):
    t = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return re.sub(r"_+", "_", t)


def rename_pins(sym_text, renames):
    """핀 번호 -> 새 이름. KiCad9 멀티라인 중첩 포맷 대응: (number "N") 위치에서
    바로 앞의 (name "...") 문자열만 위치 기반으로 치환 (§14-H: 중첩괄호 정규식 금지)."""
    if not renames:
        return sym_text
    out = sym_text
    for num, newname in renames.items():
        hits = 0
        pos = 0
        while True:
            m = re.search(r'\(number\s+"' + re.escape(str(num)) + r'"', out[pos:])
            if not m:
                break
            npos = pos + m.start()
            nm = None
            for cand in re.finditer(r'\(name\s+"([^"]*)"', out[:npos]):
                nm = cand
            if nm is None:
                raise RuntimeError(f"pin {num}: name not found before number")
            out = out[:nm.start(1)] + newname + out[nm.end(1):]
            pos = npos + (len(newname) - (nm.end(1) - nm.start(1))) + 5
            hits += 1
        if hits == 0:
            raise RuntimeError(f"pin {num} rename failed")
    return out


def main():
    cfg_path = sys.argv[1]
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    idx = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    paths = {p["id"]: p["path"] for p in idx["parts"]}
    existing_mpns = set()
    for p in idx["parts"]:
        m = json.load(open(os.path.join(ROOT, p["path"], "meta.json"), encoding="utf-8"))
        existing_mpns.add((m.get("mpn_pattern") or "").upper())
    made = skipped = 0
    for v in cfg:
        mpn = v["mpn"]
        if mpn.upper() in existing_mpns:
            print("skip(보유):", mpn); skipped += 1; continue
        src = v["src_id"]
        sd = os.path.join(ROOT, paths[src])
        smeta = json.load(open(os.path.join(sd, "meta.json"), encoding="utf-8"))
        nid = "ti_" + slug(mpn)
        nd = os.path.join(os.path.dirname(sd), nid)
        os.makedirs(nd, exist_ok=True)
        # 풋프린트: 그대로 (검증된 랜드패턴 재사용)
        fp = open(os.path.join(sd, src + ".kicad_mod"), encoding="utf-8").read()
        open(os.path.join(nd, nid + ".kicad_mod"), "w", encoding="utf-8").write(fp)
        # 심볼: id 치환 + 핀명 변경
        sym = open(os.path.join(sd, src + ".kicad_sym"), encoding="utf-8").read()
        sym = sym.replace(f'"{src}', f'"{nid}')  # 심볼명/유닛명 프리픽스 치환
        sym = rename_pins(sym, v.get("pin_renames") or {})
        open(os.path.join(nd, nid + ".kicad_sym"), "w", encoding="utf-8").write(sym)
        meta = dict(smeta)
        meta["id"] = nid
        meta["name"] = mpn
        meta["mpn_pattern"] = mpn
        meta["description"] = (f"{v['diff']} Same package and pinout as {smeta['mpn_pattern']} "
                               f"per the TI family datasheet; footprint/symbol reuse the "
                               f"gate-verified {smeta['mpn_pattern']} assets"
                               + (" (pins renamed per variant)." if v.get("pin_renames") else "."))
        meta["datasheet"] = v["datasheet"]
        meta["files"] = {k: fn.replace(src, nid) for k, fn in smeta["files"].items()
                         if not fn.endswith((".step", ".glb"))}
        meta["formats"] = [f for f in smeta["formats"] if f not in ("step", "glb")]
        meta.pop("asset_sha256", None)
        meta["tier"] = "verified-2d"
        meta["generated_by"] = "generators/clone_variants.py"
        imp = dict(smeta.get("import") or {})
        imp["modifications"] = list(imp.get("modifications") or []) + [
            f"registered as same-package variant of {smeta['mpn_pattern']} "
            f"(TI family datasheet evidence; Opus research 2026-07-17)"]
        meta["import"] = imp
        json.dump(meta, open(os.path.join(nd, "meta.json"), "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)
        made += 1
        print("등록:", nid)
    print(f"variants made {made}, skipped {skipped}")


if __name__ == "__main__":
    main()
