"""
KiCad HTTP-lib 어댑터 무헤드 통합 검사 (REQUIREMENTS §18-A — GUI 불필요).

KiCad 클라이언트가 하는 일을 그대로 재현해 전 구간을 검증한다:
  A. 프로토콜: 루트 검증 → categories.json → 카테고리별 목록 → 부품 상세
     (표본) — 스키마 키, "모든 값은 문자열" 규칙, 불리언 문자열.
  B. 정합: 상세의 symbolIdStr/Footprint 필드가 라이브 번들(PartReel.kicad_sym
     / PartReel-pretty.zip)에 실제 존재하는 심볼·풋프린트를 가리키는지.
  C. 커널: 라이브 번들을 내려받아 kicad-cli(진짜 KiCad 커널)로 파싱·렌더
     (KICAD_CLI 경로 없으면 C만 생략하고 경고).

실행: python generators/check_kicad_adapter.py  (네트워크 필요; 실패 시 비0 종료)
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
SITE = "https://partreel.com"
# 정적 API가 정본 (§18-A 3단계). KICAD_API_BASE로 워커 등 다른 구현도 검사 가능.
BASE = os.environ.get("KICAD_API_BASE", f"{SITE}/kicad/v1")
KICAD_CLI = os.environ.get(
    "KICAD_CLI", r"D:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
SAMPLE_PER_CAT = 3
# KiCad는 상세를 순차·동기로 전량 요청 → (응답시간 × 부품수) = UI 프리즈.
# 실측 회귀 게이트: 첫 동기화 추정 60초 초과면 실패 (사용자 제보 2026-08-01).
MAX_SYNC_SECONDS = 60

errs = []


def fail(msg):
    errs.append(msg)
    print("FAIL", msg)


def get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "partreel-adapter-check",
        "Authorization": "Token public",  # KiCad와 동일 헤더
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def get_json(url):
    return json.loads(get(url).decode("utf-8"))


def all_strings(obj, path="", allow_dict=("fields",)):
    """KiCad 규칙: 응답의 리프 값은 전부 문자열이어야 한다."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            all_strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            all_strings(v, f"{path}[{i}]")
    elif not isinstance(obj, str):
        fail(f"문자열 아님: {path} = {obj!r}")


def main():
    cb = f"?cb=check{os.getpid()}"

    # A-1. 루트 검증 (KiCad의 endpoint validation)
    root = get_json(f"{BASE}/{cb}")
    if "categories" not in root or "parts" not in root:
        fail(f"루트에 categories/parts 키 없음: {root}")

    # A-2. 카테고리
    cats = get_json(f"{BASE}/categories.json{cb}")
    if not isinstance(cats, list) or not cats:
        fail("categories.json이 비어있거나 리스트 아님")
    all_strings(cats, "categories")
    print(f"카테고리 {len(cats)}개")

    # 번들 (B/C용) 선다운로드
    tmp = tempfile.mkdtemp()
    sym_path = os.path.join(tmp, "PartReel.kicad_sym")
    open(sym_path, "wb").write(get(f"{SITE}/assets/PartReel.kicad_sym{cb}"))
    zf = zipfile.ZipFile(io.BytesIO(get(f"{SITE}/assets/PartReel-pretty.zip{cb}")))
    manifest = get_json(f"{SITE}/assets/kicad-bundle-manifest.json{cb}")
    bundle_syms = set(re.findall(r'\(symbol\s+"([^"]+)"',
                                 open(sym_path, encoding="utf-8").read()))
    bundle_fps = {os.path.splitext(os.path.basename(n))[0]
                  for n in zf.namelist() if n.endswith(".kicad_mod")}
    print(f"번들: 심볼 {len(bundle_syms)}개(서브유닛 포함) / 풋프린트 {len(bundle_fps)}개 "
          f"/ manifest {manifest.get('count')}개")

    # manifest ↔ 번들 정합
    for pid in manifest.get("symbols", []):
        if pid not in bundle_syms:
            fail(f"manifest에 있는데 심볼 번들에 없음: {pid}")
        if pid not in bundle_fps:
            fail(f"manifest에 있는데 풋프린트 zip에 없음: {pid}")

    # A-3/B. 카테고리 목록 + 상세 표본
    total = 0
    for c in cats:
        items = get_json(f"{BASE}/parts/category/{c['id']}.json{cb}")
        all_strings(items, f"list.{c['id']}")
        total += len(items)
        for it in items[:SAMPLE_PER_CAT]:
            d = get_json(f"{BASE}/parts/{it['id']}.json{cb}")
            all_strings(d, f"detail.{it['id']}")
            for key in ("id", "name", "symbolIdStr", "fields"):
                if key not in d:
                    fail(f"{it['id']}: 상세에 {key} 없음")
            if d.get("exclude_from_bom") not in ("True", "False", "true", "false",
                                                 "1", "0", "yes", "no", None):
                fail(f"{it['id']}: 불리언 문자열 위반: {d.get('exclude_from_bom')}")
            sym_ref = d.get("symbolIdStr", "")
            if not sym_ref.startswith("PartReel:"):
                fail(f"{it['id']}: symbolIdStr 접두 이상: {sym_ref}")
            else:
                sname = sym_ref.split(":", 1)[1]
                if sname not in bundle_syms:
                    fail(f"{it['id']}: symbolIdStr가 번들에 없음: {sname}")
            fp_ref = (d.get("fields", {}).get("Footprint", {}) or {}).get("value", "")
            if fp_ref and fp_ref.split(":", 1)[-1] not in bundle_fps:
                fail(f"{it['id']}: Footprint 필드가 zip에 없음: {fp_ref}")
    print(f"목록 합계 {total}개, 상세 표본 {SAMPLE_PER_CAT}/카테고리 검사 완료")

    # B-2. 동기화 시간 실측 (회귀 게이트) — 새 URL 10건의 평균 × 부품수
    import time
    ids = [p for p in manifest.get("symbols", [])][:10]
    t0 = time.time()
    for pid in ids:
        get(f"{BASE}/parts/{pid}.json?warm={os.getpid()}")
    per = (time.time() - t0) / max(len(ids), 1)
    est = per * len(manifest.get("symbols", []))
    print(f"응답 {per * 1000:.0f}ms/건 → 첫 동기화 추정 {est:.0f}초 "
          f"({len(manifest.get('symbols', []))}부품)")
    if est > MAX_SYNC_SECONDS:
        fail(f"첫 동기화 추정 {est:.0f}초 > 한도 {MAX_SYNC_SECONDS}초 "
             "(KiCad UI가 그만큼 멈춘다)")

    # C. 커널 검증 (kicad-cli 있으면)
    if os.path.exists(KICAD_CLI):
        out = os.path.join(tmp, "svg")
        r = subprocess.run([KICAD_CLI, "sym", "export", "svg", sym_path, "-o", out],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=900)
        n = len(os.listdir(out)) if os.path.isdir(out) else 0
        if n < len(manifest.get("symbols", [])):
            fail(f"커널 심볼 렌더 부족: {n} < {manifest.get('count')}")
        else:
            print(f"커널: 심볼 SVG {n}개 렌더 OK")
        # 풋프린트: zip 풀어서 .pretty 통째 렌더
        # (주의: fp export는 출력 폴더를 만들어주지 않음 — 미리 생성)
        pretty = os.path.join(tmp, "PartReel.pretty")
        zf.extractall(tmp)
        os.makedirs(os.path.join(tmp, "fpsvg"), exist_ok=True)
        r = subprocess.run([KICAD_CLI, "fp", "export", "svg", pretty, "-o",
                            os.path.join(tmp, "fpsvg")],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=900)
        nf = len(os.listdir(os.path.join(tmp, "fpsvg"))) if os.path.isdir(
            os.path.join(tmp, "fpsvg")) else 0
        if nf < len(bundle_fps):
            fail(f"커널 풋프린트 렌더 부족: {nf} < {len(bundle_fps)}")
        else:
            print(f"커널: 풋프린트 SVG {nf}개 렌더 OK")
    else:
        print("경고: kicad-cli 없음 — 커널 검증 생략 (KICAD_CLI 환경변수로 지정)")

    shutil.rmtree(tmp, ignore_errors=True)
    print(("PASS: KiCad 어댑터 전 구간 정상" if not errs
           else f"FAIL: {len(errs)}건"))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
