"""
수입 부품 데이터시트 URL 복원 (검증된 것만 — 날조 금지).
제조사별 URL 패턴으로 후보 생성 → HEAD 200 확인된 것만 meta.datasheet 갱신.
실행: python generators/resolve_datasheets.py [--apply]
"""
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
UA = {"User-Agent": "Mozilla/5.0 partreel-datasheet-resolver"}


def ok(url):
    try:
        req = urllib.request.Request(url, method="HEAD", headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200 and "pdf" in (r.headers.get("Content-Type") or "").lower()
    except Exception:
        return False


def ti_candidates(mpn):
    """TI: ti.com/lit/ds/symlink/<base>.pdf — 패키지 접미사 단계적 제거."""
    base = mpn.lower().replace(" ", "")
    cands = [base]
    # 뒤에서부터 접미사 제거 (DW, PW, D, ID, APW 등 + 릴 표기)
    b = re.sub(r"[-/].*$", "", base)
    if b != base:
        cands.append(b)
    for suf in ("r", "t"):
        if b.endswith(suf):
            cands.append(b[:-1])
    m = re.match(r"^([a-z]+\d+[a-z]*?\d*)", b)
    if m and m.group(1) not in cands:
        cands.append(m.group(1))
    # 일반형: 영숫자 몸통에서 꼬리 알파벳 1~3개 떼기
    for i in (1, 2, 3):
        if len(b) > i and b[:-i] not in cands and b[:-i][-1].isdigit():
            cands.append(b[:-i])
    return [f"https://www.ti.com/lit/ds/symlink/{c}.pdf" for c in dict.fromkeys(cands)]


def main():
    apply = "--apply" in sys.argv
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    targets = []
    for p in index["parts"]:
        mpath = os.path.join(ROOT, p["path"], "meta.json")
        meta = json.load(open(mpath, encoding="utf-8"))
        if meta.get("origin") != "imported":
            continue
        ds = meta.get("datasheet", "")
        if "gitlab.com" not in ds and "github.com" not in ds:
            continue  # 이미 진짜 링크
        manu = (meta.get("manufacturer") or "").upper()
        if "TEXAS" in manu or manu == "TI":
            targets.append((mpath, meta))
    print(f"TI targets: {len(targets)}")

    def resolve(t):
        mpath, meta = t
        for url in ti_candidates(meta["mpn_pattern"]):
            if ok(url):
                return (mpath, meta, url)
        return None

    hits = 0
    with ThreadPoolExecutor(12) as ex:
        for r in ex.map(resolve, targets):
            if not r:
                continue
            mpath, meta, url = r
            hits += 1
            if apply:
                meta.setdefault("import", {}).setdefault("modifications", []).append(
                    "datasheet URL resolved by manufacturer pattern + HTTP verification")
                meta["datasheet"] = url
                json.dump(meta, open(mpath, "w", encoding="utf-8"),
                          indent=2, ensure_ascii=False)
    print(f"resolved {hits}/{len(targets)}" + (" (applied)" if apply else " (dry run)"))


if __name__ == "__main__":
    main()
