"""
R2 에셋 서빙 게이트 (REQUIREMENTS §22): 모든 step/glb가 assets.partreel.com에서
200으로 서빙되는지 HEAD 전수검사 + 무작위 3개는 GET 후 meta.asset_sha256과 대조.
실행: python generators/check_r2.py
"""
import hashlib
import json
import os
import random
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BASE = "https://assets.partreel.com"


def head(url):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "partreel-qa-gate"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except Exception as e:
        return getattr(e, "code", str(e))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    targets = []  # (url, sha256)
    for p in index["parts"]:
        meta = json.load(open(os.path.join(ROOT, p["path"], "meta.json"),
                              encoding="utf-8"))
        hashes = meta.get("asset_sha256", {})
        for fn in meta.get("files", {}).values():
            if fn.lower().endswith((".step", ".glb")):
                url = f"{BASE}/{p['path']}".replace("\\", "/") + f"/{fn}"
                targets.append((url, hashes.get(fn)))
    errs = 0
    with ThreadPoolExecutor(16) as ex:
        for (url, _), st in zip(targets, ex.map(lambda t: head(t[0]), targets)):
            if st != 200:
                print(f"FAIL {st}: {url}")
                errs += 1
    # 무작위 3개 내용 해시 대조 (전송 무결성)
    rng = random.Random(42)
    for url, digest in rng.sample([t for t in targets if t[1]], min(3, len(targets))):
        req2 = urllib.request.Request(url, headers={"User-Agent": "partreel-qa-gate"})
        with urllib.request.urlopen(req2, timeout=60) as r:
            body = r.read()
        if hashlib.sha256(body).hexdigest() != digest:
            print(f"FAIL hash mismatch: {url}")
            errs += 1
    print(f"{'PASS' if not errs else 'FAIL'}: {len(targets)} R2 assets, {errs} issues")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
