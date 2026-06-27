"""
SEO/콘텐츠용 정적 페이지 생성기.
실행: python generators/build_site.py

생성물:
  - p/<id>/index.html      부품별 페이지 15개 (SEO: title/meta/canonical/OG/JSON-LD + 3D)
  - about/index.html       소개 페이지
  - guide/kicad/index.html "KiCad에 넣는 법" 가이드
  - sitemap.xml, robots.txt

공통: render()가 head(CSP·favicon·OG) + 헤더 + 푸터를 감싼다.
보안(REQUIREMENTS §6/§13): 동적 값 html.escape, CSP 메타.
"""

import json
import os
import html

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
DOMAIN = "https://partreel.com"
GITHUB = "https://github.com/mingyo186/partreel"

FMT_LABEL = {"kicad_mod": "KiCad 풋프린트", "kicad_sym": "KiCad 심볼", "step": "3D STEP", "glb": "3D 프리뷰"}
FMT_KEY = {"glb": "preview", "step": "model_3d", "kicad_mod": "footprint", "kicad_sym": "symbol"}

CSP = ("default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
       "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "connect-src 'self' https://cdn.jsdelivr.net; object-src 'none'; base-uri 'self'")


def esc(s):
    return html.escape(str(s), quote=True)


def footer(prefix):
    return f"""<footer class="site-footer">
  <div class="foot-brand">PartReel · 로그인 없는 오픈 KiCad 라이브러리</div>
  <nav class="foot-nav">
    <a href="{prefix}about/">소개</a>
    <a href="{prefix}guide/kicad/">KiCad에 넣는 법</a>
    <a href="{GITHUB}" target="_blank" rel="noopener">GitHub</a>
  </nav>
  <div class="foot-lic">코드 MIT · 부품 CC-BY-4.0 · 치수는 데이터시트 기반, 사용 전 검증 권장(as-is)</div>
</footer>"""


def render(prefix, title, desc, canonical, body, head_extra="", scripts=""):
    return f"""<!DOCTYPE html>
<html lang="ko">
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
<link rel="stylesheet" href="{prefix}assets/style.css?v=2">
{head_extra}
</head>
<body>
<header class="topbar">
  <a class="brand" href="{prefix}" style="text-decoration:none;color:inherit"><span class="logo">◈</span><span class="brand-name">PartReel</span></a>
  <div class="header-badges"><span class="hbadge ok">가입 불필요</span><span class="hbadge ok">즉시 다운로드</span></div>
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
    sym_svg = files.get("symbol_svg", "")
    fp_svg = files.get("footprint_svg", "")

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
        dls.append(f'<a class="dl" href="{prefix}{path}/{esc(fn)}" download>'
                   f'<span class="ext">{esc(fmt)}</span> {esc(FMT_LABEL.get(fmt, fmt))}</a>')
    downloads = "".join(dls)

    jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "Product", "name": name,
        "description": desc, "category": "Electronic Connector",
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
  <nav class="crumb"><a href="{prefix}">홈</a> / {esc(fam)} / {esc(name)}</nav>
  <h1>{esc(name)}</h1>
  <p class="desc">{esc(desc)}</p>
  <div class="view-tabs">
    <button class="vt active" data-view="3d">3D</button>
    <button class="vt" data-view="sym">심볼</button>
    <button class="vt" data-view="fp">풋프린트</button>
  </div>
  <div id="viewer" class="viewer part-viewer" data-glb="{prefix}{path}/{esc(glb)}" data-sym="{prefix}{path}/{esc(sym_svg)}" data-fp="{prefix}{path}/{esc(fp_svg)}">
    <div class="viewer-msg">3D 로딩 중…</div>
    <img id="view-sym" class="view-img" alt="심볼" hidden>
    <img id="view-fp" class="view-img" alt="풋프린트" hidden>
  </div>
  <h2>사양</h2>
  <table class="specs">{spec_rows}</table>
  <h2>다운로드 <span class="nologin">· 가입 없이</span></h2>
  <div class="downloads">{downloads}</div>
  <h2>데이터시트</h2>
  <a class="dl" href="{esc(ds)}" target="_blank" rel="noopener">제조사 데이터시트 (JST)</a>
  <h2>구매</h2>
  <a class="buy" href="https://www.lcsc.com/search?q={esc(mpn)}" target="_blank" rel="noopener">이 부품 구매처 보기 →</a>
  <p class="affiliate-note">제휴 링크 · 부품 라이선스: {esc(lic)}</p>
</main>"""
    scripts = f'<script type="module" src="{prefix}assets/part.js?v=2"></script>'
    title = f"{esc(name)} — KiCad 풋프린트·심볼·3D 모델 | PartReel"
    return render(prefix, title, esc(desc_short), f"{DOMAIN}/p/{pid}/", body, head_extra, scripts)


def about_page():
    prefix = "../"
    body = """<main class="doc-page">
  <h1>PartReel 소개</h1>
  <p>PartReel은 <strong>로그인 없이</strong> 바로 받는 오픈 KiCad 부품 라이브러리입니다. 데이터시트 치수로 생성한 심볼·풋프린트·3D 모델을 가입 절차 없이 즉시 다운로드할 수 있습니다.</p>
  <h2>왜 다른가</h2>
  <ul>
    <li><strong>로그인 0</strong> — 검색해서 바로 다운로드. 가입·이메일 인증 없음.</li>
    <li><strong>검증 가능한 품질</strong> — 데이터시트 치수로 결정론적 생성. 풋프린트는 KiCad 공식 라이브러리 치수와 일치하도록 만듭니다.</li>
    <li><strong>오픈</strong> — 코드는 MIT, 부품 자산은 CC-BY-4.0. 전부 git으로 버전관리됩니다.</li>
  </ul>
  <h2>어떻게 만드나</h2>
  <p>패키지 치수(피치·핀 수 등)를 파라메트릭 생성기에 넣어 심볼·풋프린트·3D(STEP/GLB)를 한 번에 생성합니다. 같은 패밀리는 숫자만 바꿔 전수 생성하므로, 흔하지만 라이브러리에 빠져있던 부품까지 빠르게 채울 수 있습니다.</p>
  <h2>라이선스 · 면책</h2>
  <p>코드 MIT / 부품 자산 CC-BY-4.0(출처 표기). 치수는 공개된 제조사 데이터시트 기반이며 as-is로 제공됩니다. 중요한 풋프린트는 제조 전 데이터시트와 대조 검증을 권장합니다.</p>
  <p><a href="../">← 홈으로</a></p>
</main>"""
    return render(prefix, "PartReel 소개 — 로그인 없는 오픈 KiCad 라이브러리",
                  "PartReel은 로그인 없이 받는 오픈 KiCad 부품 라이브러리입니다. 데이터시트 치수로 생성한 검증 가능한 풋프린트·심볼·3D 모델.",
                  f"{DOMAIN}/about/", body)


def guide_page():
    prefix = "../../"
    body = """<main class="doc-page">
  <h1>KiCad에 넣는 법</h1>
  <p>PartReel에서 받은 파일을 KiCad에 추가하는 방법입니다.</p>
  <h2>1. 심볼 (.kicad_sym)</h2>
  <ol>
    <li>KiCad → <strong>Preferences → Manage Symbol Libraries</strong></li>
    <li>Global 또는 Project 탭에서 <strong>+</strong> → 받은 <code>.kicad_sym</code> 파일 선택</li>
    <li>스키매틱 에디터에서 심볼 배치 시 사용</li>
  </ol>
  <h2>2. 풋프린트 (.kicad_mod)</h2>
  <ol>
    <li><code>.kicad_mod</code> 파일을 <code>MyLib.pretty</code> 폴더 안에 넣습니다 (풋프린트는 <code>.pretty</code> 폴더 단위로 관리)</li>
    <li><strong>Preferences → Manage Footprint Libraries</strong> → <strong>+</strong> → 그 <code>.pretty</code> 폴더 추가</li>
  </ol>
  <h2>3. 3D 모델 (.step)</h2>
  <ol>
    <li>풋프린트 에디터에서 풋프린트 열기 → <strong>Footprint Properties → 3D Models</strong></li>
    <li>받은 <code>.step</code> 파일 경로 지정</li>
  </ol>
  <p>웹의 3D 미리보기는 <code>.glb</code>(표시 전용)이며, KiCad에는 <code>.step</code>을 사용하세요.</p>
  <p><a href="../../">← 홈으로</a></p>
</main>"""
    return render(prefix, "KiCad에 부품 라이브러리 넣는 법 | PartReel",
                  "KiCad에 심볼(.kicad_sym)·풋프린트(.kicad_mod)·3D(.step)를 추가하는 단계별 가이드.",
                  f"{DOMAIN}/guide/kicad/", body)


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
    urls += [f"{DOMAIN}/about/", f"{DOMAIN}/guide/kicad/"]

    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append(f"  <url><loc>{u}</loc></url>")
    sm.append("</urlset>")
    write("sitemap.xml", "\n".join(sm) + "\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n")

    print(f"Built {len(index['parts'])} part pages + about + guide + sitemap({len(urls)}) + robots")


if __name__ == "__main__":
    main()
