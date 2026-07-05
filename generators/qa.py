"""
품질 검사 일괄 실행기 — 한 명령으로 모든 자동 게이트 실행.
실행: python generators/qa.py   (하나라도 실패하면 비0 종료)

포함(순수 파이썬, CI 게이트와 동일):
  - validate_kicad.py  구조(패드/레이어/피치/1번핀)
  - check_overlap.py   글자 겹침
  - check_render.py     렌더 완전성(파일존재/패드·외곽선 수/슬롯 obround/심볼 핀)
별도(FreeCAD 필요, 로컬): freecadcmd generators/validate_step.py  (STEP 솔리드 유효성)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKS = ["validate_kicad.py", "check_overlap.py", "check_render.py", "check_zfight.py",
          "check_asset_hashes.py", "check_r2.py", "check_visual.py"]

failed = []
for c in CHECKS:
    print(f"\n===== {c} =====")
    if subprocess.run([sys.executable, os.path.join(HERE, c)]).returncode != 0:
        failed.append(c)

print("\n" + "=" * 40)
if failed:
    print("[FAIL] failed gates:", ", ".join(failed))
    sys.exit(1)
print("[OK] ALL QUALITY GATES PASS")
