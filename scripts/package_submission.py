"""Package the clean committed release, built frontend and a labelled source cache."""
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8').strip()


def package():
    if git('status', '--porcelain'):
        raise SystemExit('Commit reviewed changes before packaging the final submission.')
    commit = git('rev-parse', 'HEAD')
    if not (ROOT/'frontend/dist/index.html').is_file():
        raise SystemExit('Build the frontend first.')
    paths = [ROOT/p for p in git('ls-files', '-z').split('\0') if p]
    paths += sorted(p for p in (ROOT/'frontend/dist').rglob('*') if p.is_file())
    cache = ROOT/'data/cache/district_forecasts/agromet_nashik.json'
    if cache.exists():
        paths.append(cache)
    folder = ROOT/'release-artifacts'
    folder.mkdir(exist_ok=True)
    target = folder/f'Panchayat-downscaling-final-{commit[:7]}.zip'
    manifest = {'commit': commit, 'packaged_at': datetime.now(timezone.utc).isoformat(),
                'district_cache_note': 'Cached public source; original issue/download dates are retained. Refresh for a later bulletin.',
                'files': {}}
    with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as out:
        for path in paths:
            name = path.relative_to(ROOT).as_posix()
            raw = path.read_bytes()
            out.writestr('Panchayat-downscaling/'+name, raw)
            manifest['files'][name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        out.writestr('Panchayat-downscaling/RELEASE.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(target) as check:
        if check.testzip() is not None:
            raise SystemExit('ZIP integrity check failed.')
        for name, meta in manifest['files'].items():
            if hashlib.sha256(check.read('Panchayat-downscaling/'+name)).hexdigest() != meta['sha256']:
                raise SystemExit('ZIP content checksum mismatch: '+name)
    sha = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(sha+'  '+target.name+'\n', encoding='ascii')
    print(target)
    print(f'{len(paths)} verified files; {target.stat().st_size/1024/1024:.1f} MiB; SHA-256 {sha}')


if __name__ == '__main__':
    package()
