"""
KiCad 파일 구조 검증기 (교차검증용 — HTTP/시각 검사와 독립).
실행: python generators/validate_kicad.py

각 부품의 .kicad_mod / .kicad_sym를 s-expression으로 직접 파싱해서:
  - 괄호 균형 + 루트 토큰(footprint / kicad_symbol_lib)
  - 풋프린트: 패드 개수 == 핀 수, 패드번호 1..N, 1번핀 (at 0 0), 피치 2.0 일치,
    필수 레이어(F.Cu/F.SilkS/F.CrtYd/F.Fab) 존재
  - 심볼: 핀 개수 == 핀 수
"불량이 있으면 비0 종료" → CI/빌드 게이트로도 사용 가능.
"""

import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
PITCH = 2.0


def balanced(text):
    depth = 0
    in_str = False
    esc = False
    for ch in text:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and not in_str


def check_footprint(text, pins, pitch):
    errs = []
    if not balanced(text):
        errs.append("괄호 불균형")
    if not re.match(r'\s*\(footprint\b', text):
        errs.append("루트가 footprint 아님")
    # 패드: (pad "N" type shape (at X Y ...)
    pads = re.findall(r'\(pad\s+"(\d+)"[^)]*?\(at\s+([-\d.]+)\s+([-\d.]+)', text)
    nums = sorted(int(n) for n, _, _ in pads)
    if len(pads) != pins:
        errs.append(f"패드 수 {len(pads)} != 핀 수 {pins}")
    if nums != list(range(1, pins + 1)):
        errs.append(f"패드 번호 불연속: {nums}")
    xs = {int(n): float(x) for n, x, _ in pads}
    if xs.get(1) != 0.0:
        errs.append(f"1번핀 X != 0 ({xs.get(1)})")
    for n in nums:
        expected = (n - 1) * pitch
        if abs(xs.get(n, -999) - expected) > 1e-6:
            errs.append(f"{n}번핀 X={xs.get(n)} != 기대 {expected}")
            break
    for layer in ('"F.Cu"', '"F.SilkS"', '"F.CrtYd"', '"F.Fab"'):
        if layer not in text:
            errs.append(f"레이어 {layer} 없음")
    return errs


def check_symbol(text, pins):
    errs = []
    if not balanced(text):
        errs.append("괄호 불균형")
    if not re.match(r'\s*\(kicad_symbol_lib\b', text):
        errs.append("루트가 kicad_symbol_lib 아님")
    npins = len(re.findall(r'\(pin\s+\w+\s+\w+\s+\(at', text))
    if npins != pins:
        errs.append(f"핀 수 {npins} != 기대 {pins}")
    return errs


def main():
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    total_err = 0
    for p in index["parts"]:
        pins = p["pins"]
        d = os.path.join(ROOT, p["path"])
        fid = p["id"]
        meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
        pitch = meta["parameters"]["pitch_mm"]
        mod = open(os.path.join(d, f"{fid}.kicad_mod"), encoding="utf-8").read()
        sym = open(os.path.join(d, f"{fid}.kicad_sym"), encoding="utf-8").read()
        errs = [f"[mod] {e}" for e in check_footprint(mod, pins, pitch)]
        errs += [f"[sym] {e}" for e in check_symbol(sym, pins)]
        if errs:
            total_err += len(errs)
            print(f"FAIL {fid}:")
            for e in errs:
                print(f"   - {e}")
        else:
            print(f"OK   {fid}  (pads={pins}, pins={pins})")
    print(f"\n{'PASS' if total_err == 0 else 'FAIL'}: {len(index['parts'])} parts, {total_err} errors")
    sys.exit(1 if total_err else 0)


if __name__ == "__main__":
    main()
