"""
JST PH 3D 모델 생성기 (FreeCAD 헤드리스).
실행: freecadcmd.exe jst_ph_3d.py

각 부품: <id>.step + <id>__housing.stl + <id>__pins.stl (GLB 컬러용 임시)

치수: footprint(jst_ph.py)의 Fab 본체와 일치 (KiCad 공식 기준).
  하우징 X[-1.95, A+1.95], Y[-1.70, 2.80], Z[0, 6.0]
  핀 0.5각, Z[-3.0, +2.0]  (A=(pins-1)*2.0)
3D 높이는 대표값(데이터시트 8.0mm 마운트 높이 근사). 풋프린트가 기능상 critical 부분.
"""

import FreeCAD as App
import Part

BASE = "D:/seriouscode/opencad-lib/library/connector/jst/ph"

PITCH = 2.0
FX0, FX1 = -1.95, 1.95     # 하우징 X 오프셋 (A 더해 우측 확장)
FY0, FY1 = -1.70, 2.80     # 하우징 Y
HZ = 6.0                   # 하우징 높이
PIN_SQ = 0.5
PIN_BELOW = 3.0            # PCB 아래
PIN_INTO = 2.0            # 하우징 안으로

PINS_RANGE = range(2, 17)


def build(pins):
    A = (pins - 1) * PITCH
    x0, x1 = FX0, A + FX1
    L = x1 - x0
    W = FY1 - FY0
    housing = Part.makeBox(L, W, HZ, App.Vector(x0, FY0, 0))
    cav = Part.makeBox(L - 1.6, W - 1.6, HZ - 1.0, App.Vector(x0 + 0.8, FY0 + 0.8, 1.0))
    housing = housing.cut(cav)

    pin_shapes = []
    for i in range(pins):
        x = i * PITCH
        pin_shapes.append(
            Part.makeBox(PIN_SQ, PIN_SQ, PIN_BELOW + PIN_INTO,
                         App.Vector(x - PIN_SQ / 2, -PIN_SQ / 2, -PIN_BELOW))
        )
    pins_solid = pin_shapes[0]
    for p in pin_shapes[1:]:
        pins_solid = pins_solid.fuse(p)
    return housing, pins_solid


def main():
    done = []
    for pins in PINS_RANGE:
        fid = "jst_ph_%dpin" % pins
        d = "%s/%s" % (BASE, fid)
        housing, pins_solid = build(pins)
        Part.makeCompound([housing, pins_solid]).exportStep("%s/%s.step" % (d, fid))
        housing.exportStl("%s/%s__housing.stl" % (d, fid))
        pins_solid.exportStl("%s/%s__pins.stl" % (d, fid))
        done.append(fid)
    print("STEP+STL generated:", len(done), "parts")


main()
