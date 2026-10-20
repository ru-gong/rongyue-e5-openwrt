#!/usr/bin/env python3
"""Check the curated publication, without contacting devices or external services."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {'.git', '__pycache__', 'dist', 'build', '.venv'}
FORBIDDEN_SUFFIXES = {'.img', '.ext4', '.bin', '.zip', '.gz', '.key', '.pem', '.pyc'}
PATTERNS = {
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'GitHub credential': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})'),
    'proxy connection URL': re.compile(r'\b(?:vless|vmess|tuic|ss|trojan)://[^\s\'"]{12,}'),
    'personal host path': re.compile(r'/Users/[A-Za-z][^/\s\'"]+/'),
    'device serial literal': re.compile(r'\bTS\d{10,}\b'),
}


def files():
    for path in ROOT.rglob('*'):
        rel = path.relative_to(ROOT)
        if any(part in IGNORED for part in rel.parts):
            continue
        if path.is_file() or path.is_symlink():
            yield path, rel


def main():
    errors = []
    count = 0
    for path, rel in files():
        count += 1
        if path.is_symlink():
            errors.append(f'{rel}: symlink is not allowed')
            continue
        if path.suffix in FORBIDDEN_SUFFIXES:
            errors.append(f'{rel}: private/binary artifact type is not allowed')
        if path.suffix.lower() in {'.png', '.jpg', '.jpeg'}:
            if rel.parts[:2] != ('docs', 'images'):
                errors.append(f'{rel}: image outside reviewed screenshot directory')
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeError:
            errors.append(f'{rel}: non-text file is not a reviewed screenshot')
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                errors.append(f'{rel}: {label}')

    for name in ('switch.sh', 'action.sh', 'customize.sh'):
        path = ROOT / 'components/system-switch/reference' / name
        syntax = subprocess.run(['sh', '-n', str(path)], capture_output=True)
        if syntax.returncode:
            errors.append(f'{path.relative_to(ROOT)}: invalid shell syntax')
            continue
        # The unconditional public-reference guard must stop before any device access.
        result = subprocess.run(['sh', str(path)], capture_output=True, timeout=5)
        if result.returncode != 64 or b'Reference only:' not in result.stderr:
            errors.append(f'{path.relative_to(ROOT)}: public-reference guard failed')

    # Check authored documentation links. Historical source text may intentionally
    # mention paths to private material that is not part of the public repository.
    document_paths = [ROOT / 'README.md', ROOT / 'README.en.md']
    document_paths += list((ROOT / 'docs').rglob('*.md'))
    document_paths += list((ROOT / 'components').rglob('README.md'))
    for path in document_paths:
        if not path.exists():
            errors.append(f'{path.relative_to(ROOT)}: missing document')
            continue
        text = path.read_text()
        for dest in re.findall(r'!?\[[^\]]*\]\(([^)\s]+)\)', text):
            if re.match(r'[a-zA-Z]+:', dest) or dest.startswith('#'):
                continue
            target = (path.parent / dest.split('#', 1)[0]).resolve()
            if not target.exists():
                errors.append(f'{path.relative_to(ROOT)}: missing local link {dest}')

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f'Publication checks passed for {count} files; system references stop before device access.')
    print('This check complements manual review; it is not a guarantee of compatibility or exhaustive secret detection.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
