"""
렌더 완전성 검사 — 우리가 겪은 버그 클래스를 자동 검출.
실행: python generators/check_render.py  (실패 시 비0 종료 → CI 게이트)

부품마다:
  A. meta.files의 모든 파일이 실제 존재 ("버튼은 있는데 파일 없음" 방지)
  B. 풋프린트 SVG에 <ellipse> 없음 (슬롯은 obround여야 함 — UFO 버그 방지)
  C. SVG 동판 패드 수 == .kicad_mod 동판 패드 수 (SMD 등 패드 누락 방지)
  D. SVG 외곽선(line) 수 == .kicad_mod 외곽선 수 (외곽선 안 그려짐 방지)
  E. 심볼 SVG 핀선 수 == .kicad_sym 핀 수 (핀 누락 방지)
"""
import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


def main():
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    total = 0
    for p in index["parts"]:
        d = os.path.join(ROOT, p["path"])
        fid = p["id"]
        meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
        errs = []

        # A. 파일 존재
        for key, fn in meta.get("files", {}).items():
            if not os.path.exists(os.path.join(d, fn)):
                errs.append(f"파일 없음: {fn}")
        # A2. 부품 페이지 존재 (build_site 누락 방지 — /p/<id>/ 404 방지)
        if not os.path.exists(os.path.join(ROOT, "p", fid, "index.html")):
            errs.append("부품 페이지 없음 (build_site.py 실행 필요)")
        # A3. API 상세 존재 (build_api 누락 방지 — /api/v1/parts/<id>.json 404 방지)
        if not os.path.exists(os.path.join(ROOT, "api", "v1", "parts", f"{fid}.json")):
            errs.append("API 상세 없음 (build_api.py 실행 필요)")
        # A4. 메타 완결성 — 기여물 포함 전부: 출처·데이터시트·라이선스 필수 (§14-E)
        if not str(meta.get("datasheet", "")).startswith("http"):
            errs.append("datasheet URL 없음")
        if len(str(meta.get("dimensions_source", ""))) < 10:
            errs.append("dimensions_source 없음 (치수 출처 필수)")
        # 자체 생성=CC-BY-4.0 / 수입=원 라이선스 유지 (§21-6ⓒ: 재라이선스 금지)
        _ALLOWED_LIC = {"CC-BY-4.0", "CERN-OHL-P-2.0", "MIT"}
        if meta.get("license") not in _ALLOWED_LIC:
            errs.append(f"license not in allowed set ({meta.get('license')})")
        if meta.get("origin") != "imported" and meta.get("license") != "CC-BY-4.0":
            errs.append("non-imported part must be CC-BY-4.0")

        kmod = _read(d, meta["files"].get("footprint"))
        ksym = _read(d, meta["files"].get("symbol"))
        fsvg = _read(d, meta["files"].get("footprint_svg"))
        ssvg = _read(d, meta["files"].get("symbol_svg"))

        if fsvg is not None and kmod is not None:
            # B. ellipse 금지
            if "<ellipse" in fsvg:
                errs.append("풋프린트 SVG에 <ellipse> 있음 (슬롯은 obround여야)")
            # C. 동판 패드 수
            kmod_copper = len(re.findall(r'\(pad\s', kmod)) - len(re.findall(r'np_thru_hole', kmod))
            svg_copper = fsvg.count('fill="#c79b5c"')
            if svg_copper != kmod_copper:
                errs.append(f"동판 패드 SVG={svg_copper} != kicad_mod={kmod_copper}")
            # D. 외곽선 수
            kmod_lines = len(re.findall(r'\(fp_line\b[^\n]*\(layer "F\.(?:SilkS|Fab|CrtYd)"\)', kmod))
            svg_lines = fsvg.count('<line')
            if svg_lines != kmod_lines:
                errs.append(f"외곽선 SVG={svg_lines} != kicad_mod={kmod_lines}")

        if ssvg is not None and ksym is not None:
            # E. 심볼 핀 수
            _pins_all = re.findall(r'\(pin\s+\w+\s+\w+\s+\(at([^)]*)\)\s*\(length\s+[-\d.]+\)((?:\s|hide|\(hide\s+yes\))*)\(', ksym)
            # 스택 핀(같은 위치·각도, 벤더 쉴드 관례)은 렌더러가 1개로 병합 표시 → 고유 위치로 센다
            ksym_pins = len({at.strip() for at, f in _pins_all if 'hide' not in f})
            ssvg_pins = ssvg.count('<line')
            if ssvg_pins != ksym_pins:
                errs.append(f"심볼 핀선 SVG={ssvg_pins} != kicad_sym={ksym_pins}")

        if errs:
            total += len(errs)
            print(f"FAIL {fid}:")
            for e in errs:
                print(f"   - {e}")

    print(f"\n{'PASS' if total == 0 else 'FAIL'}: {len(index['parts'])} parts, {total} issues")
    sys.exit(1 if total else 0)


def _read(d, fn):
    if not fn:
        return None
    path = os.path.join(d, fn)
    return open(path, encoding="utf-8").read() if os.path.exists(path) else None


if __name__ == "__main__":
    main()
