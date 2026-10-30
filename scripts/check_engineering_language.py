#!/usr/bin/env python3
"""Reject non-English text in engineering files outside the temporary UI localization allowlist."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ARABIC = re.compile(r'[\u0600-\u06FF]')
EXTENSIONS = {'.md', '.py', '.kt', '.js', '.ts', '.tsx', '.sql', '.toml', '.yml', '.yaml', '.bat', '.ps1'}
EXCLUDED_PARTS = {'.git', '.gradle', 'build', '__pycache__', '.venv'}
TRANSITIONAL_LOCALIZATION_FILES = {
    'app/main.py',
    'android/app/src/main/java/com/imddawsa/ai/MainActivity.kt',
    'web/index.html',
    'static/index.html',
}


def main() -> int:
    violations = []
    for path in ROOT.rglob('*'):
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if relative.as_posix() in TRANSITIONAL_LOCALIZATION_FILES:
            continue
        try:
            lines = path.read_text(encoding='utf-8').splitlines()
        except UnicodeDecodeError:
            violations.append(f'{relative}: file is not valid UTF-8')
            continue
        for number, line in enumerate(lines, 1):
            if ARABIC.search(line):
                violations.append(f'{relative}:{number}: Arabic text found in engineering content')
    if violations:
        print('Engineering language check failed:')
        print('\n'.join(violations))
        return 1
    print('Engineering language check passed (temporary UI localization files are explicitly allowlisted).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
