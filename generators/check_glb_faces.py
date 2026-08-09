"""
수입 GLB 면 수 손실 게이트 (REQUIREMENTS §21-C 2026-08-09 LOD2 사건).
meta.import.source_faces(업스트림 원본 면 수)가 기록된 부품의 GLB를 로드해
실제 면 수가 그보다 적으면 FAIL — 깨진 데이터/LOD 변환이 다시 배포되는 것을 막는다.
'업스트림 대비 손실' 기준이므로 원래 면이 적은 단순 박스 모델은 오탐 없음.
source_faces 미기록 부품(수리 이전 수입분·자체 제작분)은 검사 대상 아님.
실행: python generators/check_glb_faces.py  (PART_SCOPE 지원)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import trimesh
    from scope import scoped_parts
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    parts = scoped_parts(index["parts"])
    errs = checked = 0
    for p in parts:
        d = os.path.join(ROOT, p["path"])
        meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
        want = (meta.get("import") or {}).get("source_faces")
        glb = meta.get("files", {}).get("preview", "")
        if not want or not glb.endswith(".glb"):
            continue
        fpath = os.path.join(d, glb)
        if not os.path.exists(fpath):
            continue  # R2 전용 체크아웃 — 파일 존재는 check_render/check_r2 소관
        try:
            faces = len(trimesh.load(fpath, force="mesh").faces)
        except Exception as e:
            print(f"FAIL {p['id']}: {glb} 로드 불가 ({e})")
            errs += 1
            continue
        if faces < want:
            print(f"FAIL {p['id']}: GLB {faces}면 < 업스트림 원본 {want}면 — 손실 변환")
            errs += 1
        checked += 1
    print(f"{'PASS' if not errs else 'FAIL'}: {checked} GLB face-checked, {errs} issues")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
