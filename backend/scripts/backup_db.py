#!/usr/bin/env python3
"""SQLite backup/restore utility. Usage: backup_db.py backup|restore PATH"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings

source = Path(settings.database_url.replace("sqlite:///", ""))
if len(sys.argv) < 2 or sys.argv[1] not in {"backup", "restore"}:
    raise SystemExit("usage: backup_db.py backup [path] | restore PATH")
if sys.argv[1] == "backup":
    target_dir = Path(sys.argv[2] if len(sys.argv) > 2 else settings.database_backup_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"aidream-backup-{__import__('time').time_ns()}.db"
    shutil.copy2(source, target)
    print(target)
else:
    target = Path(sys.argv[2])
    if not target.exists():
        raise SystemExit(f"backup not found: {target}")
    shutil.copy2(target, source)
    print(source)
