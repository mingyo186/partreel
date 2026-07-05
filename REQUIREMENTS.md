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

## 19. 온디맨드 셀프-그로잉 레지스트리 (확정 2026-07)

**원칙(사용자)**: 파라메트릭 부품(핀헤더 등)은 **우리가 사전 대량생성하지 않는다** — 필요한 사용자/에이전트가 요청 순간에 뽑아 쓰게 한다. 단, **생성 결과는 반드시 레지스트리에 영구 등록**된다(로컬 생성이면 카탈로그·SEO·재사용에 안 쌓임). 효과: 카탈로그가 실수요 순서로 성장(§4 수요기반 원칙 일치, 얇은 대량 페이지 SEO 리스크 회피), 재생성 낭비 0, 서버 0 유지.

**흐름**: `get_part(없음)` → MCP `request_part(family, pins)` → 워커가 GitHub `repository_dispatch` → **GitHub Actions가 생성기 실행**(텍스트→FreeCAD 3D→GLB→SVG→index/site/api) → QA 게이트 → **자동 커밋+인라인 배포**(주의: GITHUB_TOKEN 푸시는 deploy.yml을 안 깨우므로 생성 워크플로가 배포까지 인라인 수행) → 몇 분 뒤 라이브 → 요청자에게 예상 id/URL 반환.

**구성요소**: `gen_connectors.py`의 `ONDEMAND` 패밀리(핀헤더 2.54/2.0/1.27mm, 1~40핀 — 치수는 KiCad 공식 대조) · `generators/generate_one.py`(단일 부품 오케스트레이터, env FAMILY/PINS) · `.github/workflows/generate-part.yml`(repository_dispatch type=generate-part) · MCP `request_part`(허용 패밀리·범위 검증 후 dispatch; 토큰 fine-grained PAT에 Issues+Contents R/W — 권한 수정해도 토큰 값 불변).

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

5. **AI 발견 4종 세트 (사용자 확정 2026-07-04, "색인만으론 부족")**: 블라인드 실험 재분석 결과 색인은 필요조건일 뿐. ①**GitHub 검색성** — 에이전트 실동선은 구글이 아니라 GitHub/GitLab 코드검색: 레포 topics·설명·README 부품 인덱스(자동생성, build_readme.py)로 부품명 검색이 레포에 걸리게. ②**provenance 공개** — 도착 후 5초 신뢰: 부품 API에 기계가독 provenance(치수 출처, 게이트 목록, CI 강제 사실, 생성기 소스 링크) 노출. 자가생성 폴백(에이전트가 검색 대신 직접 생성)을 멈추는 건 "검증 과정을 직접 확인 가능"뿐. ③색인(진행 중, 사이트맵 79p) ④**인용 축적** — §20 런칭의 진짜 기능 = 차세대 모델 훈련 데이터 진입(색인 성숙 후).

6. **스케일 전환 (사용자 확정 2026-07-04, "이 정도 부품으로 되겠어?" → 수정: "종류가 많아야 봇들의 확장에 도움")**: 93개는 시드. **역할 분담 확정**: **손 = 새 종류**(새 패키지/패밀리 = 봇이 확장할 템플릿), **봇 = 변형**(순수 config 변형은 손으로 안 만듦 — §19 온디맨드 일반화 + config 한 줄 PR 레시피; 변형 페이지는 중복콘텐츠 리스크도 있음), **수입 = 규모**(종류 폭의 본명). 실행: ⓐ순수 변형(LDO 전압 12종·SY 등급·MAX17049)은 request_part **변형 패밀리 온디맨드**로 (ht73xx/ht78xx/sy8008/max1704x — 조사로 실존 품번 검증 완료: docs/gap-list.md) ⓑ배치 4차 = **진짜 새 종류만** ~14종 (QMC5883P·DHT20·AHT25·AHT30·TP4054·TM1638·TTP224/226·디스플레이 모듈 7종) ⓒ**SparkFun 수입 파일럿 착수 (사용자 "추천대로 진행" 2026-07-05)** — 결정: ①수입품 meta에 `origin:"imported"` + `import`(source_repo/commit/파일/attribution/수정목록), verified=게이트통과 의미 유지 ②패시브(저항/캐패시터 값변형) 제외 ③파일럿 GLB는 단색(중립 그레이, 메시명 "imported" — merged-pins 게이트는 metal 메시에만 적용되므로 자연 면제) ④코트야드 부재 시 자동 생성(패드+팹 bbox+0.25, 수정목록 기록); 실크 부재분은 파일럿에서 드롭(게이트 완화 대신 — 로그 기록) ⑤명명 sparkfun_<slug>, 1차 물결 = Sensor·GNSS·RF·커넥터(패시브/Aesthetic/멀티유닛 제외) ⑥소스 커밋 고정 2423e36a, ATTRIBUTIONS.md 신설 ⑦STEP→GLB는 신규 step_to_glb 경로(FreeCAD 테셀레이션). 파이프라인 오프라인 실행(CI는 기존 qa만). 상세: scratchpad sparkfun/PILOT_PLAN.md.
**수입 확대 (사용자 확정 2026-07-05, "무료를 더 끌어쓰자 — 이름만 남기면 됨 + 저쪽엔 에이전트 전용 공간이 없다")**: 허용적 라이선스 라이브러리를 계속 수입 — 가치는 복사가 아니라 **에이전트-네이티브 승격**(부품별 API/MCP/번들/게이트/provenance/피드백 — 원 레포들엔 전무). 순서: ①**CERN Wave 0 착수** (~425: Crystals+LEMO; 시나리오 C=메타+에셋 Pages 내, R2는 Wave 2 전 별도 확인; verified-2D 등급=3D 없는 부품은 files에서 step/glb 제외+페이지 3D탭 숨김; GENERIC 3,324 제외; NRND는 수명주기 표기; 멀티유닛은 Wave 0 스킵 — docs/cern-import-plan.md) — **Wave 0 완료 (2026-07-05)**: 425 대상 → 수입 423 → 게이트 후 **318 배포** (탈락 105 = 렌더러 지오메트리 갭 104 + 오버랩 1, docs/import-cern-wave0-dropped.json; 스킵 2 = 멀티유닛/참조부재, docs/import-cern-wave0-log.json). 산출: import_cern.py(sqlite 진실원, 균형괄호 model 제거 — §14-H 재확인, fp_poly 포함 자동 코트야드), verified-2D 등급 구현(validate_step/check_zfight 면제, 3D탭 숨김+풋프린트 기본, part.js v8, API `tier` 필드), check_render 라이선스 허용목록 {CC-BY-4.0, CERN-OHL-P-2.0} (수입품 원 라이선스 유지 + 자체생성은 CC-BY-4.0 강제 유지), ATTRIBUTIONS.md CERN 절 + LICENSES/CERN-OHL-P-2.0.txt (§3.1/§3.3 수정고지+날짜=meta.import). 라이브 검증: 545부품(cern 318), 페이지/kicad_mod/API 200. Wave 1 전 과제: 렌더러 폴리곤 지오메트리 104종 (fp_arc/원형패드열 등), 공유 패키지 스키마. ②~~CDFER/JLCPCB MIT 라이브러리~~ — **스팟체크 탈락(2026-07-05)**: 풋프린트 62/118=LCSC 변환물(테이크다운 리스크)+35/118=KiCad 공식 산출물의 MIT 재표기(재라이선스 무효 의심) → 수입 제외, 상세 docs/import-audit.md ③ai03 MX 스위치 — **스팟체크 통과, MX_V2로 대체 착수(2026-07-05)**: 구 MX_Alps_Hybrid는 deprecated → 후속작 MX_V2(MIT, "designed from scratch from datasheets", 갭 확인=공식은 MX PCB/Plate+Matias 29종뿐이라 핫스왑·Gateron KS33·Choc V2·하이브리드 전부 갭). Wave A=153fp(스태빌라이저 21=기계전용 스키마 필요로 보류, Template 8 제외), 심볼은 우리가 저작(SW/LED 2핀), Dwgs.User→F.Fab 재매핑+실크 핀1 마커+자동 코트야드(기록), 전량 verified-2D, 라이선스 MIT 유지+허용목록 추가 — 상세 docs/ai03-import-plan.md ④SA 섹션(Espressif 등)은 별도 결정.

**중기 방향(사용자 2026-07-04)**:
- **검증-수입(verified import)**: 규모가 커지면 기존 오픈 자산(타 라이브러리/기여물)을 **우리 게이트로 검증해서 들여온다** — 처음부터 만드는 것보다 싸고, "검증됐다는 보증"이 우리 부가가치(§17 수익 원칙과 일치). 라이선스 호환 필수(CC-BY-SA는 카피 불가 — §14 규칙 유지, 치수=사실만 추출).
- **풋프린트 중복 제거/재활용**: 풋프린트·3D는 패키지(SOT-23, 0603, SOIC-8...) 단위로 중복이 극심 → **부품→공유 패키지 참조 구조**로 리소스·용량 절약(같은 SOIC-8을 부품마다 복제하지 않음). 스토리지뿐 아니라 검증도 패키지 1회로 끝남. 카탈로그가 커지기 전에 스키마에 반영할 것.

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

## 12. 미결정 / 오픈 이슈

- [x] 프로젝트/사이트 이름 = **PartReel** (2026-06-20). 사유: "reel in(끌어오다)" + 전자부품 릴(reel) 이중의미, 브랜드 충돌 없음, partreel.com 미등록(.com 확보 가능). 후보 PadForge/PartForge/OpenParts 등은 전부 선점됨.
- [ ] partreel.com 실제 등록 (Cloudflare/Namecheap)
- [ ] 자체 라이선스 종류 (MIT? CC-BY?)
- [x] 첫 커넥터 패밀리 = **JST-PH 확정** (2026-06-20). 순서 = 얇은 수직 슬라이스 확정.
- [x] JST-PH 치수 검증 (2026-06-20) — KiCad 공식 Connector_JST(데이터시트 기반)와 일치 확인.
- [x] 라이선스 (2026-06-20): **코드=MIT, 부품 자산=CC-BY-4.0**. (층별 분리: 소프트웨어 MIT / CAD 자산 CC-BY)
- [ ] 심볼 핀리스트 자동 추출 방법 (데이터시트 비전LLM vs 수동, 2단계 이슈)
- [ ] 수요신호 체계적 채굴(InstaPart 목록/포럼 스크랩)은 미실시 — 방향성 신호만 확보
