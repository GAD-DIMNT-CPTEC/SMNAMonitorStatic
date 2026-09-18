#!/usr/bin/env python3
"""Export the committed static frontend; never export operational data."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ref', default='HEAD', help='Commit, tag or branch; default HEAD')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    commit = git('rev-parse', '--verify', '--end-of-options', args.ref+'^{commit}').decode().strip()
    files = {}
    for record in git('ls-tree', '-r', '-z', commit, '--', 'static/').split(b'\0'):
        if not record:
            continue
        meta, name = record.split(b'\t', 1)
        mode, kind, oid = meta.decode().split()
        relative = Path(name.decode()).relative_to('static')
        if relative.parts[0] == 'data' or str(relative) == 'version.json':
            continue
        if kind != 'blob' or mode not in ('100644', '100755'):
            parser.error(f'Unsupported frontend entry: {relative}')
        files[str(relative)] = git('cat-file', 'blob', oid)
    if 'index.html' not in files:
        parser.error('This revision has no static/index.html')
    if 'version.js' in files:
        version_script = files['version.js'].decode()
        version_script = re.sub(r'commit: null', 'commit: '+json.dumps(commit), version_script, count=1)
        files['version.js'] = version_script.encode()
        # Give each committed delivery its own script/cache identity.
        files['index.html'] = re.sub(
            rb'((?:src|href)="(?:styles\.css|config\.js|app\.js|gsi\.js|version\.js|theme\.js)\?v=)[^"]+',
            lambda match: match[1]+commit.encode(), files['index.html'])
    manifest = {'commit': commit, 'files': {name: hashlib.sha256(data).hexdigest()
                                           for name, data in sorted(files.items())}}
    files['version.json'] = (json.dumps(manifest, indent=2)+'\n').encode()
    output = args.output.resolve()
    if output == (REPO/'static').resolve():
        parser.error('Use a separate delivery directory, not the source static directory')
    for name in files:
        target = output/name
        if not target.resolve().is_relative_to(output) or target.is_symlink():
            parser.error(f'Unsafe destination: {target}')
        if target.exists() and (not args.overwrite or not target.is_file()):
            parser.error(f'Destination exists: {target}; choose another directory or --overwrite')
    for name, data in files.items():
        target = output/name
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=target.parent, prefix='.smna-')
        try:
            with os.fdopen(fd, 'wb') as handle:
                handle.write(data)
            os.chmod(temporary, 0o644)
            os.replace(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)
    print(f'Exported {len(files)-1} frontend files from {commit} to {output}')
    print('Operational data untouched. No upload or deployment was performed.')


if __name__ == '__main__':
    main()
