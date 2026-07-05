"""
CERN 라이브러리 검증-수입 Wave 0 (REQUIREMENTS §21-6ⓒ 수입확대, docs/cern-import-plan.md).
실행: CERN_SRC=<클론경로> python generators/import_cern.py
그 후: build_index → render_svg → build_site → build_api → qa (실패분 드롭 후 재실행)

- 소스: CERN.sqlite (부품 진실원) → SchLib/*.kicad_sym + PcbLib/*.pretty
- 3D 원본 부재 → verified-2D 등급 (files에 step/glb 없음, 페이지 3D탭 숨김)
- CERN-OHL-P-2.0 유지(§3.3: 수정 고지 + 날짜 필수 → meta.import.modifications + import_date)
"""
import json
import os
import re
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
LIB_ROOT = os.path.join(ROOT, "library")
SRC = os.environ.get("CERN_SRC", "").strip()
COMMIT = "53054c17"
REPO = "https://gitlab.com/ohwr/cern-kicad-libs"
IMPORT_DATE = "2026-07-05"

WAVE0 = {"Crystals & Oscillators": ("timing", "CERN Crystals & Oscillators"),
         "LEMO": ("connector", "CERN LEMO")}
# Wave 1: 벤더 커넥터 전 테이블 + 소켓 (docs/cern-import-plan.md §6)
WAVE1 = {t: ("connector", f"CERN {t}") for t in
         ["3M", "AMPHENOL", "ERNI", "FCI", "HARTING", "HARWIN", "MENTOR",
          "MOLEX", "PHOENIX", "SAMTEC", "SOURIAU", "STELVIO-KONTEK COMATEL",
          "TYCO", "WEIDMULLER"]}
WAVE1["Sockets"] = ("socket", "CERN Sockets")
# Wave 2: IC/반도체 (docs/cern-import-plan.md §6 — 멀티유닛 렌더 지원 완료 전제)
WAVE2 = {"Analog & Interface": ("ic", "CERN Analog & Interface"),
         "Operational Amplifiers": ("ic", "CERN Op Amps"),
         "Regulators": ("ic", "CERN Regulators"),
         "Logic": ("ic", "CERN Logic"),
         "Standard Logic": ("ic", "CERN Standard Logic"),
         "Optocouplers": ("ic", "CERN Optocouplers"),
         "DC-DC Converters": ("power", "CERN DC-DC Converters"),
         "Diodes": ("discrete", "CERN Diodes"),
         "Transistors": ("discrete", "CERN Transistors"),
         "Sensors": ("sensor", "CERN Sensors")}
WAVES = {"0": WAVE0, "1": WAVE1, "2": WAVE2}


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return re.sub(r"_+", "_", s)


def balanced_block(text, start):
    depth, i, in_str = 0, start, False
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == '"' and text[i - 1] != "\\":
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    return None


_symcache = {}


def get_symbol(libname, symname):
    if libname not in _symcache:
        p = os.path.join(SRC, "SchLib", libname + ".kicad_sym")
        _symcache[libname] = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    text = _symcache[libname]
    m = re.search(r'\(symbol\s+"' + re.escape(symname) + r'"', text)
    if not m:
        return None
    return balanced_block(text, m.start())


def geo_bbox(fp_text):
    x0 = y0 = 1e9
    x1 = y1 = -1e9
    for m in re.finditer(r'\(pad\s+"[^"]*"\s+\w+\s+\w+\s*\(at\s+([-\d.]+)\s+([-\d.]+)'
                         r'[^)]*\)\s*\(size\s+([-\d.]+)\s+([-\d.]+)', fp_text):
        x, y, w, h = map(float, m.groups())
        r = max(w, h) / 2
        x0, y0, x1, y1 = min(x0, x - r), min(y0, y - r), max(x1, x + r), max(y1, y + r)
    for m in re.finditer(r'\(fp_line\s*\(start\s+([-\d.]+)\s+([-\d.]+)\)\s*'
                         r'\(end\s+([-\d.]+)\s+([-\d.]+)\)', fp_text):
        a, b, c, d = map(float, m.groups())
        x0, y0, x1, y1 = min(x0, a, c), min(y0, b, d), max(x1, a, c), max(y1, b, d)
    # fp_poly / fp_arc 좌표 (xy 포인트 전수 — CERN THD 커넥터는 폴리곤 중심)
    for m in re.finditer(r'\(xy\s+([-\d.]+)\s+([-\d.]+)\)', fp_text):
        a, b = float(m.group(1)), float(m.group(2))
        x0, y0, x1, y1 = min(x0, a), min(y0, b), max(x1, a), max(y1, b)
    return (x0, y0, x1, y1) if x1 > x0 else None


def add_courtyard(fp_text, bbox):
    x0, y0, x1, y1 = [round(v + s * 0.25, 2) for v, s in zip(bbox, (-1, -1, 1, 1))]
    lines = ""
    for (a, b, c, d) in [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1),
                         (x0, y1, x0, y0)]:
        lines += (f'  (fp_line (start {a} {b}) (end {c} {d})'
                  f' (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))\n')
    i = fp_text.rstrip().rfind(")")
    return fp_text.rstrip()[:i] + lines + ")\n"


def main():
    if not SRC or not os.path.exists(os.path.join(SRC, "CERN.sqlite")):
        print("CERN_SRC not set or CERN.sqlite missing")
        sys.exit(2)
    con = sqlite3.connect(os.path.join(SRC, "CERN.sqlite"))
    con.row_factory = sqlite3.Row
    accepted, skipped = [], []
    used_ids = set()
    wave = os.environ.get("CERN_WAVE", "0")
    for table, (category, family) in WAVES[wave].items():
        for row in con.execute(f'SELECT * FROM "{table}"'):
            r = dict(row)
            key = r.get("Part Number Nocolon") or r.get("Part Number") or ""
            manuf = r.get("Manufacturer") or ("LEMO" if table == "LEMO" else "CERN library")
            mpn = r.get("Manufacturer Part Number") or r.get("Part Number") or key
            status = (r.get("Status") or "").strip()
            libsym = r.get("LibSymbol") or ""
            libfp = r.get("LibFootprint") or ""
            reason = None
            if ":" not in libsym or ":" not in libfp:
                reason = "missing symbol/footprint reference"
            if reason:
                skipped.append((key, reason))
                continue
            sym_lib, sym_name = libsym.split(":", 1)
            fp_lib, fp_name = libfp.split(":", 1)
            blk = get_symbol(sym_lib, sym_name)
            if blk is None:
                skipped.append((key, f"symbol not found ({libsym})"))
                continue
            if re.search(r'\(extends\s', blk):
                skipped.append((key, "derived symbol"))
                continue
            # 멀티유닛 심볼: 렌더러 유닛 분리 지원(2026-07-05)으로 수입 허용
            fp_path = os.path.join(SRC, "PcbLib", fp_lib + ".pretty", fp_name + ".kicad_mod")
            if not os.path.exists(fp_path):
                skipped.append((key, f"footprint file missing ({libfp})"))
                continue
            fp_text = open(fp_path, encoding="utf-8").read()
            if '"F.SilkS"' not in fp_text or '"F.Fab"' not in fp_text:
                skipped.append((key, "missing silk/fab layer"))
                continue
            mods = ["extracted single symbol from library",
                    "stripped dead 3D model reference (upstream ships no 3D)"]
            # (model ...) 제거는 균형 추출로 (§14-H: 중첩 괄호에 정규식 금지)
            while True:
                mm = re.search(r'\(model\s', fp_text)
                if not mm:
                    break
                blk_m = balanced_block(fp_text, mm.start())
                if blk_m is None:
                    break
                fp_text = fp_text.replace(blk_m, "", 1)
            if '"F.CrtYd"' not in fp_text:
                bbox = geo_bbox(fp_text)
                if bbox is None:
                    skipped.append((key, "no geometry for courtyard"))
                    continue
                fp_text = add_courtyard(fp_text, bbox)
                mods.append("auto-added courtyard (pads+outline+poly bbox +0.25mm)")

            pid = "cern_" + slug(key)
            if pid in used_ids:
                skipped.append((key, "duplicate id"))
                continue
            used_ids.add(pid)

            sym_text = ('(kicad_symbol_lib (version 20211014) (generator partreel-import)\n'
                        + "  " + blk.replace("\n", "\n  ").rstrip() + "\n)\n")
            desc = (r.get("Part Description") or r.get("Comment") or key).strip()
            pins = r.get("Pin Count")
            meta = {
                "id": pid, "name": f"{mpn} (CERN library)", "category": category,
                "family": family, "manufacturer": manuf, "mpn_pattern": mpn,
                "description": f"{desc}. Imported from the CERN KiCad library "
                               f"(CERN-OHL-P-2.0, (c) CERN); passed PartReel quality "
                               f"gates. Verified-2D part: upstream ships no 3D models."
                               + (f" Lifecycle status: {status}." if status else ""),
                "parameters": {k: v for k, v in {
                    "contacts": pins, "mounting": ("SMD" if r.get("SMD") in (1, "1", "True", "Yes")
                                                   else None),
                    "case": r.get("Case"), "value": r.get("Value"),
                    "lifecycle": status or None}.items() if v not in (None, "")},
                "files": {"footprint": f"{pid}.kicad_mod", "symbol": f"{pid}.kicad_sym",
                          "footprint_svg": f"{pid}.footprint.svg",
                          "symbol_svg": f"{pid}.symbol.svg"},
                "formats": ["kicad_mod", "kicad_sym"],
                "datasheet": f"{REPO}/-/blob/master/SchLib/{sym_lib}.kicad_sym",
                "dimensions_source": f"cern-kicad-libs@{COMMIT} "
                                     f"({fp_lib}.pretty/{fp_name}.kicad_mod)",
                "verified": True, "origin": "imported", "tier": "verified-2d",
                "license": "CERN-OHL-P-2.0",
                "generated_by": "generators/import_cern.py",
                "keywords": ["cern"] + [w for w in slug(desc).split("_") if len(w) > 2][:6],
                "import": {
                    "source_repo": REPO, "source_commit": COMMIT,
                    "source_files": {"db": f"CERN.sqlite#{table}#{key}",
                                     "symbol": f"SchLib/{sym_lib}.kicad_sym#{sym_name}",
                                     "footprint": f"PcbLib/{fp_lib}.pretty/{fp_name}.kicad_mod"},
                    "attribution": "CERN (kicad-dev@cern.ch), CERN-OHL-P-2.0",
                    "import_date": IMPORT_DATE, "modifications": mods,
                },
            }
            d = os.path.join(LIB_ROOT, category, "cern", pid)
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, f"{pid}.kicad_mod"), "w", encoding="utf-8").write(fp_text)
            open(os.path.join(d, f"{pid}.kicad_sym"), "w", encoding="utf-8").write(sym_text)
            json.dump(meta, open(os.path.join(d, "meta.json"), "w", encoding="utf-8"),
                      indent=2, ensure_ascii=False)
            accepted.append(pid)
    log = {"commit": COMMIT, "wave": wave, "accepted": accepted,
           "skipped": [{"part": k, "reason": v} for k, v in skipped]}
    json.dump(log, open(os.path.join(ROOT, "docs", "import-cern-wave%s-log.json" % wave), "w",
                        encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"accepted {len(accepted)}, skipped {len(skipped)}")


if __name__ == "__main__":
    main()
