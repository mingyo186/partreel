"""
수입 부품 STL → 단색 GLB (§21-6ⓒ③). 메시명 "imported" (metal 아님 → merged-pins 게이트
자연 면제), 중립 그레이. 실행: python generators/imported_stl_to_glb.py
"""
import json
import os
import sys

import trimesh

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
COLOR = [178, 180, 186, 255]

index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
n = 0
for p in index["parts"]:
    d = os.path.join(ROOT, p["path"])
    fid = p["id"]
    stl = os.path.join(d, f"{fid}__imported.stl")
    if not os.path.exists(stl):
        continue
    m = trimesh.load(stl, force="mesh")
    m.visual.face_colors = COLOR
    scene = trimesh.Scene()
    scene.add_geometry(m, geom_name="imported")
    scene.export(os.path.join(d, f"{fid}.glb"))
    os.remove(stl)
    n += 1
print("imported GLBs:", n)
