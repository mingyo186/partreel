"""
README.md 부품 인덱스 자동생성 (§21-5 GitHub 검색성).
마커(<!-- PARTS:BEGIN --> ... <!-- PARTS:END -->) 사이를 index.json 기준으로 재작성.
부품명·MPN이 README에 있어야 GitHub 검색("W25Q64JVSSIQ kicad")이 레포를 찾는다.
실행: python generators/build_readme.py (build_index.py 이후)
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
DOMAIN = "https://partreel.com"
BEGIN, END = "<!-- PARTS:BEGIN -->", "<!-- PARTS:END -->"


def main():
    index = json.load(open(os.path.join(ROOT, "index.json"), encoding="utf-8"))
    rows = {}
    for p in index["parts"]:
        m = json.load(open(os.path.join(ROOT, p["path"], "meta.json"), encoding="utf-8"))
        cat = m.get("category", "etc")
        rows.setdefault(cat, []).append(
            f"| [{m['name']}]({DOMAIN}/p/{m['id']}/) | `{m.get('mpn_pattern', '')}` "
            f"| {m.get('manufacturer', '')} | [{m['id']}](library/{p['path'].split('library/', 1)[-1] if 'library/' in p['path'] else p['path']}) |")
    lines = [f"Currently **{len(index['parts'])} parts**, all machine-verified "
             "(structure, KLC drawing rules, render completeness, 3D coplanar/merged-pin "
             "checks, STEP kernel) with datasheet-cited dimensions.", ""]
    for cat in sorted(rows):
        lines.append(f"### {cat} ({len(rows[cat])})")
        lines.append("")
        lines.append("| Part | MPN | Manufacturer | Files |")
        lines.append("|---|---|---|---|")
        lines += sorted(rows[cat])
        lines.append("")
    block = "\n".join(lines)

    path = os.path.join(ROOT, "README.md")
    text = open(path, encoding="utf-8").read()
    if BEGIN in text and END in text:
        head, rest = text.split(BEGIN, 1)
        _, tail = rest.split(END, 1)
        text = head + BEGIN + "\n" + block + "\n" + END + tail
    else:
        text = text.rstrip() + f"\n\n## Parts index\n\n{BEGIN}\n{block}\n{END}\n"
    open(path, "w", encoding="utf-8").write(text)
    print(f"README parts index: {len(index['parts'])} parts")


if __name__ == "__main__":
    main()
