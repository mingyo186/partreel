"""
PartReel Fetch — 코어 (KiCad 비의존 순수 파이썬, 표준 라이브러리만).

역할: 파트릴에서 **고른 부품 하나만** 현재 프로젝트에 설치한다.
  1) 검색 (사이트 정적 API)
  2) 심볼/풋프린트 다운로드
  3) 프로젝트 폴더에 PartReel.kicad_sym / PartReel.pretty 로 병합 설치
  4) 프로젝트 라이브러리 테이블(sym-lib-table / fp-lib-table)에 항목 등록

KiCad 모듈을 임포트하지 않는다 — SWIG 바인딩은 KiCad 11에서 제거되므로
껍데기(action plugin)만 교체하면 되도록 분리해 둔다 (REQUIREMENTS §18-C).
"""

import json
import os
import re
import urllib.parse
import urllib.request

SITE = os.environ.get("PARTREEL_SITE", "https://partreel.com")
UA = "partreel-fetch-plugin"
LIB_NICK = "PartReel"
MAX_BYTES = 20 * 1024 * 1024


class FetchError(Exception):
    pass


def _get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read(MAX_BYTES + 1)
    except Exception as exc:
        raise FetchError(f"네트워크 오류: {exc}") from exc
    if len(data) > MAX_BYTES:
        raise FetchError(f"파일이 너무 큽니다: {url}")
    return data if binary else data.decode("utf-8")


_INDEX_CACHE = None


def load_index(force=False):
    """전체 부품 색인 (id/name/family/category/keywords)."""
    global _INDEX_CACHE
    if _INDEX_CACHE is None or force:
        doc = json.loads(_get(f"{SITE}/api/v1/parts.json"))
        _INDEX_CACHE = doc if isinstance(doc, list) else doc.get("parts", [])
    return _INDEX_CACHE


SEARCH_API = os.environ.get("PARTREEL_SEARCH", "https://mcp.partreel.com/search")


def search(query, limit=50):
    """부품 검색. 서버 검색 API를 먼저 쓰고(응답 수 KB), 실패 시 전체 색인으로
    폴백한다 — 색인은 11MB라 매번 받으면 첫 검색이 느리다(2026-08-01)."""
    q = str(query).strip()
    if not q:
        return []
    try:
        url = f"{SEARCH_API}?q={urllib.parse.quote(q)}"
        return json.loads(_get(url)).get("parts", [])[:limit]
    except Exception:
        pass  # 폴백: 전체 색인 내려받아 로컬 검색
    toks = [t for t in q.lower().split() if t]
    out = []
    for p in load_index():
        hay = " ".join(str(p.get(k, "")) for k in
                       ("id", "name", "family", "category", "manufacturer")).lower()
        hay += " " + " ".join(p.get("keywords") or []).lower()
        if all(t in hay for t in toks):
            out.append(p)
            if len(out) >= limit:
                break
    return out


def part_detail(part_id):
    if not re.fullmatch(r"[a-z0-9_\-]+", part_id or ""):
        raise FetchError(f"잘못된 부품 id: {part_id}")
    return json.loads(_get(f"{SITE}/api/v1/parts/{part_id}.json"))


def _allowed(url):
    """다운로드 허용 호스트: 사이트 도메인과 그 서브도메인(HTTPS)만."""
    u = urllib.parse.urlparse(url)
    root = urllib.parse.urlparse(SITE).hostname or ""
    h = (u.hostname or "").lower()
    return u.scheme == "https" and root and (h == root or h.endswith("." + root))


def _top_symbol_block(text, want):
    """라이브러리 텍스트에서 최상위 (symbol "want" ...) 블록 추출."""
    m = re.search(r'\(symbol\s+"%s"' % re.escape(want), text)
    if not m:
        m = re.search(r'\(symbol\s+"', text)
        if not m:
            return None
    start = m.start()
    depth, i, in_str = 0, start, False
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == '"' and text[i - 1] != "\\":
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    return None


def _symbol_names(lib_text):
    """라이브러리 안 최상위 심볼 이름들 (괄호 깊이 1)."""
    names, depth, in_str, i = [], 0, False, 0
    while i < len(lib_text):
        ch = lib_text[i]
        if in_str:
            if ch == '"' and lib_text[i - 1] != "\\":
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "(":
            m = re.match(r'\(symbol\s+"([^"]+)"', lib_text[i:])
            if m and depth == 1:
                names.append(m.group(1))
            depth += 1
        elif ch == ")":
            depth -= 1
        i += 1
    return names


def set_footprint(blk, value):
    """심볼의 Footprint 속성을 value로 지정 — **없으면 새로 넣는다**.

    우리 생성 심볼 상당수는 Footprint 속성 자체가 없어서, 있을 때만 치환하면
    프로젝트 풋프린트 연결이 비어버린다 (2026-08-01 코어 테스트가 적발).
    """
    v = str(value).replace("\\", "\\\\").replace('"', '\\"')
    if re.search(r'\(property "Footprint"', blk):
        return re.sub(r'(\(property "Footprint" ")[^"]*(")',
                      lambda m: m.group(1) + v + m.group(2), blk, count=1)
    prop = ('\n    (property "Footprint" "%s"\n'
            '      (at 0 0 0)\n      (show_name no)\n'
            '      (do_not_autoplace no)\n      (hide yes)\n'
            '      (effects (font (size 1.27 1.27)))\n    )' % v)
    m = re.search(r'^\s*\(property "Value".*?\)\)\)\s*$', blk, re.M)
    if m:
        return blk[:m.end()] + prop + blk[m.end():]
    head, _, rest = blk.partition("\n")
    return head + prop + "\n" + rest


def install_part(part_id, project_dir, progress=None):
    """부품 하나를 프로젝트에 설치. 설치된 경로/이름을 dict로 반환."""
    def say(msg):
        if progress:
            progress(msg)

    if not os.path.isdir(project_dir):
        raise FetchError(f"프로젝트 폴더가 아닙니다: {project_dir}")

    say(f"{part_id} 정보 조회…")
    detail = part_detail(part_id)
    files = detail.get("files") or {}
    for key in ("symbol", "footprint"):
        if not files.get(key):
            raise FetchError(f"{part_id}에 {key} 파일이 없습니다")
        if not _allowed(files[key]):
            raise FetchError(f"허용되지 않은 다운로드 주소: {files[key]}")

    say("심볼 내려받는 중…")
    sym_text = _get(files["symbol"])
    say("풋프린트 내려받는 중…")
    mod_text = _get(files["footprint"])

    # --- 풋프린트: <project>/PartReel.pretty/<id>.kicad_mod
    pretty = os.path.join(project_dir, f"{LIB_NICK}.pretty")
    os.makedirs(pretty, exist_ok=True)
    with open(os.path.join(pretty, f"{part_id}.kicad_mod"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(mod_text)

    # --- 심볼: <project>/PartReel.kicad_sym 에 병합 (이미 있으면 교체)
    blk = _top_symbol_block(sym_text, part_id)
    if not blk:
        raise FetchError(f"{part_id} 심볼 블록을 찾지 못했습니다")
    blk = set_footprint(blk, f"{LIB_NICK}:{part_id}")
    # 데이터시트가 소스 파일을 가리키면 부품 페이지로 (코드 파일이 열리는
    # 것은 사용자에게 "안 열림"과 같다 — 2026-08-02 제보)
    if re.search(r'\(property "Datasheet" "https?://(?:github|gitlab)\.com/'
                 r'[^"]*\.(?:kicad_mod|kicad_sym|pretty)[^"]*"', blk):
        blk = re.sub(r'(\(property "Datasheet" ")[^"]*(")',
                     lambda m: m.group(1) + f"{SITE}/p/{part_id}/" + m.group(2),
                     blk, count=1)
    sym_lib = os.path.join(project_dir, f"{LIB_NICK}.kicad_sym")
    if os.path.exists(sym_lib):
        cur = open(sym_lib, encoding="utf-8").read()
        if part_id in _symbol_names(cur):
            old = _top_symbol_block(cur, part_id)
            cur = cur.replace(old, blk)
        else:
            cur = cur.rstrip()
            assert cur.endswith(")")
            cur = cur[:-1].rstrip() + "\n  " + blk.replace("\n", "\n  ") + "\n)\n"
    else:
        cur = ('(kicad_symbol_lib (version 20231120) (generator "partreel-fetch")\n'
               "  " + blk.replace("\n", "\n  ") + "\n)\n")
    with open(sym_lib, "w", encoding="utf-8", newline="\n") as f:
        f.write(cur)

    # --- 프로젝트 라이브러리 테이블 등록
    n_sym = register_table(os.path.join(project_dir, "sym-lib-table"),
                           "sym_lib_table", f"${{KIPRJMOD}}/{LIB_NICK}.kicad_sym")
    n_fp = register_table(os.path.join(project_dir, "fp-lib-table"),
                          "fp_lib_table", f"${{KIPRJMOD}}/{LIB_NICK}.pretty")
    say("완료")
    return {
        "id": part_id,
        "name": detail.get("name") or part_id,
        "symbol_lib": sym_lib,
        "footprint_lib": pretty,
        "registered_symbol_table": n_sym,
        "registered_footprint_table": n_fp,
        "datasheet": detail.get("datasheet") or "",
        "page": detail.get("page") or f"{SITE}/p/{part_id}/",
    }


def register_table(path, root, uri):
    """프로젝트 라이브러리 테이블에 PartReel 항목 추가 (있으면 그대로 둠)."""
    entry = (f'  (lib (name "{LIB_NICK}")(type "KiCad")(uri "{uri}")'
             f'(options "")(descr "PartReel parts fetched into this project"))')
    if os.path.exists(path):
        text = open(path, encoding="utf-8").read()
        if f'(name "{LIB_NICK}")' in text.replace(" ", "").replace(
                '(name"', '(name "'):
            return False
        if f'"{LIB_NICK}"' in text:
            return False
        text = text.rstrip()
        if not text.endswith(")"):
            raise FetchError(f"라이브러리 테이블 형식이 이상합니다: {path}")
        text = text[:-1].rstrip() + "\n" + entry + "\n)\n"
    else:
        text = f"({root}\n  (version 7)\n{entry}\n)\n"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return True
