"""
통합 index.json 생성 — library/ 전체를 스캔해 모든 meta.json을 모은다.
실행: python generators/build_index.py
(여러 생성기[gen_connectors, gen_parts...]가 각자 부품을 쓰고, 인덱스는 여기서 통합.)
"""
import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
LIB = os.path.join(ROOT, "library")

parts = []
for dirpath, _, files in os.walk(LIB):
    if "meta.json" not in files:
        continue
    meta = json.load(open(os.path.join(dirpath, "meta.json"), encoding="utf-8"))
    params = meta.get("parameters", {})
    parts.append({
        "id": meta["id"], "name": meta["name"], "category": meta.get("category", ""),
        "family": meta.get("family", ""), "manufacturer": meta.get("manufacturer", ""),
        "pins": params.get("pins") or params.get("contacts"),
        "path": os.path.relpath(dirpath, ROOT).replace("\\", "/"),
        "formats": meta.get("formats", []), "verified": meta.get("verified", False),
        "keywords": meta.get("keywords", []),
    })

parts.sort(key=lambda p: (p["category"], p["family"], p["id"]))
out = {"generated_by": "opencad-lib", "count": len(parts), "parts": parts}
with open(os.path.join(ROOT, "index.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print(f"index.json -> {len(parts)} parts")
