"""
파워 MOSFET 생성기 (SOT-223 계열) — 회로 블록 작업에서 필요한 부품을
'부품 우선' 원칙대로 정식 등록하기 위한 도구.

수록 기준 (사용자 방침 2026-08-22): **현행 생산·시중 조달 쉬운 품번**만.
단종·구형 품번은 넣지 않는다 (검색해서 찾아온 사람이 실제로 살 수 있어야 한다).

풋프린트: 제조사 데이터시트의 Suggested Pad Layout 수치 그대로 (1차 사료).
심볼: 자체 작성 증가형 MOSFET 도형 (공식 라이브러리 카피 아님).
       핀 1=G, 2=D(탭 포함), 3=S — SOT-223 표준 번호.

실행: python generators/gen_mosfets.py
"""

import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_ics import _court, _fp_open, _line, _rect_lines, _smd  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


# ---------- SOT-223 풋프린트 ----------

def sot223_footprint(fid, descr, tags, land):
    """SOT-223 (3리드 + 탭). 리드열 아래(y+), 탭 위(y-), 핀1 좌하단.

    land = {C: 리드 피치, C1: 두 열 중심거리, X/Y: 리드 패드, X1/Y1: 탭 패드}
    몸통(fab) = 데이터시트 패키지 외곽 D x E.
    """
    C, C1, X, Y, X1, Y1 = (land[k] for k in ("C", "C1", "X", "Y", "X1", "Y1"))
    bx, by = land["D"] / 2, land["E"] / 2
    lead_y, tab_y = C1 / 2, -C1 / 2
    out = _fp_open(fid, descr, tags, round(-(abs(tab_y) + Y1 / 2) - 1.0, 2),
                   round(lead_y + Y / 2 + 1.0, 2))
    # fab 외곽: 핀1(좌하단) 모서리 챔퍼 1mm
    ch = 1.0
    out += _rect_lines([(-bx, -by, bx, -by), (bx, -by, bx, by), (bx, by, -bx + ch, by),
                        (-bx + ch, by, -bx, by - ch), (-bx, by - ch, -bx, -by)],
                       "F.Fab", 0.10)
    # 실크: 패드가 위아래로 나오므로 몸통 좌우 수직선만 + 핀1 틱
    out += _rect_lines([(-bx - 0.11, -by, -bx - 0.11, by),
                        (bx + 0.11, -by, bx + 0.11, by)], "F.SilkS", 0.12)
    tick_x = -C - X / 2 - 0.4
    out.append(_line(tick_x, lead_y - Y / 2, tick_x, lead_y + Y / 2, "F.SilkS", 0.12))
    cx = max(bx, C + X / 2, X1 / 2) + 0.25
    cy = max(by, lead_y + Y / 2, abs(tab_y) + Y1 / 2) + 0.25
    out += _court(-cx, -cy, cx, cy)
    for i, x in enumerate((-C, 0.0, C)):
        out.append(_smd(str(i + 1), x, lead_y, X, Y))
    out.append(_smd("2", 0, tab_y, X1, Y1))  # 탭 = 드레인(핀2)과 같은 네트
    out.append(")")
    return "\n".join(out) + "\n"


# ---------- 심볼 (자체 작도) ----------

def _poly(pts, fill="none", width=0):
    p = " ".join(f"(xy {x:g} {y:g})" for x, y in pts)
    return (f"      (polyline (pts {p}) (stroke (width {width}) (type solid))"
            f" (fill (type {fill})))")


def _text(t, x, y, justify):
    return (f'      (text "{t}" (at {x:g} {y:g} 0) (effects (font (size 0.762 0.762))'
            f" (justify {justify})))")


def pmos_symbol(pid, value):
    """증가형 P채널 MOSFET (자체 작도): 게이트 좌, 드레인 위, 소스 아래,
    벌크는 소스에 묶이고 화살표는 채널 바깥쪽(P채널 관례), 바디 다이오드 표시
    (애노드=드레인 — 역극성 보호 회로에서 이 방향이 핵심이라 그려 둔다)."""
    g = [
        _poly([(-5.08, 0), (-2.54, 0)]),                     # 게이트 인출
        _poly([(-2.54, -2.54), (-2.54, 2.54)]),              # 게이트 바
        _poly([(-1.27, 1.27), (-1.27, 2.54)]),               # 채널 3토막
        _poly([(-1.27, -0.635), (-1.27, 0.635)]),
        _poly([(-1.27, -2.54), (-1.27, -1.27)]),
        _poly([(-1.27, 1.905), (0, 1.905)]),                 # 드레인 가지
        _poly([(0, 1.905), (0, 5.08)]),
        _poly([(-1.27, -1.905), (0, -1.905)]),               # 소스 가지
        _poly([(0, -1.905), (0, -5.08)]),
        _poly([(-1.27, 0), (0, 0)]),                         # 벌크 → 소스
        _poly([(0, 0), (0, -1.905)]),
        _poly([(-0.254, 0), (-1.016, 0.381), (-1.016, -0.381), (-0.254, 0)], "outline"),
        _poly([(0, 3.81), (2.54, 3.81)]),                    # 바디 다이오드
        _poly([(2.54, 3.81), (2.54, 1.27)]),
        _poly([(0, -3.81), (2.54, -3.81)]),
        _poly([(2.54, -3.81), (2.54, 0.254)]),
        _poly([(1.905, 1.27), (3.175, 1.27), (2.54, 0.254), (1.905, 1.27)], "outline"),
        _poly([(1.905, 0.254), (3.175, 0.254)]),
        # D/S 글자는 도형 바깥(리드선 옆)에 둔다 — 도형 상자 변을 물면 회로도
        # 가독 게이트 R7(글자-외곽선 침범)에 걸린다 (2026-08-22 emi_power_in 실측)
        _text("G", -4.826, 0.381, "left bottom"),
        _text("D", 0.635, 5.588, "left bottom"),
        _text("S", 0.635, -6.858, "left bottom"),
    ]
    body = "\n".join(g)
    return f"""(kicad_symbol_lib (version 20231120) (generator "partreel-gen-mosfets")
  (symbol "{pid}" (pin_numbers hide) (pin_names (offset 0) hide) (in_bom yes) (on_board yes)
    (property "Reference" "Q" (at -3.81 6.35 0) (effects (font (size 1.27 1.27)) (justify right)))
    (property "Value" "{value}" (at -3.81 -6.35 0) (effects (font (size 1.27 1.27)) (justify right)))
    (symbol "{pid}_1_1"
{body}
      (pin passive line (at -7.62 0 0) (length 2.54)
        (name "G" (effects (font (size 1.27 1.27))))
        (number "1" (effects (font (size 1.27 1.27)))))
      (pin passive line (at 0 7.62 270) (length 2.54)
        (name "D" (effects (font (size 1.27 1.27))))
        (number "2" (effects (font (size 1.27 1.27)))))
      (pin passive line (at 0 -7.62 90) (length 2.54)
        (name "S" (effects (font (size 1.27 1.27))))
        (number "3" (effects (font (size 1.27 1.27)))))
    )))"""


# ---------- 부품 ----------

# Diodes SOT-223 랜드 (DS37199 Rev.3-2 p.6 Suggested Pad Layout = AP02001):
#   C 2.30 / C1 6.40 / X 1.20 / X1 3.30 / Y 1.60 / Y1 1.60 / Y2 8.00
#   패키지 외곽(같은 쪽 표): D 6.50 / E 3.50 (typ)
SOT223_DIODES = {"C": 2.30, "C1": 6.40, "X": 1.20, "Y": 1.60, "X1": 3.30, "Y1": 1.60,
                 "D": 6.50, "E": 3.50}

PARTS = [
    {
        "id": "diodes_dmp6023le",
        "mpn": "DMP6023LE-13",
        "name": "DMP6023LE-13 60V P-channel MOSFET (SOT-223)",
        "value": "DMP6023LE",
        "vendor": "diodes",
        "manufacturer": "Diodes Incorporated",
        "land": SOT223_DIODES,
        "datasheet": "https://www.diodes.com/assets/Datasheets/DMP6023LE.pdf",
        "description": (
            "60V P채널 증가형 파워 MOSFET, RDS(on) 28mΩ @VGS=-10V, ID -7A(TA=25°C), "
            "VGS ±20V, PD 2W, AEC-Q101. SOT-223. 24V 산업 전원의 역극성 보호·하이사이드 "
            "스위치용 (게이트 RC로 돌입전류 제한 겸용)."),
        "parameters": {"pins": 3, "mounting": "smd", "case": "SOT-223",
                       "vds": "-60V", "vgs_max": "±20V", "id_max": "-7A",
                       "rds_on": "28mΩ @ VGS=-10V", "pd": "2W",
                       "qualification": "AEC-Q101"},
        "dimensions_source": (
            "Diodes DMP6023LE datasheet DS37199 Rev.3-2 (January 2015) p.6: "
            "Suggested Pad Layout C=2.30, C1=6.40, X=1.20, X1=3.30, Y=1.60, Y1=1.60, "
            "Y2=8.00 (mm) — 랜드 수치를 그대로 사용. 몸통 외곽은 같은 페이지 SOT223 "
            "치수표 D=6.50, E=3.50 (typ). 핀 번호 1=G / 2=D(탭 공통) / 3=S — 같은 문서 "
            "p.1 'Pin Out - Top View'(위에서 S/D/G)와 SOT-223 표준 번호, "
            "독립 대조: CERN KiCad 라이브러리 SOT-223 P-MOSFET 3종 동일 번호."),
        "keywords": ["dmp6023le", "diodes", "mosfet", "p-channel", "pmos", "60v",
                     "sot-223", "sot223", "reverse polarity", "power"],
    },
]


def build(p):
    fid = p["id"]
    descr = (f"{p['name']}. SOT-223: lead pads {p['land']['X']}x{p['land']['Y']} at pitch "
             f"{p['land']['C']}, tab pad {p['land']['X1']}x{p['land']['Y1']}, row centres "
             f"{p['land']['C1']} apart (manufacturer suggested pad layout).")
    fp = sot223_footprint(fid, descr, f"{p['mpn']} MOSFET P-channel SOT-223", p["land"])
    sym = pmos_symbol(fid, p["value"])
    meta = {
        "id": fid, "name": p["name"], "category": "discrete",
        "family": "mosfet_sot223", "manufacturer": p["manufacturer"],
        "mpn_pattern": p["mpn"], "description": p["description"],
        "keywords": p["keywords"], "parameters": p["parameters"],
        "formats": ["kicad_mod", "kicad_sym"], "tier": "verified-2d",
        "license": "CC-BY-4.0", "datasheet": p["datasheet"],
        "dimensions_source": p["dimensions_source"],
        "generated_by": "generators/gen_mosfets.py",
        "files": {"footprint": f"{fid}.kicad_mod", "symbol": f"{fid}.kicad_sym"},
    }
    return fid, os.path.join("discrete", p["vendor"], fid), fp, sym, meta


def main():
    for p in PARTS:
        fid, lib_path, fp, sym, meta = build(p)
        d = os.path.join(ROOT, "library", lib_path)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, f"{fid}.kicad_mod"), "w", encoding="utf-8",
             newline="\n").write(fp)
        open(os.path.join(d, f"{fid}.kicad_sym"), "w", encoding="utf-8",
             newline="\n").write(sym)
        json.dump(meta, open(os.path.join(d, "meta.json"), "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)
        print(" ", fid, "->", os.path.relpath(d, ROOT))
    print(f"Done ({len(PARTS)} MOSFETs).")


if __name__ == "__main__":
    main()
