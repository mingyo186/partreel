"""
PartReel Fetch — 검색 대화상자 (wxPython; KiCad에 동봉된 것을 사용).

코어(core.py)는 KiCad에 의존하지 않으므로 이 파일만 GUI를 안다.
네트워크·설치는 백그라운드 스레드에서 돌려 KiCad UI가 멈추지 않게 한다
(KiCad가 부품 정보를 순차 선주입해 UI가 멈추던 사건의 교훈 — §18-A).
"""

import threading

import wx

from . import core


class FetchDialog(wx.Dialog):
    def __init__(self, parent, project_dir):
        super().__init__(parent, title="PartReel — 부품 검색/추가",
                         size=wx.Size(760, 520),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.project_dir = project_dir
        self.results = []

        outer = wx.BoxSizer(wx.VERTICAL)
        top = wx.BoxSizer(wx.HORIZONTAL)
        self.query = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.query.SetHint("예: usb c connector / jst ph 4 / rkjxm")
        btn = wx.Button(self, label="검색")
        top.Add(self.query, 1, wx.EXPAND | wx.ALL, 4)
        top.Add(btn, 0, wx.ALL, 4)
        outer.Add(top, 0, wx.EXPAND)

        self.list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        for i, (t, w) in enumerate((("이름", 220), ("ID", 220),
                                    ("분류", 90), ("패밀리", 180))):
            self.list.InsertColumn(i, t, width=w)
        outer.Add(self.list, 1, wx.EXPAND | wx.ALL, 4)

        self.status = wx.StaticText(self, label=f"프로젝트: {project_dir}")
        outer.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        bottom = wx.BoxSizer(wx.HORIZONTAL)
        self.add_btn = wx.Button(self, label="이 프로젝트에 추가")
        self.add_btn.Enable(False)
        close = wx.Button(self, wx.ID_CANCEL, "닫기")
        bottom.AddStretchSpacer()
        bottom.Add(self.add_btn, 0, wx.ALL, 6)
        bottom.Add(close, 0, wx.ALL, 6)
        outer.Add(bottom, 0, wx.EXPAND)
        self.SetSizer(outer)

        btn.Bind(wx.EVT_BUTTON, self.on_search)
        self.query.Bind(wx.EVT_TEXT_ENTER, self.on_search)
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED,
                       lambda e: self.add_btn.Enable(True))
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_add)
        self.add_btn.Bind(wx.EVT_BUTTON, self.on_add)

    # --- 백그라운드 실행 헬퍼 (UI 스레드 차단 금지)
    def _run_bg(self, work, done):
        def runner():
            try:
                res = work()
                wx.CallAfter(done, res, None)
            except Exception as exc:  # noqa: BLE001 — 사용자에게 그대로 보고
                wx.CallAfter(done, None, exc)
        threading.Thread(target=runner, daemon=True).start()

    def on_search(self, _evt):
        q = self.query.GetValue().strip()
        if not q:
            return
        self.status.SetLabel("검색 중…")
        self.list.DeleteAllItems()
        self._run_bg(lambda: core.search(q, limit=200), self._search_done)

    def _search_done(self, res, exc):
        if exc:
            self.status.SetLabel(f"검색 실패: {exc}")
            return
        self.results = res
        for p in res:
            i = self.list.InsertItem(self.list.GetItemCount(),
                                     str(p.get("name") or p["id"]))
            self.list.SetItem(i, 1, str(p["id"]))
            self.list.SetItem(i, 2, str(p.get("category") or ""))
            self.list.SetItem(i, 3, str(p.get("family") or ""))
        self.status.SetLabel(f"{len(res)}개 — 부품을 고르고 '이 프로젝트에 추가'")
        self.add_btn.Enable(False)

    def on_add(self, _evt):
        i = self.list.GetFirstSelected()
        if i < 0:
            return
        pid = self.results[i]["id"]
        self.add_btn.Enable(False)
        self.status.SetLabel(f"{pid} 설치 중…")
        self._run_bg(lambda: core.install_part(pid, self.project_dir),
                     self._add_done)

    def _add_done(self, res, exc):
        self.add_btn.Enable(True)
        if exc:
            self.status.SetLabel(f"설치 실패: {exc}")
            return
        self.status.SetLabel(
            f"추가됨: {res['name']} — 회로도의 심볼 선택창에서 "
            f"'PartReel' 라이브러리를 보세요")


def show(project_dir, parent=None):
    dlg = FetchDialog(parent, project_dir)
    dlg.ShowModal()
    dlg.Destroy()
