"""
하우징/핀 STL 쌍 -> 컬러 GLB (웹 프리뷰용). 임시 STL 삭제.
실행: python stl_to_glb.py
"""
import os
import trimesh

BASE = "D:/seriouscode/opencad-lib/library/connector/jst/ph"
HOUSING_COLOR = [235, 235, 238, 255]  # JST PH 하우징: 화이트/내추럴
PIN_COLOR = [212, 175, 55, 255]       # 핀: 골드

for pins in range(2, 17):
    fid = "jst_ph_%dpin" % pins
    d = "%s/%s" % (BASE, fid)
    h = trimesh.load("%s/%s__housing.stl" % (d, fid), force="mesh")
    p = trimesh.load("%s/%s__pins.stl" % (d, fid), force="mesh")
    h.visual.face_colors = HOUSING_COLOR
    p.visual.face_colors = PIN_COLOR
    scene = trimesh.Scene([h, p])
    scene.export("%s/%s.glb" % (d, fid))
    os.remove("%s/%s__housing.stl" % (d, fid))
    os.remove("%s/%s__pins.stl" % (d, fid))
    print("glb generated:", fid)
print("Done.")
