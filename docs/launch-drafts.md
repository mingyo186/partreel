# Launch post drafts (v2, 2026-07-24 — review before posting; post from your own accounts)

> 목적: 홍보가 아니라 **백링크 = 색인/순위 지렛대** (색인 7,600 정체의 처방, REQUIREMENTS §23).
> 게시 순서 추천: KiCad 포럼 → r/KiCad → (반응 보고) Show HN. 하루 간격, 댓글 성실 응답이 절반.
> 숫자 근거(2026-07-24): 18,260 parts / 3D ~7,170 / MCP worker ~1,000 invocations/day / 라이선스 부품별 기계판독(CC-BY-4.0·CERN-OHL-P-2.0·MIT).

---

## 1) Hacker News — "Show HN"

**Title:**
Show HN: PartReel – an 18k-part KiCad registry your AI agent can search, use, and grow

**Body:**

I got tired of two things: parts sites that gate a 2 KB footprint file behind a login, and AI agents regenerating (unverified) footprints from scratch every time someone asks.

So I built PartReel (https://partreel.com) — an open KiCad component registry designed to be a waypoint for both humans and AI agents:

- **No sign-up.** Search → symbol/footprint/3D preview → download (.kicad_mod / .kicad_sym / STEP / GLB). 18k+ parts, ~7k with 3D models.
- **Collected, not re-invented.** Most of the catalog is imported from existing open libraries (CERN's KiCad libraries, ai03's MX switches, SparkFun) — original licenses kept per part (CERN-OHL-P-2.0 / MIT / CC-BY-4.0, machine-readable in each part's metadata), full provenance recorded (source repo, commit, modifications). The thesis: the assets already exist, they're just scattered and invisible to agents.
- **Every part passes automated gates** on every deploy: s-expression structure validation, drawing-rule checks, render completeness, overlap detection, 3D mesh checks, asset-hash integrity. A part that breaks a gate blocks the deploy.
- **AI-native:** static JSON API (no auth, no rate limit), llms.txt, and a remote MCP server (https://mcp.partreel.com/mcp) with search/get/request/feedback tools. The worker currently serves ~1,000 tool calls/day.
- **Self-growing:** parametric families are generated on demand — an agent calls `request_part(family, pins)`, CI generates the part, runs the gates, uploads assets, and publishes it permanently in ~5 minutes. Generated once, cached for everyone. Agents can also report real-board results (`report_feedback`) — field-proven history accumulates per part.

Everything is open: generators MIT, per-part licenses as above, the whole thing is a git repo + static hosting + one Cloudflare Worker. https://github.com/mingyo186/partreel

Happy to answer anything about the quality gates, the import/provenance pipeline, or the on-demand generation path.

---

## 2) Reddit r/KiCad

**Title:**
I built a no-login KiCad parts registry: 18k parts, footprint+symbol+3D in one click, open licenses with provenance

**Body:**

Like many of you I hate signing up somewhere just to download a footprint. So I built **PartReel**: https://partreel.com

- No account. Search → preview (symbol / footprint / 3D tabs) → download `.kicad_mod`, `.kicad_sym`, STEP, GLB.
- ~18k parts. Most are imported from existing open libraries (CERN's KiCad libs, ai03 MX switches, SparkFun) with original licenses kept per part and full provenance (source repo + commit + what we changed). Self-generated parts cite datasheet dimensions and are matched against the official library where one exists.
- Automated quality gates run on every deploy (structure validation, drawing rules, render completeness, overlap, 3D mesh checks) — a failing part blocks the release.
- For the AI-curious: public JSON API + MCP server, and parametric families (pin headers etc.) are generated **on request** and become permanent entries — my agent asks for a 9-pin header, five minutes later it exists for everyone.

To be clear: for common parts the official library is the right answer. This is for the "I need a verified bundle *now*, without an account" workflow — and for AI assistants, which can't click through login walls at all.

**How to use downloads in KiCad:** https://partreel.com/guide/kicad/
Requests and brutal feedback welcome — a gate that should have caught something and didn't is exactly what I want to hear about.

---

## 3) KiCad 공식 포럼 (forum.kicad.info — "External Plugins & Tools" 카테고리)

**Title:**
PartReel — open, no-login parts registry (18k parts, gate-checked, with provenance)

**Body:**

Hi all,

I'd like to share a project: **PartReel** (https://partreel.com), an open component registry with no login wall.

What it does:
- One page per part with symbol / footprint / 3D previews and direct downloads (`.kicad_mod`, `.kicad_sym`, STEP, GLB).
- ~18k parts. The majority are **imported from existing open libraries** — CERN's KiCad libraries, ai03's MX switch library, SparkFun — keeping each part's original license (CERN-OHL-P-2.0 / MIT / CC-BY-4.0, machine-readable in metadata) and full provenance: source repo, pinned commit, and a list of any modifications we made. Attribution lives in ATTRIBUTIONS.md in the repo.
- Automated checks run on every deploy: s-expression structure validation, drawing-rule checks (silk clearance, fab outline, courtyard), render completeness, overlap detection, and 3D mesh sanity. A failing part blocks the deploy.
- There's also a JSON API and an MCP server so AI assistants can fetch existing parts instead of regenerating them, request missing parametric variants (generated + gated + published automatically), and report real-board feedback.

To be clear about scope: this is **not** trying to replace the official library — for common parts the official library is the right answer, and our self-generated parts match official dimensions where an official footprint exists. The aim is the workflow where you (or your AI assistant) need a verified part bundle instantly without an account — plus making already-existing open assets (CERN etc.) actually discoverable and downloadable per-part.

Source (generators MIT): https://github.com/mingyo186/partreel

Feedback very welcome — especially on the quality checks. If you find anything the gates should catch and don't, that's exactly what I want to hear.

---

### 게시 팁
- HN: 화·수 오전(미국 동부) 제출이 통계적으로 유리. 제출 후 1~2시간 댓글 상주.
- r/KiCad: 셀프프로모션에 관대한 편이지만 "피드백 구함" 톤 유지.
- KiCad 포럼: 가장 보수적 — "공식 라이브러리 대체 아님" + provenance/라이선스 준수 명시가 중요 (넣어둠).
- 셋 다 공통: 초기 댓글 질문에 빠르게·솔직하게. 결함 지적 = 선물. CERN 임포트 관련 질문 나오면: 원 라이선스 유지 + 수정목록 공개 + ATTRIBUTIONS.md를 근거로.
- 숫자는 게시 직전 최신으로 갱신할 것 (부품 수, MCP 콜 수).
