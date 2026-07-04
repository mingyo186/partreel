"""
온디맨드 단일 부품 생성 오케스트레이터 (REQUIREMENTS §19).
실행: FAMILY=pin_header_254 PINS=7 python generators/generate_one.py
     (freecadcmd 경로가 PATH에 없으면 env FREECADCMD로 지정)

텍스트(풋프린트/심볼/meta) → index → 3D(STEP/STL) → GLB → SVG → site → api → QA.
QA 실패 시 비0 종료(호출측[CI]이 커밋/배포 중단).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gen_connectors import get_family, generate  # noqa: E402


def run(cmd, **kw):
    print("+", " ".join(cmd))
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        print(f"FAILED ({r.returncode}):", " ".join(cmd))
        sys.exit(r.returncode)


def main():
    family = os.environ.get("FAMILY", "").strip()
    pins_s = os.environ.get("PINS", "").strip()
    cfg = get_family(family)
    if cfg is None:
        print(f"unknown family: '{family}'")
        sys.exit(2)
    try:
        pins = int(pins_s)
    except ValueError:
        print(f"invalid PINS: '{pins_s}'")
        sys.exit(2)
    if pins not in cfg["pins"]:
        print(f"pins {pins} out of allowed range for {family}: {cfg['pins'][0]}..{cfg['pins'][-1]}")
        sys.exit(2)

    fid = f"{family}_{pins}pin"
    print(f"Generating on-demand part: {fid}")

    # 1) 텍스트 (풋프린트/심볼/meta)
    generate(cfg, pins, fid)

    py = sys.executable
    # 2) 인덱스 (이후 단계들이 index 순회)
    run([py, os.path.join(HERE, "build_index.py")])
    # 3) 3D
    freecadcmd = os.environ.get("FREECADCMD", "freecadcmd")
    env = dict(os.environ, PART_FILTER=f"{family}:{pins}")
    run([freecadcmd, os.path.join(HERE, "gen_connectors_3d.py")], env=env)
    # 4) GLB (STL 있는 부품만 변환하므로 안전)
    run([py, os.path.join(HERE, "stl_to_glb.py")])
    # 5) SVG / 6) 사이트 / 7) API
    run([py, os.path.join(HERE, "render_svg.py")])
    run([py, os.path.join(HERE, "build_site.py")])
    run([py, os.path.join(HERE, "build_api.py")])
    # 8) 품질 게이트
    run([py, os.path.join(HERE, "qa.py")])
    print(f"OK: {fid} generated and gated")


if __name__ == "__main__":
    main()
