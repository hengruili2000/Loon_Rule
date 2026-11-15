#!/usr/bin/env python3
"""Structural and routing-regression checks; does not claim Egern runtime testing."""
from pathlib import Path
import hashlib, json, subprocess, re
ROOT = Path(__file__).resolve().parents[1]
p = json.loads(subprocess.run(['ruby', '-ryaml', '-rjson', '-e', 'puts JSON.generate(YAML.load_file(ARGV[0]))', str(ROOT / 'Egern_custom.yaml')], check=True, capture_output=True, text=True).stdout)
report = json.loads((ROOT / 'conversion-report.json').read_text())
b = (ROOT / 'sources/Loon_custom.lcf').read_bytes()
assert hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest() == report['source_blob_sha']
groups = {next(iter(g.values()))['name']: g for g in p['policy_groups']}
assert len(groups) == len(p['policy_groups']) == 28
known = set(groups) | {'DIRECT', 'REJECT'}
edges = {}
for name, group in groups.items():
    kind, data = next(iter(group.items()))
    assert kind in {'select', 'conditional'}
    if kind == 'select':
        refs = data.get('policies', [])
    else:
        refs = [data['default_policy']] + [next(iter(r.values()))['policy'] for r in data['rules']]
        assert data['rules'] == [{'ssid': {'match': 'PHICOMM_5G', 'policy': 'DIRECT'}}]
        assert data['default_policy'] == name.replace('场景', '策略')
    assert set(refs) <= known, (name, refs)
    edges[name] = [x for x in refs if x in groups]
def visit(name, path=()):
    assert name not in path, (name, path)
    for child in edges[name]:
        visit(child, (*path, name))
for name in groups:
    visit(name)
allowed = {'domain', 'domain_suffix', 'domain_keyword', 'domain_regex', 'domain_wildcard',
           'ip_cidr', 'ip_cidr6', 'asn', 'geoip', 'user_agent', 'url_regex', 'protocol',
           'dest_port', 'ssid', 'bssid', 'cellular', 'rule_set', 'and', 'or', 'not', 'default'}
def check_rule(rule, child=False):
    assert len(rule) == 1
    kind, data = next(iter(rule.items()))
    assert kind in allowed, kind
    if not child:
        assert data['policy'] in known
    if kind in {'and', 'or'}:
        assert len(data['match']) >= 2
        for item in data['match']:
            check_rule(item, True)
    elif kind == 'not':
        check_rule(data['match'], True)
    elif kind != 'default':
        assert isinstance(data['match'], str) and data['match']
for rule in p['rules']:
    check_rule(rule)
assert p['rules'][-1] == {'default': {'policy': '漏网之鱼'}}
assert not any('default' in r for r in p['rules'][:-1])
assert next(iter(groups['漏网之鱼'].values()))['policies'][:2] == ['DIRECT', '默认代理']
assert next(iter(groups['Apple服务'].values()))['policies'][0] == 'DIRECT'
assert p['dns']['forward'][0] == {'ssid': {'match': 'PHICOMM_5G', 'value': '10.0.0.1'}}
assert p['dns']['forward'][-1]['domain_wildcard']['match'] == '*'
assert p['dns']['hosts']['mtalk.google.com'] == '108.177.125.188'
assert len(report['remote_rules']) == 53
assert sum(r['mode'] == 'native-approved-replacement' for r in report['remote_rules']) == 5
assert sum(r['mode'] == 'native-with-China-exclusions' for r in report['remote_rules']) == 1
assert len(report['omitted_rules']) == 8 and len(report['plugins']) == 28
assert p['modules'] == [] and p['proxies'] == []
speed = [r['and'] for r in p['rules'] if 'and' in r and r['and'].get('name') == 'Speedtest Intl']
assert len(speed) == 1 and speed[0]['policy'] == 'Speedtest Intl'
assert len(speed[0]['match'][1]['not']['match']['or']['match']) == 3
ecr = [r['and'] for r in p['rules'] if 'and' in r and r['and'].get('name') == '开发者服务']
assert len(ecr) == 1
assert ecr[0]['match'][1]['not']['match']['domain_wildcard']['match'] == '?*.dkr.ecr.*.*.amazonaws.com'
for resource in json.loads((ROOT / 'sources/resources.json').read_text()):
    assert hashlib.sha256((ROOT / resource['path']).read_bytes()).hexdigest() == resource['sha256']
# Ruby's regex engine accepts the source's scoped inline case-insensitive flags.
checks = '''require 'yaml'; p=YAML.load_file(ARGV[0]); p['policy_groups'].each { |g| d=g.values.first; next unless d['filter']; r=Regexp.new(d['filter']); raise 'filter accepts placeholder' if r.match?('REJECT'); if d['name']=='香港手动策略'; raise unless r.match?('香港 01'); raise if r.match?('香港 游戏'); end }; puts 'regex filters passed' '''
subprocess.run(['ruby', '-e', checks, str(ROOT / 'Egern_custom.yaml')], check=True)
print(json.dumps({'status': 'passed', 'policy_groups': len(groups), 'rules': len(p['rules']), 'remote_sources': len(report['remote_rules']), 'device_tested': False}, ensure_ascii=False))
