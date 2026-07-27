"""
대용량 에셋(step/glb) → Cloudflare R2 동기화 + meta 해시 기록 (REQUIREMENTS §22).

실행:
  python generators/sync_r2.py --hash        # meta.json에 sha256만 기록 (버킷 불필요)
  python generators/sync_r2.py --upload      # 해시 기록 + wrangler로 R2 업로드
업로드는 mcp/ 의 wrangler 인증을 사용. 오브젝트 키 = library/<...>/<파일> (사이트 경로 동일).
R2 파일은 git 이력이 없으므로 meta의 sha256이 "이 커밋이 보증하는 파일" 링크가 된다.

업로드 범위 (2026-07-27 사건 — 139개 신규분 업로드가 16,543개 전량 순차 재업로드가 되어
36시간 규모로 늘어남):
  - 기본은 **R2에 아직 없는 파일만** 올린다 (HEAD로 존재 확인, 10스레드).
  - PART_SCOPE / PART_SCOPE_FILE 로 부품 범위를 좁힐 수 있다 (게이트와 동일 규약).
  - --force-all 을 주면 존재 확인 없이 전량 재업로드 (버킷 재구축용).
"""
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scope import scoped_parts  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BUCKET = "partreel-assets"
ASSET_HOST = "https://assets.partreel.com"
EXTS = (".step", ".glb")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def exists_on_r2(key_path):
    req = urllib.request.Request(f"{ASSET_HOST}/{key_path}", method="HEAD",
                                 headers={"User-Agent": "partreel-sync"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200
    except Exception:
        return False


def upload(job):
    key_path, fpath = job
    for _ in range(3):
        r = subprocess.run(["npx", "wrangler", "r2", "object", "put",
                            f"{BUCKET}/{key_path}", "--file", fpath, "--remote"],
                           cwd=os.path.join(ROOT, "mcp"), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", shell=True)
        if r.returncode == 0:
            return None
    return key_path


def main():
    upload_mode = "--upload" in sys.argv
    force_all = "--force-all" in sys.argv
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    parts = scoped_parts(index["parts"])
    if len(parts) != len(index["parts"]):
        print(f"scope: {len(parts)}/{len(index['parts'])} parts")
    hashed = 0
    jobs = []
    for p in parts:
        d = os.path.join(ROOT, p["path"])
        mpath = os.path.join(d, "meta.json")
        meta = json.load(open(mpath, encoding="utf-8"))
        changed = False
        hashes = meta.get("asset_sha256", {})
        for key, fn in meta.get("files", {}).items():
            if not fn.lower().endswith(EXTS):
                continue
            fpath = os.path.join(d, fn)
            if not os.path.exists(fpath):
                print(f"MISSING {p['id']}: {fn}")
                continue
            digest = sha256(fpath)
            if hashes.get(fn) != digest:
                hashes[fn] = digest
                changed = True
            hashed += 1
            if upload_mode:
                jobs.append((f"{p['path']}/{fn}".replace("\\", "/"), fpath))
        if changed:
            meta["asset_sha256"] = hashes
            json.dump(meta, open(mpath, "w", encoding="utf-8"),
                      indent=2, ensure_ascii=False)
    print(f"hashed {hashed} assets")

    if not upload_mode:
        return
    if not force_all:
        print(f"checking R2 for {len(jobs)} assets...")
        with ThreadPoolExecutor(16) as ex:
            present = list(ex.map(lambda j: exists_on_r2(j[0]), jobs))
        jobs = [j for j, ok in zip(jobs, present) if not ok]
        print(f"missing on R2: {len(jobs)}")
    if not jobs:
        print("uploaded 0 (nothing to do)")
        return
    fails = []
    with ThreadPoolExecutor(10) as ex:
        for i, r in enumerate(ex.map(upload, jobs)):
            if r:
                fails.append(r)
            if (i + 1) % 50 == 0 or (i + 1) == len(jobs):
                print(f"uploaded {i + 1}/{len(jobs)}", flush=True)
    print(f"upload done, fails {len(fails)}")
    if fails:
        for f in fails[:10]:
            print("UPLOAD FAIL", f)
        sys.exit(1)


if __name__ == "__main__":
    main()
