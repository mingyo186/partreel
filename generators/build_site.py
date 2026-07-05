"""
Static page generator (SEO/content). English-first (REQUIREMENTS §18: global chokepoints).
Run: python generators/build_site.py

Outputs:
  p/<id>/index.html      per-part SEO pages (title/meta/canonical/OG/JSON-LD + 3D/symbol/footprint tabs)
  about/index.html       about page
  guide/kicad/index.html "How to use in KiCad" guide
  agents/index.html      AI agent guide (MCP/API + paste-in prompt)
  sitemap.xml, robots.txt

Security (REQUIREMENTS §6/§13): dynamic values html.escape'd, CSP meta on every page.
"""

import json
import os
import hashlib
import html

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
DOMAIN = "https://partreel.com"
ASSETS_BASE = "https://assets.partreel.com"  # 대용량 에셋(step/glb) = R2 (§22)
GITHUB = "https://github.com/mingyo186/partreel"
MCP_URL = "https://mcp.partreel.com/mcp"

FMT_LABEL = {"kicad_mod": "KiCad footprint", "kicad_sym": "KiCad symbol", "step": "3D STEP", "glb": "3D preview"}
FMT_KEY = {"glb": "preview", "step": "model_3d", "kicad_mod": "footprint", "kicad_sym": "symbol"}

CSP = ("default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
       "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "connect-src 'self' https://cdn.jsdelivr.net https://assets.partreel.com; "
       "object-src 'none'; base-uri 'self'")


def esc(s):
    return html.escape(str(s), quote=True)


def footer(prefix):
    return f"""<footer class="site-footer">
  <div class="foot-brand">PartReel · open KiCad component registry, no login</div>
  <nav class="foot-nav">
    <a href="{prefix}about/">About</a>
    <a href="{prefix}guide/kicad/">Use in KiCad</a>
    <a href="{prefix}agents/">AI Agents</a>
    <a href="{prefix}api/">API</a>
    <a href="{GITHUB}" target="_blank" rel="noopener">GitHub</a>
  </nav>
  <div class="foot-lic">Code MIT · Parts CC-BY-4.0 · Dimensions derived from datasheets; verify before manufacturing (as-is).</div>
</footer>"""


def render(prefix, title, desc, canonical, body, head_extra="", scripts=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="{prefix}favicon.svg" type="image/svg+xml">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<link rel="stylesheet" href="{prefix}assets/style.css?v=5">
{head_extra}
</head>
<body>
<header class="topbar">
  <a class="brand" href="{prefix}" style="text-decoration:none;color:inherit"><span class="logo">◈</span><span class="brand-name">PartReel</span></a>
  <div class="header-badges"><span class="hbadge ok">No sign-up</span><span class="hbadge ok">Instant download</span></div>
</header>
{body}
{footer(prefix)}
{scripts}
</body>
</html>
"""


def part_page(meta, path):
    prefix = "../../"
    pid, name, desc = meta["id"], meta["name"], meta.get("description", "")
    desc_short = desc[:150]
    mpn = meta.get("mpn_pattern", "")
    fam = meta.get("family", "")
    manu = meta.get("manufacturer", "")
    ds = meta.get("datasheet", "#")
    lic = meta.get("license", "")
    params = meta.get("parameters", {})
    files = meta.get("files", {})
    glb = files.get("preview", "")
    has3d = bool(glb)
    tab3d = '<button class="vt active" data-view="3d">3D</button>\n    ' if has3d else ''
    sym_active = '' if has3d else ' active'
    # 대용량 에셋(step/glb)은 R2 (§22) — 텍스트/SVG는 Pages 유지
    glb_attr = (f' data-glb="{ASSETS_BASE}/{path}/{esc(glb)}"') if has3d else ''
    default_view = '3d' if has3d else 'sym'  # 2D 부품은 심볼 우선 (사용자 2026-07-05)
    viewer_msg = 'Loading 3D…' if has3d else 'Verified-2D part (no 3D model upstream)'
    sym_svg = files.get("symbol_svg", "")
    fp_svg = files.get("footprint_svg", "")

    rows = []
    for label, val in [("Manufacturer", manu), ("Family", fam), ("MPN pattern", mpn),
                       ("Pins", params.get("pins") or params.get("contacts")),
                       ("Pitch", f"{params.get('pitch_mm')} mm" if params.get("pitch_mm") is not None else None),
                       ("Mounting", params.get("mounting")), ("Orientation", params.get("orientation"))]:
        if val not in (None, ""):
            rows.append(f"<tr><td>{esc(label)}</td><td>{esc(val)}</td></tr>")
    spec_rows = "".join(rows)

    dls = []
    for fmt in meta.get("formats", []):
        fn = files.get(FMT_KEY.get(fmt, fmt))
        if not fn:
            continue
        base = f"{ASSETS_BASE}/{path}" if fn.lower().endswith((".step", ".glb")) \
            else f"{prefix}{path}"
        dls.append(f'<a class="dl" href="{base}/{esc(fn)}" download>'
                   f'<span class="ext">{esc(fmt)}</span> {esc(FMT_LABEL.get(fmt, fmt))}</a>')
    downloads = "".join(dls)

    # SVG는 페이지에 인라인(즉시 표시, 요청 0) — 초대형(>120KB)만 img 폴백
    def _view(el_id, fn, alt):
        try:
            body = open(os.path.join(ROOT, path, fn), encoding="utf-8").read()
        except OSError:
            body = ""
        if body and len(body) <= 120_000:
            return (f'<div id="{el_id}" class="view-img view-svg" role="img" '
                    f'aria-label="{alt}" hidden>{body}</div>')
        h = hashlib.sha1(body.encode()).hexdigest()[:8] if body else "0"
        return (f'<img id="{el_id}" class="view-img" alt="{alt}" '
                f'data-src="{prefix}{path}/{esc(fn)}?v={h}" hidden>')
    sym_view = _view("view-sym", sym_svg, "Schematic symbol")
    fp_view = _view("view-fp", fp_svg, "PCB footprint")

    # 데이터시트 링크 정직성: 수입품의 ds가 소스 레포(=데이터시트 아님)를 가리키면
    # "검색" 링크를 주 버튼으로, 레포 링크는 provenance로 표기 (라벨 거짓말 금지)
    if meta.get("origin") == "imported" and ("gitlab.com" in ds or "github.com" in ds):
        q = esc(mpn).replace(" ", "+")
        ds_links = (f'<a class="dl" href="https://www.google.com/search?q=%22{q}%22+datasheet" '
                    f'target="_blank" rel="noopener">Find datasheet ({esc(manu)} {esc(mpn)}) →</a>\n'
                    f'  <a class="dl" href="{esc(ds)}" target="_blank" rel="noopener">'
                    f'Source library file (provenance)</a>')
    else:
        ds_links = (f'<a class="dl" href="{esc(ds)}" target="_blank" rel="noopener">'
                    f'Manufacturer datasheet</a>')

    jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "Product", "name": name,
        "description": desc, "category": "Electronic Component",
        "brand": {"@type": "Brand", "name": manu}, "mpn": mpn,
    }, ensure_ascii=False)

    head_extra = (
        '<script type="importmap">\n'
        '{ "imports": { "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js", '
        '"three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/" } }\n'
        '</script>\n'
        f'<script type="application/ld+json">\n{jsonld}\n</script>'
    )
    body = f"""<main class="part-page">
  <nav class="crumb"><a href="{prefix}">Home</a> / {esc(fam)} / {esc(name)}</nav>
  <h1>{esc(name)}</h1>
  <p class="desc">{esc(desc)}</p>
  <div class="view-tabs">
    {tab3d}<button class="vt{sym_active}" data-view="sym">Symbol</button>
    <button class="vt" data-view="fp">Footprint</button>
  </div>
  <div id="viewer" class="viewer part-viewer"{glb_attr} data-default="{default_view}">
    <div class="viewer-msg">{viewer_msg}</div>
    {sym_view}
    {fp_view}
  </div>
  <h2>Specifications</h2>
  <table class="specs">{spec_rows}</table>
  <h2>Downloads <span class="nologin">· no sign-up</span></h2>
  <div class="downloads">{downloads}</div>
  <h2>Datasheet</h2>
  {ds_links}
  <h2>Buy</h2>
  <a class="buy" href="https://www.lcsc.com/search?q={esc(mpn)}" target="_blank" rel="noopener">Find this part at distributors →</a>
  <p class="affiliate-note">Affiliate link · Part license: {esc(lic)}</p>
  <h2>Field reports</h2>
  <p id="field-badge" class="desc" hidden></p>
  <p class="desc">Used this part on a real board? One click, no sign-up beyond GitHub:
    <a class="dl" href="{GITHUB}/issues/new?template=field_report_worked.yml&title=%5Bfield-report%5D%20{pid}%3A%20worked" target="_blank" rel="noopener">✅ It worked</a>
    <a class="dl" href="{GITHUB}/issues/new?template=field_report_problem.yml&title=%5Bfield-report%5D%20{pid}%3A%20problem" target="_blank" rel="noopener">⚠️ Report a problem</a>
    <span class="affiliate-note" style="display:block">Reports feed this part's public trust score (AI agents: use <code>report_feedback</code> via MCP).</span>
  </p>
  <h2>For AI agents</h2>
  <p class="desc">Machine-readable data for this part: <a href="{DOMAIN}/api/v1/parts/{pid}.json">/api/v1/parts/{pid}.json</a> (absolute download URLs).
  MCP: <code>{MCP_URL}</code> → <code>get_part("{pid}")</code>. See <a href="{DOMAIN}/llms.txt">/llms.txt</a> · <a href="{prefix}agents/">agent guide</a></p>
</main>"""
    scripts = f'<script type="module" src="{prefix}assets/part.js?v=11"></script>'
    title = f"{esc(name)} — KiCad footprint, symbol & 3D model | PartReel"
    return render(prefix, title, esc(desc_short), f"{DOMAIN}/p/{pid}/", body, head_extra, scripts)


def about_page():
    prefix = "../"
    body = """<main class="doc-page">
  <h1>About PartReel</h1>
  <p>PartReel is an open KiCad component registry you can use <strong>without signing up</strong>. Symbols, footprints and 3D models are generated from datasheet dimensions and downloadable instantly — by humans and by AI agents.</p>
  <h2>Why it's different</h2>
  <ul>
    <li><strong>No login</strong> — search, click, download. No account, no email gate.</li>
    <li><strong>Verifiable quality</strong> — parts are generated deterministically from dimensions and must pass automated quality gates (structure validation, KiCad Library Convention drawing rules, render-completeness, STEP kernel checks). Footprints are matched against the official KiCad library where one exists.</li>
    <li><strong>Open</strong> — code is MIT, part assets are CC-BY-4.0, everything is versioned in git.</li>
    <li><strong>AI-native</strong> — a public JSON API and a remote MCP server let agents search, fetch, report field feedback and contribute parts.</li>
  </ul>
  <h2>How parts are made</h2>
  <p>Package dimensions (pitch, pin count, pad sizes) feed parametric generators that emit the symbol, footprint and 3D model (STEP/GLB) together. One family config produces the whole pin-count range at consistent quality.</p>
  <h2>License &amp; disclaimer</h2>
  <p>Code MIT / part assets CC-BY-4.0 (attribution: "PartReel"). Dimensions are derived from public manufacturer datasheets and provided as-is — verify critical footprints against the datasheet before manufacturing.</p>
  <p><a href="../">← Home</a></p>
</main>"""
    return render(prefix, "About PartReel — open, no-login KiCad library",
                  "PartReel is an open KiCad component registry: datasheet-derived footprints, symbols and 3D models, no sign-up, quality-gated, AI-native.",
                  f"{DOMAIN}/about/", body)


def guide_page():
    prefix = "../../"
    body = """<main class="doc-page">
  <h1>How to use PartReel files in KiCad</h1>
  <p>Downloaded files from PartReel? Here is how to add them to KiCad.</p>
  <h2>1. Symbol (.kicad_sym)</h2>
  <ol>
    <li>KiCad → <strong>Preferences → Manage Symbol Libraries</strong></li>
    <li>In the Global or Project tab click <strong>+</strong> → select the downloaded <code>.kicad_sym</code> file</li>
    <li>Place the symbol from the schematic editor</li>
  </ol>
  <h2>2. Footprint (.kicad_mod)</h2>
  <ol>
    <li>Put the <code>.kicad_mod</code> file inside a folder named like <code>MyLib.pretty</code> (KiCad manages footprints per <code>.pretty</code> folder)</li>
    <li><strong>Preferences → Manage Footprint Libraries</strong> → <strong>+</strong> → add that <code>.pretty</code> folder</li>
  </ol>
  <h2>3. 3D model (.step)</h2>
  <ol>
    <li>Open the footprint in the footprint editor → <strong>Footprint Properties → 3D Models</strong></li>
    <li>Point it at the downloaded <code>.step</code> file</li>
  </ol>
  <p>The web preview uses <code>.glb</code> (display only); use <code>.step</code> in KiCad.</p>
  <p><a href="../../">← Home</a></p>
</main>"""
    return render(prefix, "How to add downloaded libraries to KiCad | PartReel",
                  "Step-by-step: add downloaded symbols (.kicad_sym), footprints (.kicad_mod) and 3D models (.step) to KiCad.",
                  f"{DOMAIN}/guide/kicad/", body)


def agents_page():
    prefix = "../"
    snippet = esc("""## Electronic components (KiCad)
When you need KiCad symbols/footprints/3D models, query the PartReel registry first
(no login, CC-BY-4.0, only quality-gated parts are listed):
- Search/list: fetch https://partreel.com/api/v1/parts.json and match keywords
- Detail/downloads: https://partreel.com/api/v1/parts/{id}.json (absolute URLs)
- If MCP is available: https://mcp.partreel.com/mcp (search_parts / get_part)
- After using a part on a real board, report the result via report_feedback.
Only generate a part yourself if the registry doesn't have it — then consider
contributing it back (how_to_contribute).""")
    body = f"""<main class="doc-page">
  <h1>AI Agent Guide</h1>
  <p>PartReel treats <strong>AI agents as first-class users</strong>. Verified KiCad symbols, footprints and 3D models are machine-consumable with no auth.</p>

  <h2>1. Connect via MCP (recommended)</h2>
  <p>Remote MCP — nothing to install, just register the URL:</p>
  <ul>
    <li>Claude Code: <code>claude mcp add --transport http partreel {MCP_URL}</code></li>
    <li>Any MCP client: endpoint <code>{MCP_URL}</code> (Streamable HTTP)</li>
    <li>Tools: <code>search_parts(query)</code> · <code>get_part(id)</code> · <code>list_parts()</code> · <code>report_feedback(part_id, result, notes)</code> · <code>how_to_contribute()</code></li>
    <li><strong>Please call <code>report_feedback</code> after using a part on a real board</strong> — it builds the part's field-proven trust score. Missing a part? <code>how_to_contribute</code> → PR (CI gates auto-review).</li>
  </ul>

  <h2>2. HTTP API (any agent)</h2>
  <ul>
    <li><code>GET https://partreel.com/api/v1/parts.json</code> — full list</li>
    <li><code>GET https://partreel.com/api/v1/parts/&lt;id&gt;.json</code> — detail + absolute download URLs</li>
    <li><code>GET https://partreel.com/llms.txt</code> — machine guide</li>
  </ul>

  <h2>3. Paste-in prompt</h2>
  <p>Paste this into <code>CLAUDE.md</code>, <code>.cursorrules</code> or your system prompt so your agent uses PartReel automatically:</p>
  <pre style="background:var(--panel2);border:1px solid var(--border);border-radius:8px;padding:14px;white-space:pre-wrap;font-size:12.5px;line-height:1.5">{snippet}</pre>

  <h2>4. Quality guarantees</h2>
  <p>Every listed part passed automated gates: structure validation, KiCad Library Convention drawing rules, text-overlap and render-completeness checks, STEP kernel isValid. Check <code>verified</code> and <code>dimensions_source</code> in the metadata.</p>

  <h2>5. Contribute &amp; feedback</h2>
  <p>Generated a part the registry lacks? Contribute via <a href="{GITHUB}" target="_blank" rel="noopener">GitHub</a> PR — the same CI gates auto-review it. Spec: <a href="{GITHUB}/blob/main/CONTRIBUTING-AGENTS.md" target="_blank" rel="noopener">CONTRIBUTING-AGENTS.md</a>. Field reports (successes and problems) are welcome via <code>report_feedback</code>.</p>
  <p><a href="../">← Home</a></p>
</main>"""
    return render(prefix, "AI Agent Guide — PartReel MCP & API",
                  "How AI agents use the PartReel KiCad registry: MCP endpoint, HTTP API, paste-in guide prompt, feedback and contribution.",
                  f"{DOMAIN}/agents/", body)


def write(relpath, content):
    full = os.path.join(ROOT, relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    urls = [f"{DOMAIN}/"]
    for p in index["parts"]:
        path = p["path"]
        meta = json.load(open(os.path.join(ROOT, path, "meta.json"), encoding="utf-8"))
        write(os.path.join("p", p["id"], "index.html"), part_page(meta, path))
        urls.append(f"{DOMAIN}/p/{p['id']}/")

    write(os.path.join("about", "index.html"), about_page())
    write(os.path.join("guide", "kicad", "index.html"), guide_page())
    write(os.path.join("agents", "index.html"), agents_page())
    urls += [f"{DOMAIN}/about/", f"{DOMAIN}/guide/kicad/", f"{DOMAIN}/agents/"]

    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append(f"  <url><loc>{u}</loc></url>")
    sm.append("</urlset>")
    write("sitemap.xml", "\n".join(sm) + "\n")

    robots = f"""# PartReel — AI crawlers explicitly welcome.
# Machine guide: {DOMAIN}/llms.txt   Agent guide: {DOMAIN}/agents/
User-agent: *
Allow: /

User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

Sitemap: {DOMAIN}/sitemap.xml
"""
    write("robots.txt", robots)

    print(f"Built {len(index['parts'])} part pages + about + guide + agents + sitemap({len(urls)}) + robots [EN]")


if __name__ == "__main__":
    main()
