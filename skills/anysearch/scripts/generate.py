#!/usr/bin/env python3
"""Generate shared AnySearch constants into the four CLI implementations."""
from __future__ import annotations
import json, os, sys
SCRIPT_DIR=os.path.dirname(os.path.abspath(__file__)); SHARED_DIR=os.path.join(SCRIPT_DIR,"shared")
MARKERS={".py":("# BEGIN GENERATED:{name}","# END GENERATED:{name}"),".js":("// BEGIN GENERATED:{name}","// END GENERATED:{name}"),".ps1":("# BEGIN GENERATED:{name}","# END GENERATED:{name}"),".sh":("# BEGIN GENERATED:{name}","# END GENERATED:{name}")}
def load_constants():
    with open(os.path.join(SHARED_DIR,"constants.json"),encoding="utf-8") as f:return json.load(f)
def render_constants(ext,c):
    d=c["available_domains"]; ct=c["content_types"]; fr=c["freshness_values"]; z=c["zones"]
    if ext==".py":
        lines=["AVAILABLE_DOMAINS = ["]+["    "+", ".join(f'\"{x}\"' for x in d[i:i+6])+"," for i in range(0,len(d),6)]+["]","","CONTENT_TYPES = [","    "+", ".join(f'\"{x}\"' for x in ct)+","]","","FRESHNESS_VALUES = ["+", ".join(f'\"{x}\"' for x in fr)+"]","ZONES = ["+", ".join(f'\"{x}\"' for x in z)+"]"]; return "\n".join(lines)
    if ext==".js":
        lines=["const AVAILABLE_DOMAINS = ["]+["  "+",".join(f'\"{x}\"' for x in d[i:i+6])+"," for i in range(0,len(d),6)]+["];","","const CONTENT_TYPES = [","  "+",".join(f'\"{x}\"' for x in ct)+",","];","","const FRESHNESS_VALUES = ["+",".join(f'\"{x}\"' for x in fr)+"];","const ZONES = ["+",".join(f'\"{x}\"' for x in z)+"];"]; return "\n".join(lines)
    if ext==".ps1":
        chunks=[d[i:i+6] for i in range(0,len(d),6)]; lines=["$AVAILABLE_DOMAINS = @("]+["    "+", ".join(f'\"{x}\"' for x in chunk)+( "," if i<len(chunks)-1 else "") for i,chunk in enumerate(chunks)]+[")","","$CONTENT_TYPES = @("+", ".join(f'\"{x}\"' for x in ct)+")","$FRESHNESS_VALUES = @("+", ".join(f'\"{x}\"' for x in fr)+")","$ZONES = @("+", ".join(f'\"{x}\"' for x in z)+")"]; return "\n".join(lines)
    if ext==".sh":return "\n".join(["AVAILABLE_DOMAINS=("+" ".join(f'\"{x}\"' for x in d)+")","CONTENT_TYPES=("+" ".join(f'\"{x}\"' for x in ct)+")","FRESHNESS_VALUES=("+" ".join(f'\"{x}\"' for x in fr)+")","ZONES=("+" ".join(f'\"{x}\"' for x in z)+")"])
    raise ValueError(f"unsupported extension: {ext}")
def inject(source,ext,name,content):
    begin=MARKERS[ext][0].format(name=name); end=MARKERS[ext][1].format(name=name); bi=source.find(begin); ei=source.find(end)
    if bi<0 or ei<0 or ei<=bi:return None
    after=source.index("\n",bi)+1; return source[:after]+content+"\n"+source[ei:]
def process_file(path,constants,check_only):
    if not os.path.isfile(path):print(f"  {os.path.basename(path)}: MISSING"); return False
    ext=os.path.splitext(path)[1]
    with open(path,encoding="utf-8") as f:original=f.read()
    generated=inject(original,ext,"CONSTANTS",render_constants(ext,constants))
    if generated is None:print(f"  {os.path.basename(path)}: CONSTANTS markers missing"); return False
    if generated==original:print(f"  {os.path.basename(path)}: up to date"); return True
    if check_only:print(f"  {os.path.basename(path)}: OUT OF DATE"); return False
    with open(path,"w",encoding="utf-8",newline="\n") as f:f.write(generated)
    print(f"  {os.path.basename(path)}: updated"); return True
def main():
    check_only="--check" in sys.argv; constants=load_constants(); scripts=[os.path.join(SCRIPT_DIR,"anysearch_cli"+ext) for ext in (".py",".js",".ps1",".sh")]; ok=True
    # Do not use all(): every implementation must be checked/updated even after one fails.
    for path in scripts:
        if not process_file(path,constants,check_only):ok=False
    if not ok:
        print("FAILED: one or more generated targets could not be synchronized." if not check_only else "FAILED: generated constants are out of date. Run: python skills/anysearch/scripts/generate.py")
        return 1
    print("OK: generated constants are current." if check_only else "Done."); return 0
if __name__=="__main__":raise SystemExit(main())
