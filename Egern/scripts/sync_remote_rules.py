#!/usr/bin/env python3
"""Fetch, convert and validate ALL upstreams before replacing published artifacts."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile
from rule_converter import convert_text, dump_rule_set

ROOT = Path(__file__).resolve().parents[1]

def download(url):
    run = subprocess.run(['curl', '-fsSL', '--retry', '3', '--retry-delay', '2',
                          '--connect-timeout', '15', '--max-time', '90', url],
                         capture_output=True, check=True)
    return run.stdout.decode('utf-8-sig')

def sync(root=ROOT, fetch=download):
    specs = json.loads((root / 'sources/remote-rules.json').read_text())
    ids = [x['id'] for x in specs]
    if len(ids) != len(set(ids)) or any('/' in x or '..' in x for x in ids):
        raise ValueError('Invalid or duplicate remote rule IDs')
    with ThreadPoolExecutor(max_workers=8) as pool:
        texts = list(pool.map(fetch, [x['source_url'] for x in specs]))
    pending, report = {}, {'schema_version': 1, 'sync_interval_seconds': 86400, 'sources': []}
    for spec, text in zip(specs, texts):
        native, details = convert_text(text, spec['source_url'])
        header = [f'# Generated Egern rule set: {spec["id"]}',
                  f'# Source: {spec["source_url"]}',
                  '# Managed by the daily GitHub Actions workflow; do not edit.']
        # Keep upstream attribution/license comments with the derived rules.
        for line in text.splitlines():
            if line.lstrip().startswith('#'):
                header.append(line)
        payload = '\n'.join(header) + '\n' + dump_rule_set(native)
        filename = spec['id'] + '.yaml'
        pending[filename] = payload
        report['sources'].append({**spec, 'output': 'rules/' + filename,
                                  'source_sha256': hashlib.sha256(text.encode()).hexdigest(),
                                  'output_sha256': hashlib.sha256(payload.encode()).hexdigest(), **details})
    pending['sync-report.json'] = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    output = root / 'rules'
    output.mkdir(exist_ok=True)
    # Network/parser failures above leave every last-known-good artifact intact.
    with tempfile.TemporaryDirectory(prefix='.egern-sync-', dir=root) as temp:
        for filename, content in pending.items():
            (Path(temp) / filename).write_text(content)
        for filename in pending:
            os.replace(Path(temp) / filename, output / filename)
    return report

if __name__ == '__main__':
    report = sync()
    print(json.dumps({'converted_remote_rule_sets': len(report['sources']),
                      'rules': sum(x['converted_rules'] for x in report['sources']),
                      'omitted_process_rules': sum(len(x['omitted_rules']) for x in report['sources'])}, ensure_ascii=False))
