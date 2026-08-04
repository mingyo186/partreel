"""
회로 블록 게이트 (REQUIREMENTS §24) — 공식 커널(kicad-cli)이 판정한다.

검사:
  A. block.json 재생성 → 산출물이 소스 선언과 일치 (부품 수·계층 라벨)
  B. **부모 하네스 ERC**: 임시 루트 회로도가 블록을 시트로 불러오고 인터페이스
     네트마다 시트 핀 + 라벨을 단 상태에서 `kicad-cli sch erc` — 실사용 형태.
     (블록 단독 ERC는 '부모 없는 계층 라벨' 오류가 나므로 판정 불가 —
      2026-08-04 첫 실행에서 확인. 하네스가 §21-D 데모 패턴 그대로다.)
     오류 0 필수. 경고는 알려진 무해 항목만 허용:
       lib_symbol_issues / footprint_link_issues  (헤드리스에 라이브러리 표 없음)
       isolated_pin_label                          (인터페이스 노출 네트의 본질)
  C. `kicad-cli sch export svg` 렌더 산출 (눈검증용 preview.svg)

실행: python generators/check_block.py [blocks/<분류>/<id> ...]  (없으면 전체)
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
KICAD_CLI = os.environ.get(
    "KICAD_CLI", r"D:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
ALLOWED_WARN = {"lib_symbol_issues", "footprint_link_issues", "isolated_pin_label"}

errs = []


def fail(m):
    errs.append(m)
    print("FAIL", m)


def uid(*keys):
    return str(uuid.uuid5(NS, "partreel-block-harness:" + ":".join(keys)))


def harness_root(b, sheet_file):
    """블록을 시트로 인스턴스한 임시 루트 (문법: cm5_minima 데모에서 추출)."""
    bid = b["id"]
    root_uuid = uid(bid, "harness-root")
    pins = []
    labels = []
    x, y0 = 50.8, 50.8
    for i, (net, direction) in enumerate(sorted(b.get("interface", {}).items())):
        py = y0 + 5.08 + i * 2.54
        shape = {"input": "input", "output": "output",
                 "bidirectional": "bidirectional", "passive": "passive"} \
            .get(direction, "bidirectional")
        pins.append(f'''\t\t(pin "{net}" {shape}
\t\t\t(at {x:g} {py:g} 180)
\t\t\t(uuid "{uid(bid, net, "sheetpin")}")
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify right)
\t\t\t)
\t\t)''')
        # 루트는 **전역 라벨** — 로컬 라벨을 시트 핀에 직접 얹으면 하위 네트가
        # 다핀일 때 커널 ERC가 label_dangling 오탐을 낸다 (2026-08-04 확정:
        # 넷리스트는 정상 병합을 증명하는데 ERC만 죽음. 전역 라벨이면 오류 0).
        labels.append(f'''\t(global_label "{net}"
\t\t(at {x:g} {py:g} 180)
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.27 1.27)
\t\t\t)
\t\t\t(justify right bottom)
\t\t)
\t\t(uuid "{uid(bid, net, "rootlabel")}")
\t)''')
    h = len(b.get("interface", {})) * 2.54 + 12.7
    return f'''(kicad_sch
\t(version 20250114)
\t(generator "partreel-block-harness")
\t(generator_version "1.0")
\t(uuid "{root_uuid}")
\t(paper "A4")
{chr(10).join(labels)}
\t(sheet
\t\t(at {x:g} {y0:g})
\t\t(size 25.4 {h:g})
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(stroke
\t\t\t(width 0)
\t\t\t(type solid)
\t\t)
\t\t(fill
\t\t\t(color 0 0 0 0.0000)
\t\t)
\t\t(uuid "{uid(bid, "sheet")}")
\t\t(property "Sheetname" "{bid}"
\t\t\t(at {x:g} {y0 - 0.8:g} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left bottom)
\t\t\t)
\t\t)
\t\t(property "Sheetfile" "{sheet_file}"
\t\t\t(at {x:g} {y0 + h + 0.8:g} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left top)
\t\t\t)
\t\t)
{chr(10).join(pins)}
\t\t(instances
\t\t\t(project "harness"
\t\t\t\t(path "/{root_uuid}"
\t\t\t\t\t(page "2")
\t\t\t\t)
\t\t\t)
\t\t)
\t)
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
'''


def check(block_dir):
    bid = os.path.basename(block_dir)
    b = json.load(open(os.path.join(block_dir, "block.json"), encoding="utf-8"))
    sch = os.path.join(block_dir, f"{bid}.kicad_sch")

    # A. 재생성 일치
    r = subprocess.run([sys.executable, os.path.join(ROOT, "generators", "build_block.py"),
                        block_dir], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        fail(f"{bid}: 재생성 실패 — {(r.stdout + r.stderr)[-200:]}")
        return
    text = open(sch, encoding="utf-8").read()
    n_inst = len(re.findall(r'[(]lib_id "PartReel:', text))
    if n_inst != len(b["parts"]):
        fail(f"{bid}: 부품 수 불일치 (선언 {len(b['parts'])} vs 생성 {n_inst})")
    for net in b.get("interface", {}):
        if f'(hierarchical_label "{net}"' not in text:
            fail(f"{bid}: 인터페이스 '{net}'의 계층 라벨 없음")

    # B. 부모 하네스 ERC (실사용 형태)
    tmp = tempfile.mkdtemp(prefix="blk_")
    try:
        shutil.copy(sch, os.path.join(tmp, f"{bid}.kicad_sch"))
        root = os.path.join(tmp, "harness.kicad_sch")
        with open(root, "w", encoding="utf-8", newline="\n") as f:
            f.write(harness_root(b, f"{bid}.kicad_sch"))
        rpt = os.path.join(tmp, "erc.json")
        r = subprocess.run([KICAD_CLI, "sch", "erc", "--severity-all",
                            "--format", "json", "--output", rpt, root],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if not os.path.exists(rpt):
            fail(f"{bid}: ERC 실행 실패 — {(r.stdout + r.stderr)[-200:]}")
            return
        rep = json.load(open(rpt, encoding="utf-8"))
        n_err = n_warn = 0
        for sheet in rep.get("sheets", []):
            for v in sheet.get("violations", []):
                sev, typ = v.get("severity"), v.get("type")
                desc = v.get("description", "")[:90]
                if sev == "error":
                    n_err += 1
                    fail(f"{bid}: ERC 오류 [{typ}] {desc}")
                elif sev == "warning" and typ not in ALLOWED_WARN:
                    n_warn += 1
                    fail(f"{bid}: ERC 경고(비허용) [{typ}] {desc}")
        print(f"  {bid}: 하네스 ERC 오류 {n_err} / 비허용 경고 {n_warn}")

        # C. 렌더 (눈검증 산출) — 블록 파일 자체를 내보낸다.
        # 하네스를 --pages 2로 내보내면 루트 페이지가 나온다 (2026-08-04 확인)
        outdir = os.path.join(tmp, "svg")
        r = subprocess.run([KICAD_CLI, "sch", "export", "svg",
                            "--exclude-drawing-sheet", "--no-background-color",
                            "--output", outdir, os.path.join(tmp, f"{bid}.kicad_sch")],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        svgs = glob.glob(os.path.join(outdir, "*.svg"))
        if not svgs:
            fail(f"{bid}: SVG 렌더 실패 — {(r.stdout + r.stderr)[-200:]}")
        else:
            shutil.copy(svgs[-1], os.path.join(block_dir, "preview.svg"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    targets = sys.argv[1:] or [os.path.dirname(p) for p in
                               glob.glob(os.path.join(ROOT, "blocks", "*", "*", "block.json"))]
    for t in targets:
        check(os.path.join(ROOT, t) if not os.path.isabs(t) else t)
    if errs:
        print(f"FAIL: 블록 게이트 {len(errs)}건")
        return 1
    print(f"PASS: 블록 {len(targets)}개 — 하네스 ERC/렌더/일치 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
