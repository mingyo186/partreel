# Launch post drafts (review before posting — post from your own accounts)

> 게시 순서 추천: KiCad 포럼 → r/KiCad → (반응 보고) Show HN.
> 같은 날 다 쏘지 말고 하루 간격. 댓글에 성실히 답하는 게 반응의 절반.

---

## 1) Hacker News — "Show HN"

**Title:**
Show HN: PartReel – a no-login KiCad parts registry that AI agents can grow

**Body:**

I got tired of two things: parts sites that gate a 2 KB footprint file behind a login, and AI agents regenerating (unverified) footprints from scratch every single time someone asks.

So I built PartReel (https://partreel.com) — an open KiCad component registry designed for both humans and AI agents:

- No sign-up. Search → 3D/symbol/footprint preview → download (.kicad_mod / .kicad_sym / STEP / GLB). Assets are CC-BY-4.0.
- Every part passes automated quality gates: s-expression structure validation, KiCad Library Convention drawing rules, text-overlap checks, render completeness, STEP kernel isValid. Dimensions cite datasheets and are matched against the official KiCad library where one exists.
- AI-native: static JSON API (no auth, no rate limit), llms.txt, and a remote MCP server (https://mcp.partreel.com/mcp) with search/get/feedback tools.
- Self-growing: parametric families (pin headers etc.) are generated **on demand** — an agent calls `request_part(family, pins)`, CI generates the part, runs the gates, and publishes it permanently in ~5 minutes. Generated once, cached for everyone.
- Agents can report real-board results (`report_feedback`) — field-proven history accumulates per part.

Everything is open: generators (MIT), parts (CC-BY-4.0), the whole thing is a git repo + static hosting + one Cloudflare Worker. https://github.com/mingyo186/partreel

The catalog is deliberately small right now (~50 quality-gated parts: JST families, USB-C, microSD, ESP32-WROOM, terminals, headers). The bet is that verified-and-reusable beats big-but-unverifiable, especially once agents are the main consumers.

Happy to answer anything about the quality gates, the MCP write-path, or the on-demand generation pipeline.

---

## 2) Reddit r/KiCad

**Title:**
I made a no-login KiCad parts registry (footprint + symbol + 3D in one click, CC-BY-4.0)

**Body:**

Like many of you I hate signing up somewhere just to download a footprint. So I built **PartReel**: https://partreel.com

- No account. Search → preview (3D / symbol / footprint tabs) → download `.kicad_mod`, `.kicad_sym`, STEP, GLB.
- Parts are generated from datasheet dimensions and must pass automated gates (KLC drawing rules, structure validation, STEP solid checks). Where an official KiCad footprint exists, dimensions are matched against it.
- CC-BY-4.0, everything versioned on GitHub — you can see exactly how every part was made and file issues/PRs.
- Bonus for the AI-curious: there's a public JSON API and an MCP server, and parametric families (e.g. pin headers 1–40 pins) can be generated on request and become permanent registry entries.

Catalog is young (~50 parts: JST PH/XH/GH, USB-C 16-pin, microSD, ESP32-WROOM-32, screw terminals, pin headers) — I'd rather grow it from real requests than bulk-dump thousands of unverified files. Requests and brutal feedback welcome.

**How to use downloads in KiCad:** https://partreel.com/guide/kicad/

---

## 3) KiCad 공식 포럼 (forum.kicad.info — "External Plugins & Tools" 카테고리)

**Title:**
PartReel — open, no-login parts registry (KLC-checked footprints + symbols + 3D)

**Body:**

Hi all,

I'd like to share a small project: **PartReel** (https://partreel.com), an open component registry with no login wall.

What it does:
- One page per part with 3D / symbol / footprint previews and direct downloads (`.kicad_mod`, `.kicad_sym`, STEP, GLB), all CC-BY-4.0.
- Parts are parametrically generated from datasheet dimensions. Automated checks enforce KLC drawing conventions (silk 0.12 mm with pad clearance, fab outline + pin-1 chamfer, solid courtyard), validate the s-expression structure, and verify the STEP solids. Where the official library already has the part, dimensions are matched to it.
- There's also a JSON API and an MCP server so AI assistants can fetch parts instead of regenerating them, report real-board feedback, and request missing parametric variants (generated + gated + published automatically).

To be clear about scope: this is not trying to replace the official library — for common parts the official library is the right answer. This is aimed at the workflow where you (or your AI assistant) need a verified part bundle instantly without an account, plus a growing set of on-demand parametric variants.

Source (generators MIT, parts CC-BY-4.0): https://github.com/mingyo186/partreel

Feedback very welcome — especially on the footprint quality checks. If you find anything the gates should catch and don't, that's exactly what I want to hear.

---

### 게시 팁
- HN: 화·수 오전(미국 동부) 제출이 통계적으로 유리. 제출 후 1~2시간 댓글 상주.
- r/KiCad: 셀프프로모션에 관대한 편이지만 "피드백 구함" 톤 유지.
- KiCad 포럼: 가장 보수적 — "공식 라이브러리 대체 아님" 문구가 중요 (넣어둠).
- 셋 다 공통: 초기 댓글 질문에 빠르게·솔직하게. 결함 지적 = 선물.
