"""
MCU 심볼 생성기 (R16: 실물 4면 배치) — ST 공식 핀 XML -> .kicad_sym

규칙 (rules/schematic-readability.md R16, 2026-08-10 사용자 확정):
  포트순 정렬이 아니라 **칩 핀 번호 순서대로 패키지 4면에** 다리를 낸다
  (LQFP/QFN: 핀1 좌상단에서 반시계). 참조기호는 좌상단 바깥, 값은 몸체
  내부 빈 중앙 아래. 형번은 온도 접미 와일드카드(x) 단위로 묶는다
  (예: STM32G431CBTx — 6/7은 온도 등급일 뿐 핀·패키지 동일).

1차 사료: STMicroelectronics/STM32_open_pin_data (제조사 기계가독 핀표).
손 전사 금지 — XML의 Name/Position/Type을 그대로 쓴다.

실행: python generators/gen_mcu.py "<XML파일명>" <부품id>
예:   python generators/gen_mcu.py "STM32G431C(6-8-B)Tx.xml" stm32g431cbtx
"""

import base64
import math
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
REPO = "STMicroelectronics/STM32_open_pin_data"
PITCH = 2.54
PIN_LEN = 5.08


def fetch_xml(name):
    r = subprocess.run(["gh", "api", f"repos/{REPO}/contents/mcu/{name}",
                        "--jq", ".content"], capture_output=True, text=True)
    if not r.stdout.strip():
        raise SystemExit(f"FAIL: {name} 을 {REPO}에서 못 받음")
    return base64.b64decode(r.stdout.strip()).decode("utf-8", "replace")


def pin_type(t):
    if t == "Power":
        return "power_in"
    if t in ("Reset", "Boot"):
        return "input"
    return "bidirectional"


def build(xml_name, pid):
    xml = fetch_xml(xml_name)
    pkg = re.search(r'Package="([^"]+)"', xml).group(1)
    pins = {int(p): (n, t) for n, p, t in
            re.findall(r'<Pin Name="([^"]+)" Position="(\d+)" Type="([^"]+)"', xml)}
    n = len(pins)
    if n % 4 != 0:
        raise SystemExit(f"FAIL: 핀 {n}개 — 4면 배치는 4의 배수만 (BGA류는 별도)")
    per = n // 4
    # 변 길이: 핀 스팬 + 여유. 이름 최장 길이에 맞춰 몸체 확장 (겹침 방지)
    span = (per - 1) * PITCH
    start = span / 2
    # 몸체 크기: 모서리에서 '가로 긴 이름(좌/우변) x 세로 긴 이름(상/하변)'
    # 충돌이 없어질 때까지 증분 — 핀 배열이 형번마다 달라 상수로는 안 된다
    # (G431 CBTx는 22.86에서 해소, RBTx는 더 필요함을 실측으로 확인)
    CW = 1.26   # 이름 글자 폭 (렌더 실측: 3자=3.77mm -> 1.257/자)
    GAP = 1.0   # 이름 간 최소 시각 여유

    def name_collision(body):
        inner = body - 1.016  # pin_names offset
        h_names, v_names = [], []
        for k in range(1, n + 1):
            L = len(pins[k][0]) * CW
            if k <= per:                      # 좌변: 행 y, 안쪽으로 +x
                y = start - (k - 1) * PITCH
                h_names.append((y, -inner, -inner + L))
            elif k <= 2 * per:                # 하변: 열 x, 안쪽으로 +y
                x = -start + (k - per - 1) * PITCH
                v_names.append((x, -inner, -inner + L))
            elif k <= 3 * per:                # 우변
                y = -start + (k - 2 * per - 1) * PITCH
                h_names.append((y, inner - L, inner))
            else:                             # 상변
                x = start - (k - 3 * per - 1) * PITCH
                v_names.append((x, inner - L, inner))
        for hy, hx1, hx2 in h_names:
            for vx, vy1, vy2 in v_names:
                if (hx1 - GAP < vx < hx2 + GAP) and (vy1 - GAP < hy < vy2 + GAP):
                    return True
        return False

    body = max(span / 2 + 6.35, 12.7)
    while name_collision(body) and body < 76.2:
        body += 1.27
    conn = body + PIN_LEN

    out = []
    for k in range(1, n + 1):
        name, t = pins[k]
        if k <= per:
            x, y, a = -conn, start - (k - 1) * PITCH, 0
        elif k <= 2 * per:
            x, y, a = -start + (k - per - 1) * PITCH, -conn, 90
        elif k <= 3 * per:
            x, y, a = conn, -start + (k - 2 * per - 1) * PITCH, 180
        else:
            x, y, a = start - (k - 3 * per - 1) * PITCH, conn, 270
        out.append(
            f'''      (pin {pin_type(t)} line (at {x:g} {y:g} {a}) (length {PIN_LEN:g})
        (name "{name}" (effects (font (size 1.27 1.27))))
        (number "{k}" (effects (font (size 1.27 1.27)))))''')

    value = pid.upper().replace("STM32", "STM32")
    sym = f'''(kicad_symbol_lib (version 20231120) (generator "partreel-gen-mcu")
  (symbol "{pid}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
    (property "Reference" "U" (at {-conn:g} {body + 3.18:g} 0) (effects (font (size 1.27 1.27)) (justify left)))
    (property "Value" "{value}" (at 0 {-body / 2.3:.2f} 0) (effects (font (size 1.27 1.27))))
    (symbol "{pid}_1_1"
      (rectangle (start {-body:g} {body:g}) (end {body:g} {-body:g})
        (stroke (width 0.254) (type solid)) (fill (type background)))
{chr(10).join(out)}
    )))'''
    return sym, pkg, n


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    xml_name, pid = sys.argv[1], sys.argv[2]
    sym, pkg, n = build(xml_name, pid)
    outdir = os.path.join(ROOT, "drafts", "mcu")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, f"{pid}.kicad_sym")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(sym)
    print(f"OK {pid}: {pkg} {n}핀 4면 배치 -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
