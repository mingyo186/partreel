"""
STEP 3D 유효성 검증 (FreeCAD 커널 — 교차검증용).
실행: freecadcmd.exe validate_step.py

각 부품 .step를 열어 Shape.isValid(), Volume>0, 솔리드 개수를 확인.
(서빙/메시 바운드 검사로는 못 잡는 "깨진 솔리드"를 CAD 커널로 검증)
"""
import os
import json
import Part

ROOT = "D:/seriouscode/opencad-lib"
index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))

errors = 0
for p in index["parts"]:
    fid = p["id"]
    path = "%s/%s/%s.step" % (ROOT, p["path"], fid)
    try:
        shape = Part.Shape()
        shape.read(path)
        valid = shape.isValid()
        vol = shape.Volume
        nsolids = len(shape.Solids)
        ok = valid and vol > 0 and nsolids >= 1
        if not ok:
            errors += 1
            print("FAIL %s: valid=%s vol=%.2f solids=%d" % (fid, valid, vol, nsolids))
        else:
            print("OK   %s: valid=True vol=%.1fmm3 solids=%d" % (fid, vol, nsolids))
    except Exception as e:
        errors += 1
        print("FAIL %s: %s" % (fid, e))

print("\n%s: %d parts, %d errors" % ("PASS" if errors == 0 else "FAIL", len(index["parts"]), errors))
