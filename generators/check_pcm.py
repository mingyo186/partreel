"""
PCM 저장소 검사기 (REQUIREMENTS §18-B) — GUI 불필요.

KiCad가 실제로 하는 검증을 재현한다:
  A. 공식 v2 스키마(https://go.kicad.org/pcm/schemas/v2)로 repository.json /
     packages.json / zip 내부 metadata.json 을 형식 검증
  B. 해시 연쇄 대조: repository → packages → zip (sha256/크기)
  C. zip 구조(metadata + symbols/ + footprints/) + kicad-cli 커널 렌더

실행: python generators/check_pcm.py            (로컬 pcm/ 검사)
      PCM_BASE=https://partreel.com/pcm ...     (라이브 검사)

계기: v1 스키마로 냈더니 저장소는 추가되는데 라이브러리 탭이 비어 있었다
(2026-08-01). 형식 오류를 사람이 눈으로 못 잡으므로 게이트로 고정한다.
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BASE = os.environ.get("PCM_BASE", "")  # 비면 로컬 pcm/ 검사
SCHEMA_URL = "https://go.kicad.org/pcm/schemas/v2"
KICAD_CLI = os.environ.get(
    "KICAD_CLI", r"D:\Program Files\KiCad\10.0\bin\kicad-cli.exe")

errs = []


def fail(m):
    errs.append(m)
    print("FAIL", m)


def read(name, binary=False):
    if BASE:
        with urllib.request.urlopen(f"{BASE}/{name}", timeout=60) as r:
            data = r.read()
    else:
        data = open(os.path.join(ROOT, "pcm", name), "rb").read()
    return data if binary else data.decode("utf-8")


def main():
    # 공식 스키마: 기본 UA로는 403이라 UA 지정. 받아지면 로컬에 캐시해두고
    # (docs/pcm-schema-v2.json) 네트워크가 막힌 CI에서도 형식 검증을 유지한다.
    cache = os.path.join(ROOT, "docs", "pcm-schema-v2.json")
    schema = None
    try:
        req = urllib.request.Request(SCHEMA_URL,
                                     headers={"User-Agent": "partreel-pcm-check"})
        with urllib.request.urlopen(req, timeout=60) as r:
            schema = json.loads(r.read().decode("utf-8"))
        json.dump(schema, open(cache, "w", encoding="utf-8"), indent=1)
    except Exception as e:
        if os.path.exists(cache):
            schema = json.load(open(cache, encoding="utf-8"))
            print(f"공식 스키마 내려받기 실패({e}) — 로컬 캐시 사용")
        else:
            print(f"경고: 공식 스키마 없음 ({e}) — 형식 검증 생략")

    repo = json.loads(read("repository.json"))
    pkgs_blob = read("packages.json", binary=True)
    pkgs = json.loads(pkgs_blob.decode("utf-8"))

    # A. 스키마 검증
    if schema:
        import jsonschema
        defs = schema.get("definitions", {})
        base = {"$schema": schema["$schema"], "definitions": defs}
        for obj, dname, label in ((repo, "Repository", "repository.json"),
                                  (pkgs, "PackageArray", "packages.json")):
            if dname not in defs:
                # PackageArray가 없으면 개별 Package로 검증
                continue
            try:
                jsonschema.validate(obj, {**base, "$ref": f"#/definitions/{dname}"})
                print(f"스키마 OK: {label} ({dname})")
            except jsonschema.ValidationError as e:
                fail(f"{label} 스키마 위반: {e.message} (경로 {list(e.path)})")
        if "Package" in defs:
            for p in pkgs.get("packages", []):
                try:
                    jsonschema.validate(p, {**base, "$ref": "#/definitions/Package"})
                except jsonschema.ValidationError as e:
                    fail(f"패키지 '{p.get('identifier')}' 스키마 위반: {e.message} "
                         f"(경로 {list(e.path)})")
            print(f"스키마 OK: 패키지 {len(pkgs.get('packages', []))}건")

    # v2 필수 표식 (KiCad 10이 v2를 요구 — v1이면 라이브러리 탭이 빈다)
    if repo.get("schema_version") != 2:
        fail(f"repository.schema_version != 2 ({repo.get('schema_version')})")
    if "/v2" not in str(repo.get("$schema", "")):
        fail(f"repository.$schema가 v2가 아님: {repo.get('$schema')}")
    for k in ("update_time_utc", "update_timestamp"):
        if k not in repo.get("packages", {}):
            fail(f"repository.packages.{k} 없음")

    # B. 해시 연쇄
    if hashlib.sha256(pkgs_blob).hexdigest() != repo["packages"]["sha256"]:
        fail("repository → packages sha256 불일치")
    pkg = pkgs["packages"][0]
    v = pkg["versions"][0]
    zb = read(os.path.basename(v["download_url"]), binary=True)
    if hashlib.sha256(zb).hexdigest() != v["download_sha256"]:
        fail("packages → zip sha256 불일치")
    if len(zb) != v["download_size"]:
        fail(f"download_size 불일치: {len(zb)} != {v['download_size']}")
    print(f"해시 연쇄 OK (zip {len(zb) / 1024:.0f} KB, 버전 {v['version']})")

    # C. zip 구조 + 커널
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(io.BytesIO(zb)) as z:
        names = z.namelist()
        for want in ("metadata.json",):
            if want not in names:
                fail(f"zip에 {want} 없음")
        if not any(n.startswith("symbols/") for n in names):
            fail("zip에 symbols/ 없음")
        if not any(n.startswith("footprints/") for n in names):
            fail("zip에 footprints/ 없음")
        inner = json.loads(z.read("metadata.json"))
        if inner.get("identifier") != pkg.get("identifier"):
            fail("zip metadata.json의 identifier가 packages.json과 다름")
        z.extractall(tmp)

    if os.path.exists(KICAD_CLI):
        sym = os.path.join(tmp, "symbols", "PartReel.kicad_sym")
        out = os.path.join(tmp, "svg"); os.makedirs(out, exist_ok=True)
        subprocess.run([KICAD_CLI, "sym", "export", "svg", sym, "-o", out],
                       capture_output=True, timeout=900)
        n_sym = len(os.listdir(out))
        pretty = os.path.join(tmp, "footprints", "PartReel.pretty")
        fout = os.path.join(tmp, "fpsvg"); os.makedirs(fout, exist_ok=True)
        subprocess.run([KICAD_CLI, "fp", "export", "svg", pretty, "-o", fout],
                       capture_output=True, timeout=900)
        n_fp = len(os.listdir(fout))
        n_mod = len([f for f in os.listdir(pretty) if f.endswith(".kicad_mod")])
        print(f"커널: 심볼 SVG {n_sym} / 풋프린트 {n_fp}(파일 {n_mod})")
        if n_sym < 100:
            fail(f"심볼 렌더 부족: {n_sym}")
        if n_fp < n_mod:
            fail(f"풋프린트 렌더 부족: {n_fp} < {n_mod}")
    else:
        print("경고: kicad-cli 없음 — 커널 검증 생략")

    print("PASS: PCM 저장소 정상" if not errs else f"FAIL: {len(errs)}건")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
