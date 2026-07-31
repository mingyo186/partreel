"""
Standalone single-part pre-flight check for contributors (zero dependencies).

Runs anywhere Python 3.10+ runs - no registry infrastructure, no index.json,
no network. Checks ONE part directory before you open a PR. Final judgement
is always the PR CI gates; this catches the boring failures early.

Usage:
    python check_part.py <path/to/library/<category>/<vendor>/<part_id>>

Checks:
    A. required files exist: <id>.kicad_mod, <id>.kicad_sym, meta.json
    B. meta.json parses and has the required fields (incl. dimensions_source)
    C. meta.files entries actually exist; formats match files
    D. .kicad_mod / .kicad_sym: balanced s-expressions, correct root token,
       required layers, at least one pad / one pin
    E. if a 3D asset (.step/.glb) is present: meta.asset_sha256 matches it
    F. license sanity: generated parts CC-BY-4.0, imports keep origin license

Exit code 0 = ready for PR (CI still has the final word: KLC drawing rules,
render completeness, text overlap, provenance anti-copy, STEP kernel check).

Tip - prove the files open in real KiCad (needs KiCad 8+ installed):
    kicad-cli fp export svg <id>.kicad_mod -o /tmp/fp_check
    kicad-cli sym export svg <id>.kicad_sym -o /tmp/sym_check
"""

import hashlib
import json
import os
import re
import sys

REQUIRED_META = ("id", "name", "category", "description", "files", "formats",
                 "license", "dimensions_source")


def fail(msgs, msg):
    msgs.append("FAIL " + msg)


def balanced(text):
    depth, in_str, esc = 0, False, False
    for ch in text:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and not in_str


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        print(__doc__)
        return 2
    d = os.path.abspath(sys.argv[1])
    pid = os.path.basename(d)
    msgs = []

    # A. required files
    mod_p = os.path.join(d, f"{pid}.kicad_mod")
    sym_p = os.path.join(d, f"{pid}.kicad_sym")
    meta_p = os.path.join(d, "meta.json")
    for p, what in ((mod_p, "footprint"), (sym_p, "symbol"), (meta_p, "meta.json")):
        if not os.path.exists(p):
            fail(msgs, f"{what} missing: {os.path.basename(p)}")
    if msgs:
        return report(pid, msgs)

    # B. meta fields
    try:
        meta = json.load(open(meta_p, encoding="utf-8"))
    except ValueError as e:
        fail(msgs, f"meta.json is not valid JSON: {e}")
        return report(pid, msgs)
    for k in REQUIRED_META:
        if not meta.get(k):
            fail(msgs, f"meta.{k} missing or empty")
    if meta.get("id") != pid:
        fail(msgs, f"meta.id '{meta.get('id')}' != directory name '{pid}'")
    if meta.get("dimensions_source") and len(str(meta["dimensions_source"])) < 20:
        fail(msgs, "dimensions_source too vague - cite datasheet page/figure "
                   "or standard table")

    # C. files entries exist; formats consistent
    for key, fn in (meta.get("files") or {}).items():
        if not os.path.exists(os.path.join(d, fn)):
            fail(msgs, f"meta.files.{key} points to missing file: {fn}")
    fmts = set(meta.get("formats") or [])
    if "kicad_mod" not in fmts or "kicad_sym" not in fmts:
        fail(msgs, "formats must include kicad_mod and kicad_sym")
    if "step" in fmts and not any(
            str(f).lower().endswith((".step", ".stp"))
            for f in (meta.get("files") or {}).values()):
        fail(msgs, "formats lists step but files has no .step entry")

    # D. kicad file structure
    mod = open(mod_p, encoding="utf-8").read()
    sym = open(sym_p, encoding="utf-8").read()
    if not balanced(mod):
        fail(msgs, "footprint: unbalanced parentheses")
    if not re.match(r"\s*\(footprint\b", mod):
        fail(msgs, "footprint: root token is not (footprint")
    if not re.search(r"\(pad\s", mod):
        fail(msgs, "footprint: no pads")
    for layer in ('"F.Cu"', '"F.SilkS"', '"F.CrtYd"', '"F.Fab"'):
        if layer not in mod:
            fail(msgs, f"footprint: layer {layer} missing")
    if not balanced(sym):
        fail(msgs, "symbol: unbalanced parentheses")
    if not re.match(r"\s*\(kicad_symbol_lib\b", sym):
        fail(msgs, "symbol: root token is not (kicad_symbol_lib")
    if not re.search(r"\(pin\s+\w+\s+\w+\s+\(at", sym):
        fail(msgs, "symbol: no pins")

    # E. 3D asset hash
    hashes = meta.get("asset_sha256") or {}
    for fn in os.listdir(d):
        if fn.lower().endswith((".step", ".stp", ".glb")):
            if fn not in hashes:
                fail(msgs, f"3D asset {fn} has no meta.asset_sha256 entry "
                           "(compute the file's sha256 and record it)")
            elif hashes[fn] != sha256(os.path.join(d, fn)):
                fail(msgs, f"asset_sha256 mismatch for {fn}")

    # F. license sanity
    lic = str(meta.get("license", ""))
    if meta.get("origin", "generated") == "generated" and lic != "CC-BY-4.0":
        fail(msgs, f"generated parts must be CC-BY-4.0 (got '{lic}')")
    if lic.upper().startswith("CC-BY-SA"):
        fail(msgs, "CC-BY-SA files cannot be accepted (see CONTRIBUTING)")

    return report(pid, msgs)


def report(pid, msgs):
    for m in msgs:
        print(m)
    if msgs:
        print(f"\nFAIL: {pid} - {len(msgs)} issue(s). Fix and re-run; "
              "CI gates are the final judge.")
        return 1
    print(f"PASS: {pid} - ready for PR (CI runs the full gate suite: KLC "
          "rules, render, overlap, provenance anti-copy, STEP kernel).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
