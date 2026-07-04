"""
일회성(비파라메트릭) 부품 생성기 — 부품별 함수.
실행: python generators/gen_parts.py
각 부품: 풋프린트(.kicad_mod) + 심볼(.kicad_sym) + meta.json.
인덱스는 build_index.py가 통합 생성.
"""
import json
import os
from gen_connectors import _line, LIB_ROOT  # 공통 헬퍼/루트 재사용


def _rect_lines(coords, layer, w):
    out = []
    for (x1, y1, x2, y2) in coords:
        out.append(_line(x1, y1, x2, y2, layer, w))
    return out


# ---- USB Type-C 16핀 (USB 2.0), KiCad 공식 USB_C_Receptacle_HRO_TYPE-C-31-M-12 치수 ----
def usb_c_16p():
    fid = "usb_c_16p"
    lib_path = "connector/usb/usb_c_16p"
    # (x, y, w, h, drill_dx, drill_dy) 쉴드 THT
    shields = [(4.32, 1.05, 1, 1.6, 0.6, 1.2), (-4.32, 1.05, 1, 1.6, 0.6, 1.2),
               (-4.32, -3.13, 1, 2.1, 0.6, 1.7), (4.32, -3.13, 1, 2.1, 0.6, 1.7)]
    npth = [(2.89, -2.6), (-2.89, -2.6)]
    # (name, x, width) — 모두 y=-4.045, h=1.45
    smd = [("A6", -0.25, 0.3), ("B5", 1.75, 0.3), ("A8", 1.25, 0.3), ("B6", 0.75, 0.3),
           ("A7", 0.25, 0.3), ("B7", -0.75, 0.3), ("A5", -1.25, 0.3), ("B8", -1.75, 0.3),
           ("A12", 3.25, 0.6), ("B4", 2.45, 0.6), ("A4", -2.45, 0.6), ("A1", -3.25, 0.6),
           ("B12", -3.25, 0.6), ("B9", -2.45, 0.6), ("A9", 2.45, 0.6), ("B1", 3.25, 0.6)]

    out = [f'(footprint "{fid}" (version 20221018) (generator opencad-lib)',
           '  (layer "F.Cu")',
           '  (descr "USB Type-C receptacle, 16-pin (USB 2.0 + power), SMD with through-hole shield. '
           'Dimensions match KiCad official USB_C_Receptacle_HRO_TYPE-C-31-M-12.")',
           '  (tags "USB C Type-C receptacle 16pin")',
           '  (attr through_hole)',
           '  (fp_text reference "REF**" (at 0 4.7) (layer "F.SilkS")'
           '\n    (effects (font (size 1 1) (thickness 0.15))))',
           '  (fp_text value "usb_c_16p" (at 0 -5.6) (layer "F.Fab")'
           '\n    (effects (font (size 1 1) (thickness 0.15))))']
    # Fab 사각
    out += _rect_lines([(-4.47, -3.65, 4.47, -3.65), (4.47, -3.65, 4.47, 3.65),
                        (4.47, 3.65, -4.47, 3.65), (-4.47, 3.65, -4.47, -3.65)], "F.Fab", 0.10)
    # Silk (상단 + 좌우 부분 프레임)
    out += _rect_lines([(-4.7, 3.9, 4.7, 3.9), (-4.7, 2, -4.7, 3.9), (-4.7, -1.9, -4.7, 0.1),
                        (4.7, 2, 4.7, 3.9), (4.7, -1.9, 4.7, 0.1)], "F.SilkS", 0.12)
    # Courtyard
    out += _rect_lines([(-5.32, -5.27, 5.32, -5.27), (5.32, -5.27, 5.32, 4.15),
                        (5.32, 4.15, -5.32, 4.15), (-5.32, 4.15, -5.32, -5.27)], "F.CrtYd", 0.05)
    # 패드
    for x, y, w, h, dx, dy in shields:
        out.append(f'  (pad "S1" thru_hole oval (at {x} {y}) (size {w} {h}) '
                   f'(drill oval {dx} {dy}) (layers "*.Cu" "*.Mask"))')
    for x, y in npth:
        out.append(f'  (pad "" np_thru_hole circle (at {x} {y}) (size 0.65 0.65) '
                   f'(drill 0.65) (layers "*.Cu" "*.Mask"))')
    for name, x, w in smd:
        out.append(f'  (pad "{name}" smd rect (at {x} -4.045) (size {w} 1.45) '
                   f'(layers "F.Cu" "F.Paste" "F.Mask"))')
    out.append(')')
    footprint = "\n".join(out) + "\n"

    symbol = _usb_c_symbol(fid)
    meta = {
        "id": fid, "name": "USB Type-C Receptacle 16-pin (USB 2.0)",
        "category": "connector", "family": "USB-C", "manufacturer": "HRO / Generic",
        "mpn_pattern": "TYPE-C-31-M-12",
        "description": "USB Type-C receptacle, 16-pin (USB 2.0 + power), SMD with through-hole shield tabs. "
                       "Pinout matches the common TYPE-C-31-M-12 / HRO 16-pin part.",
        "parameters": {"contacts": 16, "mounting": "SMD+THT", "orientation": "horizontal"},
        "files": {"footprint": f"{fid}.kicad_mod", "symbol": f"{fid}.kicad_sym",
                  "model_3d": f"{fid}.step", "preview": f"{fid}.glb",
                  "footprint_svg": f"{fid}.footprint.svg", "symbol_svg": f"{fid}.symbol.svg"},
        "formats": ["kicad_mod", "kicad_sym", "step", "glb"],
        "datasheet": "https://datasheet.lcsc.com/lcsc/2304140030_HCTL-CKX-3AH1_C165948.pdf",
        "dimensions_source": "Matches KiCad official USB_C_Receptacle_HRO_TYPE-C-31-M-12. 3D representative.",
        "verified": True, "license": "CC-BY-4.0", "generated_by": "generators/gen_parts.py",
        "keywords": ["usb", "usb-c", "type-c", "receptacle", "connector", "16pin"],
    }
    return fid, lib_path, footprint, symbol, meta


def _usb_c_symbol(fid):
    L = [("A1", "GND"), ("A4", "VBUS"), ("A5", "CC1"), ("A6", "D+"),
         ("A7", "D-"), ("A8", "SBU1"), ("A9", "VBUS"), ("A12", "GND")]
    R = [("B1", "GND"), ("B4", "VBUS"), ("B5", "CC2"), ("B6", "D+"),
         ("B7", "D-"), ("B8", "SBU2"), ("B9", "VBUS"), ("B12", "GND")]
    GRID, PIN = 2.54, 2.54
    top = (len(L) - 1) * GRID / 2.0
    bl, br = -6.35, 6.35
    bt, bb = top + 2.54, -top - 2.54
    out = ['(kicad_symbol_lib (version 20211014) (generator opencad-lib)',
           f'  (symbol "{fid}" (in_bom yes) (on_board yes)',
           f'    (property "Reference" "J" (at 0 {bt + 2:.2f} 0) (effects (font (size 1.27 1.27))))',
           f'    (property "Value" "{fid}" (at 0 {bb - 2:.2f} 0) (effects (font (size 1.27 1.27))))',
           '    (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
           '    (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
           f'    (symbol "{fid}_1_1"',
           f'      (rectangle (start {bl:.2f} {bt:.2f}) (end {br:.2f} {bb:.2f})'
           '\n        (stroke (width 0.254) (type solid)) (fill (type background)))']
    for i, (num, name) in enumerate(L):
        y = top - i * GRID
        out.append(f'      (pin passive line (at {bl - PIN:.2f} {y:.2f} 0) (length {PIN})'
                   f'\n        (name "{name}" (effects (font (size 1.27 1.27))))'
                   f'\n        (number "{num}" (effects (font (size 1.27 1.27)))))')
    for i, (num, name) in enumerate(R):
        y = top - i * GRID
        out.append(f'      (pin passive line (at {br + PIN:.2f} {y:.2f} 180) (length {PIN})'
                   f'\n        (name "{name}" (effects (font (size 1.27 1.27))))'
                   f'\n        (number "{num}" (effects (font (size 1.27 1.27)))))')
    out.append(f'      (pin passive line (at 0 {bb - PIN:.2f} 90) (length {PIN})'
               '\n        (name "Shield" (effects (font (size 1.27 1.27))))'
               '\n        (number "S1" (effects (font (size 1.27 1.27)))))')
    out += ['    )', '  )', ')']
    return "\n".join(out) + "\n"


# ---- microSD 카드 소켓 (push-push); 패드 위치=Hirose DM3AT 랜드패턴(데이터시트), 외곽선=자체 ----
def microsd_hc():
    fid = "microsd_hc"
    lib_path = "connector/card/microsd_hc"
    contacts = [("1", 2.775), ("2", 1.675), ("3", 0.575), ("4", -0.525), ("5", -1.625),
                ("6", -2.725), ("7", -3.825), ("8", -4.925), ("9", -5.875)]  # y=-7.725, 0.7x1.2
    # 카드감지 스위치 제2단자 = 공식 pad 10 (쉴드 아님! — 전수감사에서 발견·정정)
    det_a = (-6.825, 2.775, 1, 0.8)
    shells = [(4.325, -7.725, 1, 1.2), (-6.825, -3.425, 1, 1.2),
              (-6.825, 6.925, 1, 2.8), (6.675, 7.375, 1.3, 1.9)]  # 쉴드/마운트
    out = [f'(footprint "{fid}" (version 20221018) (generator opencad-lib)',
           '  (layer "F.Cu")',
           '  (descr "microSD card socket (push-push). Pad land pattern per Hirose DM3AT-SF-PEJM5 '
           'datasheet; body outline original.")',
           '  (tags "microSD TF card socket push-push")',
           '  (attr through_hole)',
           '  (fp_text reference "REF**" (at 0 -9.2) (layer "F.SilkS")'
           '\n    (effects (font (size 1 1) (thickness 0.15))))',
           '  (fp_text value "microsd_hc" (at 0 8.9) (layer "F.Fab")'
           '\n    (effects (font (size 1 1) (thickness 0.15))))']
    out += _rect_lines([(-6.9, -7.8, 6.9, -7.8), (6.9, -7.8, 6.9, 8.1),
                        (6.9, 8.1, -6.9, 8.1), (-6.9, 8.1, -6.9, -7.8)], "F.Fab", 0.10)
    out += _rect_lines([(-7.0, -6.9, 7.0, -6.9), (7.0, -6.9, 7.0, 8.2),
                        (7.0, 8.2, -7.0, 8.2), (-7.0, 8.2, -7.0, -6.9)], "F.SilkS", 0.12)
    out += _rect_lines([(-7.4, -8.8, 7.4, -8.8), (7.4, -8.8, 7.4, 8.6),
                        (7.4, 8.6, -7.4, 8.6), (-7.4, 8.6, -7.4, -8.8)], "F.CrtYd", 0.05)
    for name, x in contacts:
        out.append(f'  (pad "{name}" smd rect (at {x} -7.725) (size 0.7 1.2) '
                   f'(layers "F.Cu" "F.Paste" "F.Mask"))')
    dx, dy, dw, dh = det_a
    out.append(f'  (pad "10" smd rect (at {dx} {dy}) (size {dw} {dh}) '
               f'(layers "F.Cu" "F.Paste" "F.Mask"))')
    for x, y, w, h in shells:
        out.append(f'  (pad "SH" smd rect (at {x} {y}) (size {w} {h}) '
                   f'(layers "F.Cu" "F.Paste" "F.Mask"))')
    out.append(')')
    footprint = "\n".join(out) + "\n"

    # 핀명 = KiCad 공식 Micro_SD_Card_Det2 (Hirose DM3AT 대응 심볼) 그대로
    names = ["DAT2", "DAT3/CD", "CMD", "VDD", "CLK", "VSS", "DAT0", "DAT1", "DET_B", "DET_A"]
    symbol = _left_pin_symbol(fid, [(str(i + 1), names[i]) for i in range(10)], shield="SH")
    meta = {
        "id": fid, "name": "microSD Card Socket (push-push)",
        "category": "connector", "family": "microSD", "manufacturer": "Hirose / Generic",
        "mpn_pattern": "DM3AT-SF-PEJM5",
        "description": "microSD / TF card socket, push-push, SMD. Land pattern per Hirose "
                       "DM3AT-SF-PEJM5 datasheet. SD-bus pinout (DAT/CMD/CLK/VDD/VSS).",
        "parameters": {"contacts": 10, "mounting": "SMD", "orientation": "horizontal"},
        "files": {"footprint": f"{fid}.kicad_mod", "symbol": f"{fid}.kicad_sym",
                  "model_3d": f"{fid}.step", "preview": f"{fid}.glb",
                  "footprint_svg": f"{fid}.footprint.svg", "symbol_svg": f"{fid}.symbol.svg"},
        "formats": ["kicad_mod", "kicad_sym", "step", "glb"],
        "datasheet": "https://www.hirose.com/product/series/DM3",
        "dimensions_source": "Pad land pattern per Hirose DM3AT datasheet; body outline original.",
        "verified": True, "license": "CC-BY-4.0", "generated_by": "generators/gen_parts.py",
        "keywords": ["microsd", "sd", "tf", "card", "socket", "connector"],
    }
    return fid, lib_path, footprint, symbol, meta


def _left_pin_symbol(fid, pins, shield=None):
    """좌측 일렬 핀 + (옵션)하단 쉴드 핀 심볼."""
    GRID, PIN = 2.54, 2.54
    top = (len(pins) - 1) * GRID / 2.0
    bl, br = -6.35, 6.35
    bt = top + 2.54
    bb = -top - (2.54 if not shield else 5.08)
    out = ['(kicad_symbol_lib (version 20211014) (generator opencad-lib)',
           f'  (symbol "{fid}" (in_bom yes) (on_board yes)',
           f'    (property "Reference" "J" (at 0 {bt + 2:.2f} 0) (effects (font (size 1.27 1.27))))',
           f'    (property "Value" "{fid}" (at 0 {bb - 2:.2f} 0) (effects (font (size 1.27 1.27))))',
           '    (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
           '    (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
           f'    (symbol "{fid}_1_1"',
           f'      (rectangle (start {bl:.2f} {bt:.2f}) (end {br:.2f} {bb:.2f})'
           '\n        (stroke (width 0.254) (type solid)) (fill (type background)))']
    for i, (num, name) in enumerate(pins):
        y = top - i * GRID
        out.append(f'      (pin passive line (at {bl - PIN:.2f} {y:.2f} 0) (length {PIN})'
                   f'\n        (name "{name}" (effects (font (size 1.27 1.27))))'
                   f'\n        (number "{num}" (effects (font (size 1.27 1.27)))))')
    if shield:
        out.append(f'      (pin passive line (at 0 {bb - PIN:.2f} 90) (length {PIN})'
                   '\n        (name "Shield" (effects (font (size 1.27 1.27))))'
                   f'\n        (number "{shield}" (effects (font (size 1.27 1.27)))))')
    out += ['    )', '  )', ')']
    return "\n".join(out) + "\n"


# ---- ESP32-WROOM-32 모듈; 패드=Espressif/KiCad 공식 랜드패턴, 외곽선=자체 ----
def esp32_wroom32():
    fid = "esp32_wroom32"
    lib_path = "module/espressif/esp32_wroom32"
    # (name, x, y, rot) — 본체 패드 2x0.9, 써멀 5x5
    pads = [("39", -1.0, -0.755, 0, 5, 5)]
    for i in range(14):   # 1-14 좌
        pads.append((str(i + 1), -8.5, -8.255 + i * 1.27, 0, 2, 0.9))
    for i in range(10):   # 15-24 하 (90도)
        pads.append((str(15 + i), -5.715 + i * 1.27, 9.255, 90, 2, 0.9))
    for i in range(14):   # 25-38 우
        pads.append((str(25 + i), 8.5, 8.255 - i * 1.27, 0, 2, 0.9))

    out = [f'(footprint "{fid}" (version 20221018) (generator opencad-lib)',
           '  (layer "F.Cu")',
           '  (descr "Espressif ESP32-WROOM-32 Wi-Fi+BT module, SMD castellated, 38-pad + thermal. '
           'Land pattern per Espressif datasheet / KiCad RF_Module; body outline original.")',
           '  (tags "ESP32 WROOM module wifi bt")',
           '  (attr through_hole)',
           '  (fp_text reference "REF**" (at 0 -16.5) (layer "F.SilkS")'
           '\n    (effects (font (size 1 1) (thickness 0.15))))',
           '  (fp_text value "esp32_wroom32" (at 0 10.6) (layer "F.Fab")'
           '\n    (effects (font (size 1 1) (thickness 0.15))))']
    # Fab 본체 (18 x 25.5)
    out += _rect_lines([(-9, -15.745, 9, -15.745), (9, -15.745, 9, 9.76),
                        (9, 9.76, -9, 9.76), (-9, 9.76, -9, -15.745)], "F.Fab", 0.10)
    # Silk: 안테나 키프아웃 박스(패드 없는 영역) + 1번핀 틱
    out += _rect_lines([(-9, -15.745, 9, -15.745), (9, -15.745, 9, -9.5),
                        (9, -9.5, -9, -9.5), (-9, -9.5, -9, -15.745)], "F.SilkS", 0.12)
    out.append(_line(-9.6, -8.255, -9.6, -7.255, "F.SilkS", 0.12))  # pin1 틱
    # Courtyard (패드 바깥)
    out += _rect_lines([(-9.7, -15.9, 9.7, -15.9), (9.7, -15.9, 9.7, 10.3),
                        (9.7, 10.3, -9.7, 10.3), (-9.7, 10.3, -9.7, -15.9)], "F.CrtYd", 0.05)
    for name, x, y, rot, w, h in pads:
        at = f"{x} {y}" + (f" {rot}" if rot else "")
        out.append(f'  (pad "{name}" smd rect (at {at}) (size {w} {h}) '
                   f'(layers "F.Cu" "F.Paste" "F.Mask"))')
    out.append(')')
    footprint = "\n".join(out) + "\n"

    # 핀명 = Espressif ESP32-WROOM-32 데이터시트 표기 그대로 (전수감사에서 정정:
    # SENSOR_VP/VN, 플래시핀 SHD/SD2 계열, RXD0/IO3·TXD0/IO1 별칭 포함)
    nm = ["GND", "3V3", "EN", "SENSOR_VP", "SENSOR_VN", "IO34", "IO35", "IO32", "IO33", "IO25",
          "IO26", "IO27", "IO14", "IO12", "GND", "IO13", "SHD/SD2", "SWP/SD3", "SCS/CMD", "SCK/CLK",
          "SDO/SD0", "SDI/SD1", "IO15", "IO2", "IO0", "IO4", "IO16", "IO17", "IO5", "IO18",
          "IO19", "NC", "IO21", "RXD0/IO3", "TXD0/IO1", "IO22", "IO23", "GND"]
    left = [(str(i + 1), nm[i]) for i in range(19)]
    right = [(str(i + 1), nm[i]) for i in range(19, 38)]
    symbol = _lr_symbol(fid, left, right, bottom=[("39", "GND")])
    meta = {
        "id": fid, "name": "ESP32-WROOM-32 Module",
        "category": "module", "family": "ESP32", "manufacturer": "Espressif",
        "mpn_pattern": "ESP32-WROOM-32",
        "description": "Espressif ESP32-WROOM-32 Wi-Fi + Bluetooth module, SMD castellated, "
                       "38 pads + thermal. Land pattern per Espressif datasheet.",
        "parameters": {"contacts": 39, "mounting": "SMD", "orientation": "horizontal"},
        "files": {"footprint": f"{fid}.kicad_mod", "symbol": f"{fid}.kicad_sym",
                  "model_3d": f"{fid}.step", "preview": f"{fid}.glb",
                  "footprint_svg": f"{fid}.footprint.svg", "symbol_svg": f"{fid}.symbol.svg"},
        "formats": ["kicad_mod", "kicad_sym", "step", "glb"],
        "datasheet": "https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32_datasheet_en.pdf",
        "dimensions_source": "Land pattern per Espressif ESP32-WROOM-32 datasheet; body outline original.",
        "verified": True, "license": "CC-BY-4.0", "generated_by": "generators/gen_parts.py",
        "keywords": ["esp32", "wroom", "wroom-32", "module", "wifi", "bluetooth", "espressif"],
    }
    return fid, lib_path, footprint, symbol, meta


def _lr_symbol(fid, left, right, bottom=None):
    """좌/우 핀 + (옵션)하단 핀 심볼."""
    GRID, PIN = 2.54, 2.54
    n = max(len(left), len(right))
    top = (n - 1) * GRID / 2.0
    bl, br = -8.89, 8.89
    bt = top + 2.54
    bb = -top - (2.54 + (2.54 * len(bottom) if bottom else 0))
    out = ['(kicad_symbol_lib (version 20211014) (generator opencad-lib)',
           f'  (symbol "{fid}" (in_bom yes) (on_board yes)',
           f'    (property "Reference" "U" (at 0 {bt + 2:.2f} 0) (effects (font (size 1.27 1.27))))',
           f'    (property "Value" "{fid}" (at 0 {bb - 2:.2f} 0) (effects (font (size 1.27 1.27))))',
           '    (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
           '    (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
           f'    (symbol "{fid}_1_1"',
           f'      (rectangle (start {bl:.2f} {bt:.2f}) (end {br:.2f} {bb:.2f})'
           '\n        (stroke (width 0.254) (type solid)) (fill (type background)))']
    for i, (num, name) in enumerate(left):
        y = top - i * GRID
        out.append(f'      (pin passive line (at {bl - PIN:.2f} {y:.2f} 0) (length {PIN})'
                   f'\n        (name "{name}" (effects (font (size 1.27 1.27))))'
                   f'\n        (number "{num}" (effects (font (size 1.27 1.27)))))')
    for i, (num, name) in enumerate(right):
        y = top - i * GRID
        out.append(f'      (pin passive line (at {br + PIN:.2f} {y:.2f} 180) (length {PIN})'
                   f'\n        (name "{name}" (effects (font (size 1.27 1.27))))'
                   f'\n        (number "{num}" (effects (font (size 1.27 1.27)))))')
    for j, (num, name) in enumerate(bottom or []):
        x = (j - (len(bottom) - 1) / 2.0) * GRID
        out.append(f'      (pin passive line (at {x:.2f} {bb - PIN:.2f} 90) (length {PIN})'
                   f'\n        (name "{name}" (effects (font (size 1.27 1.27))))'
                   f'\n        (number "{num}" (effects (font (size 1.27 1.27)))))')
    out += ['    )', '  )', ')']
    return "\n".join(out) + "\n"


# ---- AHT20 온습도 센서 (ASAIR); 치수=ASAIR AHT20 데이터시트 V1.0 Fig.1/Fig.8 ----
def aht20():
    fid = "aht20"
    lib_path = "sensor/asair/aht20"
    # Fig.8 권장 랜드패턴: 패드 0.8x0.5, 열 중심간격 2.0, 행 피치 1.0 (센터 패드 없음 —
    # Fig.1 바텀뷰/Fig.8 모두 6패드만). 핀배치 Table 5 (탑뷰): 좌 1 NC/2 VDD/3 SCL, 우 6 NC/5 GND/4 SDA
    pads = [("1", -1.0, -1.0), ("2", -1.0, 0.0), ("3", -1.0, 1.0),
            ("4", 1.0, 1.0), ("5", 1.0, 0.0), ("6", 1.0, -1.0)]

    out = [f'(footprint "{fid}" (version 20221018) (generator opencad-lib)',
           '  (layer "F.Cu")',
           '  (descr "ASAIR AHT20 humidity and temperature sensor, I2C, SMD LGA-6 3x3x1.0mm. '
           'Land pattern per ASAIR AHT20 datasheet Fig.8 (pads 0.8x0.5, col spacing 2.0, row pitch 1.0).")',
           '  (tags "AHT20 humidity temperature sensor I2C ASAIR")',
           '  (attr smd)',
           '  (fp_text reference "REF**" (at 0 -2.6) (layer "F.SilkS")'
           '\n    (effects (font (size 1 1) (thickness 0.15))))',
           f'  (fp_text value "{fid}" (at 0 2.6) (layer "F.Fab")'
           '\n    (effects (font (size 1 1) (thickness 0.15))))']
    # Fab 본체 3x3 + 1번핀 챔퍼(1mm, 좌상)
    out += _rect_lines([(-0.5, -1.5, 1.5, -1.5), (1.5, -1.5, 1.5, 1.5),
                        (1.5, 1.5, -1.5, 1.5), (-1.5, 1.5, -1.5, -0.5),
                        (-1.5, -0.5, -0.5, -1.5)], "F.Fab", 0.10)
    # Silk 외곽 (패드 에지 x1.4에서 0.2 이상 이격) + 1번핀 틱
    out += _rect_lines([(-1.66, -1.66, 1.66, -1.66), (1.66, -1.66, 1.66, 1.66),
                        (1.66, 1.66, -1.66, 1.66), (-1.66, 1.66, -1.66, -1.66)], "F.SilkS", 0.12)
    out.append(_line(-1.9, -1.25, -1.9, -0.75, "F.SilkS", 0.12))  # pin1 틱
    # Courtyard (본체+0.25)
    out += _rect_lines([(-1.75, -1.75, 1.75, -1.75), (1.75, -1.75, 1.75, 1.75),
                        (1.75, 1.75, -1.75, 1.75), (-1.75, 1.75, -1.75, -1.75)], "F.CrtYd", 0.05)
    for name, x, y in pads:
        out.append(f'  (pad "{name}" smd rect (at {x} {y}) (size 0.8 0.5) '
                   f'(layers "F.Cu" "F.Paste" "F.Mask"))')
    out.append(')')
    footprint = "\n".join(out) + "\n"

    # 심볼: 데이터시트 Table 5 그대로 (탑뷰 좌 1/2/3 위→아래, 우 6/5/4 위→아래)
    symbol = _lr_symbol(fid, left=[("1", "NC"), ("2", "VDD"), ("3", "SCL")],
                        right=[("6", "NC"), ("5", "GND"), ("4", "SDA")])
    meta = {
        "id": fid, "name": "AHT20 Humidity and Temperature Sensor",
        "category": "sensor", "family": "AHT2x", "manufacturer": "Aosong (ASAIR)",
        "mpn_pattern": "AHT20",
        "description": "ASAIR AHT20 calibrated digital humidity and temperature sensor, I2C (address 0x38), "
                       "SMD LGA-6 package 3x3x1.0mm. Land pattern per manufacturer datasheet.",
        "parameters": {"contacts": 6, "mounting": "SMD", "interface": "I2C",
                       "i2c_address": "0x38", "supply_voltage": "2.2-5.5V",
                       "body_mm": "3.0x3.0x1.0"},
        "files": {"footprint": f"{fid}.kicad_mod", "symbol": f"{fid}.kicad_sym",
                  "model_3d": f"{fid}.step", "preview": f"{fid}.glb",
                  "footprint_svg": f"{fid}.footprint.svg", "symbol_svg": f"{fid}.symbol.svg"},
        "formats": ["kicad_mod", "kicad_sym", "step", "glb"],
        "datasheet": "https://asairsensors.com/wp-content/uploads/2021/09/"
                     "Data-Sheet-AHT20-Humidity-and-Temperature-Sensor-ASAIR-V1.0.03.pdf",
        "dimensions_source": "ASAIR AHT20 datasheet V1.0 (May 2021): Fig.1 package 3x3x1.0mm (lid 2.8), "
                             "Fig.8 recommended land pattern (6 pads 0.8x0.5, col spacing 2.0, row pitch 1.0), "
                             "Table 5 pinout.",
        "verified": True, "license": "CC-BY-4.0", "generated_by": "generators/gen_parts.py",
        "keywords": ["aht20", "asair", "aosong", "humidity", "temperature", "sensor", "i2c", "lga", "3x3mm"],
    }
    return fid, lib_path, footprint, symbol, meta


PARTS = [usb_c_16p, microsd_hc, esp32_wroom32, aht20]  # 일회성 부품 등록


def main():
    for fn in PARTS:
        fid, lib_path, footprint, symbol, meta = fn()
        d = os.path.normpath(os.path.join(LIB_ROOT, lib_path, fid))
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, f"{fid}.kicad_mod"), "w", encoding="utf-8").write(footprint)
        open(os.path.join(d, f"{fid}.kicad_sym"), "w", encoding="utf-8").write(symbol)
        json.dump(meta, open(os.path.join(d, "meta.json"), "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)
        print(f"  {fid}")
    print("Done.")


if __name__ == "__main__":
    print("Generating discrete parts...")
    main()
