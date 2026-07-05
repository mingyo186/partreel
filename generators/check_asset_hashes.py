"""
에셋 무결성 게이트 (REQUIREMENTS §22): meta.asset_sha256 vs 실제 파일 해시 일치.
R2 이전 후에는 "이 커밋이 보증하는 파일" 검증 경로가 이 해시뿐이므로 영구 게이트.
실행: python generators/check_asset_hashes.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync_r2 import sha256, EXTS  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    errs = 0
    checked = 0
    for p in index["parts"]:
        d = os.path.join(ROOT, p["path"])
        meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
        hashes = meta.get("asset_sha256", {})
        for key, fn in meta.get("files", {}).items():
            if not fn.lower().endswith(EXTS):
                continue
            fpath = os.path.join(d, fn)
            if not os.path.exists(fpath):
                continue  # 파일 존재 검사는 check_render 소관
            if fn not in hashes:
                print(f"FAIL {p['id']}: {fn} 해시 미기록 (sync_r2.py --hash 실행)")
                errs += 1
            elif sha256(fpath) != hashes[fn]:
                print(f"FAIL {p['id']}: {fn} 해시 불일치 (파일 변경 후 미갱신?)")
                errs += 1
            checked += 1
    print(f"{'PASS' if not errs else 'FAIL'}: {checked} assets, {errs} hash issues")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
