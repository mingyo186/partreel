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
        "description_full": [
            "PartReel's curated library: self-generated, quality-gated symbols "
            "and footprints with datasheet-sourced dimensions.",
            "Every part passes automated gates (structure, KiCad Library "
            "Convention drawing rules, render completeness, anti-copy provenance "
            "check against the official library) before release.",
            "Symbols carry footprint assignment, datasheet link, description and "
            "search keywords, so placing a part brings its footprint along.",
            f"This package contains {count} parts. The full catalog "
            "(21,000+ parts, no login) lives at https://partreel.com",
        ],
        "identifier": IDENT,
        "type": "library",
        "author": {"name": "PartReel",
                   "contact": {"web": SITE}},
        "license": "CC-BY-4.0",
        "resources": {"homepage": SITE},
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

    json.dump({"packages": [meta]},
              open(os.path.join(OUT, "packages.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    pkgs_blob = open(os.path.join(OUT, "packages.json"), "rb").read()

    repo = {
        "$schema": "https://go.kicad.org/pcm/schemas/v1",
        "name": "PartReel",
        "maintainer": {"name": "PartReel", "contact": {"web": SITE}},
        "packages": {
            "url": f"{SITE}/pcm/packages.json",
            "sha256": hashlib.sha256(pkgs_blob).hexdigest(),
            "update_timestamp": count,  # 부품 수 = 단조 증가 갱신 신호
        },
    }
    json.dump(repo, open(os.path.join(OUT, "repository.json"), "w",
                         encoding="utf-8"), indent=1, ensure_ascii=False)

    print(f"PCM: {pkg_name} ({len(blob) / 1024:.0f} KB, 설치 "
          f"{install_size / 1024:.0f} KB, 부품 {count}, 버전 {version})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
