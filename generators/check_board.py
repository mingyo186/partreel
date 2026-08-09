"""
보드 게이트 (REQUIREMENTS §25 1단계) — check_block과 같은 3중 판정.

  A. board.json 재생성 → 산출물 일치 (시트/전역 라벨 수)
  B. `kicad-cli sch erc` 오류 0 (허용 경고: check_block과 동일 집합)
  C. 커널 넷리스트(kicadxml)로 nets 선언 전수 대조 — 보드 네트는 양끝
     블록의 내부 부품 핀(ref.pin)으로 전개해 커널 네트 구성원과 비교.
     (블록 간 ref 중복(C1 등)이 이론상 한 네트에 겹칠 수 있으나 신호
     네트에서는 실질 없음 — 부분집합 판정으로 완화)
  D. SVG 렌더 산출 (preview.svg)

실행: python generators/check_board.py [boards/<id> ...]  (없으면 전체)
"""

import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
KICAD_CLI = os.environ.get(
    "KICAD_CLI", r"D:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
ALLOWED_WARN = {"lib_symbol_issues", "footprint_link_issues", "isolated_pin_label"}

errs = []


def fail(m):
    errs.append(m)
    print("FAIL", m)


def block_nets(block_id):
    hits = glob.glob(os.path.join(ROOT, "blocks", "*", block_id, "block.json"))
    b = json.load(open(hits[0], encoding="utf-8"))
    return b["nets"]


def check(board_dir):
    bid = os.path.basename(board_dir)
    bd = json.load(open(os.path.join(board_dir, "board.json"), encoding="utf-8"))
    sch = os.path.join(board_dir, f"{bid}.kicad_sch")

    # A. 재생성 일치
    r = subprocess.run([sys.executable, os.path.join(ROOT, "generators", "build_board.py"),
                        board_dir], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        fail(f"{bid}: 재생성 실패 — {(r.stdout + r.stderr)[-200:]}")
        return
    text = open(sch, encoding="utf-8").read()
    n_sheet = len(re.findall(r"\(sheet\n", text))
    if n_sheet != len(bd["blocks"]):
        fail(f"{bid}: 시트 수 불일치 (선언 {len(bd['blocks'])} vs {n_sheet})")
    n_glabel = len(re.findall(r"\(global_label ", text))
    want_glabel = sum(len(v) for v in bd["nets"].values())
    if n_glabel != want_glabel:
        fail(f"{bid}: 전역 라벨 수 불일치 (기대 {want_glabel} vs {n_glabel})")

    # B. ERC
    tmp = tempfile.mkdtemp(prefix="brd_")
    rpt = os.path.join(tmp, "erc.json")
    r = subprocess.run([KICAD_CLI, "sch", "erc", "--severity-all",
                        "--format", "json", "--output", rpt, sch],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if not os.path.exists(rpt):
        fail(f"{bid}: ERC 실행 실패 — {(r.stdout + r.stderr)[-200:]}")
        return
    rep = json.load(open(rpt, encoding="utf-8"))
    n_err = n_warn = 0
    for sheet in rep.get("sheets", []):
        for v in sheet.get("violations", []):
            sev, typ = v.get("severity"), v.get("type")
            if sev == "error":
                n_err += 1
                fail(f"{bid}: ERC 오류 [{typ}] {v.get('description', '')[:90]}")
            elif sev == "warning" and typ not in ALLOWED_WARN:
                n_warn += 1
                fail(f"{bid}: ERC 경고(비허용) [{typ}] {v.get('description', '')[:90]}")
    print(f"  {bid}: ERC 오류 {n_err} / 비허용 경고 {n_warn}")

    # C. 커널 넷리스트 대조
    nx = os.path.join(tmp, "net.xml")
    subprocess.run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadxml",
                    "--output", nx, sch], capture_output=True)
    if not os.path.exists(nx):
        fail(f"{bid}: 넷리스트 실행 실패")
        return
    kn = {}
    for net in ET.parse(nx).getroot().iter("net"):
        mem = {f"{n.get('ref')}.{n.get('pin')}" for n in net.findall("node")
               if not n.get("ref", "").startswith("#")}
        if mem:
            kn[net.get("name").lstrip("/")] = mem
    blk_of = {inst["ref"]: inst["block"] for inst in bd["blocks"]}
    # 재부여 지도: 블록로컬 참조(U1) -> 보드전역(U2) — build_board 산출물
    ref_map = {}
    rm_path = os.path.join(board_dir, "ref_map.json")
    if os.path.exists(rm_path):
        ref_map = json.load(open(rm_path, encoding="utf-8"))
    for net, ends in bd["nets"].items():
        expected = set()
        for e in ends:
            bref, pin_name = e.split(".", 1)
            for m in block_nets(blk_of[bref]).get(pin_name, []):
                lref, pin = m.split(".", 1)
                expected.add(f"{ref_map.get(f'{bref}.{lref}', lref)}.{pin}")
        got = kn.get(net)
        if got is None:
            fail(f"{bid}: 커널에 네트 '{net}' 없음")
        elif not expected <= got:
            fail(f"{bid}: 네트 '{net}' 구성원 누락 — 기대 {sorted(expected)} "
                 f"vs 커널 {sorted(got)}")
    print(f"  {bid}: 넷 대조 {len(bd['nets'])}개")

    # E. PCB 초기화 판정 (있을 때만): kicad-cli pcb drc — 미배선(unconnected_
    # items)은 초기화 단계의 정의상 상태라 허용, 그 외 오류/경고는 실패
    # (배치 겹침·외곽 문제를 여기서 잡는다). §25 2단계.
    pcb = os.path.join(board_dir, f"{bid}.kicad_pcb")
    if os.path.exists(pcb):
        drc = os.path.join(tmp, "drc.json")
        r = subprocess.run([KICAD_CLI, "pcb", "drc", "--severity-all",
                            "--format", "json", "--output", drc, pcb],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if not os.path.exists(drc):
            fail(f"{bid}: PCB DRC 실행 실패 — {(r.stdout + r.stderr)[-200:]}")
        else:
            rep = json.load(open(drc, encoding="utf-8"))
            n_unrouted = len(rep.get("unconnected_items", []))
            # text_height: 안트미크로 수입 풋프린트의 참조 글자 0.7mm(<0.8
            # 기본 최소) — 수입품 고유 스타일의 경고급 지적이라 허용
            allowed_drc = {"text_height"}
            bad = 0
            for v in rep.get("violations", []):
                if v.get("severity") in ("error", "warning") and \
                        v.get("type") not in allowed_drc:
                    bad += 1
                    fail(f"{bid}: DRC [{v.get('type')}] "
                         f"{v.get('description', '')[:90]}")
            print(f"  {bid}: PCB DRC 위반 {bad} / 미배선(허용) {n_unrouted}")

    # D. 렌더 (루트 페이지)
    outdir = os.path.join(tmp, "svg")
    subprocess.run([KICAD_CLI, "sch", "export", "svg", "--exclude-drawing-sheet",
                    "--no-background-color", "--pages", "1",
                    "--output", outdir, sch], capture_output=True)
    svgs = glob.glob(os.path.join(outdir, "*.svg"))
    if not svgs:
        fail(f"{bid}: SVG 렌더 실패")
    else:
        import shutil
        shutil.copy(svgs[0], os.path.join(board_dir, "preview.svg"))


def main():
    targets = sys.argv[1:] or [os.path.dirname(p) for p in
                               glob.glob(os.path.join(ROOT, "boards", "*", "board.json"))]
    for t in targets:
        check(os.path.join(ROOT, t) if not os.path.isabs(t) else t)
    if errs:
        print(f"FAIL: 보드 게이트 {len(errs)}건")
        return 1
    print(f"PASS: 보드 {len(targets)}개 — ERC/넷 대조/렌더 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
