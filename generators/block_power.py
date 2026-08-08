"""
블록용 전원 심볼 (자체 작성 — 공식 라이브러리 카피 아님, 관례 도형을 직접 그림).

동작 원리 (KiCad 표준 메커니즘):
  - 전원 심볼의 숨은 power 핀 '이름'이 곧 네트 이름이 된다 (전역 네트).
  - flag는 power_out 핀으로 그 네트에 '공급원' 표식을 줘 ERC의
    power_pin_not_driven을 만족시킨다 (PWR_FLAG와 같은 원리, 자체 도형).
"""


def _sym(name, value, pin_type, pin_name, graphics, value_y):
    g = "\n".join(graphics)
    return (
        f'(symbol "{name}" (power) (pin_names (offset 0)) (in_bom no) (on_board yes)\n'
        f'  (property "Reference" "#PWR" (at 0 {value_y - 2.54:g} 0)'
        " (effects (font (size 1.27 1.27)) (hide yes)))\n"
        f'  (property "Value" "{value}" (at 0 {value_y:g} 0)'
        " (effects (font (size 1.27 1.27))))\n"
        f'  (symbol "{name}_1_1"\n{g}\n'
        f'    (pin {pin_type} line (at 0 0 270) (length 0) hide'
        f' (name "{pin_name}" (effects (font (size 1.27 1.27))))'
        ' (number "1" (effects (font (size 1.27 1.27)))))\n'
        "  ))"
    )


def _line(x1, y1, x2, y2):
    return (f"    (polyline (pts (xy {x1:g} {y1:g}) (xy {x2:g} {y2:g}))"
            " (stroke (width 0.254) (type solid)) (fill (type none)))")


def gnd_symbol():
    """접지: 세로 스텁 + 3단 감소 바 (자체 도형)."""
    return _sym("PR_GND", "GND", "power_in", "GND", [
        _line(0, 0, 0, -1.27),
        _line(-1.27, -1.27, 1.27, -1.27),
        _line(-0.762, -1.778, 0.762, -1.778),
        _line(-0.254, -2.286, 0.254, -2.286),
    ], -4.445)


def rail_symbol(net):
    """전원 레일 (+5V 등): 세로 스텁 + 위 화살촉 (자체 도형)."""
    name = "PR_" + net.replace("+", "P").replace("-", "N")
    return name, _sym(name, net, "power_in", net, [
        _line(0, 0, 0, 1.27),
        _line(-0.762, 1.27, 0, 2.54),
        _line(0, 2.54, 0.762, 1.27),
        _line(-0.762, 1.27, 0.762, 1.27),
    ], 3.81)


def flag_symbol():
    """공급원 표식 (PWR_FLAG 상당, 자체 도형): 스텁 + 깃발."""
    return _sym("PR_FLAG", "FLAG", "power_out", "flag", [
        _line(0, 0, 0, 1.27),
        _line(0, 1.27, 1.524, 1.905),
        _line(1.524, 1.905, 0, 2.54),
        _line(0, 2.54, 0, 1.27),
    ], 3.81)
