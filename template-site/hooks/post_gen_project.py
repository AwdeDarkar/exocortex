#!/usr/bin/python3.8

from pathlib import Path

PROJECT_DIR = Path(".").resolve()
SRC_DIR = PROJECT_DIR / "src"
COMMON_DIR = PROJECT_DIR.parent.parent / "common-source"

if __name__ == "__main__":
    (SRC_DIR / "common").symlink_to(COMMON_DIR, target_is_directory=True)
