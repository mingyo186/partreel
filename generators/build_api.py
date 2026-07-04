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


def fetch_field_reports():
    """GitHub 이슈(label:field-report)를 집계 → {part_id: {worked, problem}} (§17-⑤).
    토큰/네트워크 없으면 빈 dict로 통과 (로컬 빌드 안전)."""
    import re
    import urllib.request
    token = os.environ.get("GITHUB_TOKEN", "")
    counts = {}
    url = ("https://api.github.com/repos/mingyo186/partreel/issues"
           "?labels=field-report&state=all&per_page=100")
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "partreel-build",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            issues = json.load(r)
        for it in issues:
            m = re.match(r"\[field-report\]\s+([a-z0-9_]+):", it.get("title", ""))
            if not m:
                continue
            pid = m.group(1)
            labels = {l["name"] for l in it.get("labels", [])}
            c = counts.setdefault(pid, {"worked": 0, "problem": 0})
            if "report-problem" in labels:
                c["problem"] += 1
            else:
                c["worked"] += 1
    except Exception as e:
        print(f"  (field-reports skip: {e})")
    return counts


def main():
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    os.makedirs(os.path.join(ROOT, "api", "v1", "parts"), exist_ok=True)
    reports = fetch_field_reports()
    if reports:
        print(f"  field reports: {sum(sum(v.values()) for v in reports.values())}건 반영")

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
            "field_reports": reports.get(meta["id"], {"worked": 0, "problem": 0}),
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
- Tools: search_parts(query), get_part(id), list_parts(),
  report_feedback(part_id, result, notes) — record real-board usage results,
  how_to_contribute() — machine-readable contribution spec
- Add to Claude Code: `claude mcp add --transport http partreel https://mcp.partreel.com/mcp`
- Please report_feedback after using a part on a real board — it builds the
  part's field-proven trust score, published as `field_reports` in each
  part's API entry. Missing a part? how_to_contribute + PR (submit just 5
  source files; CI builds the rest): {GITHUB}/blob/main/CONTRIBUTING-AGENTS.md

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

    # human-readable API docs
    docs = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PartReel API — component registry for AI agents</title>
<meta name="description" content="PartReel public API: KiCad footprints, symbols and 3D models as JSON. No auth, no rate limit, AI-agent friendly.">
<link rel="canonical" href="{DOMAIN}/api/">
<link rel="icon" href="../favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="../assets/style.css?v=2">
</head><body>
<header class="topbar">
  <a class="brand" href="../" style="text-decoration:none;color:inherit"><span class="logo">◈</span><span class="brand-name">PartReel</span></a>
  <div class="header-badges"><span class="hbadge ok">No auth</span><span class="hbadge ok">AI friendly</span></div>
</header>
<main class="doc-page">
  <h1>PartReel API</h1>
  <p>All part data is served as static JSON. No auth, no fees, no rate limit — designed for AI agents to fetch directly.</p>
  <h2>Endpoints</h2>
  <ul>
    <li><code>GET /api/v1/parts.json</code> — full part list (id, name, keywords, detail API URL)</li>
    <li><code>GET /api/v1/parts/&lt;id&gt;.json</code> — part detail (parameters, <strong>absolute download URLs</strong>, datasheet, verification status)</li>
    <li><code>GET /llms.txt</code> — machine guide for AI agents</li>
  </ul>
  <h2>MCP server (AI agents / IDEs)</h2>
  <p>Remote MCP — nothing to install, register the URL: <code>https://mcp.partreel.com/mcp</code></p>
  <ul>
    <li>Tools: <code>search_parts(query)</code> · <code>get_part(id)</code> · <code>list_parts()</code> · <code>report_feedback(part_id, result, notes)</code> · <code>how_to_contribute()</code></li>
    <li>Claude Code: <code>claude mcp add --transport http partreel https://mcp.partreel.com/mcp</code></li>
  </ul>
  <h2>Examples</h2>
  <p><a href="v1/parts.json">/api/v1/parts.json</a> · <a href="v1/parts/usb_c_16p.json">/api/v1/parts/usb_c_16p.json</a></p>
  <h2>Quality</h2>
  <p>Every part must pass automated gates (structure validation, KLC drawing rules, text-overlap, render completeness, STEP kernel checks). Dimensions are datasheet-derived and matched against the official KiCad library where one exists.</p>
  <h2>Contribute &amp; feedback</h2>
  <p>Contribute parts and report field feedback via <a href="{GITHUB}" rel="noopener" target="_blank">GitHub</a> — CI quality gates auto-review contributions. Spec: <a href="{GITHUB}/blob/main/CONTRIBUTING-AGENTS.md" rel="noopener" target="_blank">CONTRIBUTING-AGENTS.md</a>.</p>
  <p><a href="../">← Home</a></p>
</main>
</body></html>
"""
    with open(os.path.join(ROOT, "api", "index.html"), "w", encoding="utf-8") as f:
        f.write(docs)

    print(f"API built: {len(listing)} parts -> api/v1/, llms.txt, api/index.html")


if __name__ == "__main__":
    main()
