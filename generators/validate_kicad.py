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
    if len(re.findall(r'\(pad\s', text)) < 1:
        errs.append("패드 없음")
    for layer in ('"F.Cu"', '"F.SilkS"', '"F.CrtYd"', '"F.Fab"'):
        if layer not in text:
            errs.append(f"레이어 {layer} 없음")
    # 일렬 커넥터(피치 있음)일 때만 행 검사: 패드 수/번호/1번핀 원점/피치
    if pitch is not None and pins:
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
            if abs(xs.get(n, -999) - (n - 1) * pitch) > 1e-6:
                errs.append(f"{n}번핀 X={xs.get(n)} != 기대 {(n-1)*pitch}")
                break
    return errs


def check_symbol(text, pins):
    errs = []
    if not balanced(text):
        errs.append("괄호 불균형")
    if not re.match(r'\s*\(kicad_symbol_lib\b', text):
        errs.append("루트가 kicad_symbol_lib 아님")
    # 서브유닛 접두 == 부모 심볼명 (2026-08-01 aht30 사건: 복제 생성기가
    # "aht20_1_1" 서브유닛을 남겨 병합 라이브러리 전체가 KiCad 로드 실패).
    # 부품 id 자체가 _N_M로 끝날 수 있으므로(sparkfun_..._jps_3_1) 이름
    # 패턴이 아니라 괄호 깊이로 상위(깊이1)/서브(깊이2)를 구분한다.
    depth, in_str, cur_top = 0, False, None
    i = 0
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == '"' and text[i - 1] != "\\":
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "(":
            m = re.match(r'\(symbol\s+"([^"]+)"', text[i:])
            if m:
                if depth == 1:
                    cur_top = m.group(1)
                elif depth == 2 and cur_top:
                    if not m.group(1).startswith(cur_top + "_"):
                        errs.append(f"서브유닛 '{m.group(1)}' 접두가 부모 "
                                    f"'{cur_top}'와 불일치")
            depth += 1
        elif ch == ")":
            depth -= 1
        i += 1
    # 다이오드/LED(참조기호 D)는 도형으로 종류가 읽혀야 한다 — 사각형만 있는
    # 심볼은 회로도에서 오독된다. 또 2단자 극성 부품의 두 핀이 같은 쪽에 붙어
    # 있으면 안 된다. (2026-08-01 사용자 지적: ai03 LED 8종이 네모 + 핀 동일측)
    ref = re.search(r'\(property "Reference" "([^"]*)"', text)
    if ref and ref.group(1).strip() == "D":
        if "(polyline" not in text:
            errs.append("참조기호 D인데 도형이 없음 (LED/다이오드는 삼각형+바 필요)")
        pin_pos = re.findall(r'\(pin\s+\w+\s+\w+\s+\(at\s+([-\d.]+)\s+([-\d.]+)', text)
        if len(pin_pos) == 2:
            xs = [float(x) for x, _ in pin_pos]
            if (xs[0] < 0) == (xs[1] < 0):
                errs.append(f"2단자 극성 부품의 핀이 같은 쪽에 있음 (x={xs})")

    npins = len(re.findall(r'\(pin\s+\w+\s+\w+\s+\(at', text))
    if pins and npins != pins:
        errs.append(f"핀 수 {npins} != 기대 {pins}")
    elif npins < 1:
        errs.append("핀 없음")
    return errs


def main():
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    from scope import scoped_parts
    index["parts"] = scoped_parts(index["parts"])  # PART_SCOPE 증분 (§19-A)
    total_err = 0
    for p in index["parts"]:
        d = os.path.join(ROOT, p["path"])
        fid = p["id"]
        meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
        params = meta.get("parameters", {})
        pins = params.get("pins")
        pitch = params.get("pitch_mm")
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
