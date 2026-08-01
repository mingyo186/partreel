"""
PartReel Fetch — KiCad 액션 플러그인 등록부 (PCM 'plugin' 패키지 진입점).

공식 규격(dev-docs.kicad.org/en/addons): 패키지 zip의 `plugins/` 안에
소스를 두고, `__init__.py`가 임포트될 때 ActionPlugin을 register() 한다.

SWIG pcbnew 바인딩은 KiCad 9.0부터 deprecated(11.0 제거 예정)이므로,
실제 로직은 KiCad 비의존 모듈(partreel_fetch/core.py)에 두고 이 파일은
껍데기만 담당한다 — 나중에 IPC API로 갈아끼울 때 이 파일만 바꾸면 된다.
"""

import os

try:
    import pcbnew
except ImportError:  # KiCad 밖(테스트 등)에서 임포트될 때
    pcbnew = None


def _project_dir():
    """현재 보드가 속한 프로젝트 폴더 (없으면 None)."""
    if pcbnew is None:
        return None
    try:
        board = pcbnew.GetBoard()
        path = board.GetFileName() if board else ""
    except Exception:
        path = ""
    return os.path.dirname(path) if path else None


class PartReelFetchPlugin(pcbnew.ActionPlugin if pcbnew else object):
    def defaults(self):
        self.name = "PartReel: 부품 검색/추가"
        self.category = "Libraries"
        self.description = ("Search the PartReel registry and add the selected "
                            "part (symbol + footprint) to this project.")
        self.show_toolbar_button = True
        here = os.path.dirname(os.path.abspath(__file__))
        self.icon_file_name = os.path.join(here, "icon.png")
        self.dark_icon_file_name = self.icon_file_name

    def Run(self):
        import wx

        from .partreel_fetch import dialog

        proj = _project_dir()
        if not proj:
            wx.MessageBox(
                "먼저 프로젝트(보드)를 저장하거나 열어주세요.\n"
                "부품은 그 프로젝트 폴더에 설치됩니다.",
                "PartReel", wx.OK | wx.ICON_INFORMATION)
            return
        dialog.show(proj)


if pcbnew is not None:
    PartReelFetchPlugin().register()
