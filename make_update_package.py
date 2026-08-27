from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime
from pathlib import Path

PRESERVE_RELATIVE = {"config/settings.json","config/coordinates.json","config/templates.json","config/protocols.json","config/ui_settings.json"}
PRESERVE_PREFIXES = ("config/runtime/", "project/logs/", "project/templates/")
IGNORE_SUFFIXES = {".pyc", ".pyo", ".log"}
IGNORE_NAMES = {"__pycache__", ".git", ".idea", ".vscode", "build"}
ROOT = Path(__file__).resolve().parent

def norm_rel(path: Path) -> str: return path.as_posix()
def is_preserved(rel: str) -> bool: return rel in PRESERVE_RELATIVE or any(rel.startswith(p) for p in PRESERVE_PREFIXES)
def is_ignored(rel: str, path: Path) -> bool: return is_preserved(rel) or path.suffix.lower() in IGNORE_SUFFIXES or any(part in IGNORE_NAMES for part in Path(rel).parts)
def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b""): h.update(chunk)
    return h.hexdigest()
def scan(root: Path) -> dict[str,dict]:
    result={}
    if not root.exists(): return result
    for path in root.rglob("*"):
        if not path.is_file(): continue
        rel=norm_rel(path.relative_to(root))
        if is_ignored(rel,path): continue
        st=path.stat(); result[rel]={"size":st.st_size,"sha256":sha256(path)}
    return result

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("old_dir"); parser.add_argument("new_dir"); parser.add_argument("version"); parser.add_argument("--output",default="updates"); args=parser.parse_args()
    old_dir=Path(args.old_dir).resolve(); new_dir=Path(args.new_dir).resolve(); output_dir=Path(args.output).resolve(); output_dir.mkdir(parents=True,exist_ok=True)
    if not (new_dir/"MIS_Bot_Beta.exe").exists(): raise SystemExit("New release not found")
    old_files=scan(old_dir); new_files=scan(new_dir)
    changed=[rel for rel,meta in new_files.items() if old_files.get(rel)!=meta]; deleted=[rel for rel in old_files if rel not in new_files]
    manifest={"format":1,"product":"MIS_Bot_Beta","version":args.version,"created_at":datetime.now().isoformat(timespec="seconds"),"changed":{rel:new_files[rel] for rel in sorted(changed)},"deleted":sorted(deleted)}
    package=output_dir/f"MIS_Bot_Update_{args.version}.zip"
    with zipfile.ZipFile(package,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        zf.writestr("manifest.json",json.dumps(manifest,ensure_ascii=False,indent=2)); zf.write(ROOT/"apply_update.bat","apply_update.bat"); zf.write(ROOT/"apply_update.ps1","apply_update.ps1")
        for rel in sorted(changed): zf.write(new_dir/rel,f"files/{rel}")
    print(f"Package: {package}\nChanged files: {len(changed)}\nDeleted files: {len(deleted)}\nPackage size: {package.stat().st_size/1024/1024:.2f} MB")

if __name__=="__main__": main()
