"""
z-fighting(공면 겹침) 자동 검출 게이트 (§14-C — "microSD 또 z-fight" 사건으로 자동화).
실행: python generators/check_zfight.py   (실패 시 비0 종료 → CI 게이트)

각 부품 GLB의 메시 쌍에 대해: 같은 축·같은 법선 방향·같은 평면 오프셋의
삼각형들이 2D로 겹치면 = 렌더러가 어느 면을 그릴지 못 정하는 z-fight → FAIL.
(반대 방향 법선의 공면은 backface culling으로 무해 — 검출 제외)
"""
import json
import os
import sys

import numpy as np
import trimesh

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
EPS_PLANE = 1e-3   # 같은 평면 판정 (mm)
MIN_OVER = 0.05    # 이 이상 겹쳐야 문제로 침 (mm, 두 축 모두)


def plane_rects(mesh):
    """축정렬 면들을 (axis, normal부호, 평면오프셋) -> 2D 사각형 목록으로."""
    out = {}
    tris = mesh.triangles
    normals = mesh.face_normals
    for axis in range(3):
        idx = np.where(np.abs(normals[:, axis]) > 0.999)[0]
        for i in idx:
            sign = 1 if normals[i, axis] > 0 else -1
            off = round(float(tris[i, 0, axis]) / EPS_PLANE) * EPS_PLANE
            other = [a for a in range(3) if a != axis]
            pts = tris[i][:, other]
            out.setdefault((axis, sign, round(off, 3)), []).append(
                (pts.min(axis=0), pts.max(axis=0)))
    return out


def rects_overlap(r1, r2):
    lo = np.maximum(r1[0], r2[0])
    hi = np.minimum(r1[1], r2[1])
    d = hi - lo
    return d[0] > MIN_OVER and d[1] > MIN_OVER


def check_part(glb_path):
    scene = trimesh.load(glb_path)
    geoms = list(scene.geometry.items())
    issues = []
    for a in range(len(geoms)):
        for b in range(a + 1, len(geoms)):
            (na, ma), (nb, mb) = geoms[a], geoms[b]
            pa, pb = plane_rects(ma), plane_rects(mb)
            for key in set(pa) & set(pb):
                hit = any(rects_overlap(r1, r2) for r1 in pa[key] for r2 in pb[key])
                if hit:
                    ax = "XYZ"[key[0]]
                    issues.append(f"{na}~{nb}: {ax}={key[2]} (normal {key[1]:+d}) 공면 겹침")
                    break
    return issues


def main():
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    total = 0
    for p in index["parts"]:
        glb = os.path.join(ROOT, p["path"], f"{p['id']}.glb")
        if not os.path.exists(glb):
            continue
        issues = check_part(glb)
        if issues:
            total += len(issues)
            print(f"ZFIGHT {p['id']}:")
            for i in issues:
                print(f"   - {i}")
    print(f"\n{'PASS' if total == 0 else 'FAIL'}: {len(index['parts'])} parts, {total} coplanar overlaps")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
