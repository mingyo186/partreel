# PartReel

**로그인 없는, KiCad 네이티브 오픈 부품 라이브러리.**
부품을 데이터시트 치수로 파라메트릭하게 생성해서, 가입 없이 바로 다운로드.

> SnapEDA 같은 사이트인데 — 로그인 없고, 받은 걸 믿을 수 있고(생성 기반), KiCad에 진심.

## 무엇

- 심볼(.kicad_sym) + 풋프린트(.kicad_mod) + 3D(STEP/GLB)를 부품마다 제공
- **로그인/가입 불필요**, 즉시 다운로드
- 치수 기반 결정론적 생성 → 출처 투명, git으로 버전관리
- 현재: **JST PH 커넥터 패밀리 (2~16핀)**. 확장 예정: 다른 커넥터 → IC → 기구 표준품

## 구조

```
index.html, assets/      웹사이트 (정적, three.js 3D 프리뷰)
index.json               검색 인덱스
library/                 부품 자산 (CC-BY-4.0)
generators/              파라메트릭 생성기 (Python; KiCad 텍스트 + FreeCAD 3D)
```

## 로컬 실행

```bash
python -m http.server 8000 --directory .
# http://localhost:8000
```

## 생성 (예: JST PH)

```bash
python generators/jst_ph.py          # 풋프린트/심볼/meta (텍스트)
freecadcmd generators/jst_ph_3d.py   # 3D STEP/STL (FreeCAD 헤드리스)
python generators/stl_to_glb.py      # 컬러 GLB (웹 프리뷰)
```

## 라이선스

- **코드** (generators, 웹사이트): [MIT](LICENSE)
- **부품 자산** (library/): [CC-BY-4.0](library/LICENSE)

치수는 제조사 데이터시트 기반이며 as-is로 제공됩니다. 제조 전 검증을 권장합니다.
