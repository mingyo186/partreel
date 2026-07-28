"""
ALPS RKJXM1015004 / RKJXM2E13004 생성기 (8방향 스틱 + 센터푸시 [+ 외축 엔코더]).
계기: 두 번째 외부 부품 요청 (github issue #10, morganyunker, 카탈로그 PDF 첨부).

치수 근거 (dimensions_source):
- ALPS ALPINE RKJXM 카탈로그 p436-437 "PC board mounting hole dimensions"
  (Drawing No.1 = RKJXM10 싱글샤프트 9홀+돌기1, No.2 = RKJXM2E 듀얼샤프트
  17홀+돌기2). 홀 좌표는 도면의 PDF 벡터 지오메트리에서 직접 추출
  (rkjxm_vec3.py, 원 재구성) — 회전대칭·ø9.9/ø10.7/ø20.3/8/3/4.15 치수와 정합.
- 교차검증: 독립 실보드 구현 2종과 전 홀 일치 —
  Input Labs pcb(Alpsalpine_RKJXM1015004, 양산 게임패드): 10홀 0.005mm 이내 동일.
  Croktopus/squatterboard(RKJXM2E13004, MIT): 19홀 전부 그쪽 0.1mm 반올림 안 일치.
- 안쪽 10홀 패턴이 두 도면에서 동일 검출 = 도면 간 자체 교차검증.

실행: python generators/gen_rkjxm.py
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

PAD = 1.8
DRILL = 1.1    # 카탈로그 홀 ø1 (RKJXT 계열과 동일 리드, 필드 실장 1.0~1.1 혼용 — 안전측)
LUG_DRILL = 1.2  # 위치돌기 ø1.1

# 안쪽 공통 패턴 (KiCad y-down; 카탈로그 '실장면에서 본' 도면 = 부품면 뷰, 미러 없음)
INNER = [
    ("1", "A", 1.0, 4.85),        # 방향 A (남)
    ("2", "B", 4.85, -1.0),       # 방향 B (동)
    ("3", "C", -1.0, -4.85),      # 방향 C (북)
    ("4", "D", -4.85, 1.0),       # 방향 D (서)
    ("5", "COM", 1.0, -5.255),    # 스틱 공통
    ("6", "PUSH", 5.255, 1.0),    # 센터푸시 (3단자 동일 노드)
    ("7", "PUSH", -5.255, -1.0),
    ("8", "PUSH", -1.0, 5.255),
    ("9", "GND", -4.15, -2.7),    # 케이스 접지
]
OUTER = [
    ("10", "ENC_A", -2.5, 10.5),   # 엔코더 A상 (카탈로그 Phase A, 남측 좌)
    ("11", "ENC_B", 2.5, 10.5),    # 엔코더 B상
    ("12", "ENC_COM", -2.5, -10.5),  # E-COM ×2 (북측 쌍)
    ("13", "ENC_COM", 2.5, -10.5),
    ("14", "FIX", 5.89, -8.22),    # 고정 단자 ×4 (납땜 지지용 금속 다리)
    ("15", "FIX", 8.22, 5.89),
    ("16", "FIX", -8.22, -5.89),
    ("17", "FIX", -5.89, 8.22),
]

PARTS = {
    "alps_rkjxm1015004": {
        "name": "RKJXM1015004",
        "pins": INNER,
        "left": INNER[:4], "right": INNER[4:],   # 좌: 방향 A-D / 우: COM·PUSH·GND
        "lugs": [(1.0, -3.0)],
        "body_r": None, "body_sq": 5.5,   # 몸체 11×11 (카탈로그 Style '4-11')
        "silk_r": 6.4, "crt": 6.95, "dot": (1.0, 6.7),
        "desc": "8-directional stick switch with center push, single shaft, "
                "11x11mm body, THT, automotive grade",
        "func": "8-direction + center push",
    },
    "alps_rkjxm2e13004": {
        "name": "RKJXM2E13004",
        "pins": INNER + OUTER,
        "left": INNER, "right": OUTER,           # 좌: 스위치 9핀 / 우: 엔코더·FIX 8핀
        "lugs": [(1.0, -3.0), (0.0, -8.0)],
        "body_r": 9.75, "body_sq": None,  # 몸체 ø19.5 (시리즈 표 W=19.5)
        "silk_r": 11.7, "crt": 12.25, "dot": (1.0, 12.0),
        "desc": "8-directional stick switch with center push and outer-shaft "
                "rotary encoder (15 detent / 15 pulse), dual shaft, 19.5mm "
                "round body, THT, automotive grade",
        "func": "8-direction + center push + rotary encoder",
    },
}


def footprint(pid, cfg):
    ty = round(cfg["crt"] + 1.6, 2)
    L = [f'(footprint "{pid}"', '  (version 20240108) (generator "partreel")',
         '  (layer "F.Cu")',
         f'  (descr "ALPS {cfg["name"]} {cfg["desc"]}. Hole map per ALPS RKJXM '
         'catalog PC-board mounting hole drawing (p436-437), coordinates from '
         'the drawing vector geometry, cross-verified vs two independent '
         'field-built boards")',
         '  (attr through_hole)',
         f'  (fp_text reference "SW" (at 0 {-ty}) (layer "F.SilkS")'
         ' (effects (font (size 1 1) (thickness 0.15))))',
         f'  (fp_text value "{cfg["name"]}" (at 0 {ty}) (layer "F.Fab")'
         ' (effects (font (size 1 1) (thickness 0.15))))']
    # 몸체 (Fab)
    if cfg["body_r"]:
        L.append(f'  (fp_circle (center 0 0) (end {cfg["body_r"]} 0)'
                 ' (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))')
    else:
        s = cfg["body_sq"]
        for a, b, c, d in ((-s, -s, s, -s), (s, -s, s, s),
                           (s, s, -s, s), (-s, s, -s, -s)):
            L.append(f'  (fp_line (start {a} {b}) (end {c} {d})'
                     ' (stroke (width 0.1) (type solid)) (layer "F.Fab"))')
    # 실크 원 (패드 바깥 외접원 — 몸체 실루엣이 패드와 겹쳐 원으로 대체)
    L.append(f'  (fp_circle (center 0 0) (end {cfg["silk_r"]} 0)'
             ' (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))')
    # 핀1 마커
    dx, dy = cfg["dot"]
    L.append(f'  (fp_circle (center {dx} {dy}) (end {dx + 0.2} {dy})'
             ' (stroke (width 0.3) (type solid)) (fill solid) (layer "F.SilkS"))')
    # 코트야드
    c = cfg["crt"]
    for a, b, cx, d in ((-c, -c, c, -c), (c, -c, c, c), (c, c, -c, c), (-c, c, -c, -c)):
        L.append(f'  (fp_line (start {a} {b}) (end {cx} {d})'
                 ' (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))')
    for num, name, x, y in cfg["pins"]:
        L.append(f'  (pad "{num}" thru_hole circle (at {x} {y}) (size {PAD} {PAD})'
                 f' (drill {DRILL}) (layers "*.Cu" "*.Mask"))')
    for x, y in cfg["lugs"]:
        L.append(f'  (pad "" np_thru_hole circle (at {x} {y}) (size {LUG_DRILL} '
                 f'{LUG_DRILL}) (drill {LUG_DRILL}) (layers "F&B.Cu" "*.Mask"))')
    L.append(')')
    return "\n".join(L) + "\n"


def symbol(pid, cfg):
    left, right = cfg["left"], cfg["right"]
    rows = max(len(left), len(right))  # 두 부품 모두 홀수 행 → 2.54 그리드 정합
    top = round((rows - 1) * 1.27, 2)
    H = round(top + 2.54, 2)
    L = ['(kicad_symbol_lib (version 20231120) (generator "partreel")',
         f'  (symbol "{pid}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)',
         f'    (property "Reference" "SW" (at 0 {H + 2.54} 0)'
         '      (effects (font (size 1.27 1.27))))',
         f'    (property "Value" "{cfg["name"]}" (at 0 {-H - 2.54} 0)'
         '      (effects (font (size 1.27 1.27))))',
         f'    (symbol "{pid}_0_1"',
         f'      (rectangle (start -7.62 {H}) (end 7.62 {-H})'
         '        (stroke (width 0.254) (type solid)) (fill (type background)))',
         '    )',
         f'    (symbol "{pid}_1_1"']
    y = top
    for num, name, _, _ in left:
        L.append(f'      (pin passive line (at -12.7 {round(y, 2)} 0) (length 5.08)'
                 f' (name "{name}" (effects (font (size 1.27 1.27))))'
                 f' (number "{num}" (effects (font (size 1.27 1.27)))))')
        y -= 2.54
    y = top
    for num, name, _, _ in right:
        L.append(f'      (pin passive line (at 12.7 {round(y, 2)} 180) (length 5.08)'
                 f' (name "{name}" (effects (font (size 1.27 1.27))))'
                 f' (number "{num}" (effects (font (size 1.27 1.27)))))')
        y -= 2.54
    L += ['    )', '  )', ')']
    return "\n".join(L) + "\n"


def main():
    for pid, cfg in PARTS.items():
        d = os.path.join(ROOT, "library", "switch", "alps", pid)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, f"{pid}.kicad_mod"), "w", encoding="utf-8",
             newline="\n").write(footprint(pid, cfg))
        open(os.path.join(d, f"{pid}.kicad_sym"), "w", encoding="utf-8",
             newline="\n").write(symbol(pid, cfg))
        meta = {
            "id": pid, "name": cfg["name"], "category": "switch",
            "family": "ALPS RKJXM", "manufacturer": "ALPS ALPINE",
            "mpn_pattern": cfg["name"],
            "description": cfg["desc"] + ". Requested by the community (issue #10).",
            "parameters": {"contacts": len(cfg["pins"]), "mounting": "THT",
                           "functions": cfg["func"]},
            "files": {"footprint": f"{pid}.kicad_mod", "symbol": f"{pid}.kicad_sym",
                      "footprint_svg": f"{pid}.footprint.svg",
                      "symbol_svg": f"{pid}.symbol.svg"},
            "formats": ["kicad_mod", "kicad_sym"],
            "datasheet": f"https://tech.alpsalpine.com/e/products/detail/{cfg['name']}/",
            "dimensions_source": "ALPS ALPINE RKJXM catalog p436-437 'PC board "
                                 "mounting hole dimensions' (RKJXM10 Drawing No.1 / "
                                 "RKJXM2E Drawing No.2); hole coordinates extracted "
                                 "from the drawing's PDF vector geometry, consistent "
                                 "with printed dims (ø9.9/ø10.7/ø20.3/8/3/4.15) and "
                                 "rotational symmetry; cross-verified against two "
                                 "independent field-built implementations (Input Labs "
                                 "pcb Alpsalpine_RKJXM1015004 — identical within "
                                 "0.005mm incl. lug; Croktopus/squatterboard "
                                 "RKJXM2E13004, MIT — all 19 holes match within "
                                 "their 0.1mm rounding)",
            "verified": True, "tier": "verified-2d",
            "origin": "generated", "license": "CC-BY-4.0",
            "generated_by": "generators/gen_rkjxm.py",
            "keywords": ["alps", "rkjxm", "stick", "joystick", "switch", "8-direction",
                         "center push", "navigation"] +
                        (["encoder", "dual shaft"] if pid.endswith("2e13004") else []),
        }
        json.dump(meta, open(os.path.join(d, "meta.json"), "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)
        print("generated:", pid)


if __name__ == "__main__":
    main()
