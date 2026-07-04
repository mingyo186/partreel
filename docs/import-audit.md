# 검증-수입(Verified Import) 후보 감사 (2026-07-04, §21-6②)

에이전트 감사 — 각 라이선스는 실제 LICENSE/README에서 확인(추측 아님). 착수 여부는 사용자 결정 대기.

## 핵심 발견

1. **⭐ CERN KiCad 라이브러리 (gitlab.com/ohwr/cern-kicad-libs)** — **~17,000부품**, 2026-05 공개,
   **CERN-OHL-P-2.0 (허용적, OSI 승인)**, KiCad 9, 활발히 유지보수, REUSE/SPDX 파일별 라이선스.
   규모 대비 법적 리스크 최저 — 1순위. 단 sqlite+.kicad_dbl 데이터베이스 구조라 매핑 단계 필요.
2. **SparkFun (CC-BY-4.0)** — 우리와 라이선스 동일, 608 풋프린트+321 STEP, KiCad 9, 활성.
   **수입 파이프라인 파일럿으로 최적** (마찰 0). 주의: LICENSE 파일 없이 README 서술뿐 →
   수입 시점 README 스냅샷 보관.
3. **Espressif는 Apache가 아니라 CC-BY-SA-4.0** — 내 가정이 틀렸음(감사가 정정). 디자인 사용
   예외는 있으나 라이브러리 재배포엔 SA 강제 → CC-BY 풀에 못 섞음.
4. **MIT 소형 보석들**: CDFER/JLCPCB-Kicad-Library (184sym/303fp/278STEP — 단 EasyEDA 유래
   지오메트리 출처 스팟체크 필요), ai03 MX 키보드 스위치 라이브러리.
5. **LCSC/EasyEDA 벌크 변환 금지** — ToS상 재배포 그랜트 없음, 테이크다운 리스크.
   허용 패턴은 사용자 개시 단건 클라이언트 변환뿐.
6. **스킵**: Adafruit(KiCad 라이브러리 자체가 없고 Eagle 라이브러리는 무라이선스),
   WeAct(라이브러리 레포 없음), DigiKey(비유지보수+KiCad5 레거시+3D 없음 — SA섹션으로도 후순위).

## 아키텍처 함의 (중요)

- **부품별 라이선스 메타데이터 필요**: 전역 CC-BY-4.0 단일 라이선스 → `license` 필드가 이미
  meta에 있으므로 수입 부품은 원 라이선스 유지(CERN-OHL-P / CC-BY-SA 섹션 분리). **재라이선스
  금지** — 허용적끼리라도 남의 저작물 라이선스를 갈아붙이지 않는다(출처+원라이선스 표기).
- CC-BY-SA 자산은 명확히 분리된 섹션에서만 호스팅 가능, CC-BY 풀과 파생 혼합 금지.
- 자체 생성(우리 치수 데이터→생성기)이 장기적으로 가장 깨끗 — 수입은 커버리지 부트스트랩.

## 권고 순서

① CERN(17k, 매핑 작업 필요) ② SparkFun(파일럿 최적) ③ MIT 소형(JLCPCB lib 출처 확인 후,
MX 스위치) ④ Espressif/Seeed/arduino-lib = SA 섹션 신설 시 ⑤ DigiKey 보류 ⑥ LCSC 벌크 금지.

## 수입 시 게이트 요건 (기존 §16 + 추가)

- 원 라이선스·출처(레포+커밋 해시)·원저자 → meta.provenance에 기록
- 우리 게이트 전체 통과(구조/KLC/렌더/z-fight/STEP 커널) — 실패분은 수입 제외 목록으로
- verified 플래그는 게이트 통과 의미로만; 치수 데이터시트 대조는 별도 단계(수입분은 초기
  unverified→gates-passed 등급, §17 신뢰등급 활용)
