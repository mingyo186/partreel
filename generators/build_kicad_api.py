"""
KiCad HTTP 라이브러리용 **정적** API 생성기 (REQUIREMENTS §18-A 3단계).

배경: KiCad는 부품 상세를 순차·동기로 전량 요청하므로 (응답시간 × 부품수)가
그대로 UI 프리즈가 된다. 워커 경유는 실측 440ms/건(캐시 HIT여도 워커 커스텀
도메인이 원거리 콜로에 붙어 왕복이 김) → 446건에 3~7분. 같은 존의 정적 파일은
50~65ms라 7배 빠르다. 그래서 KiCad가 치는 4개 경로를 통째로 정적 파일로 굽는다.

생성물 (사이트 루트 기준):
  kicad/v1/index.html                     루트 검증 (JSON 본문 — KiCad는
                                          Content-Type을 보지 않고 파싱한다)
  kicad/v1/categories.json                카테고리 목록
  kicad/v1/parts/category/<cat>.json      카테고리별 부품 목록
  kicad/v1/parts/<id>.json                부품 상세 (symbolIdStr/Footprint 포함)

대상은 번들 manifest(엄선판)와 동일 — 로컬 번들에 심볼·풋프린트가 실제로 있는
부품만 노출해야 배치 시 링크가 깨지지 않는다.

실행: python generators/build_kicad_api.py
"""
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "kicad", "v1")
SITE = "https://partreel.com"


def s(v):
    """KiCad 규칙: 응답 값은 전부 문자열."""
    return "" if v is None else str(v)


def main():
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    mpath = os.path.join(ROOT, "assets", "kicad-bundle-manifest.json")
    if not os.path.exists(mpath):
        print("FAIL: 번들 manifest 없음 — build_kicad_bundle.py 먼저 실행")
        return 1
    bundled = set(json.load(open(mpath, encoding="utf-8")).get("symbols", []))
    parts = [p for p in index["parts"] if p["id"] in bundled]
    print(f"대상 {len(parts)} (manifest {len(bundled)})")

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "parts", "category"), exist_ok=True)

    # 루트 검증: KiCad는 categories/parts 키만 확인한다
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8",
         newline="\n").write(json.dumps({"categories": "", "parts": ""}))

    cats = sorted({p.get("category") for p in parts if p.get("category")})
    json.dump([{"id": s(c), "name": s(c)} for c in cats],
              open(os.path.join(OUT, "categories.json"), "w", encoding="utf-8"))

    for c in cats:
        items = [{
            "id": s(p["id"]),
            "name": s(p.get("name") or p["id"]),
            "description": s(p.get("family") or ""),
            "keywords": " ".join(p.get("keywords") or []),
        } for p in parts if p.get("category") == c]
        json.dump(items, open(os.path.join(OUT, "parts", "category", f"{c}.json"),
                              "w", encoding="utf-8"))

    for p in parts:
        pid = p["id"]
        d = os.path.join(ROOT, p["path"])
        meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
        rel = p["path"].replace("\\", "/")
        files = meta.get("files") or {}
        detail = {
            "id": s(pid),
            "name": s(meta.get("name") or pid),
            "symbolIdStr": f"PartReel:{pid}",
            "description": s(meta.get("description") or ""),
            "keywords": " ".join(meta.get("keywords") or []),
            "exclude_from_bom": "False",
            "exclude_from_board": "False",
            "exclude_from_sim": "True",
            "fields": {
                "Footprint": {"value": f"PartReel:{pid}", "visible": "False"},
                "Datasheet": {"value": s(meta.get("datasheet")), "visible": "False"},
                "PartReel": {"value": f"{SITE}/p/{pid}/", "visible": "False"},
                "Manufacturer": {"value": s(meta.get("manufacturer")), "visible": "False"},
                "MPN": {"value": s(meta.get("mpn_pattern") or meta.get("name")),
                        "visible": "False"},
                "License": {"value": s(meta.get("license")), "visible": "False"},
                "Tier": {"value": s(meta.get("tier") or
                                    ("verified" if meta.get("verified") else "")),
                         "visible": "False"},
                "Model_3D_URL": {
                    "value": (f"https://assets.partreel.com/{rel}/{files['step']}"
                              if files.get("step") else ""),
                    "visible": "False"},
            },
        }
        json.dump(detail, open(os.path.join(OUT, "parts", f"{pid}.json"),
                               "w", encoding="utf-8"))

    n = len(os.listdir(os.path.join(OUT, "parts"))) - 1  # category 디렉토리 제외
    print(f"KiCad 정적 API: 카테고리 {len(cats)} / 목록 {len(cats)} / 상세 {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
