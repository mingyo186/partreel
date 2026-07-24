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


def upload_part_assets(fid):
    """이 부품의 step/glb만 R2에 업로드 (오브젝트 키 = 레포 경로, §22).
    로컬=wrangler OAuth(mcp/), CI=env CLOUDFLARE_API_TOKEN."""
    import json
    root = os.path.normpath(os.path.join(HERE, ".."))
    idx = json.load(open(os.path.join(root, "index.json"), encoding="utf-8"))
    path = next(p["path"] for p in idx["parts"] if p["id"] == fid)
    npx = "npx.cmd" if sys.platform == "win32" else "npx"
    for ext in (".step", ".glb"):
        fpath = os.path.join(root, path, fid + ext)
        if not os.path.exists(fpath):
            continue
        key = f"{path}/{fid}{ext}".replace("\\", "/")
        run([npx, "--yes", "wrangler", "r2", "object", "put",
             f"partreel-assets/{key}", "--file", fpath, "--remote"],
            cwd=os.path.join(root, "mcp"))


def run(cmd, **kw):
    print("+", " ".join(cmd))
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        print(f"FAILED ({r.returncode}):", " ".join(cmd))
        sys.exit(r.returncode)


def main():
    family = os.environ.get("FAMILY", "").strip()
    pins_s = os.environ.get("PINS", "").strip()
    variant = os.environ.get("VARIANT", "").strip().lower()
    py = sys.executable
    freecadcmd = os.environ.get("FREECADCMD", "freecadcmd")

    from gen_ics import VARIANT_FAMILIES, build_variant  # noqa: E402
    if family in VARIANT_FAMILIES:
        # IC 변형 패밀리 (§21-6ⓐ): env VARIANT=코드 (예: FAMILY=ht73xx VARIANT=7350)
        if variant not in VARIANT_FAMILIES[family]["codes"]:
            print(f"unknown variant '{variant}' for {family}: "
                  f"{VARIANT_FAMILIES[family]['codes']}")
            sys.exit(2)
        fid = build_variant(family, variant)
        print(f"Generating on-demand variant: {fid}")
        run([py, os.path.join(HERE, "build_index.py")])
        env = dict(os.environ, IC_VARIANT=f"{family}:{variant}")
        run([freecadcmd, os.path.join(HERE, "gen_ics_3d.py")], env=env)
    else:
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
            print(f"pins {pins} out of allowed range for {family}: "
                  f"{cfg['pins'][0]}..{cfg['pins'][-1]}")
            sys.exit(2)

        fid = f"{family}_{pins}pin"
        print(f"Generating on-demand part: {fid}")
        # 1) 텍스트 (풋프린트/심볼/meta)
        generate(cfg, pins, fid)
        # 2) 인덱스 (이후 단계들이 index 순회)
        run([py, os.path.join(HERE, "build_index.py")])
        # 3) 3D
        env = dict(os.environ, PART_FILTER=f"{family}:{pins}")
        run([freecadcmd, os.path.join(HERE, "gen_connectors_3d.py")], env=env)
    # 4) GLB (STL 있는 부품만 변환하므로 안전)
    run([py, os.path.join(HERE, "stl_to_glb.py")])
    # 4.5) 새 step/glb 해시 기록 + R2 업로드 (§22). 업로드가 qa(check_r2)보다 먼저여야 함
    #      — 게이트가 R2 404를 보면 실패하는 닭-달걀 (§19 사건 2026-07-24).
    run([py, os.path.join(HERE, "sync_r2.py"), "--hash"])
    upload_part_assets(fid)
    # 5) SVG / 6) 사이트 / 7) API
    run([py, os.path.join(HERE, "render_svg.py")])
    run([py, os.path.join(HERE, "build_site.py")])
    run([py, os.path.join(HERE, "build_api.py")])
    # 8) 품질 게이트
    run([py, os.path.join(HERE, "qa.py")])
    print(f"OK: {fid} generated and gated")


if __name__ == "__main__":
    main()
