"""
ALPS RKJXT1F42001 (4방향 스틱 + 센터푸시 + 로터리 엔코더) 생성기.
계기: 첫 외부 부품 요청 (github issue #8, morganyunker, 데이터시트 첨부).

치수 근거 (dimensions_source):
- ALPS ALPINE RKJXT1F Series catalog (Update 2510), Drawing No.1
  "Mounting Hole Dimensions" (viewed from mounting side, tolerance ±0.1):
  홀 10개 φ1.0(+0.2/0), 위치돌기 홀 φ1.1(+0.1/0), 스팬 15.6×15.6,
  내측 오프셋 5.78/6.98/6.86/3.75/3/2/1.5/3.8.
- 기능 매핑: 카탈로그 라벨 (Encoder com/A/B, 스위치 A~D·com·Push, Ground)
  — 방위 대칭 (A=남, B=동, C=북, D=서; 각 방위 보조홀 = 엔코더/푸시).
- 교차검증: 독립 MIT 구현 2종(Croktopus/squatterboard, wiciu15/
  STM32-USBHID-MultimediaPilot)의 홀 좌표와 전부 일치 (실보드 검증된 배치).

실행: python generators/gen_rkjxt.py
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PID = "alps_rkjxt1f42001"
D = os.path.join(ROOT, "library", "switch", "alps", PID)

# (번호, 이름, x, y[KiCad y-down], 스위치/엔코더 기능)
PINS = [
    ("1", "A", -1.5, 7.8),        # 방향 A (남)
    ("2", "B", 7.8, 1.5),         # 방향 B (동)
    ("3", "C", 1.5, -7.8),        # 방향 C (북)
    ("4", "D", -7.8, -1.5),       # 방향 D (서)
    ("5", "COM", -1.0, -5.78),    # 스틱 스위치 공통
    ("6", "PUSH", 1.0, 6.98),     # 센터 푸시
    ("7", "ENC_A", -7.8, 1.5),    # 엔코더 A
    ("8", "ENC_B", 7.8, -1.5),    # 엔코더 B
    ("9", "ENC_COM", -1.5, -7.8), # 엔코더 공통
    ("10", "GND", 6.86, 3.75),    # 접지 단자
]
LUG = (-3.8, 1.5)  # 위치돌기 φ1.1(+0.1) → 홀 1.2

PAD = 1.8
DRILL = 1.1  # 카탈로그 홀 φ1.0(+0.2/0) 상단


def footprint():
    L = [f'(footprint "{PID}"', '  (version 20240108) (generator "partreel")',
         '  (layer "F.Cu")',
         f'  (descr "ALPS RKJXT1F42001 4-directional stick switch with encoder and '
         f'center push, 17x17mm round body, THT. Hole map per ALPS RKJXT1F catalog '
         f'Drawing No.1 (tolerance +/-0.1mm)")',
         '  (attr through_hole)']
    # 참조/값 텍스트
    L.append('  (fp_text reference "SW" (at 0 -10.6) (layer "F.SilkS")'
             ' (effects (font (size 1 1) (thickness 0.15))))')
    L.append('  (fp_text value "RKJXT1F42001" (at 0 10.6) (layer "F.Fab")'
             ' (effects (font (size 1 1) (thickness 0.15))))')
    # 몸체(원형 17mm) — Fab 실선, Silk는 살짝 크게
    L.append('  (fp_circle (center 0 0) (end 8.5 0) (stroke (width 0.1) (type solid))'
             ' (fill none) (layer "F.Fab"))')
    L.append('  (fp_circle (center 0 0) (end 8.75 0) (stroke (width 0.12) (type solid))'
             ' (fill none) (layer "F.SilkS"))')
    # 핀1 마커 (A 남쪽 홀 바깥 실크 점)
    L.append('  (fp_circle (center -1.5 9.4) (end -1.3 9.4) (stroke (width 0.3) (type solid))'
             ' (fill solid) (layer "F.SilkS"))')
    # 코트야드 (원몸체 + 여유 0.25)
    c = 8.85
    for a, b, cx, d2 in ((-c, -c, c, -c), (c, -c, c, c), (c, c, -c, c), (-c, c, -c, -c)):
        L.append(f'  (fp_line (start {a} {b}) (end {cx} {d2})'
                 ' (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))')
    for num, name, x, y in PINS:
        L.append(f'  (pad "{num}" thru_hole circle (at {x} {y}) (size {PAD} {PAD})'
                 f' (drill {DRILL}) (layers "*.Cu" "*.Mask"))')
    L.append(f'  (pad "" np_thru_hole circle (at {LUG[0]} {LUG[1]}) (size 1.2 1.2)'
             f' (drill 1.2) (layers "F&B.Cu" "*.Mask"))')
    L.append(')')
    return "\n".join(L) + "\n"


def symbol():
    # 좌측: 스위치 (A B C D COM PUSH), 우측: 엔코더 (A B COM) + GND
    left = [("1", "A"), ("2", "B"), ("3", "C"), ("4", "D"), ("5", "COM"), ("6", "PUSH")]
    right = [("7", "ENC_A"), ("8", "ENC_B"), ("9", "ENC_COM"), ("10", "GND")]
    H = 10.16
    L = ['(kicad_symbol_lib (version 20231120) (generator "partreel")',
         f'  (symbol "{PID}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)',
         f'    (property "Reference" "SW" (at 0 {H+2.54} 0)'
         '      (effects (font (size 1.27 1.27))))',
         f'    (property "Value" "RKJXT1F42001" (at 0 {-H-2.54} 0)'
         '      (effects (font (size 1.27 1.27))))',
         f'    (symbol "{PID}_0_1"',
         f'      (rectangle (start -7.62 {H}) (end 7.62 {-H})'
         '        (stroke (width 0.254) (type solid)) (fill (type background)))',
         '    )',
         f'    (symbol "{PID}_1_1"']
    y = 7.62
    for num, name in left:
        L.append(f'      (pin passive line (at -12.7 {y} 0) (length 5.08)'
                 f' (name "{name}" (effects (font (size 1.27 1.27))))'
                 f' (number "{num}" (effects (font (size 1.27 1.27)))))')
        y -= 2.54
    y = 7.62
    for num, name in right:
        L.append(f'      (pin passive line (at 12.7 {y} 180) (length 5.08)'
                 f' (name "{name}" (effects (font (size 1.27 1.27))))'
                 f' (number "{num}" (effects (font (size 1.27 1.27)))))')
        y -= 2.54
    L += ['    )', '  )', ')']
    return "\n".join(L) + "\n"


def main():
    os.makedirs(D, exist_ok=True)
    open(os.path.join(D, f"{PID}.kicad_mod"), "w", encoding="utf-8",
         newline="\n").write(footprint())
    open(os.path.join(D, f"{PID}.kicad_sym"), "w", encoding="utf-8",
         newline="\n").write(symbol())
    meta = {
        "id": PID, "name": "RKJXT1F42001", "category": "switch",
        "family": "ALPS RKJXT1F", "manufacturer": "ALPS ALPINE",
        "mpn_pattern": "RKJXT1F42001",
        "description": "4-directional stick switch with rotary encoder (30 detent / "
                       "15 pulse) and center push, 17x17mm round body, THT, automotive "
                       "grade. Requested by the community (issue #8).",
        "parameters": {"contacts": 10, "mounting": "THT",
                       "functions": "4-direction + center push + rotary encoder"},
        "files": {"footprint": f"{PID}.kicad_mod", "symbol": f"{PID}.kicad_sym",
                  "footprint_svg": f"{PID}.footprint.svg",
                  "symbol_svg": f"{PID}.symbol.svg"},
        "formats": ["kicad_mod", "kicad_sym"],
        "datasheet": "https://tech.alpsalpine.com/e/products/detail/RKJXT1F42001/",
        "dimensions_source": "ALPS ALPINE RKJXT1F Series catalog (Update 2510), "
                             "Drawing No.1 'Mounting Hole Dimensions' (10x phi1.0+0.2 "
                             "holes, 15.6x15.6 span, tol +/-0.1); function mapping from "
                             "catalog labels; cross-verified against two independent "
                             "MIT-licensed field-built implementations "
                             "(Croktopus/squatterboard, wiciu15/STM32-USBHID-"
                             "MultimediaPilot) - identical hole coordinates",
        "verified": True, "tier": "verified-2d",
        "origin": "generated", "license": "CC-BY-4.0",
        "generated_by": "generators/gen_rkjxt.py",
        "keywords": ["alps", "rkjxt1f", "stick", "encoder", "joystick", "switch",
                     "center push", "navigation"],
    }
    json.dump(meta, open(os.path.join(D, "meta.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    print("generated:", PID)


if __name__ == "__main__":
    main()
