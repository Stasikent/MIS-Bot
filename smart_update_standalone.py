from __future__ import annotations

import hashlib, json, os, shutil, sys
from pathlib import Path

PRESERVE_RELATIVE={"config/settings.json","config/coordinates.json","config/templates.json","config/protocols.json","config/ui_settings.json"}
PRESERVE_PREFIXES=("config/runtime/","project/logs/","project/templates/")
IGNORE_NAMES={"__pycache__",".git",".idea",".vscode"}
IGNORE_SUFFIXES={".pyc",".pyo",".log"}
TRANSPORT_FILES={"update_pc_from_flash.bat","smart_update_standalone.exe","smart_update_standalone.py"}
MANIFEST_NAME=".mis_bot_update_manifest.json"

def norm_rel(path:Path)->str:return path.as_posix()
def is_ignored(rel,path):
    if any(part in IGNORE_NAMES for part in Path(rel).parts):return True
    if path.suffix.lower() in IGNORE_SUFFIXES:return True
    if rel.startswith("project/logs/") and path.suffix.lower() in {".png",".jpg",".jpeg",".webp"}:return True
    return rel in TRANSPORT_FILES
def is_preserved(rel):return rel in PRESERVE_RELATIVE or any(rel.startswith(p) for p in PRESERVE_PREFIXES)
def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda:fh.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()
def scan_tree(root):
    result={}
    for path in root.rglob("*"):
        if not path.is_file():continue
        rel=norm_rel(path.relative_to(root))
        if is_ignored(rel,path):continue
        stat=path.stat();result[rel]={"size":stat.st_size,"sha256":sha256(path)}
    return result
def load_manifest(path):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return {}
def save_manifest(path,files):path.write_text(json.dumps({"format":1,"files":files},ensure_ascii=False,indent=2),encoding="utf-8")
def infer_source_dir():return Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parent
def parse_args():
    source=infer_source_dir();destination=Path(r"C:\MIS_Bot_Beta");args=sys.argv[1:]
    if not args:return source,destination,True
    if len(args)==1 and not args[0].startswith("--"):return source,Path(args[0]).resolve(),True
    delete_obsolete="--delete-obsolete" in args;pos=[a for a in args if not a.startswith("--")]
    if len(pos)>=1:source=Path(pos[0]).resolve()
    if len(pos)>=2:destination=Path(pos[1]).resolve()
    return source,destination,delete_obsolete

def main():
    source,destination,delete_obsolete=parse_args()
    if not source.exists() or not (source/"MIS_Bot_Beta.exe").exists():print(f"[ERROR] Invalid source: {source}");return 2
    if not (destination/"MIS_Bot_Beta.exe").exists():print(f"[ERROR] Existing MIS Bot installation not found: {destination}");return 2
    source_files=scan_tree(source);manifest_path=destination/MANIFEST_NAME;old_manifest=load_manifest(manifest_path).get("files",{});new_manifest=dict(old_manifest)
    copied=skipped=preserved=failed=deleted=0
    for rel,meta in sorted(source_files.items()):
        src=source/rel;dst=destination/rel
        if is_preserved(rel) and dst.exists():preserved+=1;continue
        same=False
        if dst.exists():
            try:same=dst.stat().st_size==meta["size"] and sha256(dst)==meta["sha256"]
            except Exception:pass
        if same:skipped+=1;new_manifest[rel]=meta;continue
        try:
            dst.parent.mkdir(parents=True,exist_ok=True);tmp=dst.with_name(dst.name+".update_tmp");shutil.copy2(src,tmp);os.replace(tmp,dst);copied+=1;new_manifest[rel]=meta;print(f"[COPY] {rel}")
        except Exception as e:failed+=1;print(f"[FAIL] {rel}: {e}")
    if delete_obsolete:
        source_set=set(source_files)
        for rel in sorted(set(old_manifest)-source_set):
            if is_preserved(rel):continue
            dst=destination/rel
            try:
                if dst.exists() and dst.is_file():dst.unlink();deleted+=1
                new_manifest.pop(rel,None)
            except Exception as e:failed+=1;print(f"[FAIL DELETE] {rel}: {e}")
    save_manifest(manifest_path,new_manifest);(destination/"project"/"logs").mkdir(parents=True,exist_ok=True);(destination/"config"/"runtime").mkdir(parents=True,exist_ok=True)
    print(f"Copied changed/new: {copied}; identical: {skipped}; preserved: {preserved}; deleted: {deleted}; errors: {failed}")
    return 1 if failed else 0
if __name__=="__main__":raise SystemExit(main())
