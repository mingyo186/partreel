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


def check_merged_pins(glb_path, expected):
    """핀 뭉침 검출: 금속(2번째) 메시가 접점 2개 이상인데 연결체 1개면 = 통짜 스트립."""
    if not expected or expected < 2:
        return None
    scene = trimesh.load(glb_path)
    # 금속 메시는 이름("pins")으로 식별; 옛 GLB(이름 없음)는 두 번째 메시 폴백
    metal = None
    for name, g in scene.geometry.items():
        if "pins" in name.lower():
            metal = g
            break
    if metal is None:
        geoms = list(scene.geometry.values())
        if len(geoms) < 2:
            return None
        metal = geoms[1]
    bodies = len(metal.split(only_watertight=False))
    # 줄 단위 뭉침도 검출: 연결체 수가 기대 핀수의 60% 미만이면 FAIL
    # (걸윙=핀당 2조각이 fuse로 1조각씩, EP/실드 여유 감안해 60% 문턱)
    if bodies >= 2 and bodies < expected * 0.6:
        return f"금속 연결체 {bodies}개 < 기대 핀 {expected}개의 60% (줄 뭉침 의심)"
    if bodies == 1:
        return f"금속 메시가 한 덩어리 (접점 {expected}개인데 개별 표현 아님)"
    return None


def main():
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    meta_pins = {}
    for p in index["parts"]:
        m = json.load(open(os.path.join(ROOT, p["path"], "meta.json"), encoding="utf-8"))
        prm = m.get("parameters", {})
        v = prm.get("pins") or prm.get("contacts")
        try:
            v = int(v)
        except (TypeError, ValueError):
            v = None  # 문자열/결측(수입 메타) — 핀수 검사 스킵
        meta_pins[p["id"]] = v
    # 증분(2026-07-12): 지난 PASS와 mtime+size 동일한 GLB는 스킵 (7k 전수=수시간 병목)
    snap_path = os.path.join(ROOT, "docs", "zfight-verified.json")
    try:
        snap = json.load(open(snap_path, encoding="utf-8"))
    except Exception:
        snap = {}
    newsnap = {}
    checked = 0
    total = 0
    for p in index["parts"]:
        glb = os.path.normpath(os.path.join(ROOT, p["path"], f"{p['id']}.glb"))
        if not os.path.exists(glb):
            continue
        st = os.stat(glb)
        sig = f"{st.st_mtime_ns}:{st.st_size}"
        newsnap[glb] = sig
        if snap.get(glb) == sig:
            continue
        checked += 1
        issues = check_part(glb)
        merged = check_merged_pins(glb, meta_pins.get(p["id"]))
        if merged:
            issues.append(merged)
        if issues:
            total += len(issues)
            print(f"FAIL {p['id']}:")
            for i in issues:
                print(f"   - {i}")
    if total == 0:
        json.dump(newsnap, open(snap_path, "w", encoding="utf-8"))
    print(f"\n{'PASS' if total == 0 else 'FAIL'}: {len(index['parts'])} parts "
          f"(checked {checked}), {total} 3D issues (coplanar/merged-pins)")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
