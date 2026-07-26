"""
풋프린트 원산지 판별기 (REQUIREMENTS §21-C / next-wave-sources 액션 3).
"이름이 같다"가 아니라 "패드 지오메트리가 같다"로 공식 KiCad 라이브러리 복사 여부를 판정.

용법:
  python generators/check_provenance.py --official <공식클론경로> --index      # 서명 색인 생성(1회)
  python generators/check_provenance.py --official <경로> --file a.kicad_mod [b.kicad_mod ...]
  python generators/check_provenance.py --official <경로> --pairs pairs.json   # [{file, official_name}]

판정:
  IDENTICAL  패드 전부 일치(±0.005mm) → 공식 산출물 복사 (수입 거부)
  NEAR       패드 수 같고 최대 편차 <0.05mm → 파생 의심 (수동 검토)
  DIFFERENT  그 외 → 자체 제작으로 인정
서명: 패드(번호,종류,모양,크기,상대좌표)를 1번 패드 기준 정규화·정렬. 이름 무관 전수
탐색은 (패드수, 크기 멀티셋) 버킷으로 후보를 좁힌 뒤 비교.
"""
import argparse
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

PAD_RE = re.compile(
    r'\(pad\s+"([^"]*)"\s+(\w+)\s+(\w+)\s*\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+[-\d.]+)?\)'
    r'\s*\(size\s+([-\d.]+)\s+([-\d.]+)')


def pads_of(text):
    out = []
    for m in PAD_RE.finditer(text):
        num, typ, shape, x, y, w, h = m.groups()
        out.append((num, typ, shape, float(x), float(y), float(w), float(h)))
    return out


def signature(pads):
    """1번(정렬 첫) 패드 기준 상대좌표로 정규화한 튜플 목록."""
    if not pads:
        return None
    pads = sorted(pads, key=lambda p: (p[0], p[3], p[4]))
    ox, oy = pads[0][3], pads[0][4]
    return tuple((p[0], p[1], p[2], round(p[3] - ox, 3), round(p[4] - oy, 3),
                  round(p[5], 3), round(p[6], 3)) for p in pads)


def bucket_key(pads):
    sizes = tuple(sorted((round(p[5], 2), round(p[6], 2)) for p in pads))
    return f"{len(pads)}|{hash(sizes) & 0xffffffff:x}"


def compare(sig_a, sig_b):
    """(판정, 최대편차mm). 패드수 다르면 DIFFERENT."""
    if sig_a is None or sig_b is None or len(sig_a) != len(sig_b):
        return "DIFFERENT", None
    worst = 0.0
    for a, b in zip(sig_a, sig_b):
        if a[1] != b[1] or a[2] != b[2]:  # 종류/모양 다름
            return "DIFFERENT", None
        d = max(abs(a[3] - b[3]), abs(a[4] - b[4]), abs(a[5] - b[5]), abs(a[6] - b[6]))
        worst = max(worst, d)
    if worst <= 0.005:
        return "IDENTICAL", worst
    if worst < 0.05:
        return "NEAR", worst
    return "DIFFERENT", worst


def build_index(official_dir, cache_path):
    idx = {}
    files = glob.glob(os.path.join(official_dir, "*.pretty", "*.kicad_mod"))
    for f in files:
        try:
            pads = pads_of(open(f, encoding="utf-8", errors="replace").read())
        except OSError:
            continue
        if not pads:
            continue
        name = os.path.splitext(os.path.basename(f))[0]
        idx.setdefault(bucket_key(pads), []).append(
            {"name": name, "sig": signature(pads)})
    json.dump(idx, open(cache_path, "w", encoding="utf-8"))
    print(f"indexed {len(files)} official footprints -> {cache_path}")


def load_index(cache_path):
    raw = json.load(open(cache_path, encoding="utf-8"))
    return {k: [{"name": e["name"], "sig": tuple(tuple(t) for t in e["sig"])}
                for e in v] for k, v in raw.items()}


def judge_file(path, idx, official_dir=None, official_name=None):
    pads = pads_of(open(path, encoding="utf-8", errors="replace").read())
    sig = signature(pads)
    if official_name and official_dir:
        cands = glob.glob(os.path.join(official_dir, "*.pretty", official_name + ".kicad_mod"))
        best = ("DIFFERENT", None, official_name)
        for c in cands:
            v, d = compare(sig, signature(pads_of(open(c, encoding="utf-8",
                                                       errors="replace").read())))
            if v != "DIFFERENT" or best[0] == "DIFFERENT":
                best = (v, d, official_name)
            if v == "IDENTICAL":
                break
        return best
    # 이름 무관 전수 탐색 (버킷)
    for e in idx.get(bucket_key(pads), []):
        v, d = compare(sig, e["sig"])
        if v in ("IDENTICAL", "NEAR"):
            return (v, d, e["name"])
    return ("DIFFERENT", None, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--official", required=True)
    ap.add_argument("--index", action="store_true")
    ap.add_argument("--pairs")
    ap.add_argument("--file", nargs="*")
    args = ap.parse_args()
    cache = os.path.join(ROOT, "docs", "official-fp-signatures.json")
    if args.index:
        build_index(args.official, cache)
        return
    idx = load_index(cache) if os.path.exists(cache) else {}
    results = []
    if args.pairs:
        for ent in json.load(open(args.pairs, encoding="utf-8")):
            v, d, ref = judge_file(ent["file"], idx, args.official, ent.get("official_name"))
            results.append({"file": ent["file"], "verdict": v, "max_delta_mm": d, "matched": ref})
    for f in (args.file or []):
        v, d, ref = judge_file(f, idx)
        results.append({"file": f, "verdict": v, "max_delta_mm": d, "matched": ref})
    for r in results:
        print(f"{r['verdict']:<10} {os.path.basename(r['file']):<50} "
              f"delta={r['max_delta_mm']} match={r['matched']}")
    out = os.path.join(ROOT, "docs", "provenance-report.json")
    json.dump(results, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
