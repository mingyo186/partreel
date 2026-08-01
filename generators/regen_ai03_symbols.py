"""
ai03 수입분 심볼 재생성 (REQUIREMENTS §21 품질).

계기(2026-08-01 사용자 지적): LED가 회로도에서 그냥 네모로 그려져 있었다.
수입기가 LED·스위치를 구분 없이 사각형 1개로 그렸고, 게다가 두 핀을 모두
왼쪽에 붙여 놨다(2단자 부품으로 명백한 오류). 수입기(import_ai03.make_symbol)를
표준 도형으로 고쳤으므로, 이미 등록된 부품의 심볼도 같은 함수로 다시 만든다.

풋프린트·meta는 건드리지 않는다 (심볼 도형만 교체).
실행: python generators/regen_ai03_symbols.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
from import_ai03 import make_symbol  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def main():
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    parts = [p for p in index["parts"] if p["id"].startswith("ai03_")]
    led = sw = 0
    for p in parts:
        pid = p["id"]
        d = os.path.join(ROOT, p["path"])
        meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
        is_led = meta.get("parameters", {}).get("type") == "led" or "led" in pid
        text = make_symbol(pid, is_led, meta.get("datasheet") or "")
        open(os.path.join(d, f"{pid}.kicad_sym"), "w", encoding="utf-8",
             newline="\n").write(text)
        led += is_led
        sw += not is_led
    print(f"재생성: LED {led} + 스위치 {sw} = {len(parts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
