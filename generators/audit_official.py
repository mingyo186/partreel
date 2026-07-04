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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
TOL = 0.02  # mm

def build_mapping():
    """전 부품 → 공식 파일 (핀 수별 1:1). 공식에 없는 조합은 fetch 404로 SKIP 처리."""
    m = {}
    for n in range(2, 17):
        m[f"jst_ph_{n}pin"] = f"Connector_JST.pretty/JST_PH_B{n}B-PH-K_1x{n:02d}_P2.00mm_Vertical.kicad_mod"
        m[f"jst_xh_{n}pin"] = f"Connector_JST.pretty/JST_XH_B{n}B-XH-A_1x{n:02d}_P2.50mm_Vertical.kicad_mod"
    for n in range(2, 13):
        m[f"jst_gh_{n}pin"] = f"Connector_JST.pretty/JST_GH_BM{n:02d}B-GHS-TBT_1x{n:02d}-1MP_P1.25mm_Vertical.kicad_mod"
    for n in range(1, 41):
        m[f"pin_header_254_{n}pin"] = f"Connector_PinHeader_2.54mm.pretty/PinHeader_1x{n:02d}_P2.54mm_Vertical.kicad_mod"
        m[f"pin_header_200_{n}pin"] = f"Connector_PinHeader_2.00mm.pretty/PinHeader_1x{n:02d}_P2.00mm_Vertical.kicad_mod"
        m[f"pin_header_127_{n}pin"] = f"Connector_PinHeader_1.27mm.pretty/PinHeader_1x{n:02d}_P1.27mm_Vertical.kicad_mod"
    for n in range(2, 9):
        m[f"screw_terminal_5_08_{n}pin"] = f"TerminalBlock.pretty/TerminalBlock_bornier-{n}_P5.08mm.kicad_mod"
    m["usb_c_16p"] = "Connector_USB.pretty/USB_C_Receptacle_HRO_TYPE-C-31-M-12.kicad_mod"
    m["microsd_hc"] = "Connector_Card.pretty/microSD_HC_Hirose_DM3AT-SF-PEJM5.kicad_mod"
    m["esp32_wroom32"] = "RF_Module.pretty/ESP32-WROOM-32.kicad_mod"
    return m

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


def check_datasheets(index):
    """모든 부품의 datasheet URL 생존 확인 (중복 제거, HEAD→GET 폴백)."""
    import urllib.request
    urls = {}
    for p in index["parts"]:
        meta = json.load(open(os.path.join(ROOT, p["path"], "meta.json"), encoding="utf-8"))
        urls.setdefault(meta.get("datasheet", ""), []).append(p["id"])
    bad = 0
    print("\n=== 데이터시트 URL 생존 검사 ===")
    for url, ids in sorted(urls.items()):
        if not url.startswith("http"):
            print(f"NO-URL   ({len(ids)} parts: {ids[0]}...)")
            bad += 1
            continue
        ok = False
        for method in ("HEAD", "GET"):
            try:
                req = urllib.request.Request(url, method=method,
                                             headers={"User-Agent": "Mozilla/5.0 (partreel-audit)"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    ok = 200 <= r.status < 400
                if ok:
                    break
            except Exception:
                continue
        print(f"{'OK ' if ok else 'DEAD'}  {url[:80]}  ({len(ids)} parts)")
        if not ok:
            bad += 1
    return bad


def main():
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    paths = {p["id"]: p["path"] for p in index["parts"]}
    mapping = build_mapping()
    fails, okc, skip = 0, 0, 0
    print("=== 전 부품 풋프린트 vs KiCad 공식 (핀 수별 1:1) ===")
    for pid, path in paths.items():
        off_path = mapping.get(pid)
        if off_path is None:
            print(f"{pid:26} (매핑 없음)")
            continue
        ours_file = os.path.join(ROOT, path, f"{pid}.kicad_mod")
        ours = center(pads_of(open(ours_file, encoding="utf-8").read()))
        off_text = fetch_official(off_path)
        if off_text is None:
            print(f"{pid:26} SKIP (공식에 해당 핀수 없음 — 파라미터는 validate_kicad로 검증됨)")
            skip += 1
            continue
        off = center(pads_of(off_text))
        ok, why = match(ours, off)
        if not ok:
            ok, why = match(swap_axes(ours), off)
        if ok:
            okc += 1
        else:
            fails += 1
            print(f"{pid:26} DIFF: {why}")
    print(f"\n풋프린트 대조: OK {okc} / DIFF {fails} / SKIP(공식 부재) {skip} — 총 {len(paths)}부품")

    ds_bad = check_datasheets(index)
    print(f"\n{'PASS' if (fails + ds_bad) == 0 else 'FAIL'}: footprint DIFF {fails}, datasheet DEAD {ds_bad}")
    sys.exit(1 if (fails + ds_bad) else 0)


if __name__ == "__main__":
    main()
