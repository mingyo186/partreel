"""
정본 문서 아티팩트 무결성 카나리아 (REQUIREMENTS §21-C).

배경: 2026-07-27 check_provenance 수시 실행이 정본 docs/provenance-report.json
(수입 제외 목록의 근거, 106종 판정)을 덮어쓰는 사고 2회 — 정본이 비면 다음
물결 수입에서 라이선스 위험 부품이 통과된다. check_provenance는 이제
--canonical 없이는 정본을 쓰지 않지만, 이 카나리아가 정본 상태 자체를 검증한다.

검사: provenance-report.json이 JSON 리스트이고, IDENTICAL 판정을 1건 이상
포함할 것 (공식 15,447종과의 대조에서 IDENTICAL 0건 = 덮어쓰기 의심).
실행: python generators/check_docs_integrity.py
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def main():
    path = os.path.join(ROOT, "docs", "provenance-report.json")
    try:
        rep = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"FAIL: provenance-report.json unreadable: {e}")
        return 1
    if not isinstance(rep, list) or len(rep) < 50:
        print(f"FAIL: provenance-report.json suspicious "
              f"(entries={len(rep) if isinstance(rep, list) else 'not-a-list'}, "
              "expected >=50) — 정본 클로버 의심")
        return 1
    n_ident = sum(1 for r in rep if r.get("verdict") == "IDENTICAL")
    if n_ident == 0:
        print("FAIL: provenance-report.json has no IDENTICAL verdicts — "
              "정본 클로버 의심 (수입 제외 목록이 비게 됨)")
        return 1
    print(f"PASS: provenance-report.json intact "
          f"({len(rep)} entries, {n_ident} IDENTICAL)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
