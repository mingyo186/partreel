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
import urllib.error
import urllib.request
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SITE = "https://partreel.com"
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
    # 모든 패키지의 해시·크기 대조 (라이브러리 + 플러그인)
    zips = {}
    for p in pkgs["packages"]:
        for ver in p["versions"]:
            b = read(os.path.basename(ver["download_url"]), binary=True)
            # 구조 검사는 **최신 버전**(versions[0]) 기준 — 덮어쓰면 마지막
            # 순회분(가장 오래된 zip)이 검사돼 새 결함을 놓친다
            zips.setdefault(p["identifier"], b)
            if hashlib.sha256(b).hexdigest() != ver["download_sha256"]:
                fail(f"{p['identifier']}: zip sha256 불일치")
            if len(b) != ver["download_size"]:
                fail(f"{p['identifier']}: download_size 불일치 "
                     f"({len(b)} != {ver['download_size']})")
            print(f"해시 연쇄 OK: {p['identifier']} "
                  f"({len(b) / 1024:.0f} KB, v{ver['version']}, {p['type']})")

    # === 회귀 게이트: 이미 발행한 버전을 목록에서 떨어뜨리지 않았는가 ===
    # PCM은 '설치된 버전'을 목록에서 찾아 상태를 계산한다. 옛 버전을 지우면
    # 그 버전을 쓰던 사용자에게 "버전 패키지를 찾을 수 없습니다"가 뜬다
    # (2026-08-01 사용자 제보). 라이브 목록과 대조해 유실을 막는다.
    KEEP = 5
    try:
        req = urllib.request.Request(f"{SITE}/pcm/packages.json",
                                     headers={"User-Agent": "partreel-pcm-check"})
        with urllib.request.urlopen(req, timeout=30) as r:
            live = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        print(f"경고: 라이브 packages.json 대조 생략 (네트워크/파싱: {e})")
        live = None
    if live:
        new_by_id = {p["identifier"]: {v["version"] for v in p["versions"]}
                     for p in pkgs["packages"]}
        for p in live.get("packages", []):
            ident = p["identifier"]
            if ident not in new_by_id:
                fail(f"라이브에 있던 패키지가 사라짐: {ident}")
                continue
            gone = [v["version"] for v in p["versions"]
                    if v["version"] not in new_by_id[ident]]
            # 보관 한도(KEEP)에 도달해 가장 오래된 것만 밀려나는 건 정상
            if gone and len(new_by_id[ident]) < KEEP:
                fail(f"{ident}: 발행했던 버전이 목록에서 사라짐 {gone} "
                     f"(현재 {len(new_by_id[ident])}개 < 보관한도 {KEEP}) — "
                     "그 버전 사용자는 PCM에서 오류를 본다")
            elif gone:
                print(f"  이력 정리(정상): {ident} {gone} 밀려남 "
                      f"(보관한도 {KEEP} 유지)")

    # 플러그인 패키지 구조 (공식 규격: plugins/ 직접 배치 + resources/icon.png)
    for p in pkgs["packages"]:
        if p["type"] != "plugin":
            continue
        with zipfile.ZipFile(io.BytesIO(zips[p["identifier"]])) as z:
            n = z.namelist()
            if "plugins/__init__.py" not in n:
                fail(f"{p['identifier']}: plugins/__init__.py 없음")
            if "resources/icon.png" not in n:
                fail(f"{p['identifier']}: resources/icon.png 없음")
            if "metadata.json" not in n:
                fail(f"{p['identifier']}: metadata.json 없음")
            # 배치 파일은 ASCII 전용 — cmd.exe는 OEM 코드페이지(한국어 cp949)로
            # 파싱하므로 UTF-8 한글이 들어가면 파일 자체가 깨진다
            # (2026-08-01 사용자 제보: 실행 시 '...은(는) 내부 또는 외부 명령...' 연발)
            for path in n:
                if path.lower().endswith((".cmd", ".bat")):
                    raw = z.read(path)
                    bad = [b for b in raw if b > 127]
                    if bad:
                        fail(f"{p['identifier']}: {path}에 비ASCII 바이트 "
                             f"{len(bad)}개 — cp949 콘솔에서 배치 파싱이 깨진다")
            import struct
            for path, want in (("resources/icon.png", 64), ("plugins/icon.png", 24)):
                if path in n:
                    d = z.read(path)
                    w, h = struct.unpack(">II", d[16:24])
                    if (w, h) != (want, want):
                        fail(f"{p['identifier']}: {path} 크기 {w}x{h} "
                             f"(규격 {want}x{want})")
            print(f"플러그인 구조 OK: {p['identifier']}")

    pkg = next(p for p in pkgs["packages"] if p["type"] == "library")
    v = pkg["versions"][0]
    zb = zips[pkg["identifier"]]

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
