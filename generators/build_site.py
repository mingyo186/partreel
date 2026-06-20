"""
SEO용 정적 부품 페이지 생성기.
실행: python generators/build_site.py

각 부품마다 크롤링 가능한 정적 페이지(p/<id>/index.html)를 생성:
  - <title>, <meta description>, canonical, Open Graph
  - JSON-LD Product 구조화 데이터
  - 서버 렌더된 사양/다운로드(자바스크립트 없이도 콘텐츠가 보임)
  - 3D 프리뷰(점진적 향상, assets/part.js)
추가로 sitemap.xml, robots.txt 생성.

보안(REQUIREMENTS §6/§13): 동적 값은 html.escape, CSP 메타 포함.
"""

import json
import os
import html

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
DOMAIN = "https://partreel.com"

FMT_LABEL = {"kicad_mod": "KiCad 풋프린트", "kicad_sym": "KiCad 심볼", "step": "3D STEP", "glb": "3D 프리뷰"}
FMT_KEY = {"glb": "preview", "step": "model_3d", "kicad_mod": "footprint", "kicad_sym": "symbol"}

CSP = ("default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
       "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "connect-src 'self' https://cdn.jsdelivr.net; object-src 'none'; base-uri 'self'")


def esc(s):
    return html.escape(str(s), quote=True)


def part_page(meta, path):
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

    rows = []
    for label, val in [("제조사", manu), ("패밀리", fam), ("MPN 패턴", mpn),
                       ("핀 수", params.get("pins")),
                       ("피치", f"{params.get('pitch_mm')} mm" if params.get("pitch_mm") is not None else None),
                       ("실장", params.get("mounting")), ("방향", params.get("orientation"))]:
        if val not in (None, ""):
            rows.append(f"<tr><td>{esc(label)}</td><td>{esc(val)}</td></tr>")
    spec_rows = "".join(rows)

    dls = []
    for fmt in meta.get("formats", []):
        fn = files.get(FMT_KEY.get(fmt, fmt))
        if not fn:
            continue
        dls.append(f'<a class="dl" href="../../{path}/{esc(fn)}" download>'
                   f'<span class="ext">{esc(fmt)}</span> {esc(FMT_LABEL.get(fmt, fmt))}</a>')
    downloads = "".join(dls)

    jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "Product", "name": name,
        "description": desc, "category": "Electronic Connector",
        "brand": {"@type": "Brand", "name": manu}, "mpn": mpn,
    }, ensure_ascii=False)

    title = f"{name} — KiCad 풋프린트·심볼·3D 모델 | PartReel"
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc_short)}">
<link rel="canonical" href="{DOMAIN}/p/{pid}/">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(name)} | PartReel">
<meta property="og:description" content="{esc(desc_short)}">
<meta property="og:url" content="{DOMAIN}/p/{pid}/">
<link rel="stylesheet" href="../../assets/style.css">
<script type="importmap">
{{ "imports": {{ "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js", "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/" }} }}
</script>
<script type="application/ld+json">
{jsonld}
</script>
</head>
<body>
<header class="topbar">
  <a class="brand" href="../../" style="text-decoration:none;color:inherit"><span class="logo">◈</span><span class="brand-name">PartReel</span></a>
  <div class="header-badges"><span class="hbadge ok">가입 불필요</span><span class="hbadge ok">즉시 다운로드</span></div>
</header>
<main class="part-page">
  <nav class="crumb"><a href="../../">홈</a> / {esc(fam)} / {esc(name)}</nav>
  <h1>{esc(name)}</h1>
  <p class="desc">{esc(desc)}</p>
  <div id="viewer" class="viewer part-viewer" data-glb="../../{path}/{esc(glb)}"><div class="viewer-msg">3D 로딩 중…</div></div>
  <h2>사양</h2>
  <table class="specs">{spec_rows}</table>
  <h2>다운로드 <span class="nologin">· 가입 없이</span></h2>
  <div class="downloads">{downloads}</div>
  <h2>데이터시트</h2>
  <a class="dl" href="{esc(ds)}" target="_blank" rel="noopener">제조사 데이터시트 (JST)</a>
  <h2>구매</h2>
  <a class="buy" href="https://www.lcsc.com/search?q={esc(mpn)}" target="_blank" rel="noopener">이 부품 구매처 보기 →</a>
  <p class="affiliate-note">제휴 링크 · 부품 라이선스: {esc(lic)}</p>
</main>
<script type="module" src="../../assets/part.js"></script>
</body>
</html>
"""


def main():
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    urls = [f"{DOMAIN}/"]
    for p in index["parts"]:
        path = p["path"]
        meta = json.load(open(os.path.join(ROOT, path, "meta.json"), encoding="utf-8"))
        outdir = os.path.join(ROOT, "p", p["id"])
        os.makedirs(outdir, exist_ok=True)
        with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
            f.write(part_page(meta, path))
        urls.append(f"{DOMAIN}/p/{p['id']}/")

    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append(f"  <url><loc>{u}</loc></url>")
    sm.append("</urlset>")
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(sm) + "\n")

    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n")

    print(f"Built {len(index['parts'])} part pages + sitemap.xml + robots.txt")


if __name__ == "__main__":
    main()
