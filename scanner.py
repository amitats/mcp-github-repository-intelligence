from collections import Counter
from pathlib import Path
from config import settings

EXCLUDED_DIRS = {
    ".git",".idea",".vscode",".venv","venv","env","__pycache__","node_modules",
    "dist","build","target",".pytest_cache",".mypy_cache",".ruff_cache",".tox",
    ".nox",".terraform","htmlcov","coverage",".next",".cache","vendor"
}
BINARY_EXTENSIONS = {
    ".png",".jpg",".jpeg",".gif",".ico",".pdf",".zip",".tar",".gz",".jar",".war",
    ".class",".exe",".dll",".so",".dylib",".woff",".woff2",".ttf",".pyc",".db",
    ".sqlite",".bin"
}
LANG = {
    ".py":"Python",".go":"Go",".java":"Java",".js":"JavaScript",".jsx":"JavaScript",
    ".ts":"TypeScript",".tsx":"TypeScript",".rs":"Rust",".cs":"C#",".cpp":"C++",
    ".c":"C",".rb":"Ruby",".php":"PHP",".kt":"Kotlin",".tf":"Terraform",".sh":"Shell"
}

def scan_repository(root: Path):
    out=[]
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel=p.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if p.suffix.lower() in BINARY_EXTENSIONS:
            continue
        try:
            if p.stat().st_size > settings.max_file_size:
                continue
        except OSError:
            continue
        out.append(p)
    return out

def detect_languages(files):
    c=Counter(LANG[p.suffix.lower()] for p in files if p.suffix.lower() in LANG)
    return [k for k,_ in c.most_common()]

def repository_structure(root, files):
    dirs=Counter()
    ext=Counter()
    for p in files:
        r=p.relative_to(root)
        if len(r.parts)>1:
            dirs[r.parts[0]] += 1
        if p.suffix:
            ext[p.suffix.lower()] += 1
    return {
        "top_level_directories":[{"name":k,"file_count":v} for k,v in dirs.most_common(30)],
        "common_extensions":[{"extension":k,"file_count":v} for k,v in ext.most_common(20)]
    }
