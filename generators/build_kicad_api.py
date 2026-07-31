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
# 온라인 라이브러리 노출 상한 (첫 동기화 = 상한 × 응답시간)
LIVE_LIMIT = int(os.environ.get("KICAD_LIVE_LIMIT", "120"))
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

    # 노출 규모 제한 (§18-A 3단계): KiCad는 상세를 전량 선주입하므로
    # (응답시간 × 부품수)가 UI 프리즈가 된다. 전체 세트는 **오프라인 번들**이
    # 즉시 제공하므로, 온라인 라이브러리는 "번들 받은 뒤 새로 생긴 것"만
    # 보여주면 충분하다 → 최신 LIMIT개. 최초 등장 순서는 원장(ledger)으로 추적.
    ledger_path = os.path.join(ROOT, "docs", "part-ledger.json")
    first_run = not os.path.exists(ledger_path)
    try:
        ledger = json.load(open(ledger_path, encoding="utf-8"))
    except (OSError, ValueError):
        ledger = {"order": []}
    known = set(ledger["order"])
    # 원장 최초 생성 시엔 전부 "기존 부품"으로 본다 (전량이 신규로 잡히면
    # 알파벳 뒤쪽만 뽑혀 한 카테고리에 쏠림)
    fresh = [] if first_run else [p["id"] for p in parts if p["id"] not in known]
    if first_run:
        ledger["order"] = [p["id"] for p in parts]
    ledger["order"] += fresh
    json.dump(ledger, open(ledger_path, "w", encoding="utf-8"), indent=0)

    # ① 새로 생긴 부품(원장에 없던 것)은 무조건 포함 — 온라인 노출의 존재 이유.
    # ② 남은 자리는 카테고리 라운드로빈으로 채워 대표성 확보 (id 알파벳순으로
    #    자르면 한 카테고리에 쏠린다 — 첫 구현에서 실제로 1개 카테고리만 남음).
    live_ids = set(fresh[-LIVE_LIMIT:])
    by_cat = {}
    for p in parts:
        if p["id"] not in live_ids:
            by_cat.setdefault(p.get("category") or "", []).append(p["id"])
    cats_cycle = sorted(by_cat)
    i = 0
    while len(live_ids) < LIVE_LIMIT and any(by_cat.values()):
        c = cats_cycle[i % len(cats_cycle)]
        if by_cat[c]:
            live_ids.add(by_cat[c].pop(0))
        i += 1

    parts = [p for p in parts if p["id"] in live_ids]
    print(f"온라인 노출 {len(parts)} / 번들 {len(bundled)} (원장 {len(ledger['order'])})")

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
