"""
하우징/핀 STL 쌍 -> 컬러 GLB (웹 프리뷰). index.json의 모든 부품 순회. 임시 STL 삭제.
실행: python stl_to_glb.py
"""
import os
import json
import trimesh

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
HOUSING_COLOR = [235, 235, 238, 255]  # 화이트/내추럴
PIN_COLOR = [212, 175, 55, 255]       # 골드

index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
n = 0
for p in index["parts"]:
    fid = p["id"]
    d = os.path.join(ROOT, p["path"])
    hp = os.path.join(d, f"{fid}__housing.stl")
    pp = os.path.join(d, f"{fid}__pins.stl")
    if not (os.path.exists(hp) and os.path.exists(pp)):
        print("skip (no stl):", fid)
        continue
    h = trimesh.load(hp, force="mesh")
    pn = trimesh.load(pp, force="mesh")
    h.visual.face_colors = HOUSING_COLOR
    pn.visual.face_colors = PIN_COLOR
    trimesh.Scene([h, pn]).export(os.path.join(d, f"{fid}.glb"))
    os.remove(hp)
    os.remove(pp)
    n += 1
print("glb generated:", n)
