"""
수입 부품 STEP → STL 테셀레이션 (FreeCAD 헤드리스, §21-6ⓒ⑦).
실행: freecadcmd generators/import_steps_mesh.py
대상: meta.origin=="imported" 이고 GLB 없는 부품. <id>__imported.stl 생성
     (이후 python generators/imported_stl_to_glb.py 가 단색 GLB로 변환).
"""
import json
import os
import sys

import FreeCAD  # noqa: F401
import Mesh
import Part

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
n = 0
for p in index["parts"]:
    d = os.path.join(ROOT, p["path"])
    meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
    if meta.get("origin") != "imported":
        continue
    fid = meta["id"]
    stl = os.path.join(d, f"{fid}__imported.stl")
    if os.path.exists(os.path.join(d, f"{fid}.glb")) or os.path.exists(stl):
        continue
    step = os.path.join(d, f"{fid}.step")
    try:
        shape = Part.read(step)
        if shape.isNull() or not shape.Solids:
            print("SKIP (no solids):", fid)
            continue
        mesh = Mesh.Mesh()
        mesh.addFacets(shape.tessellate(0.15))
        mesh.write(stl)
        n += 1
    except Exception as e:
        print("FAIL:", fid, e)
print("tessellated:", n)
