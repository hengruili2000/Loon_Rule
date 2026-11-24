#!/usr/bin/env python3
"""Structural and routing-regression checks; does not claim Egern runtime testing."""
from pathlib import Path
import hashlib, json, subprocess, re
from dns_forward import dns_forward, dns_transport_rules
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
        assert data['rules'] == [{'ssid': {'match': 'ASUS_C8_5G', 'policy': 'DIRECT'}}]
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
def read_yaml(path):
    return json.loads(subprocess.run(['ruby', '-ryaml', '-rjson', '-e',
        'puts JSON.generate(YAML.load_file(ARGV[0]))', str(path)],
        check=True, capture_output=True, text=True).stdout)
settings = read_yaml(ROOT / 'sources/user-settings.yaml')
for key, value in settings.items():
    if key != 'dns':
        assert p[key] == value, f'User setting changed: {key}'
assert p['modules'] == read_yaml(ROOT / 'sources/user-modules.yaml')['modules']
assert len(p['modules']) == 14 and all(m['enabled'] for m in p['modules'])
dns = settings['dns']
transport = list(dns_transport_rules(dns))
assert p['rules'][:len(transport)] == transport
forward = p['dns']['forward']
assert p['dns'] == {**dns, 'forward': dns_forward(dns, p['rules'][len(transport):], p['policy_groups'])}
assert forward[-1] == {'domain_wildcard': {'match': '*', 'value': 'DNSPod'}}

by_match = {data['match']: (i, data['value'])
            for i, r in enumerate(forward) for kind, data in r.items()
            if kind in {'proxy_rule_set', 'domain_suffix'}}
assert by_match['bahamut.com.tw'][1] == 'RemoteDNS'
china_urls = [r['rule_set']['match'] for r in p['rules'] if 'rule_set' in r
              and r['rule_set'].get('name') in {'ChinaMax', 'ChinaMax - Domain'}]
assert len(china_urls) == 2
assert all(by_match[url][1] == 'DNSPod' for url in china_urls)
apple_tv = next((position, value) for url, (position, value) in by_match.items()
                if url.endswith('/AppleTV.list'))
apple = next((position, value) for url, (position, value) in by_match.items()
             if url.endswith('/Apple.list'))
assert apple_tv[1] == 'RemoteDNS' and apple[1] == 'DNSPod' and apple_tv[0] < apple[0]
assert all(apple[0] < by_match[url][0] for url in china_urls)
china_domain_resource = next(r for r in json.loads((ROOT / 'sources/resources.json').read_text())
                             if r['url'] == china_urls[1])
domain_lines = [s.strip() for s in (ROOT / china_domain_resource['path']).read_text().splitlines()
                if s.strip() and not s.startswith('#')]
exact = {s for s in domain_lines if not s.startswith('.')}
suffixes = {s[1:] for s in domain_lines if s.startswith('.')}
def china_domain_match(domain):
    labels = domain.split('.')
    return domain in exact or any('.'.join(labels[i:]) in suffixes for i in range(len(labels)))
assert china_domain_match('static.mokahr.com')
assert china_domain_match('sns-v14.rednotecdn.com')
assert not china_domain_match('notmokahr.com')
assert not china_domain_match('rednotecdn.com.example.invalid')
for rule in p['dns']['forward']:
    assert next(iter(rule.values()))['value'] in set(p['dns']['upstreams']) | {'reject', 'system'}
assert len(report['remote_rules']) == 53
assert sum(r['mode'] == 'converted-remote' for r in report['remote_rules']) == 7
assert sum(r['mode'] == 'converted-remote-with-China-exclusions' for r in report['remote_rules']) == 1
sync_report = json.loads((ROOT / 'rules/sync-report.json').read_text())
assert len(report['plugins']) == 28
assert len(p['rules']) == report['rules'] == 62 + len(transport)
# Daily rule sync can change omissions without regenerating the profile report.
for source in sync_report['sources']:
    assert source['input_rules'] == source['converted_rules'] + len(source['omitted_rules']), source['id']
    native = read_yaml(ROOT / source['output'])
    assert all(key == 'no_resolve' or key.endswith('_set') for key in native)
    assert sum(len(v) for k, v in native.items() if k != 'no_resolve') == source['converted_rules']
assert p['proxies'] == []
speed = [r['and'] for r in p['rules'] if 'and' in r and r['and'].get('name') == 'Speedtest Intl']
assert len(speed) == 1 and speed[0]['policy'] == 'Speedtest Intl'
assert speed[0]['match'][0]['rule_set']['match'].endswith('/Egern/rules/Speedtest.yaml')
assert len(speed[0]['match'][1]['not']['match']['or']['match']) == 3
assert any(r.get('rule_set', {}).get('name') == '开发者服务' for r in p['rules'])
dev = read_yaml(ROOT / 'rules/Category-Dev.yaml')
assert any(re.fullmatch(regex, '123.dkr.ecr.us-east-1.amazonaws.com') for regex in dev['domain_regex_set'])
assert not any(re.fullmatch(regex, '123.dkr.ecr.us.east.amazonaws.com') for regex in dev['domain_regex_set'])
for resource in json.loads((ROOT / 'sources/resources.json').read_text()):
    assert hashlib.sha256((ROOT / resource['path']).read_bytes()).hexdigest() == resource['sha256']
# Ruby's regex engine accepts the source's scoped inline case-insensitive flags.
checks = '''require 'yaml'; p=YAML.load_file(ARGV[0]); p['policy_groups'].each { |g| d=g.values.first; next unless d['filter']; r=Regexp.new(d['filter']); raise 'filter accepts placeholder' if r.match?('REJECT'); if d['name']=='香港手动策略'; raise unless r.match?('香港 01'); raise if r.match?('香港 游戏'); end }; puts 'regex filters passed' '''
subprocess.run(['ruby', '-e', checks, str(ROOT / 'Egern_custom.yaml')], check=True)
print(json.dumps({'status': 'passed', 'policy_groups': len(groups), 'rules': len(p['rules']), 'remote_sources': len(report['remote_rules']), 'dns_forward_rules': len(p['dns']['forward']), 'user_settings_exact_match': True, 'enabled_modules': len(p['modules']), 'device_tested': False, 'full_schema_validated': False}, ensure_ascii=False))
