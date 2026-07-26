"""
게이트 증분 스코프 (REQUIREMENTS §19-A — PR당 전량 검사 금지, CI 병목 방지).
env PART_SCOPE="id1,id2"가 있으면 해당 부품만 검사 대상으로 좁힌다. 없으면 전량.
"""
import os


def scope_ids():
    v = os.environ.get("PART_SCOPE", "").strip()
    return set(x for x in v.split(",") if x) if v else None


def scoped_parts(parts):
    ids = scope_ids()
    if ids is None:
        return parts
    return [p for p in parts if p["id"] in ids]


def path_in_scope(path):
    """library/<...>/<part_id>/<file> 경로가 스코프 안인지 (디렉토리명 기준)."""
    ids = scope_ids()
    if ids is None:
        return True
    return os.path.basename(os.path.dirname(path)) in ids
