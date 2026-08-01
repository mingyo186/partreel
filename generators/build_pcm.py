"""
KiCad PCM(플러그인·콘텐츠 매니저) 저장소 생성기 (REQUIREMENTS §18-B).

사용자는 KiCad 안에서 **저장소 URL 한 번 등록 → Install**, 이후 갱신은 버튼
한 번. PCM이 라이브러리 테이블에 자동 등록해주므로(KICAD_3RD_PARTY) 심볼·
풋프린트 라이브러리를 수동으로 추가할 필요도 없다.

생성물 (사이트 루트 기준):
  pcm/partreel-library-<ver>.zip   metadata.json + symbols/ + footprints/
  pcm/repository.json              KiCad에 등록하는 주소
  pcm/packages.json                패키지 목록(버전·해시·크기)

전제: build_kicad_bundle.py가 먼저 돌아 assets/PartReel.kicad_sym 과
assets/PartReel-pretty.zip 이 최신이어야 한다.

실행: python generators/build_pcm.py
"""
import datetime
import hashlib
import io
import json
import os
import shutil
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ASSETS = os.path.join(ROOT, "assets")
OUT = os.path.join(ROOT, "pcm")
SITE = "https://partreel.com"
IDENT = "com.partreel.library"


PLUGIN_SRC = os.path.normpath(os.path.join(ROOT, "plugin"))
PLUGIN_FILES = ("__init__.py", "icon.png", "partreel_fetch/__init__.py",
                "partreel_fetch/core.py", "partreel_fetch/dialog.py",
                "resources/icon.png")
RELEASE_LEDGER = os.path.join(ROOT, "docs", "pcm-release.json")


def _zi(name):
    """고정 타임스탬프 ZipInfo — 결정적 패키지 (버전 churn 방지)."""
    zi = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    zi.compress_type = zipfile.ZIP_DEFLATED
    zi.external_attr = 0o644 << 16
    return zi


def content_hash(paths):
    """내용 해시 (zip은 타임스탬프 때문에 매번 달라져 기준으로 못 씀)."""
    h = hashlib.sha256()
    for p in paths:
        h.update(os.path.basename(p).encode())
        h.update(open(p, "rb").read())
    return h.hexdigest()


KEEP_RELEASES = 5


def load_ledger():
    try:
        return json.load(open(RELEASE_LEDGER, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_ledger(led):
    json.dump(led, open(RELEASE_LEDGER, "w", encoding="utf-8"), indent=1)


def record_release(key, entry):
    """발행 이력 누적 — **옛 버전을 목록에서 지우면 안 된다.**

    PCM은 설치된 버전을 저장소 목록에서 찾아 상태를 계산한다. 최신 하나만
    올려두면 캐시가 옛 버전을 가리키는 사용자에게 '버전 패키지를 찾을 수
    없습니다' 오류가 난다 (2026-08-01 사용자 제보). 공식 저장소도 버전
    이력을 유지한다."""
    led = load_ledger()
    rel = led.setdefault(key, {}).setdefault("releases", [])
    rel = [r for r in rel if r["version"] != entry["version"]]
    rel.insert(0, entry)
    led[key]["releases"] = rel[:KEEP_RELEASES]
    save_ledger(led)
    return led[key]["releases"]


def next_version(key, major_minor, digest):
    """내용이 바뀌면 patch를 올린다 — 안 올리면 PCM이 '업데이트 없음'으로 보고
    업데이트 버튼이 비활성화된다 (2026-08-01 사용자 제보로 발견)."""
    led = load_ledger()
    prev = led.get(key, {})
    if prev.get("major_minor") == major_minor and prev.get("hash") == digest:
        ver = prev.get("version") or f"{major_minor}.0"
    elif prev.get("major_minor") == major_minor:
        ver = f"{major_minor}.{int(str(prev.get('version', '0.0.0')).split('.')[-1]) + 1}"
    else:
        ver = f"{major_minor}.0"
    # releases 이력은 보존하고 현재 상태만 갱신 (통째 대입하면 이력이 지워진다)
    entry = led.setdefault(key, {})
    entry.update({"major_minor": major_minor, "hash": digest, "version": ver})
    save_ledger(led)
    return ver


def prune_zips(prefix, keep_names):
    """이력에서 밀려난 옛 zip 파일 정리 (목록에 있는 것은 반드시 남긴다)."""
    for fn in os.listdir(OUT):
        if fn.startswith(prefix) and fn.endswith(".zip") and fn not in keep_names:
            os.remove(os.path.join(OUT, fn))


def library_content_hash(sym_path, zip_path):
    """심볼 파일 + 풋프린트 zip **항목 내용** 기준 해시.
    zip 파일 자체는 압축 메타 때문에 흔들릴 수 있어 항목으로 판정한다."""
    h = hashlib.sha256()
    h.update(open(sym_path, "rb").read())
    with zipfile.ZipFile(zip_path) as z:
        for n in sorted(z.namelist()):
            h.update(n.encode())
            h.update(z.read(n))
    return h.hexdigest()


def plugin_content_hash():
    """플러그인 소스 해시 — 텍스트는 LF 정규화 후 판정."""
    h = hashlib.sha256()
    for rel in PLUGIN_FILES:
        p = os.path.join(PLUGIN_SRC, rel)
        h.update(rel.encode())
        h.update(open(p, "rb").read() if rel.endswith(".png")
                 else open(p, encoding="utf-8").read().encode("utf-8"))
    return h.hexdigest()


def build_plugin_package():
    """PartReel Fetch 액션 플러그인 패키지 (§18-C).

    공식 구조: plugins/ 안에 소스 직접, resources/icon.png(64x64), metadata.json.
    """
    meta = {
        "$schema": "https://go.kicad.org/pcm/schemas/v1",
        "name": "PartReel Fetch",
        "description": "Search PartReel and add just the parts you pick to the "
                       "current project.",
        "description_full": "\n".join([
            "Adds a PartReel search dialog to the PCB editor toolbar.",
            "Search the full PartReel registry (21,000+ parts, no login), pick a "
            "part, and only that part's symbol and footprint are downloaded into "
            "the current project (PartReel.kicad_sym / PartReel.pretty) and "
            "registered in the project library tables.",
            "Use this instead of installing a whole library when you only need a "
            "few parts. Requires network access to partreel.com.",
        ]),
        "identifier": "com.partreel.fetch",
        "type": "plugin",
        "author": {"name": "PartReel", "contact": {"web": SITE}},
        "license": "MIT",
        "resources": {"Homepage": SITE,
                      "Documentation": f"{SITE}/guide/kicad/"},
        "tags": ["plugin", "library", "search", "partreel"],
    }
    ver = next_version("fetch", "1.0", plugin_content_hash())
    name = f"partreel-fetch-{ver}.zip"
    path = os.path.join(OUT, name)
    install_size = 0
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        pkg_meta = dict(meta)
        pkg_meta["versions"] = [{"version": ver, "status": "stable",
                                 "kicad_version": "8.0"}]
        body = json.dumps(pkg_meta, indent=2, ensure_ascii=False)
        z.writestr(_zi("metadata.json"), body)
        install_size += len(body.encode("utf-8"))
        for rel in ("__init__.py", "icon.png",
                    "partreel_fetch/__init__.py", "partreel_fetch/core.py",
                    "partreel_fetch/dialog.py"):
            src = os.path.join(PLUGIN_SRC, rel)
            # 텍스트는 LF로 정규화 (윈도우 CRLF ↔ CI LF 차이로 버전 churn)
            data = (open(src, "rb").read() if rel.endswith(".png")
                    else open(src, encoding="utf-8").read().encode("utf-8"))
            z.writestr(_zi(f"plugins/{rel}"), data)
            install_size += len(data)
        icon = open(os.path.join(PLUGIN_SRC, "resources", "icon.png"), "rb").read()
        z.writestr(_zi("resources/icon.png"), icon)
        install_size += len(icon)

    blob = open(path, "rb").read()
    entry = {
        "version": ver,
        "status": "stable",
        "kicad_version": "8.0",
        "download_url": f"{SITE}/pcm/{name}",
        "download_sha256": hashlib.sha256(blob).hexdigest(),
        "download_size": len(blob),
        "install_size": install_size,
    }
    meta["versions"] = record_release("fetch", entry)
    prune_zips("partreel-fetch-", {os.path.basename(v["download_url"])
                                   for v in meta["versions"]})
    print(f"PCM: {name} ({len(blob) / 1024:.0f} KB) — 플러그인 v{ver} "
          f"(이력 {len(meta['versions'])}개)")
    return meta


def main():
    sym_path = os.path.join(ASSETS, "PartReel.kicad_sym")
    zip_path = os.path.join(ASSETS, "PartReel-pretty.zip")
    mf_path = os.path.join(ASSETS, "kicad-bundle-manifest.json")
    for p in (sym_path, zip_path, mf_path):
        if not os.path.exists(p):
            print(f"FAIL: {os.path.basename(p)} 없음 — build_kicad_bundle.py 먼저")
            return 1
    manifest = json.load(open(mf_path, encoding="utf-8"))
    count = manifest.get("count") or len(manifest.get("symbols", []))
    # 부품 수 = 마이너, 내용 변경 = 패치 (부품 수가 그대로여도 심볼/풋프린트
    # 내용이 바뀌면 버전이 올라가야 PCM이 업데이트를 제공한다)
    version = next_version("library", f"1.{count}",
                           library_content_hash(sym_path, zip_path))

    meta = {
        "$schema": "https://go.kicad.org/pcm/schemas/v1",
        "name": "PartReel Library",
        "description": "Open, no-login KiCad parts: symbols + footprints, "
                       "gate-verified with datasheet provenance.",
        # 스키마상 **문자열**이어야 한다 (배열로 내면 패키지 전체가 거부되어
        # 라이브러리 탭이 빈다 — 2026-08-01 check_pcm이 적발). 줄바꿈으로 문단 구분.
        "description_full": "\n".join([
            "PartReel's curated library: self-generated, quality-gated symbols "
            "and footprints with datasheet-sourced dimensions.",
            "Every part passes automated gates (structure, KiCad Library "
            "Convention drawing rules, render completeness, anti-copy provenance "
            "check against the official library) before release.",
            "Symbols carry footprint assignment, datasheet link, description and "
            "search keywords, so placing a part brings its footprint along.",
            f"This package contains {count} parts. The full catalog "
            "(21,000+ parts, no login) lives at https://partreel.com",
        ]),
        "identifier": IDENT,
        "type": "library",
        "author": {"name": "PartReel",
                   "contact": {"web": SITE}},
        "license": "CC-BY-4.0",
        "resources": {"Homepage": SITE,
                      "Documentation": f"{SITE}/guide/kicad/"},
        "tags": ["library", "symbols", "footprints", "partreel"],
        "versions": [],
    }

    os.makedirs(OUT, exist_ok=True)  # 옛 버전 zip 보존 (이력 유지)
    pkg_name = f"partreel-library-{version}.zip"
    pkg_path = os.path.join(OUT, pkg_name)

    install_size = 0
    with zipfile.ZipFile(pkg_path, "w", zipfile.ZIP_DEFLATED) as z:
        pkg_meta = {k: v for k, v in meta.items() if k != "versions"}
        pkg_meta["versions"] = [{
            "version": version,
            "status": "stable",
            "kicad_version": "8.0",
        }]
        body = json.dumps(pkg_meta, indent=2, ensure_ascii=False)
        z.writestr(_zi("metadata.json"), body)
        install_size += len(body.encode("utf-8"))

        sym = open(sym_path, "rb").read()
        z.writestr(_zi("symbols/PartReel.kicad_sym"), sym)
        install_size += len(sym)

        with zipfile.ZipFile(zip_path) as src:
            for n in src.namelist():
                if not n.endswith(".kicad_mod"):
                    continue
                data = src.read(n)
                # PartReel.pretty/<id>.kicad_mod → footprints/PartReel.pretty/...
                z.writestr(_zi(f"footprints/{os.path.basename(os.path.dirname(n))}/"
                               f"{os.path.basename(n)}"), data)
                install_size += len(data)

    blob = open(pkg_path, "rb").read()
    lib_entry = {
        "version": version,
        "status": "stable",
        "kicad_version": "8.0",
        "download_url": f"{SITE}/pcm/{pkg_name}",
        "download_sha256": hashlib.sha256(blob).hexdigest(),
        "download_size": len(blob),
        "install_size": install_size,
    }
    meta["versions"] = record_release("library", lib_entry)
    prune_zips("partreel-library-", {os.path.basename(v["download_url"])
                                     for v in meta["versions"]})

    packages = [meta, build_plugin_package()]
    json.dump({"packages": packages},
              open(os.path.join(OUT, "packages.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    pkgs_blob = open(os.path.join(OUT, "packages.json"), "rb").read()

    # repository.json은 **v2 스키마**여야 한다 — KiCad 10은 v2를 요구하고,
    # v1로 내면 저장소는 추가되지만 라이브러리 탭에 아무것도 안 뜬다
    # (2026-08-01 사용자 제보로 발견, 공식 저장소와 필드 대조해 확정).
    now = datetime.datetime.now(datetime.timezone.utc)
    stamp = int(now.timestamp())
    repo = {
        "$schema": "https://go.kicad.org/pcm/schemas/v2#/definitions/Repository",
        "schema_version": 2,
        "name": "PartReel",
        "maintainer": {"name": "PartReel", "contact": {"web": SITE}},
        "packages": {
            "url": f"{SITE}/pcm/packages.json",
            "sha256": hashlib.sha256(pkgs_blob).hexdigest(),
            "update_time_utc": now.strftime("%Y-%m-%d %H:%M:%S"),
            "update_timestamp": stamp,
        },
    }
    json.dump(repo, open(os.path.join(OUT, "repository.json"), "w",
                         encoding="utf-8"), indent=1, ensure_ascii=False)

    print(f"PCM: {pkg_name} ({len(blob) / 1024:.0f} KB, 설치 "
          f"{install_size / 1024:.0f} KB, 부품 {count}, 버전 {version})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
