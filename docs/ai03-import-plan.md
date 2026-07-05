# ai03 MX_V2 수입 계획 (Wave A) — 2026-07-05

REQUIREMENTS §21-6ⓒ 수입 확대 ③ 실행안. 스팟체크 결과 포함.

## 스팟체크 (통과)

- 소스: https://github.com/ai03-2725/MX_V2 commit `0b379ee` (구 MX_Alps_Hybrid는
  deprecated — 후속작으로 대체). 라이선스 **MIT** (LICENSE 파일 존재, (c) ai03).
- 출처: README "Designed from scratch using official datasheets and accurate
  measurements" + 템플릿→generate.py 파라메트릭 구조. EasyEDA/KiCad 공식 유래 흔적
  없음(파일 내 마커·명명 규칙 확인). **CDFER/JLCPCB와 달리 깨끗** (그쪽은 탈락 —
  docs/import-audit.md).
- 갭 확인 (GitLab kicad-footprints master, Button_Switch_Keyboard.pretty 29파일):
  공식 = Cherry MX PCB/Plate + Matias뿐. **핫스왑·Gateron KS-33 로우프로파일·
  Kailh Choc V2(PG1353)·MX/Alps 하이브리드·스태빌라이저 전부 공식 부재** = 진짜 갭.

## 범위

| 라이브러리 | 수 | 처리 |
|---|---|---|
| MX_Solderable / MX_Hotswap / MX_Alps_Hybrid / Alps_Solderable | 109 | 수입 |
| Gateron_KS33_{Solderable,Hotswap} / Kailh_PG1353_{Solderable,Hotswap} | 36 | 수입 |
| Switch_Misc (스위치 정렬 LED 4종×변형) | 8 | 수입 |
| Alps_MX_Stabilizers | 21 | **보류** — 전기 핀 0 = 기계 전용 부품 스키마 필요 (GX12/16과 동일 보류사유) |
| Template.pretty | 8 | 제외 (업스트림이 "Do not use in production" 명시) |

## 결정 사항

1. **심볼**: 업스트림은 의도적으로 심볼 없음(KiCad 기본 SW_Push와 페어링 전제).
   → 우리가 최소 2핀 심볼을 저작해 페어링(스위치=SW 심볼, LED 부품=LED 심볼).
   meta.import.modifications에 "symbol authored by PartReel" 기록. 부품 라이선스는
   MIT 유지(우리 심볼도 MIT로 냄 — 단일 라이선스 유지, 재라이선스 아님: 우리 저작물).
2. **레이어 수정(기록)**: 키보드 관례상 아웃라인이 Dwgs.User에 있고 실크 없음 →
   ①Dwgs.User 도형을 F.Fab로 재매핑 ②pad1 옆 실크 핀1 마커 점 추가(스위치 장착 후
   가려짐 — 무해) ③코트야드 부재 시 자동 생성(bbox+0.25, CERN과 동일). 전부
   modifications에 기록.
3. **3D**: 업스트림 3D는 핫스왑 소켓 STEP 3종뿐(스위치 본체 없음, 오프셋 배치) →
   Wave A는 전량 **verified-2D 등급**(CERN과 동일: files에 step/glb 없음, 3D탭 숨김,
   model 참조 제거). 파라메트릭 스위치 3D 백필은 후속.
4. **명명/분류**: id `ai03_<slug>`, category `switch`(신설), family "ai03 MX Hotswap"
   등 라이브러리별. datasheet = 업스트림 .kicad_mod blob URL(부품별 도면 URL 부재).
5. **라이선스**: MIT 유지 + check_render 허용목록에 MIT 추가. ATTRIBUTIONS.md ai03 절
   + MIT 전문은 부품 meta의 attribution으로 충족(MIT §: 저작권 고지 유지 — LICENSES/
   MIT-ai03.txt 동봉).

## 게이트/드롭 방침

CERN Wave 0과 동일: 게이트 실패분은 이유 로그와 함께 드롭
(docs/import-ai03-dropped.json), 수입 로그 docs/import-ai03-log.json.
