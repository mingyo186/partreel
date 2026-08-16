# OpenCAD Library Platform — 요구사항 / 스펙

> 작성: 2026-06-20 · 상태: 기획 확정, 1차 구현 착수 직전
> 이름: **PartReel** (확정 2026-06-20) · 도메인 `partreel.com` 미등록 확인됨(등록 필요) · `opencad-lib`는 코드 폴더명

대화는 세션마다 휘발되므로 이 문서가 **단일 진실 소스(Source of Truth)**. 새 세션 시작 시 이 파일부터 읽을 것.

---

## 0. 작업 규칙 (워크플로우) — 항상 준수

> **결정 → 문서 → 구현 순서를 지킨다.**

1. 대화로 새로운 **결정/요구사항이 나오면, 먼저 이 문서에 반영**(추가/수정)한다.
2. 그 다음 **이 문서를 근거로 구현**한다. 구현이 문서를 앞서가지 않게 한다.
3. 아직 안 정해진 건 **§12 미결정/오픈 이슈**에 적는다. 결정되면 본문으로 옮긴다.
4. 프로젝트 작업 시작 전 이 문서를 먼저 읽는다.
5. **품질 검증 의무 (최우선)**: 모든 구현물, 특히 UI/사이트는 **실제로 실행·렌더해서 눈으로 검증**한다(스크린샷 캡처 등). 추측으로 "됐다"고 보고하지 않는다. **"당연히 동작해야 하는 것이 동작 안 하는" 명백한 버그를 남기지 않는다** — 예: 깨진 다운로드 링크, 안 뜨는 3D 프리뷰, 빈 목록, 눌리지 않는 버튼, 404. 검증 후 발견된 문제는 고친 뒤 보고한다.
5-1. **교차검증 (다른 방법으로도)**: 검증은 **한 가지 방법만 반복하지 말고 독립적인 다른 방법으로 교차검증**한다. 같은 렌즈만 쓰면 그 렌즈가 못 보는 결함을 놓친다. 예: HTTP 200 ↔ **실제 파일 파싱/구조 검증** ↔ 시각 렌더 ↔ **CAD 커널 검증(STEP isValid/volume)** ↔ 외부 검증기(KiCad). 특히 "받아지는데 정작 안 열리는/안 맞는" 결함은 서빙 검사로는 못 잡으므로 콘텐츠 자체를 별도 방법으로 검증.
6. **보안 의무 (상시)**: 정적 사이트라 공격면은 작지만 항상 신경 쓴다.
   - 레포에 **비밀키/토큰/크리덴셜 절대 커밋 금지** (.gitignore로 env류 차단).
   - **동적 값 렌더 시 HTML 이스케이프**(XSS 방지) — 특히 향후 사용자 기여 데이터.
   - 외부 스크립트는 **버전 고정 + 신뢰 출처만**(jsdelivr), **CSP**로 출처 제한.
   - GitHub Actions **최소 권한**(이미 contents:read/pages:write/id-token:write).
   - **HTTPS 강제**, 계정 **2FA**(GitHub/Cloudflare).
   - 자세한 체크리스트는 §13.

---

## 1-0. 존재 이유 (사용자 정의 2026-07-17 — 모든 우선순위의 근거)

> **PartReel = AI가 활동하기 좋은 중간 거점.** AI에 연결되지 않은 채 흩어져 있는
> 기존 자산(부품 라이브러리 등)을 모아, 일일이 찾아다니는 번거로움을 없애고
> **AI가 자유롭게 추가·수정·변경해서 사용**할 수 있게 하는 곳.

- **모으기 > 만들기**: 기존에 만들어진 것을 다시 만들지 않는다. 수입(검증-수입)이
  기본, 자체 생성은 어디에도 없는 것에만.
- AI 쓰기 경로(MCP report_feedback/request_part/기여 PR)가 읽기 경로만큼 중요 —
  "추가·수정·변경"이 가능해야 거점이다.

## 1. 한 줄 정의

> SnapMagic(구 SnapEDA) 같은 **부품 라이브러리 검색→다운로드 사이트**인데,
> **로그인 없고 + KiCad 네이티브 + 받은 걸 믿을 수 있는(생성 기반)** 버전.

전자(심볼/풋프린트/3D) 라이브러리부터 시작, 추후 기구(3D) 확장.

## 2. 타깃 사용자

- **무료/오픈 툴 사용자 전용** — KiCad, FreeCAD 사용자. 유료 툴(Altium 등) 비대상.
- 1차: KiCad로 PCB 설계하는 취미/스타트업/소규모 개발자 (JLCPCB/LCSC 생태계 포함).

## 3. 핵심 차별화 (vs SnapEDA/Ultra Librarian/SamacSys)

| 축 | 경쟁사 | 우리 |
|---|---|---|
| 로그인 | 강제 (최대 불만) | **없음** ← 1순위 차별점 |
| 품질 신뢰 | 알고리즘 오매칭, 재검증 필요 | **치수 기반 결정론적 생성 + 출처 치수 공개** |
| 대상 툴 | Altium 중심, 툴 다양 | **KiCad 네이티브 1등** (무료 진영 비어있음) |
| 롱테일 | 수요 있는 것만 수작업 | **파라메트릭 전수 생성** (한계비용 0) |
| 워크플로우 | 웹만 | 웹 메인 + **CLI/git 부가** |

포지션 한 줄: **"easyeda2kicad가 망치는 커넥터를, 로그인 없이, 제대로 만든 KiCad 라이브러리."**

## 4. 확정된 핵심 결정

1. **생성형 모델**: 데이터시트/표준 치수(=사실, 저작권 없음)로 **직접 생성** → 저작권 깨끗.
   - ❌ 금지: 남의 STEP/PDF/도면 재배포, 제조사 로고/브랜드 그래픽, 데이터시트 PDF 호스팅.
   - ✅ 허용: 치수만 보고 새로 모델링, 부품번호 호환 표기(명목적 사용), 자체 라이선스 배포.
   - 면책 문구 필수: "치수는 데이터시트 기반, 사용 전 검증 권장(as-is)".
2. **배포 = 정적**: 실시간 온라인 생성 X. **오프라인 배치 사전생성 → 정적 파일 배포**. 서버/DB 없음.
   - git = 소스 오브 트루스(원본 보관). 사용자는 git을 직접 안 봄.
   - 파이프라인: **git → CI 빌드 → 자기 도메인 CDN(Cloudflare Pages)**. 사용자는 자기 도메인에서만 다운로드 (트래픽/SEO/수익이 자기 것이어야 함).
3. **무료 툴 전용 노선**: KiCad·FreeCAD 등 완전 무료 툴만 타깃.
4. **수요 신호 기반 생성**: "라이브러리 없는 것 전부"가 아니라 **"검색되는데 안 나오는 것"**(갭 ∩ 수요)만 생성. 빈 니치=빈 시장 함정 회피.
5. **다운로드 신뢰성**(경쟁사 최대 실패모드 회피): 기존 사이트는 ①로그인 가로채기 ②"페이지는 있는데 그 포맷 파일은 실제로 없음" ③실시간 생성 타임아웃 ④다운로드 한도로 다운로드가 자주 실패함. 우리 정적+무로그인 구조가 ①③④는 원천 차단. ②만 우리도 실수 가능 → 원칙:
   - 표시된 모든 포맷은 **실제 파일이 반드시 존재**. 없으면 그 버튼/포맷을 아예 안 띄움.
   - **빌드 시 검증**: 배포 전 CI가 모든 부품×모든 포맷 파일 존재를 체크, 빠지면 배포 실패.
   - 링크-실제파일 일치 보장(404/빈 파일 금지).

## 5. 비치헤드 & 1차 웻지

- **비치헤드**: 전자 / **KiCad**. (사유: 사용자가 전자를 더 잘 앎=파운더 도메인핏, 무료 EDA 절대강자=KiCad, easyeda2kicad/SnapEDA가 무료·무가입 수요 입증, 수익화 유리=Digikey/Mouser/LCSC 제휴 성숙.)
- **1차 웻지 = 커넥터 패밀리**. (사유: 자동생성이 못 하는 영역[비표준 기하학]=진짜 갭, 모든 보드가 쓰는 고수요, 그런데 패밀리 단위로 파라메트릭[피치×핀수→전수 생성], easyeda2kicad가 품질 엉망이라 정면승부 가능, 전기+기구 반반이라 추후 기구 확장 다리.)
- **2순위**: 모듈/devkit(ESP32 모듈 등) — 고수요지만 일회성 고정 기하학이라 수작업.
- **버린 것**: 맨 IC(표준 패키지) — KiCad 기본+easyeda2kicad가 이미 덮어서 갭 작음.

## 6. SEO = 트래픽 엔진 (제품의 본질)

부품번호 하나 = 검색 랜딩 페이지. "누가 부품 검색했을 때 우리 페이지가 떠서 로그인 없이 파일 준다"가 제품 핵심.
운영: 수요신호 수집(InstaPart 요청목록/포럼 footprint 요청/LCSC 인기순위) → 우선순위 큐 → 생성 → 부품번호별 SEO 랜딩(로그인0) → 구글 색인 → 트래픽 → 어필리에이트.

## 7. 수익 모델

- **광고는 약함** (엔지니어=애드블록 최강, 단가 푼돈). 메인 아님.
- **메인 = 유통사 어필리에이트** ("이 부품 어디서 사 →" 수수료). 전자=Digikey/Mouser/LCSC(성숙). 기구=약함(McMaster 제휴 없음).
- 초기: Sovrn(자동 링크변환)+AliExpress+Amazon 제휴로 가볍게. 트래픽 커지면 직접 제휴/프리미엄/스폰서.
- **닭-달걀 주의**: 제휴 승인엔 트래픽 필요 → 순서는 ①무가입 고품질로 트래픽 ②제휴 ③수익. 절대 로그인/유료벽으로 마찰 만들지 말 것(=경쟁사 실수 복제).

## 8. 기술 아키텍처

- **생성 엔진**: KiCad(전자, pcbnew/kicad-cli 파이썬 API) + FreeCAD(3D, 헤드리스 파이썬). 둘 다 오픈소스+스크립터블. **생성 자체는 이미 PoC로 검증됨(이전 세션에서 라이브러리 작동 확인).**
- **풋프린트**: IPC-7351(패드 치수) + **KLC(KiCad Library Convention, klc.kicad.org) 그리기 규격 준수**. silk 0.12mm(패드 0.2mm 비침범), fab 0.10mm 본체+pin1 1mm 모따기, courtyard 0.05mm(커넥터 0.5mm 클리어런스), pin1 마커. (밀도 Most/Nominal/Least 3종 = 향후 차별점.)
- **중립 포맷 전략**: MVP는 KiCad를 마스터로. 확장 시 자체 중립 JSON 스키마(part.json)→포맷별 렌더러로 일반화.
- **출력 포맷**: KiCad(.kicad_sym/.kicad_mod) + STEP + STL + GLB(웹 프리뷰). 배치로 전부 사전생성(런타임 변환 없음).
- **파일 저장**: 이산(나사규격/핀수)=전수 사전생성→정적파일. 연속(임의 길이)=CLI 로컬생성(하이브리드).
- **MVP 스택(전부 무료)**: GitHub 레포 + Cloudflare Pages(도메인/CDN/서빙) + three.js(.glb 프리뷰). 커지면 Cloudflare R2(egress 무료, 100GB≈월 $1.5).
- **생성 파일은 로컬생성→git 커밋→CI는 배포만** (CI에 FreeCAD 세팅 회피). CI 자동생성은 나중.

## 9. 용량/비용

- 파일당 KB~수MB. 수백 부품=수백MB=완전 무료. 트래픽 요금은 Cloudflare라 **항상 0**.
- 걸리는 한도: Cloudflare Pages 배포당 **파일 2만 개**, 무료 저장 한도. 넘으면 R2(월 몇 천 원).

## 10. 로드맵

**전략 = 얇은 수직 슬라이스(Thin Vertical Slice)**: "사이트부터" 또는 "부품 전체부터"가 아니라, 샘플 몇 개로 데이터 형식을 먼저 확정한 뒤 사이트를 그 위에 올리고 확장. (사이트와 부품은 데이터 형식으로 묶여 있어 부품 출력이 사이트 데이터 계약을 결정하기 때문.)

1. **0단계(현재)**: JST-PH 샘플 3개(2·4·6핀) 생성 → **데이터 형식 확정**(파일구조/meta.json/index.json).
2. **1단계**: 최소 정적 사이트(샘플 목록 + 3D프리뷰 + 무가입 다운로드)를 진짜 데이터 위에 구축.
3. **2단계**: JST-PH 패밀리 전수 생성(2~16핀) → 사이트에 투입. GitHub 레포 + Cloudflare Pages 배포.
4. **3단계**: 커넥터 패밀리 확장(JST-XH/SH, Molex/Hirose...) + 수요신호 채굴로 우선순위 + 어필리에이트.
5. **4단계**: CLI(pip), 모듈/devkit, KiCad PCM 플러그인.
6. **확장**: 전자 IC 롱테일 → 기구 표준품(FreeCAD).

## 11. 현재 작업

✅ **0단계 완료(2026-06-20)**: JST-PH 샘플 3개(2·4·6핀) 전 자산 생성 완료 — 풋프린트/심볼/STEP/GLB/meta.json/index.json. 데이터 형식 확정됨. 3D 치수 검증 통과(X=(n-1)*2+3, Y=4.5, Z=7.5).
- 생성기(config 기반 공통): `generators/gen_connectors.py`(텍스트+통합 index), `generators/gen_connectors_3d.py`(FreeCAD STEP/STL), `generators/stl_to_glb.py`(GLB), `generators/render_svg.py`(SVG). 패밀리는 gen_connectors.py의 FAMILIES 설정에 추가.
- FreeCAD 실행: `"C:\Users\mg_seo\AppData\Local\Programs\FreeCAD 1.1\bin\freecadcmd.exe" <script>` (GUI RPC 불필요 — 헤드리스 배치).

✅ **1단계 완료(2026-06-20)**: 최소 정적 사이트 구축·검증 완료.
- 파일: `index.html`, `assets/style.css`, `assets/app.js`. 웹 루트 = 레포 루트(상대경로). three.js(CDN importmap) + GLTFLoader로 .glb 프리뷰.
- 로컬 실행: `python -m http.server 8766 --directory D:/seriouscode/opencad-lib` (또는 `.claude/launch.json`의 opencad-site).
- **품질 검증 통과**(규칙 §0-5): 부품목록 렌더 / 3D 프리뷰 렌더(핀수별 정확) / 부품 전환 동작 / 사양 갱신 / **다운로드 6링크 전부 HTTP 200** / 콘솔 에러 0 / verify 경고 표시 / 어필리에이트(LCSC 검색) 링크.

🔄 **2단계 진행 중(2026-06-20)**:
- ✅ **치수 검증 완료**: KiCad 공식 Connector_JST(JST 데이터시트 기반)와 풋프린트 일치 — 패드 oval 1.2×1.75/drill 0.75, Fab/Silk/Crt 좌표 정합. 본체 비대칭(y -1.70~2.80) 반영. meta `verified: true`.
- ✅ **전수 생성 완료**: JST-PH 2~16핀 = **15부품 × 5자산 = 75파일**. index.json 15건.
- ✅ **품질 검증**(규칙 §0-5): 사이트 15개 렌더 / 부품 전환 동작 / 3D 모델 로드(2·6·16핀 확인) / 다운로드 링크 HTTP 200 / verify 경고 사라짐 / 콘솔 에러 0. (스크린샷 도구는 연속 WebGL 애니메이션으로 타임아웃 — DOM/HTTP/eval로 검증, 사이트 버그 아님.)

✅ **배포 완료(2026-06-20)**: GitHub Pages 라이브.
- 레포: https://github.com/mingyo186/partreel (public)
- 라이브 사이트: **https://mingyo186.github.io/partreel/**
- 배포: `.github/workflows/deploy.yml` (push 시 자동, site+library만 publish). gh 인증=mingyo186.
- 라이선스: 코드 MIT(`LICENSE`) / 부품 CC-BY-4.0(`library/LICENSE`).
- **라이브 검증 통과**: HTML/index.json/assets/다운로드(step·kicad_mod) 전부 HTTP 200.

✅ **커스텀 도메인 연결(2026-06-20)**: partreel.com (Cloudflare Registrar 구매) → GitHub Pages 연결 완료.
- DNS(Cloudflare): `@`·`www` CNAME → mingyo186.github.io (DNS only). A레코드 185.199.108~111.153 정상.
- http://partreel.com 라이브 확인됨(200). **HTTPS 인증서는 GitHub 자동 발급 대기 중** → 발급되면 `gh api -X PUT repos/mingyo186/partreel/pages -F https_enforced=true` 로 강제 전환 켜기.

✅ **SEO 1순위 완료(2026-06-20)**: 부품별 정적 페이지 + 보안.
- `generators/build_site.py` → `p/<id>/index.html` 15개 (title/meta/canonical/OG/JSON-LD Product) + `sitemap.xml`(16 URL) + `robots.txt`.
- `assets/part.js` 부품 페이지 3D 뷰어. 홈 SPA에 permalink 추가.
- 보안: 전 페이지 **CSP** 메타, 동적 값 **HTML 이스케이프**(§13).
- 라이브 검증 통과: partreel.com/p/jst_ph_4pin/ 등 200, SEO 태그·sitemap·robots·3D·다운로드 정상, 콘솔 에러 0.

✅ **HTTPS 강제 완료** · ✅ **Google Search Console 등록+sitemap 제출+색인 요청 완료**(사용자) · ✅ **2순위 다듬기 완료(2026-06-23)**: 모바일 반응형 / About(/about/) / KiCad 가이드(/guide/kicad/) / favicon / 전 페이지 푸터. build_site.py에 공통 render() 도입. sitemap 18 URL. 라이브 검증 통과.

**검색 엔진 도입 (사용자 확정 2026-07-26 "검색 엔진을 달아야할까")**: 손수 만든 검색을 하루 두 번 고친 시점(어순 토큰화→숫자 경계)에서 한계 인정 → **MiniSearch** 채택 (MIT, ~30KB, 의존성 0). 오타 허용(fuzzy)+접두 매칭+관련도 순위+필드 가중치(name/mpn>keywords). 원칙: ①라이브러리 파일은 assets/vendor/에 버전 고정 자체 호스팅(CSP, 외부 CDN 런타임 의존 금지) ②로드 실패 시 기존 토큰 AND 검색 폴백 유지 ③계기 = 레딧 제보("5 pin JST" 미검색, 시맨틱 요청) — fuzzy+토큰화가 실질 수요의 90%.

⚠️ **모바일 줌 부재 사건 (2026-07-24, r/KiCad 런칭 댓글 제보 "zooming was totally broken")**: 뷰어가 `touch-action: none`으로 브라우저 기본 핀치·스크롤을 막아놓고 터치 핀치 줌은 미구현 → 모바일에서 확대 불가 + 뷰어 위 페이지 스크롤 먹통. 데스크톱(휠)은 정상이라 우리 검증에서 안 잡힘 — **교훈: UI 검증은 모바일 뷰포트+터치 입력 포함**. 수정: makeZoomable(app.js v13/part.js v12 공통)에 ①2포인터 핀치 줌(zoomAt 공통 헬퍼, svg viewBox·img transform 양 경로) ②touch-action 동적 전환(미확대=pan-y로 페이지 스크롤 통과, 확대=none으로 팬 전용) ③Firefox 휠 deltaMode(줄/페이지 단위) 정규화. style.css v3/v6.
**후속 정정(같은 날)**: 제보자는 모바일이 아니라 **데스크톱 터치패드** — 진짜 원인은 뷰어가 모든 휠 이벤트를 preventDefault로 삼켜 두손가락 스크롤 시 "페이지 멈춤+의도 않은 줌" = 고장 체감. **입력 재설계(part.js v13/app.js v14/style.css v4·v7)**: 미확대 상태의 일반 휠은 페이지에 양보, 줌 입력 = 핀치(터치·ctrl+휠) / 확대 중 휠 / 더블클릭 토글 / **줌 버튼 오버레이(+·−·⟲, 3D 탭에선 숨김)**. 이벤트당 배율 [0.5,2] 클램프. 교훈: **뷰어가 스크롤 제스처를 가로채면 안 됨 — 명시적 줌 입력만 하이재킹.**

✅ **뷰 셀렉터 완료(2026-06-23)**: 뷰어에 **[3D | 심볼 | 풋프린트] 탭**. 심볼·풋프린트는 `generators/render_svg.py`가 .kicad_sym/.kicad_mod 파싱→SVG 미리보기 생성(부품당 .symbol.svg/.footprint.svg, meta.files에 등록). 홈 SPA(app.js)+부품 페이지(part.js) 양쪽 적용. **교차검증**: 브라우저 렌더로 SVG 품질 시각 확인 + 탭 전환 eval 검증(양쪽 페이지). 에셋에 `?v=` 캐시버스팅 도입(앞으로 JS/CSS 변경 시 v 올릴 것).

**▶ NEXT 후보**:
1. **커넥터 패밀리 확장** (JST-XH 2.5mm/JST-SH 1.0mm, Molex 등) — 생성기 복제. 확장 시 jst_ph→텍스트, jst_ph_3d→3D, stl_to_glb→GLB, render_svg→SVG, build_site→페이지 순으로 재생성 → sitemap 갱신 → Search Console 재제출.
2. 3D 뷰어 컨트롤(회전 멈춤/리셋 버튼).
3. 검색 개선 / 카테고리 필터.
4. 수요신호 채굴로 다음 패밀리 우선순위.

원래 목표(참고): "이게 우리 품질이다" 샘플 + **데이터 형식 확정**. (첫 패밀리 JST-PH 확정 사유: 리포배터리 표준, 취미 수요 확실, 2.0mm 피치 × 핀수로 파라메트릭 전수 생성 가능.)

치수 주의: 샘플은 파이프라인/형식 확정이 목적. **공개(publish) 전 JST 데이터시트로 최종 치수 검증 필수**(우리 차별점이 품질이므로).

## 13. 보안 체크리스트

- [x] 레포에 비밀키/토큰 없음 (gh 토큰은 OS keyring, 레포 아님). `.gitignore`로 env류 차단.
- [x] 생성 사이트(부품 페이지)에서 동적 값 **HTML 이스케이프** (build_site.py `html.escape`).
- [x] **CSP** 메타: script는 self+jsdelivr만, object-src none, base-uri self.
- [x] 외부 의존성 three.js **버전 고정**(0.160.0), jsdelivr.
- [x] GitHub Actions **최소 권한**.
- [x] HTTPS 강제 완료. 인증서 approved + https_enforced=true. https://partreel.com 라이브, http→https 자동전환. (인증서가 처음 멈춰서 커스텀도메인 뺐다 다시 넣어 재발급 트리거함.)
- [ ] 계정 2FA 확인 (GitHub/Cloudflare) — 사용자 몫.
- [ ] (향후) 사용자 기여 부품 받게 되면 입력 검증/샌드박싱 강화. CSP에서 'unsafe-inline' 제거(importmap→해시/nonce).

## 14. 품질 기준 (부품/패밀리 합격 기준 — publish/`verified:true` 전 모두 충족)

새 패밀리를 추가할 때 이 바를 넘어야 한다. 오늘(2026-06) 잡은 교훈 포함.

### A. 풋프린트 (.kicad_mod) — KLC + IPC-7351
- 패드 치수는 IPC-7351 / 데이터시트 기반. **KiCad 공식 라이브러리에 동일 부품 있으면 그 치수와 대조 일치.**
- 1번핀 구분 형상(roundrect/rect), 나머지 oval/circle. drill·pad·pitch 정확.
- Silk **0.12mm**, 패드와 **≥0.2mm**(패드 위 안 지나감), pin1 모따기.
- Fab **0.10mm** 본체 외곽 + pin1 모따기.
- Courtyard **0.05mm 실선**(점선 아님), 커넥터 **0.5mm** 클리어런스.
- Reference "REF**"(silk) / value(fab).

### B. 심볼 (.kicad_sym)
- 핀 개수 = 부품 핀수, 번호 1..N 연속, 핀 이름 존재, 본체 사각, Reference 적절(커넥터 J).

### C. 3D (STEP/GLB)
- STEP: `isValid`, 부피>0, 솔리드 정상. 본체 치수 = 풋프린트 fab와 일치.
- GLB: 컬러, 웹 경량(수 KB).
- **형상 사실성(2026-07 추가, 스크류터미널 제네릭 사건)**: 게이트는 "유효한 솔리드"만 잡고 "그 부품답게 생겼나"는 못 잡음 → **새 패밀리/새 3D 스타일은 대표 1개를 반드시 시각 확인.** 스타일: gen_connectors_3d의 style 필드(shrouded 기본/header/terminal).
- **3D 완결 기준(2026-07-04 사용자 확정 — "디테일 무한 손질은 독")**: 3D는 ①외곽 치수 도면 정확(간섭체크) ②한눈 식별 ③렌더 결함 없음(z-fighting 등) 이 셋이면 **완결**. 그 이상 리얼리즘은 백로그. **근본 개선(백로그)**: 프리미티브 눈대중 조립 대신 **데이터시트 측면도 프로파일 폴리곤을 좌표 그대로 압출**하는 방식으로 재작성(도면=모델 1:1, KiCad 공식 방식) — 런칭 후.
- **공면(z-fighting) 금지 — 자동 게이트화(2026-07-04, "microSD 또 z-fight" 사건)**: `generators/check_zfight.py`가 모든 GLB의 메시 쌍에서 같은 축·같은 법선·같은 평면의 겹치는 면을 기하학적으로 검출 (qa.py + deploy/pr-gates CI 포함 — **사람이 눈으로 찾지 않음**). 해소 패턴: standoff 띄우기 / XY 비겹침 / 0.02 관통 랩.
- **시각검수는 반드시 실제 뷰어로(2026-07, "떠있는 띠" 사건)**: matplotlib 기반 `render_check.py`는 **깊이(가림) 처리를 못 해 형상 결함을 가릴 수 있음** → 퀵룩 용도로만. **정식 검수 = 로컬 서버 띄워 부품 페이지 3D 탭을 실제 브라우저(three.js)로 렌더**해서 확인 (사용자가 보는 그 화면). 겸: 특징 지오메트리는 프로그래매틱 교차확인(예: trimesh split으로 핀 개수, 부피 비교).

### D. SVG 미리보기
- 풋프린트: 패드+드릴+silk+fab+courtyard(실선)+**pin1 삼각형(빈 공간, 선과 안 겹침)**. 모든 레이어 선이 실제로 그려질 것(패드만 X).
- 심볼: 본체+핀+번호+이름.

### E. 메타 (meta.json / index.json)
- 필수 필드 + `files`의 **모든 파일이 실제 존재**(없으면 그 포맷 미표시). datasheet·license·verified.
- **MPN은 데이터시트에 실존하는 주문 가능 품번 그대로** (2026-07, "B4B-XH" 사건 — 표시용으로 접미사를 잘라 비실존 품번을 만들었음). 축약·가공·추측 금지. 이름에도 전체 MPN 표기.

### F. 검증 (교차검증 — §5/§5-1, 한 방법만 X)
1. `python generators/validate_kicad.py` → PASS (구조).
2. `freecadcmd generators/validate_step.py` → PASS (CAD 커널).
3. **SVG 눈으로 확인**(풋프린트+심볼 각 1개 이상 브라우저 렌더) + **글자 겹침 검사 `check_overlap.py`**(텍스트 bbox 충돌 자동 검출 — 스크린샷 불가 시 필수, CI 게이트).
4. 사이트: 부품 렌더 + 뷰 탭 동작 + 다운로드 HTTP 200 + 콘솔 에러 0.
5. CI 게이트(validate_kicad) green = 배포 통과.
6. 치수 데이터시트/KiCad공식 대조 후에만 `verified:true`.

### G. 생성 파이프라인 순서 (새 패밀리)
1. `gen_connectors.py` (FAMILIES에 패밀리 config 추가) → 풋프린트/심볼/meta/통합 index
2. `freecadcmd generators/gen_connectors_3d.py` → STEP/STL
3. `stl_to_glb.py` → GLB
4. `render_svg.py` → SVG
5. `build_site.py` → 페이지/sitemap
6. F의 검증 → 커밋/배포 → sitemap을 Search Console 재제출

### H-0. 도면 판독 규칙 (2026-07-04, AHT10 원형 패드 사건)
데이터시트 도면을 읽을 때 **모든 그래픽 요소를 하나씩 열거·분류**할 것(패드/홀/마커/실크). 각 패드는 **모양(원/사각/오벌)까지 기록** — "패드는 다 같은 모양"이라고 가정 금지. AHT10은 1번 패드만 원형인데 이를 센서 벤트홀로 오독함(사용자 지적으로 발견). 본문 서술(예: "rounded portion...round solder mask opening")과 도면을 교차 대조.

### H. 알려진 함정 (오늘 겪음)
- **중첩 괄호 정규식**: `(stroke (width X) (type solid))`, `(name "x" (effects ...))` 파싱 시 `[^)]*` 쓰면 깨짐 → 비탐욕 `.*?` 사용.
- **"서빙됨 ≠ 유효함"**: HTTP 200은 파일 존재만 증명. 파서/CAD커널로 내용 검증 필수.
- **에셋 캐시**: JS/CSS 변경 시 `?v=` 버전 올릴 것(안 그러면 사용자/브라우저가 옛것 봄).

## 15. 확장 큐 (2026-06 수요∩갭 채굴 결과 — 순서대로 진행)

KiCad 기본에 없거나 빈약 + 검색 수요 큰 것. 각각 §14 품질기준 통과 + KiCad공식/데이터시트 대조 후 `verified`.
1. ✅ **USB-C 리셉터클 16핀** (TYPE-C-31-M-12) — gen_parts
2. ⏸️ USB-C 6핀 전원 — **보류**: KiCad 공식 풋프린트 없음(데이터시트 확보 후)
3. ✅ **ESP32-WROOM-32 모듈** — gen_parts
4. ✅ **microSD 소켓** (Hirose DM3AT) — gen_parts
5. ✅ **JST-GH 1.25mm** 2~12핀 — gen_smd_connectors
6. ✅ **스크류 터미널 5.08mm** 2~8극 (KF301) — gen_connectors(pad_shape=circle)

**→ 큐 완료(②만 보류). 현재 51부품.** 다음 확장: Search Console 데이터로 우선순위 결정.

구조: 일회성(1~4)은 `generators/gen_parts.py`(부품별 함수), 파라메트릭 패밀리(5)는 gen_connectors FAMILIES, 터미널(6)은 별도.

**전략 정정(2026-06): SEO 플레이 확정.** KiCad 기본 라이브러리가 common 부품(USB-C/JST/FFC/헤더/터미널/ESP32-WROOM 등)을 이미 광범위하게 가짐 → "KiCad에 없는 것"이라는 순수 갭은 작음. 따라서 차별점은 **갭이 아니라 "로그인 없음 + 심볼·풋프린트·3D 번들 + 3D프리뷰 + SEO 랭킹"**(=SnapEDA 모델). 고검색 부품을 KiCad 중복이어도 만들어 검색 유입을 잡는다. 진짜 롱테일 MPN은 보조. (index.json은 `build_index.py`가 library/ 스캔으로 생성 — 다중 소스 통합.)

## 16. 자동 품질 게이트 (매 배포 자동 — 사용자 수동 확인 불필요)

한 명령: **`python generators/qa.py`**. CI(`deploy.yml`)가 push마다 실행, **하나라도 실패하면 배포 차단**.

| 게이트 | 잡는 것 | 겪었던 버그 |
|---|---|---|
| `validate_kicad.py` | 구조: 패드 수·번호·1번핀 원점·피치·레이어 (행검사는 피치 있을 때만) | 잘못된 패드 배치, XH 피치 |
| `check_overlap.py` | 심볼/풋프린트 텍스트 bbox 겹침 | "1" 겹침, 오른쪽 핀 이름 삐짐 |
| `check_render.py` | 렌더 완전성: 파일존재 / 동판패드수 일치 / 외곽선수 일치 / **슬롯 obround(`<ellipse>` 금지)** / 심볼 핀수 일치 | 외곽선 안그려짐, SMD패드 누락, UFO 슬롯, 파일누락 |
| `validate_step.py` (로컬, FreeCAD) | STEP 솔리드 유효성(isValid/부피) | 깨진 솔리드 |

**규칙: 새로운 버그 클래스를 만나면 → 그 검사를 위 스크립트에 1회 추가** → 이후 영구 자동 검출. 사용자가 매번 눈으로 검수할 필요 없음(게이트가 막음).

## 17. PartReel 2.0 — AI-네이티브 레지스트리 (확정 2026-06)

**비전**: 사람이 사이트에서 다운받는 모델(SnapEDA식)은 구세대. 앞으로 소비자는 **AI 에이전트**다. 에이전트가 ①검증된 부품을 조회/재사용(매번 재생성=낭비) ②사용 피드백을 기록(실보드 검증 이력=해자) ③없는 부품은 생성해서 기여(우리 QA 게이트가 심사관)하는 **부품 레지스트리**로 전환. "npm/PyPI의 CAD 부품판, 소비자는 AI".

**확정 결정**:
- **모델 = 하이브리드**: 기여는 오픈(누구나/에이전트), 등록은 **자동 게이트 심사**(qa.py, GitHub PR→CI→머지=등록, 무서버 유지). 신뢰 등급(unverified→gates-passed→field-proven).
- **접근 3계층**: ①웹(사람용 뷰어/SEO — 기존 사이트 유지, 검증이력 표시 추가) ②**HTTP API**(모든 AI가 fetch 가능, 정적 JSON) ③**MCP 서버**(딥 통합, 리모트 URL 등록만 — 설치 불필요. Cloudflare Workers 예정).
- **수익**: 개인 무료 원칙 유지(성장 엔진). 돈은 **신뢰·편의·대량**에서 — API/MCP 유료 티어(대량 호출), 제조사 검증 배지, 프라이빗 레지스트리, 에이전트 경유 어필리에이트. 데이터는 공짜가 되지만(AI가 만드니까) **"검증됐다는 보증"은 공짜가 안 됨** — 이걸 판다.
- 피드백 신뢰: 초기엔 GitHub 계정 기반(PR/이슈)로 신원·이력 묶음.

**로드맵**: ①✅정적 HTTP API + llms.txt + /api/ 문서 → ②✅**리모트 MCP 서버 v1 라이브** — `https://mcp.partreel.com/mcp` (CF Workers, `mcp/worker.js` 의존성0 stateless Streamable HTTP, 도구 search_parts/get_part/list_parts, 정적 API를 읽는 얇은 어댑터. 배포: `cd mcp && npx wrangler deploy`, 계정 mingyo186@gmail.com 인증됨. 프로토콜 검증: initialize/tools_list/search/get + 다운로드 URL 200) → ③피드백 경로(GitHub 이슈 템플릿→배지) → ④기여 경로(PR 템플릿+게이트 문서화) → ⑤유료 티어.
클라이언트 등록: `claude mcp add --transport http partreel https://mcp.partreel.com/mcp`

**AI 발견(discovery) 전략** (2026-07 확정): 만들어도 에이전트가 저절로 오지 않음 — 두 갈래.
1. **온사이트(봇용 가이드)**: robots.txt에 AI 크롤러 명시 환영 + llms.txt 위치 주석 · **/agents/ 에이전트 가이드 페이지**(MCP/API 사용법 + **복붙용 가이드 프롬프트**: 사용자가 자기 CLAUDE.md/.cursorrules에 붙여넣으면 그 에이전트가 부품 필요시 PartReel을 조회하게 됨 = 배포형 성장 루프) · **부품 페이지마다 "AI로 사용" 힌트**(크롤러가 부품 페이지에 왔다가 API/MCP 존재를 학습).
2. **외부 등록**: ✅공식 MCP 레지스트리(io.github.mingyo186/partreel v1.0.0 active) · ✅awesome-mcp-servers PR #9156(머지 대기, 안 돼도 무방) · 잔여: Smithery/mcp.so/PulseMCP.

**생태계 루프 (2026-07 확정)** — 남의 목록 의존 대신 우리가 허브가 된다. 핵심 = AI가 읽기만 하는 곳이 아니라 **남기고 가는 곳**(피드백/기여 쓰기 경로 = 재방문 이유 = 네트워크 효과 = 복제 불가 해자):
- **③ MCP 쓰기 도구**: `report_feedback(part_id, result, notes)` — 워커가 GitHub 이슈로 기록(이슈 전용 fine-grained PAT를 CF 워커 시크릿 `GITHUB_TOKEN`으로; 라벨 `field-report`). `how_to_contribute` 도구 — 기여 방법을 기계용 포맷으로 반환.
- **④ 기여 경로 ✅(E2E 검증 2026-07-04)**: `CONTRIBUTING-AGENTS.md` + **pr-gates.yml — 모든 PR을 동일 게이트로 자동 심사**(구조/겹침/렌더/메타완결성/STEP커널). 불량 기여 테스트(PR #2, 패드 삭제)를 게이트가 정확히 거부함. 머지=게시.
- **⑥ 자가수정 루프 (사용자 확정 2026-07-04, "이슈를 일일이 못 본다 — 가이드 주고 상대 봇이 고치게")**: problem 리포트가 열리면 **GitHub Actions가 자동으로 수정 가이드 코멘트**(부품 소스 위치, provenance API 링크, 데이터시트 인용 요구, PR→CI 게이트 자동심사 안내)를 남김 → 신고한 봇/사람이 직접 PR로 수정 → 게이트 green → **메인테이너는 머지 클릭만**. 사람 개입 최소화; 자동머지는 보류(라이선스/스팸 리스크 — 게이트 신뢰 쌓이면 재검토). worked 리포트엔 감사 코멘트.
- **⑤ 신뢰 표시 ✅(2026-07-04)**: 부품별 `field_reports` → API 필드 + **사이트 배지**(part.js가 부품 API를 읽어 worked/problem>0일 때만 표시). **사람 피드백 경로 ✅**: 부품 페이지 "Field reports" 섹션에 원클릭 GitHub 이슈 링크(✅worked/⚠problem, 프리필 제목) + **이슈 폼 템플릿**(.github/ISSUE_TEMPLATE — 폼이 라벨을 자동 부착하므로 권한 없는 사용자도 라벨 보장; URL labels 파라미터는 콜라보레이터만 적용되는 함정 회피).

### 19-A. 분산 생성 전환 (사용자 확정 2026-07-26 "모든 각자의 AI가 움직이는 걸 원했다")

**방향**: "요청하면 우리가 만들어주는" 중앙 생성에서 → **"각자의 AI가 만들어 PR로 가져오면 우리는 게이트로 검증·등록·배포만 하는"** 분산 생성으로. 우리 역할 = 공장이 아니라 등기소(레지스트리 본연). 근거: 중앙 생성은 우리 컴퓨팅·템플릿에 갇히고, 분산은 무한 확장 + §1-0 모으기>만들기의 완성형.
- 이미 있음: pr-gates.yml (외부 PR 자동 게이트), 기여 크레딧(21-B), Reported-by 관행.
- **할 일**: 에이전트용 기여 명세 — agents 페이지 + llms.txt에 부품 디렉토리 구조·meta.json 스키마·게이트 목록·PR 절차를 기계가독형으로 + 완전한 예시 부품 1개. "Make a part and PR it to PartReel"이 한 문장 프롬프트로 성립해야 함.
- request_part(중앙 생성)는 간단 규격품용 보조로 유지.
- **표준 답변 확정 (사용자 2026-07-26 "다음부턴 그냥 3번째 방법만")**: "없는 부품 어떻게 얻냐"는 질문에는 **분산 생성 한 가지만 안내한다** — 표준 문구는 "만들어라"가 아니라 **"한 줄 복붙"** 프레임 (사용자 교정 2026-07-26 — 떠넘기기로 읽히면 안 됨): "쓰시는 AI에 이 한 줄만 붙여넣으세요: 'Fetch CONTRIBUTING-AGENTS.md and build <MPN>, then open a PR' — 그게 전부. CI가 자동 심사하고, 병합되면 본인 포함 누구나 다운로드." 이슈·request_part는 AI 없다는 사람에게만 차선. 이 답 자체가 파트릴의 정체성 선언. **답글에 "여기 요청 주면 계속 만들어준다" 류 문구 금지** (사용자 2026-07-28) — 우리가 계속 만들어주는 건 분산 생성 방향에 역행; 원-프롬프트 안내로 끝낸다.

## 19. 온디맨드 셀프-그로잉 레지스트리 (확정 2026-07)

**원칙(사용자)**: 파라메트릭 부품(핀헤더 등)은 **우리가 사전 대량생성하지 않는다** — 필요한 사용자/에이전트가 요청 순간에 뽑아 쓰게 한다. 단, **생성 결과는 반드시 레지스트리에 영구 등록**된다(로컬 생성이면 카탈로그·SEO·재사용에 안 쌓임). 효과: 카탈로그가 실수요 순서로 성장(§4 수요기반 원칙 일치, 얇은 대량 페이지 SEO 리스크 회피), 재생성 낭비 0, 서버 0 유지.

**흐름**: `get_part(없음)` → MCP `request_part(family, pins)` → 워커가 GitHub `repository_dispatch` → **GitHub Actions가 생성기 실행**(텍스트→FreeCAD 3D→GLB→SVG→index/site/api) → QA 게이트 → **자동 커밋+인라인 배포**(주의: GITHUB_TOKEN 푸시는 deploy.yml을 안 깨우므로 생성 워크플로가 배포까지 인라인 수행) → 몇 분 뒤 라이브 → 요청자에게 예상 id/URL 반환.

**구성요소**: `gen_connectors.py`의 `ONDEMAND` 패밀리(핀헤더 2.54/2.0/1.27mm, 1~40핀 — 치수는 KiCad 공식 대조) · `generators/generate_one.py`(단일 부품 오케스트레이터, env FAMILY/PINS) · `.github/workflows/generate-part.yml`(repository_dispatch type=generate-part) · MCP `request_part`(허용 패밀리·범위 검증 후 dispatch; 토큰 fine-grained PAT에 Issues+Contents R/W — 권한 수정해도 토큰 값 불변).

⚠️ **온디맨드 채널 고장 사건 (발견 2026-07-24, "커밋에 문제 없냐" 점검 중)**: R2 이전(§22, 7-11) 이후 repository_dispatch 생성 런 전패(7-17/7-20/7-24, 실요청 pin_header_254_8pin 포함). 원인 2중:
① **CRLF 해시 불일치 112개** — `.gitattributes` 부재로 Windows 커밋 시 git이 텍스트인 .step의 CRLF→LF 정규화. meta.asset_sha256은 로컬(CRLF) 기준, CI 체크아웃은 LF → check_asset_hashes FAIL. **수정**: `.gitattributes`에 `*.step -text` 등 바이너리 취급 + `git add --renormalize`로 블롭을 로컬 바이트(CRLF)와 일치시킴(로컬·meta·R2 모두 CRLF라 블롭만 맞추면 3자 일치 — 재해시·재업로드 불필요). **교훈: 해시로 보증하는 파일은 git eol 변환 금지 대상.**
② **주문형 파이프라인이 R2 시대 미대응** — 새 step/glb의 asset_sha256 미기록(check_render "해시 미기록" FAIL) + CI에 R2 업로드 크리덴셜 없음(업로드해도 못 올림 → 다운로드 링크 404). **수정**: generate_one.py에 sync_r2 --hash 단계 추가; 워크플로에 R2 업로드 단계(시크릿 `R2_WRANGLER_TOKEN` 필요 — **사용자 액션 대기**, 시크릿 등록 전까지 CI 채널은 명시적 실패 유지). 밀린 요청(pin_header_254_8pin)은 로컬 생성→R2 동기화→정규 배포로 이행.

✅ **E2E 검증 완료(2026-07-04)**: MCP request_part(pin_header_254,7) → CI 생성(micromamba/conda-forge freecad+trimesh+scipy, ~1분!) → 게이트 → 봇 커밋 → 인라인 배포 → **/p/pin_header_254_7pin/ 라이브(53부품)**. 트러블슈팅 기록: ①apt에 freecad 없음(noble)→conda-forge ②trimesh가 scipy 요구 ③**배포 레이스**: generate-part와 deploy.yml이 다른 concurrency 그룹이라 옛 콘텐츠가 이길 수 있음→둘 다 `group: pages`로 직렬화. ④**인라인 배포 "성공 보고 후 미반영"(2026-07-04 ht7330)**: Pages가 success 보고하고도 구버전 서빙(+간헐 오류 동반) → generate-part에 **Verify live 단계**(부품 API 200 폴링 3분, 실패 시 런 red — deploy.yml 수동 재실행 신호). 변형 패밀리 E2E: MCP request_part(ht73xx,7330)→CI 성공→(배포 이슈 복구 후) 라이브 = **95부품**.

## 20. 런칭 보류 + 봇 기반 우선 (사용자 확정 2026-07-04)

**커뮤니티 런칭(KiCad포럼/r.KiCad/ShowHN)은 구글 색인이 차오른 뒤로 보류.** 그때까지 우선순위 = **봇(에이전트)이 원활하게 활동할 기반**:
1. **CI 파생물 자동 빌드**: deploy/pr-gates가 index→svg→site→api를 자동 생성 — 기여자(봇)는 원천 5파일(kicad_mod/sym/step/glb/meta)만 제출. (사람이 build_site 깜빡하는 실수 클래스도 소멸)
2. **field_reports를 API에 노출**(§17-⑤): CI가 GitHub 이슈(label:field-report)를 집계해 부품 API에 `field_reports:{worked,problem}` — 봇이 신뢰 신호를 기계로 읽음.
3. CONTRIBUTING-AGENTS 요구사항 완화 반영.

## 21. 확장 기준 = 공식 라이브러리 갭 (사용자 확정 2026-07-04)

**근거 — 블라인드 실험(2026-07-04)**: 백지 에이전트 2명에게 부품 획득 과제(JST GH 6핀, 1x37 핀헤더) → 둘 다 **KiCad 공식 GitLab 직행**, 몇 분 내 완료, PartReel 미등장. SnapEDA류는 로그인벽으로 즉시 거절. **1x37 핀헤더도 공식에 풋프린트+심볼+3D 전부 존재**(1~40핀 전 구간) → 온디맨드 핀헤더는 차별화 아님(§19 구조 자체는 유지 — 가치는 공식에 없는 패밀리에서만 발생).

**결론**: 공식에 있는 부품으로는 에이전트가 절대 안 온다. §15의 "중복이라도 SEO" 정정을 재정정 — **확장 우선순위 = "공식 라이브러리에 없는 부품" ∩ 수요**. 에이전트가 막히는 유일한 순간(공식에 없음 + SnapEDA 로그인벽)이 우리 유입 지점. 기존 53개 = 신뢰구축용(기계검증 증명), 유입용 아님.

**실행**:
1. ✅**갭 리스트 채굴 완료(2026-07-04)** → **`docs/gap-list.md`** (확정 갭 10순위 + 제외 목록 + 방법론). 확장은 이 리스트 순서로. **채굴 방법론(교훈)**: ①갭 판정은 **GitLab master 기준**(kicad.github.io는 릴리즈 스냅샷 — 1차 조사 톱10 중 8개가 이것 때문에 오탐) ②비직관적 배치 주의(INA219→Sensor_Energy, DHT22→AM2302 등 — 이름검색 한 곳만 보면 거짓 부재) ③오픈 MR 확인(활성 MR=곧 닫힐 갭이니 제외, 수년 방치 MR=공식 무관심 영역=기회) ④착수 직전 master 재확인. 확정 1착: **AHT20 온습도 가족**(심볼+풋프린트+3D 전부 부재, 수요 최상).
2. **에이전트 페인포인트 정면 마케팅**: 블라인드 실험에서 에이전트가 직접 불평한 것 = 우리가 이미 가진 것 → 색인용 페이지/llms.txt에 명시: ①부품별 개별 심볼 파일(공식은 6.7MB 통짜) ②풋프린트↔심볼 매핑 기계가독(meta.json) ③부품별 안정 permalink(공식은 태그/브랜치 404 함정) ④로그인·인증 0 API.
3. **핀헤더 온디맨드 강등**: 유지하되 차별화 포인트에서 제외. 온디맨드 패밀리 추가는 갭 리스트 기반으로만.
4. **배치 확장 20종 (사용자 확정 2026-07-04, "3개는 너무 적다 — 20개 만들고 검토")**: 갭 리스트 순위대로 일괄 생성 후 일괄 검토. 대상(전부 master 부재 확인, 방치 MR 포함=공식 무관심 영역): ①QMC5883L(LGA-16) ②HMC5883L(LCC-16) ③TTP223 SOT-23-6 ④IP5306(ESOP-8) ⑤TP5100(ESOP-8) ⑥CN3791(SSOP-10) ⑦MP1584EN(SOIC-8) ⑧SY8008(SOT-23) ⑨SY8089(SOT-23) ⑩HT7333(SOT-89) ⑪HT7833(SOT-89) ⑫ADXL345(LGA-14) ⑬A4988(QFN-28) ⑭W25Q64JV(SOIC-8 208mil, MR 2022 방치) ⑮DRV8825(HTSSOP-28, MR 방치) ⑯SSD1306 0.96" I2C 모듈 ⑰SH1106 1.3" 모듈 ⑱ST7789 1.3" 모듈(⚠️모듈류=대표 벤더 도면 명시) ⑲⑳TTP229/GX16 등 데이터시트 확보 여부로 확정. **표준 패키지(SOT/SOIC/ESOP/LGA/QFN) 공용 생성 헬퍼**를 만들어 재사용(§21 중복제거 방향의 첫 적용) — 단 치수는 부품별 데이터시트 권장 랜드패턴 우선, 없으면 패키지 도면+IPC. 각 부품 §14 전체 기준 + H-0 도면판독 규칙 적용.

5. **AI 발견 4종 세트 (사용자 확정 2026-07-04, "색인만으론 부족")**: 블라인드 실험 재분석 결과 색인은 필요조건일 뿐. ①**GitHub 검색성** — 에이전트 실동선은 구글이 아니라 GitHub/GitLab 코드검색: 레포 topics·설명·README 부품 인덱스(자동생성, build_readme.py)로 부품명 검색이 레포에 걸리게. ②**provenance 공개** — 도착 후 5초 신뢰: 부품 API에 기계가독 provenance(치수 출처, 게이트 목록, CI 강제 사실, 생성기 소스 링크) 노출. 자가생성 폴백(에이전트가 검색 대신 직접 생성)을 멈추는 건 "검증 과정을 직접 확인 가능"뿐. ③색인 — **정적 둘러보기 페이지 신설(2026-07-10)**: Search Console 실측 = 사이트맵으로 13,950p 발견됐으나 **색인 2p뿐**. 원인: 홈이 SPA(JS 목록)라 크롤러가 부품으로 가는 HTML 링크를 못 봄 → 사이트맵 외 유입 경로 0인 "외딴 페이지"로 취급. 대책: `/browse/`(카테고리)→`/browse/<cat>/`(패밀리)→`/browse/<cat>/<fam>/`(부품 링크 전체)의 일반 `<a>` 링크 허브 + 부품 페이지 빵부스러기의 패밀리를 해당 browse 페이지로 링크(양방향 그물) + 홈에 정적 카테고리 링크 + 사이트맵에 browse 포함. (기존 문구: 색인 진행 중, 사이트맵 79p) ④**인용 축적** — §20 런칭의 진짜 기능 = 차세대 모델 훈련 데이터 진입(색인 성숙 후).

6. **스케일 전환 (사용자 확정 2026-07-04, "이 정도 부품으로 되겠어?" → 수정: "종류가 많아야 봇들의 확장에 도움")**: 93개는 시드. **역할 분담 확정**: **손 = 새 종류**(새 패키지/패밀리 = 봇이 확장할 템플릿), **봇 = 변형**(순수 config 변형은 손으로 안 만듦 — §19 온디맨드 일반화 + config 한 줄 PR 레시피; 변형 페이지는 중복콘텐츠 리스크도 있음), **수입 = 규모**(종류 폭의 본명). 실행: ⓐ순수 변형(LDO 전압 12종·SY 등급·MAX17049)은 request_part **변형 패밀리 온디맨드**로 (ht73xx/ht78xx/sy8008/max1704x — 조사로 실존 품번 검증 완료: docs/gap-list.md) ⓑ배치 4차 = **진짜 새 종류만** ~14종 (QMC5883P·DHT20·AHT25·AHT30·TP4054·TM1638·TTP224/226·디스플레이 모듈 7종) ⓒ**SparkFun 수입 파일럿 착수 (사용자 "추천대로 진행" 2026-07-05)** — 결정: ①수입품 meta에 `origin:"imported"` + `import`(source_repo/commit/파일/attribution/수정목록), verified=게이트통과 의미 유지 ②패시브(저항/캐패시터 값변형) 제외 ③파일럿 GLB는 단색(중립 그레이, 메시명 "imported" — merged-pins 게이트는 metal 메시에만 적용되므로 자연 면제) ④코트야드 부재 시 자동 생성(패드+팹 bbox+0.25, 수정목록 기록); 실크 부재분은 파일럿에서 드롭(게이트 완화 대신 — 로그 기록) ⑤명명 sparkfun_<slug>, 1차 물결 = Sensor·GNSS·RF·커넥터(패시브/Aesthetic/멀티유닛 제외) ⑥소스 커밋 고정 2423e36a, ATTRIBUTIONS.md 신설 ⑦STEP→GLB는 신규 step_to_glb 경로(FreeCAD 테셀레이션). 파이프라인 오프라인 실행(CI는 기존 qa만). 상세: scratchpad sparkfun/PILOT_PLAN.md.
**수입 확대 (사용자 확정 2026-07-05, "무료를 더 끌어쓰자 — 이름만 남기면 됨 + 저쪽엔 에이전트 전용 공간이 없다")**: 허용적 라이선스 라이브러리를 계속 수입 — 가치는 복사가 아니라 **에이전트-네이티브 승격**(부품별 API/MCP/번들/게이트/provenance/피드백 — 원 레포들엔 전무). 순서: ①**CERN Wave 0 착수** (~425: Crystals+LEMO; 시나리오 C=메타+에셋 Pages 내, R2는 Wave 2 전 별도 확인; verified-2D 등급=3D 없는 부품은 files에서 step/glb 제외+페이지 3D탭 숨김; GENERIC 3,324 제외; NRND는 수명주기 표기; 멀티유닛은 Wave 0 스킵 — docs/cern-import-plan.md) — **Wave 0 완료 (2026-07-05)**: 425 대상 → 수입 423 → 게이트 후 **318 배포** (탈락 105 = 렌더러 지오메트리 갭 104 + 오버랩 1, docs/import-cern-wave0-dropped.json; 스킵 2 = 멀티유닛/참조부재, docs/import-cern-wave0-log.json). 산출: import_cern.py(sqlite 진실원, 균형괄호 model 제거 — §14-H 재확인, fp_poly 포함 자동 코트야드), verified-2D 등급 구현(validate_step/check_zfight 면제, 3D탭 숨김+풋프린트 기본, part.js v8, API `tier` 필드), check_render 라이선스 허용목록 {CC-BY-4.0, CERN-OHL-P-2.0} (수입품 원 라이선스 유지 + 자체생성은 CC-BY-4.0 강제 유지), ATTRIBUTIONS.md CERN 절 + LICENSES/CERN-OHL-P-2.0.txt (§3.1/§3.3 수정고지+날짜=meta.import). 라이브 검증: 545부품(cern 318), 페이지/kicad_mod/API 200. Wave 1 전 과제: ~~렌더러 폴리곤 지오메트리 104종~~ **해결(2026-07-05 렌더러 업그레이드)**: render_svg 심볼에 polyline/circle/arc(3점→SVG A 패스)/다중 rectangle/pin_numbers·names hide 플래그/스택핀 병합("9-12") 지원 + check_render 핀카운트 스택인지(고유 위치·각도) → **CERN 423 전량 배포 (감쇠 0), 총 803부품**. **멀티유닛 심볼 지원 완료(2026-07-05)**: render_svg 유닛 분리 렌더(가로 배치+A/B 라벨, 유닛0 도형=매 유닛·핀=첫 유닛만, 핀 전용 유닛=본체 합성) + check_render 유닛 인지 핀카운트(렌더러와 _unit_blocks 공유=단일 진실원) + check_overlap `<g translate>` 인지. ACF2101BU(듀얼 op-amp)/RN DIL16 15xR(유닛0 공통핀)/100ELT22로 시각 검증. import_cern 멀티유닛 스킵 해제 → Wave 0 = **425/425 전량, 총 805부품**. CERN 멀티유닛 1,765심볼(커넥터 540, 로직 441, 릴레이 184, op-amp 105...) 수입 가능해짐. 남은 Wave 1/2 과제: **R2 활성화(사용자 대시보드 액션 대기)** — 공유 패키지 스키마는 R2 후 재평가(창고 이전으로 용량 압박 해소 시 우선순위 하락). — **Wave 1 완료 (2026-07-05)**: 벤더 커넥터 15테이블 4,327 대상 → 4,321 수입 → 98 드롭(패드 없는 기구 액세서리 95+기타 3, docs/import-cern-wave1-dropped.json) → **4,223 배포 = 총 5,028부품 라이브** (cern 4,648). socket 카테고리 신설, import_cern CERN_WAVE 파라미터화, 멀티유닛 포함, 풋프린트 텍스트는 git 유지(검색·게이트·이력 — §22 미결 해소: 사용자 문답으로 확정). **Wave 2 완료 (2026-07-05)**: IC 10테이블 8,984 → 8,966 수입(스킵 18) → 48 드롭(0.5%: 핀/패드 특이형·겹침, docs/import-cern-wave2-dropped.json) → **8,918 배포 = 총 13,946부품 라이브**(cern 13,566). ic/power/discrete 카테고리, 멀티유닛 op-amp 프로덕션 검증(ADA4000-4AR 4유닛 A-D 렌더). **Wave 3 착수(2026-07-10, 사용자 승인)**: 브랜드 패시브(R/C/L/네트워크/서미스터/포텐셔미터)+릴레이+퓨즈+스위치+트랜스포머 17테이블 7,767행 중 GENERIC(주문불가 품번) 3,320 제외 → 4,447 대상. 카테고리: passive/relay/fuse/switch/transformer. GENERIC 필터는 임포터 전역 적용(§7-4 결정). 잔여: Wave 4 결정류(GENERIC·기계류·Obsolete 정책). **렌더 품질 사건(2026-07-05, 사용자 3M MDR 페이지 지적)**: ①KiCad9 멀티라인 fp_line을 렌더러가 미매칭(252선 누락)+**게이트가 같은 방식으로 세서 통과** — 검사기·피검사자가 맹점 공유 시 게이트 무력화. 수정=균형블록 파서 iter_fp_lines를 렌더러·게이트가 공유(단일 진실원) ②Cmts/Dwgs 문서 레이어 흐림 렌더 추가(벤더 셸 외곽선) ③심볼 bezier 지원 ④수입품 데이터시트 라벨 정직화(소스레포 링크는 provenance로, 주 버튼=제조사+MPN 검색). 표본감사: 무작위 15 대조 → 12 PASS/3 DEVIATION/0 FAIL(docs/import-audit-sample.md). 파라메트릭 3D 백필(IPC명→패키지 생성기 ~6종, verified-2D→풀3D 승격)은 별도 트랙. ②~~CDFER/JLCPCB MIT 라이브러리~~ — **스팟체크 탈락(2026-07-05)**: 풋프린트 62/118=LCSC 변환물(테이크다운 리스크)+35/118=KiCad 공식 산출물의 MIT 재표기(재라이선스 무효 의심) → 수입 제외, 상세 docs/import-audit.md ③ai03 MX 스위치 — **Wave A 완료(2026-07-05)**: 153부품 전량 게이트 통과·배포 = **698부품 라이브** (switch 카테고리 신설, 구포맷 fp_line 신포맷 정규화+레이어 인용 정규화 임포터 내장, 도형요소 줄단위 분리 — check_render 줄단위 카운트 요구). 스팟체크 상세: 구 MX_Alps_Hybrid는 deprecated → 후속작 MX_V2(MIT, "designed from scratch from datasheets", 갭 확인=공식은 MX PCB/Plate+Matias 29종뿐이라 핫스왑·Gateron KS33·Choc V2·하이브리드 전부 갭). Wave A=153fp(스태빌라이저 21=기계전용 스키마 필요로 보류, Template 8 제외), 심볼은 우리가 저작(SW/LED 2핀), Dwgs.User→F.Fab 재매핑+실크 핀1 마커+자동 코트야드(기록), 전량 verified-2D, 라이선스 MIT 유지+허용목록 추가 — 상세 docs/ai03-import-plan.md ④SA 섹션 = **보류 확정(사용자 2026-07-05)**: 부품 수백 개 얻자고 '우리 부품은 조건 안 따져도 됨'이라는 단일 라이선스 단순함을 깨는 건 손해. Espressif급 인기 부품은 치수-사실 자체 생성으로 커버. 갭이 실제로 남으면 재론.

**중기 방향(사용자 2026-07-04)**:
- **검증-수입(verified import)**: 규모가 커지면 기존 오픈 자산(타 라이브러리/기여물)을 **우리 게이트로 검증해서 들여온다** — 처음부터 만드는 것보다 싸고, "검증됐다는 보증"이 우리 부가가치(§17 수익 원칙과 일치). 라이선스 호환 필수(CC-BY-SA는 카피 불가 — §14 규칙 유지, 치수=사실만 추출).
- **풋프린트 중복 제거/재활용**: 풋프린트·3D는 패키지(SOT-23, 0603, SOIC-8...) 단위로 중복이 극심 → **부품→공유 패키지 참조 구조**로 리소스·용량 절약(같은 SOIC-8을 부품마다 복제하지 않음). 스토리지뿐 아니라 검증도 패키지 1회로 끝남. 카탈로그가 커지기 전에 스키마에 반영할 것.

### 21-C. 생성 도구 산출물 판정 규칙 (사용자 확정 2026-07-26 "노르딕은 GO로 진행해라")

`kicad-footprint-generator` 등 생성 도구로 만든 풋프린트의 수입 가부:
- **허용**: 저작자가 **자기 치수 입력**으로 도구를 돌린 것 (증거: 데이터시트 기반 치수 기록, 공식 라이브러리와 이름 충돌 없음, 도구를 자체 포크/패치해서 운용). 도구 사용은 저작이다. → nordic-lib-kicad GO 근거.
- **거부**: 공식 KiCad 라이브러리 **산출물의 바이트 카피**를 재라이선스한 것 (CDFER 탈락 근거, Keebio의 ipc 생성기 파일 5개도 동일).
- 판단 기준은 "누가 돌렸나"가 아니라 "입력이 누구 것인가".

다음 물결 소스 감사: docs/next-wave-sources.md (2026-07-26, GO 8곳 ~3,000-5,500 잠재). 1차 실행 = nordic-lib-kicad (사용자 GO), 나머지는 색인 신호 후.

**NEAR/IDENTICAL 풋프린트 대체 수입 (2026-07-27)**: Antmicro 물결 프리스킵 199 중 **139개**가 패시브 풋프린트 4종(C_0402/D_0402/L_0402_1005Metric, C_1206_3216Metric) 때문 — 이 4종은 KiCad 공식과 **파일명까지 동일 + 지오메트리 편차 0.01~0.05mm** = 구버전 공식 카피로 판정, 파일 제외 유지. 부품 자체(심볼·3D·메타)는 Apache-2.0으로 문제없으므로 **풋프린트만 우리가 자체 생성해 교체 수입**한다:
- 랜드패턴 수치 = IPC-7351 밀도 레벨 B(공칭), 출처 KEMET C1002 X7R SMD 카탈로그 Table 3 (1005: 패드 0.62×0.62·간격 0.45·코트야드 1.90×1.00 / 3216: 패드 1.15×1.80·간격 1.50·코트야드 4.70×2.30). 치수=사실, 우리 입력으로 우리가 생성 = 우리 저작(§21-C 원칙 "입력이 누구 것인가"와 일치).
- provenance: meta `import.modifications`에 교체 사실 명시. 교차검증: 생성 풋프린트를 check_provenance로 돌려 공식 대비 **DIFFERENT 판정 확인** 후 수입.

**2차 완료 (2026-07-31)**: 잔여 60 중 **34개 복구** (generators/pkg_land.py — 제조사 데이터시트 권장 랜드패턴 8종: TI TSSOP-14·QFN-24, Microchip VQFN-16, Vishay PowerPAK 1212-8, 2520 인덕터는 TDK/Bourns/Murata-DFE/Murata-LQM 4분할 — 권장 패턴이 상반되어 원본의 범용 단일 풋프린트보다 개선). 치수는 서브에이전트가 데이터시트 도면을 텍스트+고배율 렌더+**PDF 벡터 실측** 3중 검증으로 추출, 전건 DIFFERENT 확인. 총 21,657 라이브. 잔여 26 = 소량 롱테일(LQFP-144 3, X2QFN 3, DFN 4, TSOP-II 2, 기타 1~2개짜리) — 공수 대비 보류, 수요 신호 시 같은 방법으로.

**3D GLB LOD2 결함 전수 수리 + 면 수 손실 게이트 (2026-08-09, 사용자 제보 → 8e81020 단건 수리의 전수 확장)**: 수입기가 웹 경량화로 LOD2를 우선 변환했는데, LOD2는 과감한 데시메이션이라 소형 칩 부품의 금속 단자가 뭉개진다 (c3216: LOD2 28면 vs 원본 136면 — "끝부분 깨짐" 제보; LOD2 변환본과 깨진 배포본이 바이트 일치로 원인 확정 — 당초 심링크 가설은 교차검증에서 기각). 조치:
- 4KB 미만 antmicro GLB 955개 전수: 업스트림 원본(비LOD) gltf+bin으로 재변환, **면 수가 늘어난 것만 교체** + `asset_sha256` 갱신 + R2 덮어쓰기.
- 수입기(import_antmicro)는 이후 **원본(비LOD)만 변환** — LOD2/LOD1 우선순위 제거. 원본도 칩 부품 ~9KB 수준이라 웹 부담 없음. 심링크 텍스트(Windows·raw 응답)는 상대경로 해석으로 따라감.
- meta `import.source_faces`에 업스트림 원본 면 수 기록 (이번 수리분부터).
- 게이트 `check_glb_faces.py` (qa 편입): GLB 실제 면 수 < `import.source_faces` 이면 FAIL. '업스트림 대비 손실' 기준이므로 원래 면이 적은 정상 단순 박스는 오탐 없음 (§16 새 게이트는 전체 카탈로그 오탐 확인 후 푸시).
- 잔여: 4KB 이상 antmicro GLB 1,216개도 LOD2 유래 — 시각 결함 신호 시 같은 방법으로 확장 (source_faces 미기록이라 게이트 대상 아님).

### 21-D. 기존 부품 3D 업그레이드 기여 경로 (2026-07-30 — 사용자 타컴퓨터 STEP 기여 시도가 명세 공백으로 거부된 사건)

verified-2d 부품(1.8만+)에 외부가 STEP을 얹는 기여 = 우리가 가장 원하는 백필. 경로:
1. **기여물**: `library/**/<id>/<id>.step` 추가 + 같은 부품 `meta.json` 3곳 수정 — `files.step`, `formats`에 "step" 추가, `asset_sha256`에 STEP의 sha256 기록(기여자가 계산 = "이 커밋이 보증하는 파일" 원칙 유지).
2. **PR 게이트**: 기존 조건부 FreeCAD isValid 검사(steps!=0)가 커널 검증, check_asset_hashes(스코프 지원 추가)가 해시 일치 검증. R2 검사는 PR에서 안 돎(머지 전 미업로드가 정상).
3. **머지 후**: deploy.yml이 **누락 기반 전량 대조**(스코프 없는 `sync_r2 --upload` — 체크아웃에 존재하는 git 추적 step/glb 전체를 R2와 대조, 없는 것만 병렬 업로드) 후 check_r2 게이트 통과 시 배포 → 다운로드 링크 즉시 유효. (2026-08-06 전환 — 이전 방식 "직전 커밋 diff 감지"는 concurrency 취소 시 영구 누락: 2026-08-05 사건, §22)
4. **tier**: STEP만으로는 verified-2d 유지(웹 3D 미리보기는 GLB 필요) — GLB 변환·승격은 우리 배치(stl_to_glb)로 후처리. STEP 다운로드 버튼은 즉시 제공.
5. 같은 계정(쓰기 권한) 머신은 포크 불가 → 브랜치 푸시로 PR (CONTRIBUTING에 명시).

외부 제보(버그·품질 지적)로 수정이 이뤄지면 제보자를 영구 기록한다 — 오픈 프로젝트에서 제보는 코드만큼의 기여:
1. **커밋 트레일러**: 제보 기반 수정 커밋에 `Reported-by: <플랫폼> <핸들>` (리눅스 커널 관행). 예: `Reported-by: reddit u/asdfasdferqv`.
2. **CREDITS.md** (레포 루트): 제보자·내용·수정 커밋을 사람이 읽는 표로 축적. 필드 리포트(워크드/프라블럼 이슈)도 여기 집계.
3. 부품 단위 기여(PR)는 깃허브 기본 기록 + 필요시 meta `contributed_by` (첫 외부 PR 때 구현).
4. **답글 크레딧 (사용자 확정 2026-07-25)**: 제보 기반 수정을 배포하면 제보자에게 **수정 커밋 링크와 함께 "네 덕에 수정됐다" 답글**을 단다 (github.com/mingyo186/partreel/commit/<sha>). 다음 수정부터 적용 — 제보→수정→커밋 링크 답글이 표준 루프.

### 21-A. 수요기반 변형 등록기 (clone_variants — 2026-07-17 시작, 2026-07-24 범용화)

**원리**: Search Console 검색어(실수요) → Opus 조사(제조사 패밀리 데이터시트로 "같은 패키지·같은 핀배치" 확인) → `generators/clone_variants.py`가 기존 게이트-검증 부품의 풋프린트·심볼을 재사용해 형제 품번 등록. 핀 이름 차이만 `pin_renames`(위치 기반 치환)로 반영. **핀 위치가 다르면 변형 금지** — 조사가 핀배치를 확증 못 하면 등록하지 않는다.

- 1차(2026-07-17): TI 전원 16종 (docs/variants-ti-power.json — TPS2595 11, LM516x 4, TPS26602).
- 2차(2026-07-24): 검색어 7개 조사 → **6개는 이미 보유**(정확 mpn_pattern 일치 — 검색 노출이 나온 이유), 갭 1개 = PESD15VS5UD-Q(Nexperia, 비-Q 버전과 핀배치 동일함을 양쪽 데이터시트 원문으로 확증). **범용화**: config에 `prefix`(기본 "ti_")·`vendor_note`(기본 TI 문구) 추가 — TI 하드코딩 제거. src에 3D가 있고 풋프린트 동일하면 `carry_3d: true`로 step/glb 복사·해시 기록(내용 동일=해시 동일, 파일명만 변경)·R2 업로드 후 tier 유지.
- 부수 교정(조사 중 발견): cern_tca9406dcur case "TSSOP8"→"VSSOP-8 (US8)", cern_tps26600pwpt·ti_tps26602pwpt case "SSOP16"→"HTSSOP-16 PowerPAD", 데이터시트 플레이스홀더 3건(GitLab 링크)→제조사 제품 페이지(Renesas 5PB1102 / Molex 5040500391 / Microchip DSC1001).

### 18-A. KiCad HTTP 라이브러리 어댑터 (사용자 GO 2026-07-31 "어댑터 만들어보자" — §18 시나리오 D의 1단계)

KiCad 8+의 심볼 선택 패널에 파트릴 카탈로그가 라이브러리로 뜨게 하는 어댑터:
- **구조**: 정적 파일 증설 없이 **기존 MCP 워커에 번역 라우트** `/kicad/v1/*` 추가 — categories.json(카테고리 목록), parts/category/<cat>.json(부품 목록), parts/<id>.json(상세)를 우리 index/api에서 실시간 변환. Cache API로 캐싱(index 30분, 응답 10-60분). KiCad 규칙: 모든 값 문자열, HTTP 200만 처리.
- **한계(스펙 자체의 제약)**: HTTP lib은 메타데이터만 전달, 심볼은 로컬 라이브러리 참조(symbolIdStr) — InvenTree 연동도 동일. → **플레이스홀더 심볼 라이브러리**(PartReel.kicad_sym 1파일, "실파일은 PartReel 필드 링크에서" 안내 도형) 배포 + 상세 fields에 페이지·풋프린트·심볼·데이터시트 URL 노출. 진짜 파일 설치는 PCM 패키지(후속)로.
- **배포물**: ①워커 라우트 ②assets/partreel.kicad_httplib (root_url=https://mcp.partreel.com/kicad, token "public") ③assets/PartReel.kicad_sym ④가이드 페이지 설치 섹션.
- 검증: curl로 4엔드포인트 스펙 형태 검사 + 실제 KiCad에서 눈검증.

**구축 완료 + 실물 검증 (2026-08-01, KiCad 10.0.5)**: 심볼 선택창에 PartReel_Live 카테고리·부품(RKJXM2E13004로 확인)·설명·플레이스홀더 미리보기까지 표시 확인. 과정에서 확정된 사실 2건:
1. **root_url은 끝 슬래시 필수** (KiCad가 "v1/…"을 그대로 이어붙임 — 없으면 /kicadv1로 새서 조용히 실패). 워커는 /kicad/v1, /kicadv1, 이중슬래시 전부 허용하도록 관용 파싱 + 설정파일에 슬래시 명시.
2. **KiCad 10은 선택창 첫 오픈 때 부품 상세를 1건씩 전량 선주입** (실측 1~2건/초, wrangler tail로 확인). 2.1만 전체 서빙 시 첫 로딩 4~6시간 → HTTP lib은 **엄선판(antmicro_/cern_ 제외 자체 제작 ~446개, 첫 동기화 4~7분)**만 노출. 풀 카탈로그는 사이트·API·MCP 담당. 가이드에 두 한계 정직 고지.

**2단계 — 진짜 심볼·풋프린트 번들 (사용자 GO 2026-08-01 "플레이스홀더 이상하다 + 로컬 저장도")**: 플레이스홀더 대신,
- `generators/build_kicad_bundle.py`가 엄선판 전 부품의 심볼을 **PartReel.kicad_sym 한 파일로 병합**(심볼명=부품 id로 개명, 서브유닛 접두 포함) + 풋프린트 446개를 **PartReel-pretty.zip**으로 묶음 + 포함 목록 `kicad-bundle-manifest.json` 생성.
- 워커 상세 응답: manifest에 있는 부품은 `symbolIdStr="PartReel:<id>"` + `fields.Footprint="PartReel:<id>"` → 선택창 미리보기·배치·풋프린트 연결까지 실물. manifest 밖(번들보다 새 부품)은 PLACEHOLDER 폴백.
- 번들 재생성을 deploy·generate-part 빌드 단계에 포함(온디맨드 신부품 반영). 3D는 용량상 번들 제외(다운로드 링크 유지).
- 검증: kicad-cli sym export svg로 병합 파일 커널 검증 + KiCad 실물 눈검증.

**3단계 — 첫 동기화 멈춤 해소 (사용자 제보 2026-08-01 "실제로 쓸려니 계속 멈춘다")**: KiCad는 부품 상세를 **순차·동기**로 전량 요청하므로 응답시간 × 부품수가 그대로 UI 프리즈 시간이 된다. 실측: 워커 경유 **440ms/건**(동일 URL 반복도 캐시 미스 — 워커 응답이 엣지 캐시에 안 들어감) × 446 = **3~7분 멈춤**. 정적 파일은 50ms.
- 대책 ①**워커 자체 캐시**: `caches.default`로 워커 응답을 엣지에 저장(재요청 시 origin·연산 0), manifest를 **모듈 스코프 캐시**(요청당 서브요청 1회 제거), 남은 서브요청은 병렬화.
- 대책 ②**목록 선주입**: 카테고리 목록 응답에 상세와 동일한 필드를 미리 실어 KiCad가 상세를 덜 요청하게 유도(스펙 허용 범위 내 추가 키).
- 목표: 첫 동기화 60초 이내. 검증은 `check_kicad_adapter.py`에 **응답시간·총 동기화 추정 시간 측정**을 추가해 회귀를 게이트로 잡는다.

**4단계 — HTTP 라이브러리 권장 철회 (사용자 지적 2026-08-01 "기술적으로 문제 있는 거 같지?")**: 실측·구조 검토 결과 HTTP lib은 **오프라인 번들과 병용 시 순손실**. 근거: ①번들(446)과 온라인(120)이 겹쳐 **선택창에 부품 중복 표시** ②재시작마다 20초 선주입(캐시가 세션 메모리) ③스펙상 심볼 전달 불가라 번들이 어차피 필요 = 순수 덤 ④사이트 지연이 회로도 편집기 시작을 붙잡음 ⑤루트 검증이 index.html에 JSON을 넣는 편법(KiCad가 Content-Type 미검사에 의존).
→ **정본 배포 경로 = 오프라인 2파일**(PartReel.kicad_sym + PartReel-pretty.zip). HTTP lib은 기존 사용자 보호를 위해 엔드포인트만 유지하고 가이드에서 "실험적·비권장"으로 격하, 사유 4가지 명시. PCM 패키지(§18 시나리오 D)가 나오면 그쪽으로 흡수.

### 18-C. PartReel Fetch 플러그인 (사용자 GO 2026-08-01 "EASYEDA처럼 고르면 그때 받게")

**문제**: 통짜 배포는 규모의 한계 — 실측 전체 카탈로그 **1,104MB**(풋프린트 814 + 심볼 290). 엄선판 446개(0.88MB)는 통짜여도 되지만 21,657개는 불가.
**제약(공식 문서 확인)**: KiCad는 심볼이 **로컬 파일**에 있어야 배치 가능(HTTP lib은 메타데이터 전용), 회로도 편집기 API는 KiCad 10에도 없음 → 배치 자동화는 11 이후. SWIG pcbnew 바인딩은 9.0부터 deprecated, 11.0에서 제거 예정.
**설계**: PCM `plugin` 패키지로 배포하는 **검색→선택 부품만 프로젝트에 설치** 도구.
- 패키지 구조(공식): `plugins/__init__.py` + 소스, `resources/icon.png`(64x64, PCM 표시용), 툴바 아이콘 24x24는 plugins/ 안, `metadata.json` type=`plugin`.
- **핵심 로직은 KiCad 비의존 순수 파이썬 모듈**(`partreel_fetch/core.py`)로 분리 — 검색·다운로드·프로젝트 설치. 껍데기만 `pcbnew.ActionPlugin`. SWIG 제거(11.0) 시 IPC API로 껍데기만 교체.
- 동작: 대상 프로젝트 폴더에 `PartReel.kicad_sym`(부품 심볼 append) + `PartReel.pretty/<id>.kicad_mod` 생성, 프로젝트 라이브러리 테이블(`sym-lib-table`/`fp-lib-table`)에 항목 등록. 3D는 링크로.
- 검증: 코어를 GUI 없이 단위 검증(임시 프로젝트에 설치 → kicad-cli로 커널 렌더 → 테이블 파싱 확인).

### 18-B. PCM 패키지 (사용자 질문 2026-08-01 "다운로드 말곤 답이 없나?" → GO)

KiCad 내장 **플러그인·콘텐츠 매니저** 저장소를 우리가 직접 호스팅해, 사용자는 **URL 한 번 등록 → Install**, 이후 갱신은 KiCad 안에서 버튼 한 번. PCM이 라이브러리 테이블에 자동 등록(KICAD_3RD_PARTY)하므로 수동 라이브러리 추가도 사라진다.
- **산출물**(`generators/build_pcm.py`): `pcm/partreel-library-<ver>.zip`(metadata.json + symbols/PartReel.kicad_sym + footprints/PartReel.pretty/) + `pcm/repository.json` + `pcm/packages.json`. sha256·download_size·install_size 기록 필수.
- identifier `com.partreel.library`, type `library`, license CC-BY-4.0, kicad_version 8.0.
- 버전은 부품 수 기반(`1.<부품수>.0`)으로 자동 증가 — 새 부품이 늘면 PCM이 업데이트로 인식.
- deploy에서 재생성·배포. 검증: zip 구조·해시 대조 + kicad-cli로 zip 내부 심볼/풋프린트 커널 렌더.

## 18. 길목 배치 전략 (확정 2026-07)

**원칙**: 우리가 만드는 것만큼, **부품이 필요한 흐름(시나리오)의 길목마다 PartReel이 서 있게** 배치한다. 다른 도구/프로젝트가 우리에게 붙기 쉽게.

시나리오 감사:
| 시나리오 | 길목 | 배치 상태 |
|---|---|---|
| A. 사람 구글 검색 | 검색결과 | 🟡 SEO 있음, **한국어라 글로벌 손해** → 영어화 |
| B. AI 채팅 요청 | AI 웹검색 인용·MCP 레지스트리 | 🟡 공식 레지스트리✅ / Smithery 등 ❌ |
| C. 코딩 에이전트+KiCad | 에이전트 룰·**기존 KiCad MCP 서버들** | 🔴 → kicad-mcp 프로젝트들에 "없는 부품은 PartReel API" 통합 PR/제안 |
| D. KiCad 안 (PCM) | KiCad 플러그인 매니저 | 🔴 → PCM 플러그인 (중기) |
| E. CLI 파워유저 | PyPI | 🔴 (후순위) |
| F. 타 프로젝트의 인프라로 | 그들 문서/코드 | 🟡 API 준비됨, 아웃리치 필요 |

실행 순서: ①✅**영어화**(전 페이지 EN, 한글 0 검증) → ②✅kicad-mcp 통합 제안 — **mixelpixx/KiCAD-MCP-Server#297 이슈 제출**(1435★, "생성 전 레지스트리 조회" 제안 + PR 의사 표명. 반응 오면 PR 여부 결정) → ③Smithery/디렉터리 → ④KiCad PCM 플러그인 → ⑤PyPI CLI.

**폴백/확장 방침(2026-07, 사용자 확정)**: 타 프로젝트 통합이 거절/무반응이어도 무방 — **우리식으로 직접 구성**한다(우리 MCP를 나란히 등록하면 도구 수정 없이 같은 효과 + 복붙 프롬프트 배포). 그리고 **PartReel은 KiCad 전용이 아니다** — 레지스트리·API·MCP·게이트 구조는 포맷 중립이며, §8의 중립 스키마 전략대로 향후 다른 EDA 포맷(Eagle 등)·기구(STEP 중심) 도메인으로 확장 가능. KiCad는 1차 시장일 뿐.

## 22. 대용량 에셋 = Cloudflare R2 (사용자 확정 2026-07-05 "R2로 옮기자")

**역할 분담**: 깃헙 = 사무실(소스·진실원본 meta/텍스트·사이트·CI 게이트·기여·이력) / R2 = 창고(대용량 에셋). 사유: Pages 사이트 1GB 한계 — CERN Wave 1(풋프린트 고유분 241MB)부터 예산 초과, Wave 2(17k)는 물리적 불가. R2 무료 티어 10GB+이그레스 무료 = 비용 0.

- 버킷 `partreel-assets`, 공개 도메인 **assets.partreel.com** (r2.dev 개발 URL은 레이트리밋 — 프로덕션 금지).
- **Phase 1**: 기존 3D 바이너리(step/glb)를 R2로 이전, 다운로드/뷰어 URL 전환. **Phase 2**: Wave 1+ 수입 에셋은 처음부터 R2로.
- **신뢰 연결 유지**: R2 파일은 git 이력이 없으므로 meta.json(깃헙)에 **sha256 해시 기록** — "이 커밋이 보증하는 파일" 검증 경로 유지. 게이트에 R2 URL 200 + 해시 일치 검사 추가(§16 원칙: 새 결함 클래스=영구 게이트).
- 업로드는 wrangler CLI(인증 완료 계정), CI 시크릿으로 자동화 검토.
- ⚠️ **연쇄 취소 업로드 누락 사건 (2026-08-05) → 배포 R2 단계 누락 기반 전환 + check_r2 게이트 편입 (2026-08-06)**: PR #19 머지 커밋(3b8a85a, yeonho step/glb 4개)의 배포가 후속 푸시(d29c2d89)의 `concurrency: cancel-in-progress`로 취소 → 다음 런은 fetch-depth 2로 "직전 커밋 diff"만 보므로 취소된 커밋의 에셋이 **영영 미업로드**(R2 404, 수동 sync_r2 --upload로 복구). 구조 결함: diff 기반 증분은 "모든 커밋의 배포가 완주한다"를 전제 — concurrency 취소와 양립 불가. **수정**: ①deploy.yml R2 단계를 스코프 없는 `sync_r2 --upload`(누락 기반)로 — CI 체크아웃엔 git 추적 step/glb만 존재하므로 대조 대상은 전 부품(16.6k)이 아니라 추적분(2,721개, 421MB)뿐. 실측(2026-08-06, CI 동형 클론): meta 스캔 ~11s + 해시 ~4s는 무시 가능하나 **전량 HEAD 대조는 표본 벤치(39ms/개→예상 2분)와 달리 실제 ~9분**(2,721개 연속 시 CDN 스로틀) → 매 배포 부담이라 **검증 스냅샷 프리필터**(env `SKIP_VERIFIED=1`) 채택: docs/r2-verified.json에 같은 해시로 기재된 에셋은 HEAD 생략. 안전 논거 = 스냅샷은 check_r2 PASS(전 대상 200 검증) 시에만 기록되므로 "미업로드인데 스냅샷 기재"는 불가능 — 취소로 누락된 에셋은 반드시 필터에 남아 HEAD→업로드된다. 통상 배포 HEAD 수 = 스냅샷 미기재 신규분 몇 개 = 수 초. 어떤 런이 취소돼도 다음 완주 런이 복구(연쇄 취소 안전). 한계(기존과 동일): 존재하는 R2 오브젝트의 내용 교체는 안 함(--force-all 수동), R2 측 삭제는 check_r2 표본이 확률적으로 검출. ②`check_r2.py`를 deploy.yml 게이트로 편입(업로드 직후, 404 시 배포 중단 — §16 원칙: 새 결함 클래스=영구 게이트. 이번 사건도 check_r2가 배포 파이프라인에서 돌기만 했으면 즉시 red: 누락 4개가 스냅샷 부재=신규분 전수 HEAD 대상이었음). CI 비용 = 신규/변경분 + 표본 300 ≈ 수십 초. 스냅샷(docs/r2-verified.json) 갱신은 로컬 qa PASS 커밋으로(CI는 읽기만). 게이트 편입 검증(가짜 에셋 주입 테스트) 중 **check_r2 자체 맹점 발견·수정**: 해시 미기록(None) 에셋은 스냅샷 부재(None)와 None==None이라 "변경 없음" 판정 → 표본 확률(~2%)로만 검사되던 구멍 — 부재 센티널 비교로 스냅샷 미기재는 해시 기록 여부와 무관하게 전수 검사(1차 방어인 check_render의 "해시 미기록" 게이트와 독립 이중화). ③CI 전량 스캔 시 R2 전용 부품(체크아웃에 3D 없음)의 "MISSING" 경고 1.4만 줄 방지 — sync_r2에 env `MISSING_OK=1`(개별 경고 대신 합계 1줄, deploy.yml에서 설정).
- **Phase 1 완료 (2026-07-05)**: 버킷 생성, assets.partreel.com 연결(zone 2b1f5e31…), CORS {partreel.com, localhost:8931 / GET·HEAD}(mcp/r2-cors.json), 454 에셋 업로드+해시 대조 PASS, build_site/api URL 전환(+CSP connect-src), check_r2.py 게이트(전수 HEAD+무작위 해시 3, **UA 필수** — 기본 python UA는 봇보호 403), deploy.yml이 Pages 아티팩트에서 step/glb 제외(~195MB 절약, 사이트 ~20MB로 슬림) — R2 200/Pages 404/뷰어 R2 로드 전부 라이브 검증. **Wave 1 용량 게이트 해제됨.** 미결: Wave 1 대형 kicad_mod(241MB 텍스트)를 git에 둘지 R2로 뺄지 — git에 두면 CI 게이트 단순(사이트는 이미 슬림), 레포만 ~460MB로 성장. 다음 세션에서 결정.

## 23. 오픈 상태에서의 지위 방어 (사용자 문제제기 2026-07-05 "컨셉을 뺏길 수도")

**게이트 = 복리 자산 (사용자 정리 2026-07-26)**: 분산 생성에서 상대 AI는 시간·토큰·시행착오를 아끼고, 그 대가로 부품·제보를 낸다. 게이트 코드는 MIT로 열려 있어도 복사 불가한 것 세 가지 — ①사건→게이트 강화의 살아있는 루프(포크=죽은 스냅샷) ②부품별 신뢰 이력(필드 리포트·심사 기록) ③길목 지위(kicad-mcp 기본 레지스트리 등). 데이터는 퍼가도 '검증이 일어나는 장소'는 못 가져간다.

**정직한 전제**: 코드(MIT)·데이터(CC-BY 등)·컨셉은 복제 가능하고 막을 수 없다(오픈의 대가). **해자는 데이터가 아니라 축적·운영·유통에 있다** — 복제자는 파일은 가져가도 아래는 못 가져간다:

1. **인용 축적 = 최대 해자**: partreel.com URL이 검색색인·GitHub 코드검색·MCP 레지스트리·타 프로젝트 문서·**차세대 모델 훈련데이터**에 쌓이는 것. 복제 사이트는 0에서 시작. → 런칭·색인·길목배치(§18)가 곧 방어 전략.
2. **라이선스 귀속 강제**: 우리 생성물=CC-BY-4.0 → 복제자도 PartReel 표기 의무 = 복제가 오히려 우리 브랜드를 유통시킴. 수입품 provenance 체인도 동일.
3. **피드백 데이터 선점**: field-report(worked/problem) 신뢰 데이터는 시간·사용자가 만드는 것 — 후발주자가 못 삽. 배지·API 노출 강화 유지.
4. **운영 속도**: 갭 채굴→검증→배포 파이프라인+함정 카탈로그(§14-H)는 문서가 아니라 근육. 카탈로그 성장 속도 자체가 해자.
5. **브랜드 보호(선택, 미결정)**: PartReel 상표 출원(한국 KIPO ~6만원/미국 USPTO ~$250) — 이름 도용만 막아도 복제 사이트는 "짝퉁" 포지션. §12로.
6. **하지 말 것**: 데이터 폐쇄·라이선스 강화로의 회귀 — 오픈+무마찰이 존재 이유이자 유통력. 폐쇄는 해자를 없앰.

## 12. 미결정 / 오픈 이슈

- [x] 프로젝트/사이트 이름 = **PartReel** (2026-06-20). 사유: "reel in(끌어오다)" + 전자부품 릴(reel) 이중의미, 브랜드 충돌 없음, partreel.com 미등록(.com 확보 가능). 후보 PadForge/PartForge/OpenParts 등은 전부 선점됨.
- [ ] partreel.com 실제 등록 (Cloudflare/Namecheap)
- [ ] 자체 라이선스 종류 (MIT? CC-BY?)
- [x] PartReel 상표 출원 = **보류 (사용자 확정 2026-07-05 "에이전트 시대에 이름은 중요하지 않을 것")**. 논리: 브랜드(감성)의 가치는 하락, 이름의 가치는 식별자(주소)로 이동 — 식별자 방어는 등록이 아니라 ①도메인 보유 ②정식 MCP 레지스트리 선점 ③검증가능 provenance로 하는 게 정공법(전부 확보됨). 선사용 증거는 git 이력·도메인 등록일·레지스트리 등재일·Wayback 스냅샷으로 자동 축적. 사칭(유사 도메인/가짜 MCP) 발견 시 재론.
- [x] 첫 커넥터 패밀리 = **JST-PH 확정** (2026-06-20). 순서 = 얇은 수직 슬라이스 확정.
- [x] JST-PH 치수 검증 (2026-06-20) — KiCad 공식 Connector_JST(데이터시트 기반)와 일치 확인.
- [x] 라이선스 (2026-06-20): **코드=MIT, 부품 자산=CC-BY-4.0**. (층별 분리: 소프트웨어 MIT / CAD 자산 CC-BY)
- [ ] 심볼 핀리스트 자동 추출 방법 (데이터시트 비전LLM vs 수동, 2단계 이슈)
- [ ] 수요신호 체계적 채굴(InstaPart 목록/포럼 스크랩)은 미실시 — 방향성 신호만 확보


## §23. 생성 루프 완결: 즉시 공유 스테이징 (2026-08-02 사용자 결정)

**결정**: "지들이 만든 부품도 파트릴로 올라가야 진짜 의미가 있다. 올라간 부품이
바로 공유가 되어야 한다. 지금은 PR이 머지되어야 공유된다" — 이 마찰을 없앤다.

**구조 — 2단 티어**:
1. **staging (즉시 공유, unverified)**: AI가 MCP `submit_part` 도구로 부품을
   올리면 워커가 구조 검증 후 R2 `staging/<id>/`에 저장. **그 순간부터**
   `search_parts` 결과에 `status:"staging"`으로 노출되고 다운로드 URL이
   유효하다 (assets.partreel.com/staging/<id>/...).
2. **registry (verified)**: 시간별 GitHub Action(staging-promote.yml)이
   스테이징 부품을 수집해 전체 게이트(check_part 수준)를 돌리고, 통과분은
   자동으로 PR을 연다(Actions 기본 토큰 — 새 시크릿 불요). 머지되면 정식
   등록·verified, 스테이징에서 제거. 게이트 실패분은 사유를 스테이징
   메타에 기록해 제출자가 조회 가능.

**검색 0건 = 생성 유도 지점**: `search_parts`/`/search`가 0건일 때 응답에
생성·제출 안내(how_to_contribute + submit_part 사용법)를 구조화해 포함한다.
빈 배열만 돌려주면 AI는 떠난다.

**남용 방어** (워커에서 강제):
- 텍스트 파일만: `<id>.kicad_sym` + `<id>.kicad_mod` + meta(JSON). 3D는 승격 후.
- 크기 상한: sym/mod 각 512KB, meta 32KB. id는 `^[a-z][a-z0-9_]{2,63}$`.
- 구조 검증: s-expr 괄호 균형 + 루트 토큰(kicad_symbol_lib/footprint) + 패드/핀 존재.
- meta 필수: name, description, license(허용 목록), dimensions_source.
- 정식 카탈로그와 id 충돌 시 거부. 같은 staging id 재제출은 덮어쓰기(갱신).
- 스테이징 총량 상한 300 (초과 시 제출 거부 — 승격/정리로 비운다).
- 표시 정직성: staging 부품은 모든 표면에서 unverified/staged 표기.

**의도**: 부품이 없는 순간(검색 실패)이 곧 생성이 일어나는 순간이 되도록
루프를 닫는다. 분산 생성 비전(§1-0)의 실행 형태.

**§23-B. 배치 배포 + 로컬 부품 스테이징 병행 (2026-08-10 사용자 결정)**:
"계속 스테이징을 쓰자."
- 서빙은 전부 Pages 배포본이라 커밋만으로는 사이트도 MCP도 반영 안 된다
  (깃 = 원본 보관). 부품 1개에도 전체 재빌드+배포 ~8분이 따라와 과하다.
- **운영**: 로컬 제작 부품은 게이트 통과 후 커밋 + `submit_staging.py`로
  스테이징 병행 제출 → 즉시 MCP 검색·다운로드 노출. **정식 배포는 배치**
  (사용자 지시 시 또는 일 1회). 구조 변경(동적 서빙)은 배포 큐가 실제
  병목이 될 때 재검토.
- 승격 봇 3분류 (staging-promote.yml): **배포됨(API 200)→스테이징 정리** /
  **커밋만 됨(git에 있음)→보류**(지우지도 PR하지도 않음 — 스테이징이
  커밋~배포 공백을 서빙) / **둘 다 아님→게이트 후 승격 PR**.
- 제출은 워커 submit_part 경로만 사용 (R2 직접 쓰기 금지 — 스테이징
  index.json은 워커가 관리하므로 직접 쓰면 어긋난다).
- **운영자 verified 스테이징**: 로컬 전체 게이트를 통과한 부품은 스테이징에
  unverified가 아니라 **verified**로 표시된다 — submit 시 운영자 토큰
  (Cloudflare 시크릿 SUBMIT_TOKEN ↔ 로컬 ~/.partreel/submit_token, 레포에
  절대 커밋 금지)을 동봉하면 워커가 status:"verified"/origin:
  "partreel-operator"로 기록. 외부 제출은 종전대로 staging(unverified).
  전 구간 실증: 시험 부품 제출→검색 staged_parts에 "verified (staged,
  pre-deploy)" 노출→청소 (2026-08-10).
- 후속 후보: build_site 증분화(PART_SCOPE)로 배치 배포 자체도 단축.


## §24. 회로 블록 층 (기능 모듈) — 2026-08-04 사용자 결정

> **이관 (2026-08-10 사용자 결정)**: "파트릴은 부품만 올라가는 거고, 회로
> 설계는 따로 만들어서 관리" — 블록·보드 **제작(작업장)과 설계 규칙집은
> 비공개 레포 github.com/mingyo186/boardworks** 로 이전. 파트릴에는
> 완성 블록 배포물(dist/design_blocks)만 남아 공개된다. §24/§25의 결정
> 기록은 역사로 여기 보존, 이후 설계 결정은 boardworks에서 관리.

**결정**: "나중에 창업할 때 회로를 그때 그리기엔 오래 걸린다. 미리 기능별로
회로 모듈을 만들어 놓고, 나중엔 합치기만 하면 되게 하자." 부품(재료) 위에
**블록(반제품)** 층을 쌓는다. 우선 용도는 사장님 자체 설계 자산이며,
파트릴 공개(카탈로그의 blocks 섹션)는 품질이 쌓인 뒤 별도 결정.

**형식** (§21-D 데모 분석 결과를 그대로 적용):
- 블록 1개 = 자립(self-contained) `.kicad_sch` 시트 1장. KiCad 데모의
  재사용 시트 패턴 — 부모 회로도에서 시트로 불러 쓰고, 여러 번 인스턴스 가능.
- 인터페이스 = 계층 라벨(hierarchical label). 시트 핀으로 노출된다.
- `lib_symbols` 캐시에 파트릴 심볼을 내장해 **파일 하나로 자립** (데모 분석:
  심볼은 .kicad_sch에 캐시됨). Footprint 필드는 PartReel:<id>로 연결.
- 소스는 `blocks/<분류>/<block_id>/block.json` (부품·네트·인터페이스 선언)
  → `generators/build_block.py`가 .kicad_sch 생성. 손그림이 아니라 선언형:
  재생성 가능해야 게이트·수정·일괄 갱신이 된다.

**1차 사료 원칙 (spec-and-drawing-first의 회로판)**:
- 회로 토폴로지·부품값의 근거는 **제조사 데이터시트의 Typical Application /
  평가보드 회로도**. block.json에 `circuit_source` 필수 (URL+페이지/그림).
- 파트릴에 없는 부품이 필요하면 먼저 부품을 등록하고 블록에서 참조한다
  (부품이 우선 — 블록이 부품 카탈로그를 견인).

**기계 검증 게이트** (`generators/check_block.py`, qa 편입 예정):
- `kicad-cli sch erc` — 오류 0 (경고는 보고). 공식 커널이 판정.
- `kicad-cli sch export svg` — 렌더 눈검증용 산출.
- block.json ↔ 생성물 대조: 부품 수, 인터페이스 라벨 존재.


**추가 결정 (2026-08-04 사용자 피드백)**: 자동 격자 배치는 **불합격**.
"데이터만 맞으면 되는 게 아니라 사람이 회로를 보려면 규칙이 필요하다."
- 블록 회로도는 사람 가독 관례를 지켜야 한다: 전원 위 / GND 아래 /
  신호 좌→우 흐름 / 기능 중심 배치 / 관례적 부품 배열 (풀업은 전원에서
  아래로 내려오는 형태 등).
- 진행 방식 변경: **하루 하나씩, 사용자와 함께 그리며 규칙을 확정**한다
  (2026-08-05부터). 확정된 규칙은 생성기에 반영해 이후 블록에 자동 적용.
- 현 i2c_pullup(격자 배치판)은 파이프라인 증명용 — 규칙 확정 후 재배치.

**초기 블록 로드맵** (범용 → 산업 계측 순):
1. i2c_pullup — I2C 풀업 (파이프라인 증명용 최소 블록) ✅
2. power_usbc_5v — USB-C 5V 입력 + ESD/퓨즈 ✅ (usb_c_5v, rev 0.1)
3. ldo_3v3 — 5V→3.3V LDO (+ 입출력 캐패시터) ✅ (rev 0.1)
4. mcu 최소 회로 ✅ **g431_min** (STM32G431CBTx, rev 0.1, 2026-08-10) —
   ESP32 대신 R16 4면 심볼을 확립한 G431로 선행. ESP32는 후속.
5. swd_debug — SWD 디버그 헤더 → **3종으로 확장** (2026-08-10 사용자 결정:
   ST-LINK V3SET 기준, 확장보드로 UART까지 사용):
   ① swd_uart_hdr254 (2.54 1x8, SWD+UART+전원 — 점퍼선용, 핀 순서는 파트릴
     규약으로 특성표에 명기) ✅ rev 0.1
   ② stdc14 (ST 정식 14핀 1.27) ✅ rev 0.1 — 사용자가 UM2448 PDF 제공
     (2026-08-10). 핀표 = UM2448 Rev 9 §8.1.2 Table 6 (1-2 Reserved 연결금지 /
     3 T_VCC / 4 SWDIO / 5·7 GND / 6 SWCLK / 8 SWO / 9-10 JTAG전용 NC /
     11 GNDDetect→GND / 12 NRST / 13 VCP_RX / 14 VCP_TX). 커넥터 =
     Samtec FTSH-107-01-L-DV-K-A (문서 명기) → gen_ftsh.py로 부품 생성
     (치수: 피치 1.27 계열 + Arm UG 101636의 105 몸체 6.35x4.78 파라메트릭 +
     antmicro 105 양산 랜드 0.76x2.4; Samtec 공식 print 403 — 확보 시 대조).
   ③ cortex_debug_10 (ARM 표준 10핀 1.27, FTSH-105-01-L-DV-007-K) ✅ rev 0.1
     — 핀표 근거: Arm ULINKplus UG 101636 'JTAG/SWD Interface' 그림
     (1 VCC/2 SWDIO/3 GND/4 SWCLK/5 GND/6 SWO/7 KEY/8 NC/9 GNDDetect/10 nRESET)
   부수 수리: pin_header 패밀리 심볼 pin_names hide (Pin_N이 외곽선 침범 —
   R7), R7 침범 판정 0.25mm 캘리브레이션 (0.04mm 스침 오탐 제거),
   gen_connectors의 루트 index.json 덮어쓰기 제거 (21,664→37 사고 재발 방지).
6. rs485_iface — RS-485 트랜시버 (산업 계측용)
7. sensor_4_20ma — 4-20mA 수신 프론트엔드 (산업 계측용)

**블록 선언의 배치 지시 (P13, 2026-08-10)**: block.json parts[]에
`place: {role, near}` — 부품의 회로 역할(decoupling/bulk/pullup/pulldown/
filter)과 근접 대상("U1.24" = 핀, "J1" = 부품)을 블록 저자가 선언한다.
"부품 하나하나 설명하면 힘들다 — 부품 속성에 AI가 보고 판단할 지시가
있어야" (사용자). 배치기는 이를 읽어 대상 핀 옆에 연결 패드가 핀을
향하게 놓는다 (build_pcb, 2차원 밀어내기로 변을 따라 나란히).

**g431_min에서 확정된 규칙·기반 (2026-08-10)**:
- 생성기: 계층/로컬 라벨과 전원 심볼에 **회전 지원** (라벨 스핀 0/90/180/270 =
  우/상/좌/하, justify는 커널 관례 0·90=left/180·270=right; 전원 rot 180 =
  뒤집힘 — 윗변 GND·아랫변 레일용, 값 텍스트는 도형 반대편으로 자동 이동).
- 가독 검사기: SVG 회전 글자(<g transform="rotate(A CX CY)">) 실측 편입 —
  MCU 4면 라벨·핀이름의 R1/R6/R7 검사가 정확해짐. 전 블록 무회귀 확인.
- 심볼 규칙: **VREF+/-는 power_in** (XML Type이 MonoIO여도 기준전압 입력 —
  bidirectional이면 전원 깃발과 pin_to_pin ERC 경고. gen_mcu에 반영).
- MCU 블록 형태: 전원 핀은 각 변에서 스텁+전원 심볼로 즉시 종단, 디커플링은
  몸체 아래 별도 클러스터(레일 쌍), 미사용 IO는 전부 계층 라벨로 노출,
  BOOT0는 10k 풀다운 고정(SWD로 플래시 — 라벨 미노출), NRST는 100nF+라벨.
- 교차검증: 하네스 ERC와 **독립적으로** 커널 넷리스트(kicadxml)를 뽑아
  block.json nets 선언과 구성원 전수 대조 (g431_min 40/40 일치).
- 부품 등록: 10kΩ 0402(vishay_crcw040210k0fked), 1µF 0402
  (samsung_cl05a105ka5nnnc, gen_chip_c 신설 — 벤더 폴더 samsung/).


## §25. 한 몸 개발 기획: 보드 정의서 → 회로도·PCB·펌웨어 (2026-08-08 사용자 요청)

**요청**: "회로도부터 펌웨어까지 한방에 되게 할 순 없을까." 부서별로 갈라진
작업(회로/PCB/펌웨어)을 AI가 한 흐름으로 통합하는 기획.

**핵심 설계 — 단일 진실 소스 `board.json` (보드 정의서)**:
도구 세 개를 합치려 하지 말고, 셋 위에 선언 한 장을 둔다. 보드 정의서에는
①쓸 블록들(§24)과 연결 ②MCU와 핀 할당 ③보드 제약(층수·크기)만 적는다.
나머지는 전부 생성물이다:

```
                 board.json (단일 진실)
        ┌──────────┼──────────────┐
   회로도(.kicad_sch)  넷리스트      pins.h / board_config.h
   (블록 조합 생성)      │           (펌웨어 핀맵 자동 생성)
        │            PCB 시작점         │
   kicad-cli ERC    (IPC 배치 보조)   펌웨어 빌드 게이트
                    kicad-cli DRC
```

**"한 몸"의 실체 = 핀맵의 자동 왕복**: 회로에서 UART를 PA9→PB6으로 옮기면
pins.h가 자동 재생성되고 펌웨어가 다시 빌드-검증된다. 펌웨어가 PWM 핀을
요구하면 보드 정의서 검증기가 그 핀의 타이머 능력을 회로 쪽에서 확인한다.
지금은 부서 둘이 메일로 하던 정합을 생성기+게이트가 한다.

**단계별 계획** (각 단계가 독립적으로 유용해야 함):
- **0단계 (완료)**: 부품 21,659 + §24 블록 생성기 + ERC 게이트.
- **1단계 — 보드 정의서 v1**: board.json 스키마 확정. 블록 조합 →
  루트 회로도(.kicad_sch, 시트 인스턴스들) + **pins.h 생성**. ERC 게이트.
  성과물: "선언 한 장이면 회로도와 펌웨어 헤더가 같이 나온다."

  **v1 스키마 확정 (2026-08-10, 사용자 "4번도 진행해"로 착수)**:
  `boards/<id>/board.json` = { id, name, revision, blocks:
  [{ref:"B1", block:"usb_c_5v"}...], nets: {"USB_DP": ["B1.USB_DP",
  "B3.PA12"]...} }. 규칙:
  - 시트 = 블록 재사용 (Sheetfile 상대경로 → blocks/<분류>/<id>/<id>.kicad_sch,
    복사 없음 — 블록 수정이 모든 보드에 반영).
  - 연결 = 시트 핀 + **전역 라벨** 쌍 (§21-D 하네스 패턴 그대로 — 커널
    실증된 유일 조합). 전원(+5V/+3V3/GND)은 블록 내부 전역 심볼로 자동
    병합, 보드 선언 불필요.
  - 미연결 인터페이스 핀은 no_connect 명시 (ERC 잡음 0 원칙).
  - 게이트: 재생성 일치 + ERC 오류 0 + 커널 넷리스트로 nets 선언 전수 대조
    (블록 게이트와 같은 3중).
  - 핀 할당의 AF(대체기능) 검증은 2단계로 (ST XML 신호표 대조 예정).
  - **보드 전역 주석(annotate)** (2026-08-10): 블록 조합은 참조번호가
    겹치므로(U1 두 개 등 — SMT 작업지시 불가) build_board가 블록 sch를
    **인스턴스별 사본**(<ref>_<block>.kicad_sch)으로 보드 폴더에 넣고
    KiCad 계층 주석 방식(instances 교체)으로 보드 전역 고유 번호를 새긴다.
    R12 자유 텍스트 표기도 함께 갱신. 블록 원본은 불변(공유 라이브러리),
    보드 폴더는 자립형이 된다. 지도는 ref_map.json (check_board 넷 대조가
    사용).
  - `layers` 필드 추가 (2026-08-10, P4): 층수는 설계 전 사용자 확인 —
    g431_devkit = 2층. PCB 배치 규칙은 **rules/pcb-layout.md** (P1 외곽
    선언 우선·잠정 산정은 용지 중앙 / P2 커넥터 가장자리·삽입구 바깥 /
    P3 디버그는 MCU 근처 / P4 층수 확인)에 쌓는다 — 회로도 규칙집과 동일
    방식: 보드를 함께 만들며 확정, build_pcb.py에 반영.
- **2단계 — PCB 다리**: kicad-cli로 넷리스트 추출 → PCB 초기화, IPC로
  블록 단위 배치 보조(전원부 모아두기 등). DRC 게이트. 배선은 사람
  (자동배선 품질이 아직 실무 수준이 아님 — 정직한 한계).

  **첫 걸음 완료 (2026-08-10, g431_devkit)**: build_pcb.py (KiCad 동봉
  파이썬/pcbnew) — 넷리스트 → 풋프린트 로드(임시 .pretty) → 블록(시트)
  단위 열 배치 → 패드-네트 연결 → Edge.Cuts. 게이트 = check_board E:
  kicad-cli pcb drc, **unconnected_items만 허용**(초기화 정의상 상태),
  text_height 경고 허용(안트미크로 수입 스타일). DRC가 부품 결함 2급을
  실전 적발: ① LQFP 핀1 실크 점이 패드에 정확 접촉(pkg_land d1
  0.35→0.65, LQFP 상수 PACKAGES 영구화) ② FTSH 실크 가로선이 패드 관통
  (세로 끝선으로 교체). 안트미크로 28종 근접 의심은 별도 감사 태스크.
- **3단계 — 펌웨어 스캐폴드**: MCU별 템플릿(ESP32/STM32)에 pins.h 결합,
  주변장치 초기화 코드 생성, **컴파일 통과를 게이트로**.

  **착수 결정 (2026-08-11, 사용자 "그래 진행해" — 시나리오 감사에서 미검증
  1순위로 추천 승인)**: 구현은 boardworks 레포.
  - 툴체인 = **xpack arm-none-eabi-gcc 15.2 포터블** (boardworks/tools/,
    freerouting과 같은 상주·git 제외 방식) + **CMSIS만** (cmsis_core +
    cmsis_device_g4 얕은 클론) — HAL 미사용. 스캐폴드는 베어메탈 최소:
    startup(.s)·system·링커(.ld)는 ST CMSIS 템플릿, main.c는 pins.h의
    **모든 define을 실제 참조하는 핀 테이블 + GPIO 클럭/모드 초기화**
    생성 → 넷 이름이 바뀌면 컴파일이 깨진다 = pins.h가 하중을 받는 구조.
  - pins.h 이름은 HAL 호환(GPIOx/GPIO_PIN_n) 유지 — 사용자가 나중에
    Cube HAL로 갈아타도 그대로 쓰임. 베어메탈용 GPIO_PIN_n 정의는
    스캐폴드 동봉 호환 헤더가 제공.
  - 게이트 `check_firmware.py`: make 의존 없이 gcc 직접 호출(윈도우 무의존)
    → 컴파일+링크 성공 = 통과. **음성 시험 필수**: 핀 이름을 일부러
    바꿔 게이트가 실패하는지 확인 후 채택 (검사기 맹점 방지 문화).
  - G431CB 메모리: FLASH 128K@0x08000000, RAM 22K(SRAM1+2 연속)@0x20000000,
    CCM 10K@0x10000000.

  **완료 (2026-08-11 같은 날)**: build_firmware.py + check_firmware.py
  (게이트 I 재생성 일치 / J gcc -Wall -Werror 컴파일+링크 / K 크기 기록).
  g431_devkit 실증: 핀 7·포트 A,B → text 880B. **음성 시험 통과 2종**:
  ①넷 개명(SDA→I2C_SDA) 후 이전 main.c → I단계 '재생성 불일치' 적발
  (회로-펌웨어 어긋남은 커밋된 산출물과 재생성물의 다이제스트 차이로
  잡힌다) ②pins.h 짝 손상 → 생성기 FAIL. 이로써 §25 핵심 문장
  "board.json 한 장 → 회로도+PCB(배선까지)+pins.h+컴파일되는 펌웨어"가
  전 구간 실증. 남은 것 = 4단계 역방향(펌웨어 핀 요구 → 회로 능력
  검증, ST 핀 XML)과 주변장치 초기화 확장(지금은 GPIO 입력 안전 기본값).

**시나리오 현황판 + 기본-우선 방침 (2026-08-11, 사용자 "일단 기본적인
기능을 구현하고 고도화 하는게 좋지 않을까" / "니 기억력이 무한대가
아니니까 잘 적어놔야")**: 전 시나리오의 **기본 기능을 먼저 채우고,
고도화는 그 다음** — 깊이 파기 전에 폭을 닫는다.

| 시나리오 | 기본 기능 | 상태 | 고도화 백로그 (후순위) |
|---------|----------|------|----------------------|
| A/B 블록→보드→pins.h | 선언→회로도+PCB+펌웨어 | 🟢 실증 (g431_devkit 1회) | 타 MCU 프로파일, 다른 조합 반복 실증 |
| C 파트릴 루프 | 부품 공급+블록 배포 | 🟢 상시 | — |
| G 자동 배선 | freerouting 왕복+DRC 0 | 🟢 **기본 충족 판정** (2026-08-11) | 위치 락, 리턴비아 완전 강제, 잔여 11 손배선 |
| D 핀 능력 검증 | ST 핀 XML로 AF 기계 대조 | 🟢 기본 완료 (2026-08-11) | 타이머/ADC 능력, ESP32 헤더 |
| E 깃 형상관리 | boardworks CI 푸시 게이트 | 🟢 기본 완료 (2026-08-11) | 그림 diff, rev 태그 릴리스, 거버 자산 |
| F 수치 출처 기록 | block.json에 출처 필드+게이트 | 🟢 기본 완료 (2026-08-11) | 페이지 단위 정밀 인용, PDF 벡터 실측 자동 대조 |
| 4단계 역방향 | 펌웨어 핀 요구→회로 검증 | 🟢 기본 완료 (2026-08-12) | 주변장치 초기화 생성, 사용자 코드 스캔 |

검증 깊이 정직 표기: 🟢도 보드 1장 1회 실증 — 반복·조합 실증은 고도화측.

**D 착수 결정 (2026-08-11, 사용자 "진행해")**: 핀 능력 기계 검증 기본형.
- 1차 사료 = **ST 공식 STM32_open_pin_data XML** (BSD-3, boardworks/tools/
  st_pin_data/ 에 대상 MCU 파일만 동봉 — CI 자립 위해 git 포함, 실측:
  PB7=I2C1_SDA·PA15=I2C1_SCL·PA2/3=USART2_TX/RX·PB3=SYS_JTDO-SWO·
  PA11/12=USB_DM/DP 확인).
- **요구는 블록이 선언**: block.json `pin_requires` = {포트: 신호 글롭}
  (예 i2c_pullup: SDA→"I2C*_SDA"). 블록에 한 번 적으면 그 블록을 쓰는
  모든 보드가 검사를 공짜로 받는다. 어느 보드 넷이 그 포트를 MCU PXn에
  연결하면, 그 핀의 XML 신호 목록에 글롭 일치가 있어야 PASS.
- **인스턴스 정합**: 같은 블록의 포트들이 같은 주변장치 계열(I2C/USART...)
  이면 공통 인스턴스(I2C1 등) 교집합이 비면 FAIL — SDA는 I2C1인데 SCL이
  I2C3뿐인 배선을 잡는다.
- 게이트 = check_pin_caps.py (MCU 프로파일은 build_firmware.PROFILES 공유,
  pin_xml 키 추가). SWDIO/SWCLK 등 고정 명명 핀(PXn 아님)은 기본형에선
  검사 대상 외. 음성 시험 2종(패턴 불일치·인스턴스 불일치) 필수.

  **D 기본형 완료 (2026-08-11 같은 날)**: pin_requires 3블록 선언
  (usb_c_5v 0.3 / stdc14 0.2 / i2c_pullup 0.3), g431_devkit 실증 —
  대조 7건 전부 공식표 확증(USB_DM/DP, SWO, USART2_TX/RX, I2C1_SDA/SCL)
  + 인스턴스 정합 USART2·I2C1. **음성 2종 통과**: ①SCL→PB9 = 패턴
  불일치 적발(보유 신호 목록 제시) ②SCL→PA8 = I2C3_SCL 존재해도
  SDA(I2C1)와 교집합 없음 적발. 전 게이트 회귀 초록. 시나리오 D
  기본 = 🟢. 고도화 백로그: 타이머/ADC 능력, ESP32 헤더, 고정 명명 핀.

**E 착수 결정 (2026-08-11, 사용자 "진행해")**: boardworks CI 푸시 게이트
기본형 (파트릴 방식 이식).
- GitHub Actions ubuntu: KiCad 10 PPA + apt gcc-arm-none-eabi + CMSIS 얕은
  클론 + 파트릴 공개 레포 체크아웃(PARTREEL_ROOT). 게이트 4종 전부 실행
  (check_block 전 블록 / check_board / check_pin_caps / check_firmware).
- 최소 권한(contents: read), 시크릿 불필요. 툴체인 탐색 일반화(PATH 우선
  → tools/ 포터블 폴백)로 리눅스/윈도우 양쪽 커버.
- 배포 없음 — 순수 검증(비공개 설계 레포). 그림 diff·rev 태그 릴리스는
  고도화 백로그.

  **E 기본형 완료 (2026-08-11 같은 날)**: 첫 주행 초록 2m23s — 리눅스에서
  게이트 4종 전부 통과 (KiCad 10 PPA + apt ARM GCC 조합 실증). 과정
  수확: 툴체인 경로 일반화 중 size 도구 경로 버그(.exe 접미사 오인)를
  **로컬 게이트가 즉시 적발** — 게이트 문화가 제 코드도 잡는다.
  교훈 재확인: 검증 명령을 tail로 파이프하면 종료코드가 삼켜진다
  (pipefail 규칙 — 게이트는 exit code를 직접 봐야 한다).

**F 착수 결정 (2026-08-11, 사용자 "진행해")**: 값 출처 기록 기본형.
- 실태: 전 블록이 이미 블록 수준 출처(circuit_source — 문서+절 표기)를
  보유. 기본형은 이를 **상속 기본값**으로 삼고, 부품별 `source` 필드는
  **출처가 circuit_source와 다른 값에만** 명시한다 (예: usb_c_5v의 ESD
  다이오드 값은 USB 스펙이 아니라 USBLC6 데이터시트가 사료).
- 게이트(check_block 신설 단계): 부품마다 source 해석 — 명시/상속 집계
  보고, **둘 다 없으면 FAIL** (circuit_source 없는 블록 방지). 페이지·
  그림 단위 정밀 인용과 PDF 실측 대조는 고도화 백로그.
- 원칙: 확인 못 한 페이지 번호를 지어내지 않는다 — 거친 인용(문서명+
  용도)이 가짜 정밀 인용보다 낫다.

  **F 기본형 완료 (2026-08-11 같은 날)**: check_block A2 단계 — 7블록
  집계(명시 1/상속 18), usb_c_5v 0.4에 첫 개별 출처(D1 ESD 값 =
  USBLC6-2 데이터시트, circuit_source인 USB-C 스펙과 사료가 다른 사례).
  음성 시험 수확: circuit_source 없는 블록은 **생성기(§24 필수 규칙)가
  선행 차단**하고 있었음 — A2는 이중 방어 + 집계 가시화 역할.

**4단계 착수 결정 (2026-08-12, 사용자 "진행해")**: 역방향 기본형 —
펌웨어의 핀 요구를 회로가 충족하는지 기계 검증.
- 선언 = `boards/<id>/firmware/requires.json`: {넷이름: 신호 글롭}
  (펌웨어 저자/AI가 응용 의도를 적는 곳 — 예 "SDA": "I2C*_SDA").
  블록 pin_requires(하드웨어 인터페이스의 요구)와 방향이 반대: 이쪽은
  **응용이 회로에 거는 요구**다.
- 판정(check_pin_caps 확장): ①요구한 넷이 board.json에 존재하는가
  (없으면 FAIL — "회로에 그 넷 없음"이 역방향의 핵심 적발)
  ②그 넷의 MCU 핀이 요구 신호를 지원하는가 (D의 XML 대조 재사용)
  ③같은 계열 요구끼리 인스턴스 정합. PXn 아닌 고정 명명 핀은 대상 외.
- 음성 시험 2종: 회로에 없는 넷 요구, 능력 밖 신호 요구.

  **4단계 기본형 완료 (2026-08-12 같은 날)**: check_pin_caps N단계.
  g431_devkit requires.json 7건 전부 확증 + 펌웨어측 인스턴스 정합
  (FW I2C=I2C1, FW USART=USART2 — 블록측과 합류 판정). 음성 2종 통과
  (SPI_MOSI 넷 부재, SDA에 SPI 요구 = 보유 신호 목록 제시하며 거부).
  이로써 **기본-우선 큐 전체 소진: 시나리오 A~G + 3·4단계 기본 = 전부
  🟢** (2026-08-08 서면 감사 → 08-12 실물 실증 완료). 남은 것은 전부
  고도화 백로그.

**검토 강화 2건 (2026-08-12, 사용자 "순서대로 진행해")**:
- ⓐ ST 핀 XML 표본 대조: PA2/PA15/PB7을 DS12589 두 표(핀 정의 p52/57/59
  + AF 표 p61/62)와 대조 — 전부 일치, XML 사료 신뢰 확증.
- ⓑ check_board A 재생성 검사를 카운트→**바이트 대조**로 강화 (같은
  개수의 다른 내용물을 통과시키는 맹점 제거). 생성이 바이트 결정적임을
  선실측(2회 생성 diff 동일) 후 채택, 음성 시험 = 1바이트 변조 파일 지목.
- 미결(발주와 묶임): 실보드 실행 검증. 반복·조합 실증은 고도화측 유지.

**제조 문서 출력 결정 (2026-08-12, 사용자 "발주까진 좀 힘들꺼 같고
필요문서 출력하는거 까지 하자")**: 발주는 보류, 문서까지만.
- build_fab.py → boards/<id>/fab/: ①거버+드릴 (kicad-cli pcb export
  gerbers/drill) ②BOM CSV (kicad-cli sch export bom — 참조·값·풋프린트·
  수량) ③배치좌표 POS (kicad-cli pcb export pos, mm) ④fab_report.json
  (파일 목록·크기·행수 대조).
- 검증: POS 행수 = SMT 풋프린트 수, BOM 행 전개 = 부품 수, 거버 장수 =
  동박 2 + 실크/마스크/외곽 — 숫자 대조를 fab_report에 기록. 발주 시
  rev 1.0 확정과 실보드 실행 검증이 같이 닫힌다 (보류 중).
- 아날로그 로드맵 1/5 vdda_split v0.1 완료 (같은 날): DS12589 Fig.16
  사료, 삼성/안트미크로 심볼 핀 기하 차이를 게이트가 적발한 사례 기록.

  **제조 문서 완료 (2026-08-12 같은 날)**: build_fab.py — 거버 9층+드릴,
  BOM 12행(19참조), POS 19행, fab_report 숫자 대조 전부 정합. 교차검증:
  드릴 32공(0.3 비아 + 0.6 기구), Edge_Cuts 드로우 실측 31.1×30.8mm.
  자체 집계 버그 2건(BOM 'C3-C5' 범위 미전개, 거버 확장자 미인지) 적발
  후 교정 — 검증 숫자도 검증 대상. 발주·rev 1.0·실보드 실행 검증은
  보류 상태 유지 (사용자 결정 대기).

**자동 배선 로드맵 (2026-08-16, 사용자 "자동 배선이 어렵다는 건 안다.
많은 기업에서 시도했고 모두 실패했지. 그땐 사람이 직접 코딩을 해서 그렇다.
지금은 AI가 있잖아, 그래서 개선하려는 거지. 예제를 학습하라고 했던 이유도
자동 배선을 하고 싶기 때문" / "시작해")**:

freerouting 한계 진단(실측 기반): ①미학 개념 없음(방향성·정렬·잔조각이
목표함수 밖, DSN direction 무시) ②넷 의미 모름(GND 트랙 84조각, 전원
neck-down) ③설계 의도 입력 채널 없음 ④막히면 포기(배치 되돌릴 줄 모름).
= "못 그리는" 게 아니라 **"왜 그렇게 그려야 하는지 모르는"** 라우터. 우리는
그 "왜"를 데모 10장(CV1~19)과 실측(PW1~8)으로 이미 뽑아둠.

경로 = **라우터를 버리는 게 아니라 라우터가 하는 일을 줄인다**:
- **1단계 (착수)**: 의미 있는 넷은 우리 코드가 규칙대로 **먼저** 그린다 —
  `generators/route_semantic.py`: ①디커플링/벌크 캡→IC 전원핀 최단 직결
  (P13 근접 배치가 전제, 같은 층 0.3~0.5폭) ②전원 넷 = 공급원에서 소비처로
  넷클래스 폭 고정, 층 전환은 비아 1개 이하 ③USB 차동쌍 = 두 선을 등간격
  나란히(스큐 자동 최소) ④GND = 존+스티칭(기존). 그린 트랙은 DSN에
  '기배선(고정 wire)'으로 넘겨 freerouting은 **잔여 신호만**. 성공 기준:
  PW2 폭미달 0, PW4 잔조각 비율 하락, 미배선 0 유지, DRC 0.
- 2단계: 잔여 신호도 우리 규칙 라우터 (2층 소형 SMD 한정 그리드 A*,
  비용함수에 PW3 방향성·꺾임 수·잔조각 페널티 직접 반영).
- 3단계: 데모 학습을 비용함수 가중치 수치화에 활용.
- 원칙: 매 단계 freerouting 단독 결과와 **같은 보드로 지표 비교**(PW1~5,
  미배선, DRC)를 기록 — 개선이 숫자로 보여야 다음 단계로.

  **1단계 1차 결과 (2026-08-16 같은 날)**: route_semantic.py — 디커플링
  직결 4/7(뒷면 캡 비아 포함), 차동쌍 실패(D1→U2 7mm, L/Z 경로 한계).
  대조: PW2 13→6, 잔조각 25.8→22.2%, 존 채움 +4%p, 트랙 182→159. 그러나
  **미배선 0→1** — 선행 배선이 라우터 경로를 막음(순서 문제, 다음 과제).
  **발견: freerouting은 비결정적** — 같은 입력에 실행마다 결과가 다름
  (미배선 1~5, USB 스큐 1.5~7.7mm 변동). 게이트 재현성의 적 → 2단계
  자체 라우터의 또 다른 근거(결정적 재생성이 게이트 전제). 당장은
  route_board가 N회 시도 후 지표 최선을 택하는 방식 검토.

  **설계 문서 (2026-08-16, 사용자 "설계 문서 먼저 써봐. AI를 적극 활용할
  수 있게, 키캐드에 붙여 쓸 수 있게, 너무 룰을 딱 정하면 범용성이 약해 —
  필요한 파라미터는 니가 정리해서 프로그램으로")**:
  boardworks/docs/autorouter-design.md v0.1 — 원칙(파라미터화·AI 우선
  인터페이스·결정적 엔진·DSN/SES 표준 경계·점진 대체·GPL 카피 금지),
  아키텍처 6단(파서→넷 분류→의미 배선→A* 그리드→PathFinder 협상→후처리),
  파라미터 목록 6군(fab/net_roles/cost/targets/layers/profiles, 각 항목
  why·range 동반), AI 활용 지점 4개, KiCad 통합 3경로(CLI→액션 플러그인→
  PCM), 지표·단계 R0~R4, 미결(언어·곡선·참고 소스 범위). 승인 대기.

**boardworks 공개 여부 (2026-08-16, 사용자)**: "공개할지 말지 아직 안
정했어. 제대로 동작되는지 확인되면 그때 해야겠지." — **비공개 유지**.
공개 검토의 선행 조건 = 실동작 확인 (실보드 실행 검증, 즉 발주 후).
그 전까지 README·문서 정비는 내부용으로만.
- **4단계 — 왕복 정합**: 회로 변경 → 펌웨어 diff 자동 제시 / 펌웨어의
  핀 요구 → 회로 능력 검증. AI(Claude)가 중재자.

**조종석**: VS Code 워크스페이스 하나에 펌웨어+하드웨어 폴더, kicad-studio/
KiCanvas 뷰어로 사장님이 에디터 안에서 회로·PCB 확인, KiCad는 편집 창.


**시나리오 검토 추가 (2026-08-08 사용자 지시 3건)**:
- **E. 깃 형상관리 (바닥)**: 하드웨어+펌웨어+board.json 한 레포. 푸시마다
  ERC·DRC·빌드 게이트(파트릴 방식 이식). rev=태그, 발주 거버=릴리스 자산.
  커밋마다 kicad-cli SVG 렌더로 **그림 diff**를 PR에 첨부 (텍스트 diff는
  기계용). 미결: 배선 중간 상태의 커밋 단위 관례.
- **F. 데이터시트 정확도 루프**: 모든 수치에 출처 필수(핀 능력·회로값·치수
  각각 페이지/그림). PDF 벡터 실측 3중 확인을 회로 값에도 적용. MCU 핀
  능력은 제조사 기계가독 자료(ST 핀 CSV, ESP-IDF 헤더)가 1차 사료.
  미결: 데이터시트 없는 부품 처리(미검증 딱지 vs 차단).
- **G. 부품 락 + 자동 패턴**: 사용자가 위치 중요 부품(커넥터·홀·안테나·
  방열)만 락 → 나머지 자동 배치 → freerouting을 락 존중으로 실행 → DRC →
  사람 검토. '배선은 전적으로 사람'(초안)을 수정: 단순 신호는 자동+DRC,
  전원 대전류·고속·아날로그만 사람 필수. 선행: 1~2층 보드로 freerouting
  품질 파일럿.


**기술 원칙 (2026-08-08 사용자 지시)**:
- **오픈소스 적극 활용, 없으면 제작.** 기능별로 모듈화해서 조립한다.
- **설계 규칙은 기능별 규칙집으로 관리**: `rules/` 디렉토리에 도메인별
  파일(핀할당/배치/배선/전원...)로 버전 관리하고, 기계화 가능한 규칙은
  게이트로 강제한다. 첫 규칙 (사용자 확정): **핀 할당은 AI 초안으로 가되,
  특수 기능 핀이 아닌 한 PCB에서 그 부품이 놓일 방향의 핀을 배정한다**
  (배선 짧고 깨끗해짐 — 배치와 핀맵의 결합).
- **데이터시트 없는 부품**: ①링크를 사용자에게 제시해 다운로드 요청
  ②링크조차 없으면 부품에 '데이터시트 미확보' 표시를 남기고 진행.
- 배선 중간 커밋 관례 항목은 폐기 — 'DRC 통과 시점마다 저장'으로 단순 확정.

**구현 가능성 점검표 (2026-08-08 오픈소스 실사)**:
| 모듈 | 오픈소스 후보 | 판정 |
|------|-------------|------|
| 회로도 생성(가독) | atopile(v0.16, 코드→PCB) — **회로도 출력이 없어 부적합** (우리는 사람이 읽는 회로도가 1급 산출물) | **자체** (build_block 확장) + atopile의 모듈·수식검증 개념 차용 |
| ERC/DRC/렌더/거버 | kicad-cli (공식) | **채택** (이미 사용 중) |
| 그림 diff (형상관리 E) | **kiri** — KiCad≥5 지원, kicad-cli 기반 | **채택** (파일럿) |
| 자동 배선 (락+패턴 G) | **freerouting** — DSN/SES 교환 | **채택 후보** (KiCad10 왕복 파일럿 필수) |
| PCB 라이브 제어 | KiCad IPC + kipy (공식) | **채택** (설치 완료) |
| 핀 할당(방향 인식) | 마땅한 것 없음 (CubeMX는 비공개) | **자체** — MCU 핀 능력표(제조사 CSV/헤더) + 방향 규칙 |
| pins.h 생성 | 단순 문제 | **자체** |
| 부품 공급 | 파트릴 (자체 보유) | 채택 |
| VS Code 뷰어 | kicad-studio / KiCanvas | 채택 후보 (품질 확인) |
| 펌웨어 뼈대 | ESP-IDF·STM32Cube 공식 템플릿 | 채택 + 자체 결합 |


**파일럿 결과 (2026-08-08 실측)**:
- **freerouting 왕복: 기계적으로 성공** — pcbnew로 DSN 내보내기(기존 배선
  815개 제거한 interf_u 데모, 네트 174) → freerouting 2.3.0(포터블 Java 25,
  시스템 Java 21은 클래스버전 불일치) 81초, 미배선 0 → SES 재수입(세그먼트
  890/비아 38) → 커널 DRC. **품질은 미달**: clearance 193건 + 미연결 8
  (단, 시험판이 구식 THT 밀집 데모라 규칙 불일치 요인 섞임 — footprint 경고
  25건은 데모 자체 문제). 판정: **조건부 채택** — 파이프라인은 확보,
  실사용 판정은 대표 보드(현대식 2층 SMD)와 넷클래스 정리 후 재실측.
- **kiri: 윈도우 부적합 확정** (공식 문서가 비추천 명시) — 내부 원리(kicad-cli
  SVG 렌더 비교)가 단순하므로 그림 diff는 **자체 경량 스크립트**로 전환.
  (오픈소스 우선 원칙의 예외 사유: 플랫폼 미지원)


**시나리오 검증 감사표 (2026-08-08 종결)**: 전 시나리오 '가능' 판정, 봉쇄 0.
- 🟢 실증/소스확정: C(파트릴 루프), D(ST 공식 핀 XML·ESP-IDF 헤더 실존 확인),
  E(푸시-게이트 상시 운용, 넷리스트 추출 실증), F(PDF 3중 확인 파이프라인)
- 🟡 구현 대기: A/B(블록·board.json·pins.h — 공통 병목 = 가독 배치 규칙),
  G(왕복 실증, 품질 재실측 대기)
- diff는 3층 구조로 확정: ①넷리스트(전기적 진실, 게이트) ②BOM ③렌더(사람용).
  그림 단독 판정 금지 (2026-08-08 사용자 지적).

**정직한 한계 (기획 시점)**:
- 회로도 라이브 API 없음 → 회로도는 파일 생성 방식 유지 (KiCad가 열면 반영)
- §24 가독 배치 규칙이 아직 미확정 — 1단계의 선행 조건 (함께 그리기로 확정)
- 자동배선·시뮬레이션은 범위 외 (필요 시 별도 판단)
- 1차 사료 원칙 유지: 블록은 데이터시트 회로, 핀 능력표는 MCU 데이터시트.

**파트릴과의 관계**: 부품(§21)→블록(§24)→보드(§25)의 자연 연장. 우선은
사장님 자체 개발 자산이며, 공개 여부는 §24와 같이 별도 결정.

## §26. 설계 작업 8단계 구조 (2026-08-16 사용자 지시)

사용자 원문: "전체적인 작업 구조의 분리가 필요해. 요구사항을 받고, 요구사항을
충족하는 부품을 찾고, 부품의 수급과 성능을 온라인과 데이터시트에서 확인, 각
부품을 모듈화하고, 전체적인 회로 구성을 해서 검토, 다음 PCB 요구사항에 맞게
부품 배치, 배선, 거버파일 출력으로 단계별로 있어야 각각의 파라미터들을 조율
가능하지 않을까." / "단계에서도 필요하면 세부 단계로 가야 하는 거야."

**원칙**
- 단계마다 **입력 문서 → 파라미터 파일 → 산출물 → 게이트** 네 가지를 갖는다.
  단계 사이는 파일로만 연결(한 단계의 산출물이 다음 단계의 입력).
- **재귀적**: 세부 단계도 같은 형식으로 쪼갠다 (예: S7 배선 = 의미배선 →
  안내선 → 가닥별 A* → 협상 → 후처리 → 마감, 각각 자기 파라미터·리포트).
- 파라미터는 R0 방식(value/unit/range/why/source)으로 통일 — AI가 읽고
  조율·설명한다. 코드 상수 금지.
- 각 단계는 독립 실행·독립 게이트가 가능해야 한다 (부분 재실행).

**단계표** (boardworks 기준)
| 단계 | 입력 | 파라미터 | 산출물 | 게이트 | 상태 2026-08-16 |
|---|---|---|---|---|---|
| S1 요구사항 | 사용자 요구(기능·전원·인터페이스·크기·환경) | requirements 스키마 | boards/<id>/requirements.json | 필수 항목·모순 검사 | **없음** — board.json 설명 문장뿐 |
| S2 부품 탐색 | S1 | 탐색 규칙(카탈로그 우선, 대안 수) | candidates.json (역할별 후보) | 역할당 후보 ≥1 | 없음 (파트릴 검색+AI 판단이 암묵) |
| S3 부품 확인 | S2 | 공급처·재고 API, 데이터시트 검증 항목 | parts_verified.json (수급·핵심 성능·출처) | 미확보 표시·링크 요청 | 부분 (데이터시트만, F 출처 필드) |
| S4 모듈화 | S3 | 블록 규칙(R1~R19, P13 place) | blocks/<id>/block.json + .kicad_sch | check_block | ✅ (블록 8종) |
| S5 회로 구성·검토 | S4 | board.json 스키마, 핀 능력(D) | boards/<id>/*.kicad_sch, pins.h, net_alias | check_board A~C, check_pin_caps | ✅ |
| S6 배치 | S5 + PCB 요구(크기·층·커넥터 위치·락) | 배치 규칙 P1~P16 (파라미터화 예정) | .kicad_pcb(배치), place_report | check_board E~G | ✅ (규칙은 아직 코드 안) |
| S7 배선 | S6 | router/profiles (R0) | .kicad_pcb(배선), routing_report | check_board H (PW1~9) | 진행 중 (R1 완료·R2 착수) |
| S8 출력 | S7 | 제조사 프로파일(층·최소치·파일 형식) | fab/ (거버·드릴·BOM·POS) | fab_report 숫자 대조 | ✅ (제조사 프로파일은 미분리) |

**갭 (다음 작업 후보)**: ①S1 requirements.json 스키마 ②S2/S3 부품 탐색·확인
파이프라인(파트릴 API + 공급처 조회 + 데이터시트 항목 검증) ③S6 배치 규칙
파라미터화(P 규칙을 R0 방식으로) ④S8 제조사 프로파일 분리 ⑤단계별
파라미터 폴더 통일 (`boards/<id>/params/s1..s8.json` 또는 단계별 파일).

**단계 실행기**: `boardworks run <board> --from S5 --to S7` 형태의 단일 진입
(각 단계 스크립트를 순서·의존으로 호출, 실패 시 어느 단계인지 보고) — 구현 예정.
