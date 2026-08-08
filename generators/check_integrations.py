"""
유통망 연동 계약 검사 (순찰용) — 우리가 API를 바꾸면 하류 연동 전부가
한꺼번에 깨진다 (2026-08-07 사용자 지적: "업데이트가 있었는데 거기서
문제가 생길 수도 있잖아").

두 방향을 본다:
  A. **우리 쪽 계약**: 하류 3곳(mixelpixx / eda-agent / Seeed)이 실제로
     의존하는 엔드포인트·필드가 라이브에서 그대로인지.
       - /api/v1/parts.json          : parts[] + id/name
       - /api/v1/parts/<id>.json     : files.symbol/footprint 절대 URL (https)
       - mcp.partreel.com /mcp       : tools/list에 search_parts/get_part
       - mcp.partreel.com /search?q= : parts[] + id
  B. **상류 변경 감지**: 그쪽 저장소의 연동 파일 SHA가 바뀌면 알림
     (바뀜 = 우리 연동을 손댔다는 뜻 — 깨졌는지 확인 필요).
     상태 파일: docs/integration-watch.json

실행: python generators/check_integrations.py   (비0 종료 = 계약 위반)
"""

import json
import os
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
STATE = os.path.join(ROOT, "docs", "integration-watch.json")
UA = {"User-Agent": "partreel-integration-check"}

UPSTREAM = {
    "mixelpixx/KiCAD-MCP-Server": ["src/tools/parts-registry.ts"],
    "salitronic/eda-agent": ["src/eda_agent/libimport/providers/partreel.py"],
    "Seeed-Studio/kicad-mcp-server": ["src/kicad_mcp_server/utils/parts_registry.py",
                                      "src/kicad_mcp_server/tools/parts_registry.py"],
}

errs = []


def fail(m):
    errs.append(m)
    print("FAIL", m)


def get(url, data=None):
    req = urllib.request.Request(url, data=data, headers={
        **UA, **({"Content-Type": "application/json"} if data else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def check_contract():
    # parts.json
    idx = get("https://partreel.com/api/v1/parts.json")
    parts = idx if isinstance(idx, list) else idx.get("parts")
    if not parts or "id" not in parts[0] or "name" not in parts[0]:
        fail("parts.json: parts[]/id/name 계약 위반")
        return
    pid = parts[0]["id"]
    # 상세
    d = get(f"https://partreel.com/api/v1/parts/{pid}.json")
    files = d.get("files") or {}
    for k in ("symbol", "footprint"):
        if not str(files.get(k, "")).startswith("https://"):
            fail(f"parts/{pid}.json: files.{k} 절대 https URL 아님 — eda-agent fetch가 깨짐")
    # MCP tools
    t = get("https://mcp.partreel.com/mcp",
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode())
    names = {x["name"] for x in t["result"]["tools"]}
    for need in ("search_parts", "get_part"):
        if need not in names:
            fail(f"MCP tools/list에 {need} 없음 — mixelpixx/Seeed 도구가 깨짐")
    # search API (fetch 플러그인 + 하류 검색)
    s = get("https://mcp.partreel.com/search?q=usb")
    if "parts" not in s:
        fail("/search 응답에 parts 없음")
    print(f"계약 OK: parts.json({len(parts)}) / 상세 files URL / MCP 도구 / search")


def check_upstream():
    try:
        state = json.load(open(STATE, encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    changed = []
    for repo, paths in UPSTREAM.items():
        for path in paths:
            r = subprocess.run(["gh", "api", f"repos/{repo}/contents/{path}",
                                "--jq", ".sha"], capture_output=True, text=True)
            sha = r.stdout.strip()
            if not sha:
                continue  # 조회 실패는 경보 아님 (다음 순찰에 재시도)
            key = f"{repo}:{path}"
            if state.get(key) and state[key] != sha:
                changed.append(key)
            state[key] = sha
    json.dump(state, open(STATE, "w", encoding="utf-8"), indent=1)
    if changed:
        print("상류 연동 파일 변경 감지 (우리 연동을 손댐 — 확인 필요):")
        for c in changed:
            print("  -", c)
    else:
        print(f"상류 변경 없음 ({sum(len(v) for v in UPSTREAM.values())}개 파일 감시)")
    return changed


def main():
    check_contract()
    changed = check_upstream()
    if errs:
        print(f"FAIL: 계약 위반 {len(errs)}건")
        return 1
    print("PASS: 연동 계약 정상" + (" (상류 변경 있음 — 위 목록 확인)" if changed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
