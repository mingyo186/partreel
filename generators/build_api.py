"""
AI 에이전트용 정적 HTTP API 생성 (PartReel 2.0 1단계, REQUIREMENTS §17).
실행: python generators/build_api.py

생성물 (전부 정적 — GitHub Pages에서 그대로 서빙):
  api/v1/parts.json        전체 부품 목록 (절대 URL 포함)
  api/v1/parts/<id>.json   부품 상세 (meta + 다운로드 절대 URL + 페이지 URL)
  llms.txt                 AI 에이전트 발견/안내 파일 (사이트 루트)
  api/index.html           사람이 읽는 API 문서
"""
import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
DOMAIN = "https://partreel.com"
GITHUB = "https://github.com/mingyo186/partreel"


def abs_url(*parts):
    return DOMAIN + "/" + "/".join(p.strip("/") for p in parts if p)


def main():
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    os.makedirs(os.path.join(ROOT, "api", "v1", "parts"), exist_ok=True)

    listing = []
    for p in index["parts"]:
        meta = json.load(open(os.path.join(ROOT, p["path"], "meta.json"), encoding="utf-8"))
        files = {k: abs_url(p["path"], fn) for k, fn in meta.get("files", {}).items()}
        detail = {
            "id": meta["id"], "name": meta["name"],
            "category": meta.get("category"), "family": meta.get("family"),
            "manufacturer": meta.get("manufacturer"), "mpn_pattern": meta.get("mpn_pattern"),
            "description": meta.get("description"), "parameters": meta.get("parameters", {}),
            "formats": meta.get("formats", []), "files": files,
            "datasheet": meta.get("datasheet"), "license": meta.get("license"),
            "verified": meta.get("verified", False),
            "dimensions_source": meta.get("dimensions_source"),
            "keywords": meta.get("keywords", []),
            "page": abs_url("p", meta["id"]) + "/",
            "api": abs_url("api/v1/parts", meta["id"] + ".json"),
        }
        with open(os.path.join(ROOT, "api", "v1", "parts", f"{meta['id']}.json"),
                  "w", encoding="utf-8") as f:
            json.dump(detail, f, indent=2, ensure_ascii=False)
        listing.append({k: detail[k] for k in
                        ("id", "name", "category", "family", "manufacturer",
                         "keywords", "verified", "page", "api")}
                       | {"pins": meta.get("parameters", {}).get("pins")
                          or meta.get("parameters", {}).get("contacts")})

    with open(os.path.join(ROOT, "api", "v1", "parts.json"), "w", encoding="utf-8") as f:
        json.dump({"registry": "PartReel", "version": 1, "count": len(listing),
                   "docs": abs_url("api") + "/", "license_assets": "CC-BY-4.0",
                   "parts": listing}, f, indent=2, ensure_ascii=False)

    # llms.txt — AI 에이전트 발견/안내 (사이트 루트)
    llms = f"""# PartReel — open KiCad component registry (AI-friendly)

> No-login registry of verified KiCad footprints, symbols and 3D models
> (STEP/GLB). Assets CC-BY-4.0. Built to be consumed by AI agents.

## API (static JSON, no auth, no rate limit)
- All parts: {DOMAIN}/api/v1/parts.json
- Part detail: {DOMAIN}/api/v1/parts/{{id}}.json (absolute download URLs inside)
- Human page per part: {DOMAIN}/p/{{id}}/

## MCP server (remote, Streamable HTTP — for AI agents/IDEs)
- Endpoint: https://mcp.partreel.com/mcp
- Tools: search_parts(query), get_part(id), list_parts()
- Add to Claude Code: `claude mcp add --transport http partreel https://mcp.partreel.com/mcp`

## Quality
Every part passes automated gates (structure validation, KiCad Library
Convention drawing rules, text-overlap check, render completeness, STEP
kernel isValid). Dimensions derived from manufacturer datasheets / matched
to KiCad official library where available. `verified: true` in metadata.

## Contributing / feedback
Agents and humans can contribute parts or report usage feedback via GitHub:
{GITHUB}
Contributions are auto-reviewed by the same quality gates in CI.

## License
Code MIT. Component assets CC-BY-4.0 (attribution: "PartReel").
"""
    with open(os.path.join(ROOT, "llms.txt"), "w", encoding="utf-8") as f:
        f.write(llms)

    # 사람용 API 문서 (간단)
    docs = f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PartReel API — AI 에이전트용 부품 레지스트리</title>
<meta name="description" content="PartReel 공개 API: KiCad 풋프린트·심볼·3D를 JSON으로. 인증 불필요, AI 에이전트 친화.">
<link rel="canonical" href="{DOMAIN}/api/">
<link rel="icon" href="../favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="../assets/style.css?v=2">
</head><body>
<header class="topbar">
  <a class="brand" href="../" style="text-decoration:none;color:inherit"><span class="logo">◈</span><span class="brand-name">PartReel</span></a>
  <div class="header-badges"><span class="hbadge ok">인증 불필요</span><span class="hbadge ok">AI 친화</span></div>
</header>
<main class="doc-page">
  <h1>PartReel API</h1>
  <p>모든 부품 데이터를 정적 JSON으로 제공합니다. 인증·요금·rate limit 없음. AI 에이전트가 바로 fetch해서 쓰도록 설계됐습니다.</p>
  <h2>엔드포인트</h2>
  <ul>
    <li><code>GET /api/v1/parts.json</code> — 전체 부품 목록 (id·이름·키워드·상세 API URL)</li>
    <li><code>GET /api/v1/parts/&lt;id&gt;.json</code> — 부품 상세 (파라미터·<strong>다운로드 절대 URL</strong>·데이터시트·검증 상태)</li>
    <li><code>GET /llms.txt</code> — AI 에이전트용 안내</li>
  </ul>
  <h2>MCP 서버 (AI 에이전트/IDE용)</h2>
  <p>리모트 MCP — 설치 없이 URL만 등록: <code>https://mcp.partreel.com/mcp</code></p>
  <ul>
    <li>도구: <code>search_parts(query)</code> · <code>get_part(id)</code> · <code>list_parts()</code></li>
    <li>Claude Code: <code>claude mcp add --transport http partreel https://mcp.partreel.com/mcp</code></li>
  </ul>
  <h2>예시</h2>
  <p><a href="v1/parts.json">/api/v1/parts.json</a> · <a href="v1/parts/usb_c_16p.json">/api/v1/parts/usb_c_16p.json</a></p>
  <h2>품질</h2>
  <p>모든 부품은 자동 게이트(구조 검증·KLC 도면 규칙·글자 겹침·렌더 완전성·STEP 커널 검증)를 통과해야 등록됩니다. 치수는 제조사 데이터시트 기반이며 가능한 경우 KiCad 공식 라이브러리와 대조합니다.</p>
  <h2>기여 · 피드백</h2>
  <p>부품 기여와 사용 피드백은 <a href="{GITHUB}" rel="noopener" target="_blank">GitHub</a>로. 기여물은 CI의 동일 품질 게이트가 자동 심사합니다.</p>
  <p><a href="../">← 홈으로</a></p>
</main>
</body></html>
"""
    with open(os.path.join(ROOT, "api", "index.html"), "w", encoding="utf-8") as f:
        f.write(docs)

    print(f"API built: {len(listing)} parts -> api/v1/, llms.txt, api/index.html")


if __name__ == "__main__":
    main()
