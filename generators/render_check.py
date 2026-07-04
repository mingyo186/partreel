"""
3D 형상 시각검수 도구 — GLB를 PNG로 렌더 (§14 F: 새 패밀리/스타일은 눈으로 확인).
실행: python generators/render_check.py <part_id> [출력.png]
예:   python generators/render_check.py screw_terminal_5_08_4pin check.png
"""
import json
import os
import sys

import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
COLORS = ["#e8e8ee", "#d4af37", "#8899aa"]


def main():
    pid = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else f"{pid}_check.png"
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    part = next((p for p in index["parts"] if p["id"] == pid), None)
    if not part:
        print("unknown part id:", pid)
        sys.exit(1)
    glb = os.path.join(ROOT, part["path"], f"{pid}.glb")
    m = trimesh.load(glb)

    fig = plt.figure(figsize=(14, 6))
    for k, (elev, azim, title) in enumerate([(35, -55, "iso"), (80, -90, "top"), (8, -88, "front")]):
        ax = fig.add_subplot(1, 3, k + 1, projection="3d")
        for i, geo in enumerate(m.geometry.values()):
            tris = geo.vertices[geo.faces]
            ax.add_collection3d(Poly3DCollection(
                tris, facecolor=COLORS[i % len(COLORS)], edgecolor="#44444422", linewidths=0.1))
        all_v = np.vstack([g.vertices for g in m.geometry.values()])
        c = all_v.mean(axis=0)
        r = (all_v.max(axis=0) - all_v.min(axis=0)).max() / 2
        ax.set_xlim(c[0] - r, c[0] + r)
        ax.set_ylim(c[1] - r, c[1] + r)
        ax.set_zlim(c[2] - r, c[2] + r)
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        ax.set_title(title, color="#888")
    plt.tight_layout()
    plt.savefig(out, dpi=90, facecolor="#1a1d24")
    print("saved:", out)


if __name__ == "__main__":
    main()
