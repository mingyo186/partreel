"""
대용량 에셋(step/glb) → Cloudflare R2 동기화 + meta 해시 기록 (REQUIREMENTS §22).

실행:
  python generators/sync_r2.py --hash        # meta.json에 sha256만 기록 (버킷 불필요)
  python generators/sync_r2.py --upload      # 해시 기록 + wrangler로 R2 업로드
업로드는 mcp/ 의 wrangler 인증을 사용. 오브젝트 키 = library/<...>/<파일> (사이트 경로 동일).
R2 파일은 git 이력이 없으므로 meta의 sha256이 "이 커밋이 보증하는 파일" 링크가 된다.
"""
import hashlib
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BUCKET = "partreel-assets"
EXTS = (".step", ".glb")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    upload = "--upload" in sys.argv
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    hashed = uploaded = 0
    for p in index["parts"]:
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
            if upload:
                key_path = f"{p['path']}/{fn}".replace("\\", "/")
                r = subprocess.run(
                    ["npx", "wrangler", "r2", "object", "put",
                     f"{BUCKET}/{key_path}", "--file", fpath, "--remote"],
                    cwd=os.path.join(ROOT, "mcp"), capture_output=True, text=True,
                    shell=True)
                if r.returncode != 0:
                    print(f"UPLOAD FAIL {key_path}: {(r.stderr or '')[-200:]}")
                    sys.exit(1)
                uploaded += 1
        if changed:
            meta["asset_sha256"] = hashes
            json.dump(meta, open(mpath, "w", encoding="utf-8"),
                      indent=2, ensure_ascii=False)
    print(f"hashed {hashed} assets" + (f", uploaded {uploaded}" if upload else ""))


if __name__ == "__main__":
    main()
