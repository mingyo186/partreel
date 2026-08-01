"""PartReel Fetch 코어 단위 검증 (GUI 없음): 검색 → 설치 → 커널 렌더 → 테이블."""
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"D:\seriouscode\opencad-lib\plugin")
from partreel_fetch import core  # noqa: E402

K = r"D:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
errs = []


def fail(m):
    errs.append(m)
    print("FAIL", m)


# 1) 검색
hits = core.search("rkjxm encoder", limit=5)
print("검색 'rkjxm encoder':", [h["id"] for h in hits])
if not hits:
    fail("검색 결과 없음")

hits2 = core.search("usb c connector", limit=3)
print("검색 'usb c connector':", [h["id"] for h in hits2][:3])

# 2) 임시 프로젝트에 2개 설치 (두 번째는 병합 경로 검증)
proj = tempfile.mkdtemp(prefix="prj_")
targets = ["alps_rkjxm2e13004", "jst_ph_4pin"]
for pid in targets:
    r = core.install_part(pid, proj, progress=lambda m: None)
    print(f"설치 {pid}: 심볼={os.path.basename(r['symbol_lib'])} "
          f"풋프린트={os.path.basename(r['footprint_lib'])} "
          f"표등록(sym/fp)={r['registered_symbol_table']}/{r['registered_footprint_table']}")

# 3) 결과 구조 확인
sym_lib = os.path.join(proj, "PartReel.kicad_sym")
names = core._symbol_names(open(sym_lib, encoding="utf-8").read())
print("라이브러리 내 심볼:", names)
for pid in targets:
    if pid not in names:
        fail(f"{pid} 심볼이 라이브러리에 없음")
    if not os.path.exists(os.path.join(proj, "PartReel.pretty", f"{pid}.kicad_mod")):
        fail(f"{pid} 풋프린트 파일 없음")

# Footprint 속성이 프로젝트 라이브러리를 가리키는지
txt = open(sym_lib, encoding="utf-8").read()
for pid in targets:
    blk = core._top_symbol_block(txt, pid)
    m = re.search(r'\(property "Footprint" "([^"]*)"', blk or "")
    got = m.group(1) if m else "(없음)"
    if got != f"PartReel:{pid}":
        fail(f"{pid} Footprint 속성이 'PartReel:{pid}'가 아님: {got}")

# 4) 테이블 파일 (중복 등록 안 되는지)
for tbl, root in (("sym-lib-table", "sym_lib_table"), ("fp-lib-table", "fp_lib_table")):
    p = os.path.join(proj, tbl)
    if not os.path.exists(p):
        fail(f"{tbl} 없음"); continue
    body = open(p, encoding="utf-8").read()
    n = body.count('(name "PartReel")')
    print(f"{tbl}: PartReel 항목 {n}개")
    if n != 1:
        fail(f"{tbl}에 PartReel 항목이 {n}개 (1이어야 함)")
    if not body.startswith("(" + root):
        fail(f"{tbl} 루트 토큰 이상")

# 5) 진짜 KiCad 커널로 렌더 (설치 결과가 실제로 열리는지)
if os.path.exists(K):
    out = os.path.join(proj, "svg"); os.makedirs(out, exist_ok=True)
    subprocess.run([K, "sym", "export", "svg", sym_lib, "-o", out],
                   capture_output=True, timeout=600)
    n_sym = len(os.listdir(out))
    fout = os.path.join(proj, "fpsvg"); os.makedirs(fout, exist_ok=True)
    subprocess.run([K, "fp", "export", "svg", os.path.join(proj, "PartReel.pretty"),
                    "-o", fout], capture_output=True, timeout=600)
    n_fp = len(os.listdir(fout))
    print(f"커널 렌더: 심볼 SVG {n_sym}, 풋프린트 SVG {n_fp}")
    if n_sym < len(targets):
        fail(f"심볼 렌더 부족: {n_sym} < {len(targets)}")
    if n_fp < len(targets):
        fail(f"풋프린트 렌더 부족: {n_fp} < {len(targets)}")
else:
    print("경고: kicad-cli 없음 — 커널 검증 생략")

# 6) 보안: 외부 호스트 차단
if core._allowed("https://evil.example.com/a.kicad_sym"):
    fail("외부 호스트가 허용됨")
if not core._allowed("https://partreel.com/library/x/a.kicad_sym"):
    fail("정상 호스트가 차단됨")

shutil.rmtree(proj, ignore_errors=True)
print("PASS: Fetch 코어 정상" if not errs else f"FAIL: {len(errs)}건")
sys.exit(1 if errs else 0)
