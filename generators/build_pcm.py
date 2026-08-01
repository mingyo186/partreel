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
PLUGIN_VERSION = "1.0.0"


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
    name = f"partreel-fetch-{PLUGIN_VERSION}.zip"
    path = os.path.join(OUT, name)
    install_size = 0
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        pkg_meta = dict(meta)
        pkg_meta["versions"] = [{"version": PLUGIN_VERSION, "status": "stable",
                                 "kicad_version": "8.0"}]
        body = json.dumps(pkg_meta, indent=2, ensure_ascii=False)
        z.writestr("metadata.json", body)
        install_size += len(body.encode("utf-8"))
        for rel in ("__init__.py", "icon.png",
                    "partreel_fetch/__init__.py", "partreel_fetch/core.py",
                    "partreel_fetch/dialog.py"):
            src = os.path.join(PLUGIN_SRC, rel)
            data = open(src, "rb").read()
            z.writestr(f"plugins/{rel}", data)
            install_size += len(data)
        icon = open(os.path.join(PLUGIN_SRC, "resources", "icon.png"), "rb").read()
        z.writestr("resources/icon.png", icon)
        install_size += len(icon)

    blob = open(path, "rb").read()
    meta["versions"] = [{
        "version": PLUGIN_VERSION,
        "status": "stable",
        "kicad_version": "8.0",
        "download_url": f"{SITE}/pcm/{name}",
        "download_sha256": hashlib.sha256(blob).hexdigest(),
        "download_size": len(blob),
        "install_size": install_size,
    }]
    print(f"PCM: {name} ({len(blob) / 1024:.0f} KB) — 플러그인")
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
    # 부품 수를 마이너 버전으로 — 부품이 늘면 PCM이 자동으로 '업데이트 있음' 표시
    version = f"1.{count}.0"

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

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT, exist_ok=True)
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
        z.writestr("metadata.json", body)
        install_size += len(body.encode("utf-8"))

        sym = open(sym_path, "rb").read()
        z.writestr("symbols/PartReel.kicad_sym", sym)
        install_size += len(sym)

        with zipfile.ZipFile(zip_path) as src:
            for n in src.namelist():
                if not n.endswith(".kicad_mod"):
                    continue
                data = src.read(n)
                # PartReel.pretty/<id>.kicad_mod → footprints/PartReel.pretty/...
                z.writestr(f"footprints/{os.path.basename(os.path.dirname(n))}/"
                           f"{os.path.basename(n)}", data)
                install_size += len(data)

    blob = open(pkg_path, "rb").read()
    meta["versions"] = [{
        "version": version,
        "status": "stable",
        "kicad_version": "8.0",
        "download_url": f"{SITE}/pcm/{pkg_name}",
        "download_sha256": hashlib.sha256(blob).hexdigest(),
        "download_size": len(blob),
        "install_size": install_size,
    }]

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
