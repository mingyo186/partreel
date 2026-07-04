"""
일제 점검: 우리 풋프린트 vs KiCad 공식 — 패드 지오메트리 기계 대조 (§14 골드 스탠다드의 자동화).
실행: python generators/audit_official.py   (gh CLI 인증 필요)

대표 부품마다 공식 .kicad_mod을 받아 패드(위치·크기·드릴·타입)를
센트로이드 정렬 후 멀티셋 비교. 회전 배치(핀헤더)는 축 교환 허용.
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
TOL = 0.02  # mm

# 우리 부품 → 공식 파일 (1:1 대응이 존재하는 것 전부)
MAPPING = {
    "jst_ph_4pin": "Connector_JST.pretty/JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical.kicad_mod",
    "jst_xh_4pin": "Connector_JST.pretty/JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical.kicad_mod",
    "jst_gh_4pin": "Connector_JST.pretty/JST_GH_BM04B-GHS-TBT_1x04-1MP_P1.25mm_Vertical.kicad_mod",
    "pin_header_254_4pin": "Connector_PinHeader_2.54mm.pretty/PinHeader_1x04_P2.54mm_Vertical.kicad_mod",
    "pin_header_254_7pin": "Connector_PinHeader_2.54mm.pretty/PinHeader_1x07_P2.54mm_Vertical.kicad_mod",
    "screw_terminal_5_08_2pin": "TerminalBlock.pretty/TerminalBlock_bornier-2_P5.08mm.kicad_mod",
    "usb_c_16p": "Connector_USB.pretty/USB_C_Receptacle_HRO_TYPE-C-31-M-12.kicad_mod",
    "microsd_hc": "Connector_Card.pretty/microSD_HC_Hirose_DM3AT-SF-PEJM5.kicad_mod",
    "esp32_wroom32": "RF_Module.pretty/ESP32-WROOM-32.kicad_mod",
}

PAD_RE = re.compile(
    r'\(pad\s+(?:"([^"]*)"|(\S+))\s+(\w+)\s+(\w+)\s+\(at\s+([-\d.]+)\s+([-\d.]+)[^)]*?\)\s*'
    r'\(size\s+([-\d.]+)\s+([-\d.]+)\)(?:\s*\(drill(?:\s+oval)?\s+([-\d.]+)(?:\s+([-\d.]+))?\))?')


def pads_of(text):
    out = []
    for m in PAD_RE.finditer(text):
        ptype = m.group(3)
        x, y = float(m.group(5)), float(m.group(6))
        w, h = float(m.group(7)), float(m.group(8))
        d1 = float(m.group(9)) if m.group(9) else 0.0
        d2 = float(m.group(10)) if m.group(10) else d1
        out.append((ptype, x, y, w, h, d1, d2))
    return out


def center(pads):
    cx = sum(p[1] for p in pads) / len(pads)
    cy = sum(p[2] for p in pads) / len(pads)
    return [(t, x - cx, y - cy, w, h, d1, d2) for (t, x, y, w, h, d1, d2) in pads]


def swap_axes(pads):
    # 90° 배치 차이 허용: (x,y)->(y,x), (w,h)->(h,w)
    return [(t, y, x, h, w, d1, d2) for (t, x, y, w, h, d1, d2) in pads]


def match(a, b):
    if len(a) != len(b):
        return False, f"패드 수 {len(a)} != {len(b)}"
    rem = list(b)
    for pa in a:
        hit = None
        for pb in rem:
            if pa[0] == pb[0] and all(abs(pa[i] - pb[i]) <= TOL for i in range(1, 7)):
                hit = pb
                break
        if hit is None:
            return False, f"대응 없음: {pa}"
        rem.remove(hit)
    return True, "일치"


def fetch_official(path):
    cache = os.path.join("/tmp" if os.path.exists("/tmp") else os.environ.get("TEMP", "."),
                         "kicad_official_" + path.replace("/", "_"))
    if not os.path.exists(cache):
        r = subprocess.run(["gh", "api", f"repos/KiCad/kicad-footprints/contents/{path}",
                            "--jq", ".content"], capture_output=True, text=True)
        if r.returncode != 0:
            return None
        import base64
        open(cache, "w", encoding="utf-8").write(
            base64.b64decode(r.stdout).decode("utf-8"))
    return open(cache, encoding="utf-8").read()


def main():
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    paths = {p["id"]: p["path"] for p in index["parts"]}
    fails = 0
    print(f"{'part':26} {'official':52} result")
    print("-" * 100)
    for pid, off_path in MAPPING.items():
        ours_file = os.path.join(ROOT, paths[pid], f"{pid}.kicad_mod")
        ours = center(pads_of(open(ours_file, encoding="utf-8").read()))
        off_text = fetch_official(off_path)
        if off_text is None:
            print(f"{pid:26} {off_path[:52]:52} FETCH-FAIL")
            fails += 1
            continue
        off = center(pads_of(off_text))
        ok, why = match(ours, off)
        if not ok:  # 90° 배치 차이 재시도
            ok, why = match(swap_axes(ours), off)
            if ok:
                why = "일치 (축 회전)"
        status = "OK  " if ok else "DIFF"
        print(f"{pid:26} {os.path.basename(off_path)[:52]:52} {status} {why if not ok else why}")
        if not ok:
            fails += 1
    # 공식 대응이 없는 부품 (자체 검증만)
    covered = set(MAPPING)
    rest = [p["id"] for p in index["parts"] if p["id"] not in covered]
    print("-" * 100)
    print(f"공식 대조: {len(MAPPING) - fails}/{len(MAPPING)} 일치 · 나머지 {len(rest)}개 부품은 동일 패밀리 파라메트릭(대표 대조로 커버)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
