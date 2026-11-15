#!/usr/bin/env python3
"""Download only the public resources referenced by the migration."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib, json, re, subprocess

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / 'sources/Loon_custom.lcf').read_text()
section = text.split('[Remote Rule]')[1].split('[Host]')[0]
jobs = []
for line in section.splitlines():
    if line.startswith('http'):
        url = line.split(',')[0]
        if url.endswith('.list'):
            jobs.append((url, 'original'))
for service in ['TikTok', 'Netflix', 'Spotify', 'Lan', 'China', 'Speedtest', 'ChinaMax']:
    jobs.append((f'https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/{service}/{service}.list', service))

def fetch(job):
    url, role = job
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    target = ROOT / 'sources/resources' / (key + '.txt')
    target.parent.mkdir(parents=True, exist_ok=True)
    run = subprocess.run(['curl', '-fsSL', '--retry', '2', '--max-time', '60', url, '-o', str(target)], capture_output=True, text=True)
    return {'url': url, 'role': role, 'path': str(target.relative_to(ROOT)), 'ok': run.returncode == 0, 'error': run.stderr.strip() if run.returncode else '', 'sha256': hashlib.sha256(target.read_bytes()).hexdigest() if run.returncode == 0 else None}

with ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(fetch, jobs))
(ROOT / 'sources/resources.json').write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n')
print(json.dumps({'downloaded': sum(x['ok'] for x in results), 'failed': [x for x in results if not x['ok']]}, ensure_ascii=False, indent=2))
