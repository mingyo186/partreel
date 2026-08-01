"""
PartReel Fetch — **단독 실행** 진입점 (PCB 편집기 없이 사용).

계기(2026-08-01 사용자 지적): "회로도 그리고 PCB 그리지, PCB 그리고 회로 그리냐."
맞는 지적이다. KiCad는 회로도 편집기용 플러그인 API가 아직 없어서(11 이후 예정)
액션 플러그인 버튼은 PCB 편집기에만 달 수 있다. 그건 우리 사정이지 사용자
사정이 아니므로, 같은 도구를 PCB 편집기 없이 바로 띄울 수 있게 한다.

사용:
    python -m partreel_fetch              # 최근 KiCad 프로젝트 자동 감지
    python -m partreel_fetch <프로젝트폴더>

프로젝트를 못 찾으면 폴더 선택창을 띄운다.
"""

import glob
import json
import os
import sys


def recent_project_dir():
    """KiCad 설정의 최근 파일 목록에서 프로젝트 폴더 추정."""
    roots = []
    appdata = os.environ.get("APPDATA") or ""
    if appdata:
        roots += glob.glob(os.path.join(appdata, "kicad", "*", "kicad.json"))
    home = os.path.expanduser("~")
    roots += glob.glob(os.path.join(home, ".config", "kicad", "*", "kicad.json"))
    roots += glob.glob(os.path.join(home, "Library", "Preferences", "kicad",
                                    "*", "kicad.json"))
    for cfg in sorted(roots, reverse=True):  # 최신 버전 폴더 우선
        try:
            hist = json.load(open(cfg, encoding="utf-8")).get("system", {}) \
                       .get("file_history", [])
        except (OSError, ValueError):
            continue
        for path in hist:
            d = os.path.dirname(path)
            if os.path.isdir(d) and os.access(d, os.W_OK):
                return d
    return None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    import wx  # KiCad 동봉 파이썬에만 있음 — 함수 안에서 임포트

    from . import dialog

    app = wx.App(False)
    proj = argv[0] if argv else recent_project_dir()
    if not proj or not os.path.isdir(proj):
        dlg = wx.DirDialog(None, "부품을 추가할 KiCad 프로젝트 폴더를 고르세요",
                           style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() != wx.ID_OK:
            return 1
        proj = dlg.GetPath()
        dlg.Destroy()
    dialog.show(proj)
    return 0


if __name__ == "__main__":
    sys.exit(main())
