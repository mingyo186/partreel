"""
파트릴 성장 지표 리포트 (순찰용) — 로컬 wrangler OAuth 토큰으로 조회.

지표 (판단 기준: 4~6주 관찰, REQUIREMENTS 참조):
  1. 사이트 방문/페이지뷰 (Cloudflare Web Analytics RUM)
  2. MCP 워커 요청량 (우리 테스트 포함 총량 — 해석 주의)
  3. 에셋 다운로드 상위 경로 (assets.partreel.com — 3D + 스테이징)
     * 한계: partreel.com 직접 다운로드(심볼/풋프린트)는 DNS가 GitHub Pages
       직결이라 집계 밖 (2026-08-02 확인)
  4. 스테이징 제출 수 / 승격 PR 수 (§23 생성 루프의 핵심 신호)

실행: python generators/metrics_report.py [일수=7]
토큰: %APPDATA%/xdg.config/.wrangler/config/default.toml (레포에 없음)
"""

import datetime
import json
import os
import re
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
ACCT = "59c582799b858f66a23af4561c26c696"
ZONE = "2b1f5e317f276eb936c0382f9c691c26"  # partreel.com


def token():
    p = os.path.join(os.environ.get("APPDATA", ""), "xdg.config", ".wrangler",
                     "config", "default.toml")
    m = re.search(r'oauth_token\s*=\s*"([^"]+)"', open(p, encoding="utf-8").read())
    return m.group(1)


def gql(query, variables, tok):
    req = urllib.request.Request(
        "https://api.cloudflare.com/client/v4/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
    if d.get("errors"):
        raise RuntimeError(json.dumps(d["errors"])[:200])
    return d["data"]["viewer"]


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    tok = token()
    today = datetime.datetime.now(datetime.UTC)
    start_date = (today - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    start_time = (today - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. 방문
    v = gql("""query($a: String!, $s: Date!) { accounts(filter:{accountTag:$a}) {
        rumPageloadEventsAdaptiveGroups(limit: 40, filter:{date_geq:$s}, orderBy:[date_ASC])
        { count sum { visits } dimensions { date } } } }""",
            {"a": ACCT, "s": start_date}, tok)["accounts"][0]["rumPageloadEventsAdaptiveGroups"]
    print(f"== 사이트 방문 (최근 {days}일) ==")
    print(f"  합계: 방문 {sum(r['sum']['visits'] for r in v)} / 뷰 {sum(r['count'] for r in v)}")
    for r in v[-7:]:
        print(f"  {r['dimensions']['date']}: 방문 {r['sum']['visits']:>4} / 뷰 {r['count']:>4}")

    # 2. MCP 워커
    w = gql("""query($a: String!, $s: Time!) { accounts(filter:{accountTag:$a}) {
        workersInvocationsAdaptive(limit: 5000, filter:{datetime_geq:$s})
        { sum { requests } dimensions { datetimeHour } } } }""",
            {"a": ACCT, "s": start_time}, tok)["accounts"][0]["workersInvocationsAdaptive"]
    daily = {}
    for r in w:
        d = r["dimensions"]["datetimeHour"][:10]
        daily[d] = daily.get(d, 0) + r["sum"]["requests"]
    print(f"== MCP 워커 요청 (총량 — 우리 테스트/게이트 포함) ==")
    print(f"  합계 {sum(daily.values())} / 일평균 {sum(daily.values()) // max(1, len(daily))}")

    # 3. 에셋 다운로드 (존 분석은 24시간 창 제한 — 최근 24h)
    s24 = (today - datetime.timedelta(hours=23)).strftime("%Y-%m-%dT%H:%M:%SZ")
    a = gql("""query($z: String!, $s: Time!) { zones(filter:{zoneTag:$z}) {
        httpRequestsAdaptiveGroups(limit: 15, filter:{datetime_geq:$s,
          clientRequestHTTPHost:"assets.partreel.com"}, orderBy:[count_DESC])
        { count dimensions { clientRequestPath } } } }""",
            {"z": ZONE, "s": s24}, tok)["zones"][0]["httpRequestsAdaptiveGroups"]
    dl = [r for r in a if r["dimensions"]["clientRequestPath"] not in ("/", "/robots.txt")]
    print("== 에셋 다운로드 상위 (최근 24시간, 3D+스테이징) ==")
    for r in dl[:8]:
        print(f"  {r['count']:>5}  {r['dimensions']['clientRequestPath'][:70]}")

    # 4. 생성 루프 신호 (§23)
    try:
        req = urllib.request.Request("https://assets.partreel.com/staging/index.json",
                                     headers={"User-Agent": "partreel-metrics"})
        with urllib.request.urlopen(req, timeout=20) as r:
            staged = len(json.load(r).get("parts", []))
    except Exception:
        staged = 0
    prs = subprocess.run(
        ["gh", "pr", "list", "--repo", "mingyo186/partreel", "--state", "all",
         "--search", "Promote staged", "--json", "number,state,createdAt"],
        capture_output=True, text=True)
    promo = [p for p in (json.loads(prs.stdout or "[]"))
             if p["createdAt"] >= start_time]
    print("== 생성 루프 (§23) ==")
    print(f"  스테이징 현재 {staged}건 / 최근 {days}일 승격 PR {len(promo)}건")


if __name__ == "__main__":
    main()
