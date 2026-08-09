"""
로컬 부품 -> 스테이징 병행 제출 (§23, 2026-08-10 배치 배포 결정의 짝).

배치 배포 운영에서 커밋~배포 사이 공백을 메운다: 게이트 통과한 부품을
워커 submit_part로 던지면 그 즉시 MCP 검색·다운로드에 노출된다.
R2에 직접 쓰지 않는 이유: 스테이징 index.json을 워커가 관리하므로
워커 경로를 타야 인덱스가 어긋나지 않는다.

배포 후에는 승격 봇이 자동 정리하고, 배포 전에는 '보류'로 남아
스테이징이 계속 서빙한다 (staging-promote.yml 2단계 분류).

실행: python generators/submit_staging.py library/<분류>/<벤더>/<부품id> [...]
"""

import json
import os
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
MCP = "https://mcp.partreel.com/mcp"
# 운영자 토큰 (§23-B): 있으면 verified로 스테이징. 레포 밖 로컬 파일/환경변수
# 에만 존재 — 절대 커밋하지 않는다. Cloudflare 시크릿(SUBMIT_TOKEN)과 쌍.
TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".partreel", "submit_token")


def operator_token():
    t = os.environ.get("PARTREEL_SUBMIT_TOKEN", "").strip()
    if t:
        return t
    try:
        return open(TOKEN_FILE, encoding="utf-8").read().strip()
    except OSError:
        return ""


def submit(part_dir):
    part_dir = os.path.join(ROOT, part_dir) if not os.path.isabs(part_dir) else part_dir
    pid = os.path.basename(part_dir.rstrip("/\\"))
    meta = json.load(open(os.path.join(part_dir, "meta.json"), encoding="utf-8"))
    args = {
        "id": pid,
        "name": meta["name"],
        "description": meta["description"],
        "category": meta["category"],
        "license": meta.get("license", "CC-BY-4.0"),
        "dimensions_source": meta.get("dimensions_source", ""),
        "datasheet": meta.get("datasheet", ""),
        "symbol": open(os.path.join(part_dir, f"{pid}.kicad_sym"), encoding="utf-8").read(),
        "footprint": open(os.path.join(part_dir, f"{pid}.kicad_mod"), encoding="utf-8").read(),
    }
    tok = operator_token()
    if tok:
        args["operator_token"] = tok
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": "submit_part", "arguments": args}}
    req = urllib.request.Request(
        MCP, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "User-Agent": "partreel-submit-staging"})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = json.loads(r.read().decode("utf-8"))
    content = (body.get("result") or {}).get("content") or []
    text = "".join(c.get("text", "") for c in content if c.get("type") == "text")
    try:
        res = json.loads(text)
    except ValueError:
        res = {"raw": text or body}
    if res.get("shared"):
        print(f"OK   {pid}: 스테이징 공유됨 — {res['downloads']['symbol']}")
        return True
    print(f"FAIL {pid}: {res.get('error') or res}")
    return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    ok = all([submit(d) for d in sys.argv[1:]])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
