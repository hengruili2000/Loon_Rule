#!/usr/bin/env python3
"""Build a native Egern profile from the saved Loon profile and public sources.

No third-party Python dependencies. Ruby/Psych is used only for YAML serialization.
Run fetch_sources.py first to refresh the public rule snapshots.
"""
from pathlib import Path
from collections import Counter
from urllib.parse import unquote
import hashlib, ipaddress, json, re, subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'sources/Loon_custom.lcf'
raw = SOURCE.read_text()
sections = {}
current = None
for line in raw.splitlines():
    line = line.strip()
    if line.startswith('[') and line.endswith(']'):
        current = line[1:-1]; sections[current] = []
    elif current and line and not line.startswith('#'):
        sections[current].append(line)
general = dict(x.split('=', 1) for x in sections['General'])
general = {k.strip(): v.strip() for k, v in general.items()}
resources = json.loads((ROOT / 'sources/resources.json').read_text())
assert all(x['ok'] for x in resources), 'One or more rule resources failed to download'
by_url = {x['url']: x for x in resources}
by_role = {x['role']: x for x in resources if x['role'] != 'original'}
skipped, normalized, remote_report = [], [], []
TYPES = {'DOMAIN': 'domain', 'DOMAIN-SUFFIX': 'domain_suffix',
         'DOMAIN-KEYWORD': 'domain_keyword', 'DOMAIN-WILDCARD': 'domain_wildcard',
         'DOMAIN-REGEX': 'domain_regex', 'IP-CIDR': 'ip_cidr',
         'IP-CIDR6': 'ip_cidr6', 'IP-ASN': 'asn', 'GEOIP': 'geoip',
         'USER-AGENT': 'user_agent', 'URL-REGEX': 'url_regex'}
ECR = 'AND,((DOMAIN-WILDCARD,?*.dkr.ecr.?*.amazonaws.com),(NOT,((DOMAIN-WILDCARD,?*.dkr.ecr.*.*.amazonaws.com))))'

def condition(line, label):
    if line == ECR:
        return {'and': {'match': [
            {'domain_wildcard': {'match': '?*.dkr.ecr.?*.amazonaws.com'}},
            {'not': {'match': {'domain_wildcard': {'match': '?*.dkr.ecr.*.*.amazonaws.com'}}}}
        ]}}
    if ',' not in line:
        return {('domain_suffix' if line.startswith('.') else 'domain'): {'match': line.lstrip('.')}}
    parts = [x.strip() for x in line.split(',')]
    typ, match = parts[:2]
    if typ == 'PROCESS-NAME':
        skipped.append({'source': label, 'rule': line, 'reason': 'Egern documented rule types do not include process-name matching'})
        return None
    if typ not in TYPES:
        raise ValueError(f'Unsupported rule in {label}: {line}')
    kind = TYPES[typ]
    if kind in ('ip_cidr', 'ip_cidr6'):
        canonical = str(ipaddress.ip_network(match, strict=False))
        if canonical != match:
            normalized.append({'source': label, 'from': match, 'to': canonical})
        match = canonical
    if kind == 'user_agent':
        match = unquote(match)
    data = {'match': match}
    if 'no-resolve' in parts[2:]:
        data['no_resolve'] = True
    return {kind: data}

def source_conditions(resource):
    result = []
    for line in (ROOT / resource['path']).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith(('#', ';', '//')):
            continue
        c = condition(line, resource['url'])
        if c:
            result.append(c)
    return result

def with_policy(c, policy, name=None):
    c = json.loads(json.dumps(c))
    d = next(iter(c.values())); d['policy'] = policy
    if name:
        d['name'] = name
    return c

def split_csv(value):
    return [x.strip() for x in value.split(',') if x.strip()]

profile = {
    'ipv6': False,
    'http_port': int(general['wifi-access-http-port']),
    'socks_port': int(general['wifi-access-socks5-port']),
    'allow_external_connections': False,
    'close_connections_on_policy_change': True,
    'bypass_tunnel_proxy': split_csv(general['skip-proxy']),
    'real_ip_domains': split_csv(general['real-ip']),
    'vif_excluded_routes': split_csv(general['bypass-tun']),
    'proxy_latency_test_url': general['proxy-test-url'],
    'direct_latency_test_url': general['internet-test-url'],
}
dns = {'bootstrap': split_csv(general['dns-server']),
       'upstreams': {'默认加密DNS': split_csv(general['doh-server'])},
       'forward': [], 'hosts': {}}
for line in sections['Host']:
    host, value = [x.strip() for x in line.split('=', 1)]
    if host.startswith('ssid:'):
        dns['forward'].append({'ssid': {'match': host.split(':', 1)[1].strip(), 'value': value.split('server:', 1)[1].strip()}})
    elif value.startswith('server:'):
        kind = 'domain_wildcard' if '*' in host else 'domain'
        dns['forward'].append({kind: {'match': host, 'value': value.split(':', 1)[1].strip()}})
    else:
        dns['hosts'][host] = value
dns['forward'].append({'domain_wildcard': {'match': '*', 'value': '默认加密DNS'}})
profile['dns'] = dns
profile['proxies'] = []
filters = {}
for line in sections['Remote Filter']:
    name, value = line.split('=', 1)
    filters[name] = re.search(r'FilterKey="(.*)"$', value).group(1)

groups = []
for line in sections['Proxy Group']:
    name, value = line.split('=', 1)
    fields = split_csv(value); typ = fields.pop(0)
    icon = next((x.split('=', 1)[1] for x in fields if x.startswith('img-url=')), None)
    fields = [x for x in fields if not x.startswith('img-url=')]
    data = {'name': name}
    if typ == 'select':
        if len(fields) == 1 and fields[0] in filters:
            data.update(policies=['节点订阅'], flatten=True, filter='^(?!REJECT$)(?:' + filters[fields[0]] + ')')
        else:
            data['policies'] = fields
        kind = 'select'
    elif typ == 'ssid':
        options = dict(x.split('=', 1) for x in fields)
        assert options['default'] == options['cellular']
        data.update(rules=[{'ssid': {'match': k.strip('"'), 'policy': v}} for k, v in options.items() if k not in ('default', 'cellular')], default_policy=options['default'])
        kind = 'conditional'
    else:
        raise ValueError(f'Unsupported group: {line}')
    if icon:
        data['icon'] = icon
    groups.append({kind: data})
# The original template contains no subscription or local proxy credentials.
# REJECT is deliberately excluded by the regional filters; empty regions fail closed.
groups.append({'select': {'name': '节点订阅', 'policies': ['REJECT'], 'urls': [], 'update_interval': 86400, 'icon': 'tray.and.arrow.down'}})
profile['policy_groups'] = groups
profile['default_subscription_group'] = '节点订阅'
profile['default_proxy_group'] = '节点订阅'
rules = [{'protocol': {'match': 'stun', 'policy': 'REJECT', 'name': '原 disable-stun=true'}}]
final_policy = None
for line in sections['Rule']:
    fields = split_csv(line)
    if fields[0] == 'FINAL':
        final_policy = fields[1]; continue
    rules.append(with_policy(condition(','.join(fields[:2]), 'Loon local rules'), fields[2]))

replacement = {'TikTok': 'TikTok', 'Speedtest Intl': 'Speedtest', 'Netflix': 'Netflix',
               'Spotify': 'Spotify', 'LAN': 'Lan', 'CN REGION': 'China'}
china_original = next(x['url'] for x in resources if x['role'] == 'original' and x['url'].endswith('/ChinaMax/ChinaMax.list'))
china_domain = next(x['url'] for x in resources if x['role'] == 'original' and x['url'].endswith('/ChinaMax/ChinaMax_Domain.list'))

for line in sections['Remote Rule']:
    fields = split_csv(line)
    url = fields[0]; options = dict(x.split('=', 1) for x in fields[1:])
    policy, tag = options['policy'], options['tag']
    if options.get('enabled', 'true') == 'false':
        continue
    if tag == 'Speedtest Intl':
        # Keep exclusions local to Speedtest; do not reorder the global China rules.
        china_conditions = [{'rule_set': {'match': x}} for x in [by_role['China']['url'], china_original, china_domain]]
        c = {'and': {'match': [
            {'or': {'match': source_conditions(by_role['Speedtest'])}},
            {'not': {'match': {'or': {'match': china_conditions}}}}
        ]}}
        rules.append(with_policy(c, policy, tag))
        mode, resolved = 'native-with-China-exclusions', by_role['Speedtest']['url']
    elif tag in replacement:
        resource = by_role[replacement[tag]]
        rules.extend(with_policy(c, policy, tag) for c in source_conditions(resource))
        mode, resolved = 'native-approved-replacement', resource['url']
    elif url.endswith(('/Anthropic.list', '/Category-Dev.list')):
        rules.extend(with_policy(c, policy, tag) for c in source_conditions(by_url[url]))
        mode, resolved = 'native-snapshot', url
    else:
        # Verify every rule is understood before retaining the original live URL.
        before = len(skipped)
        source_conditions(by_url[url])
        assert len(skipped) == before, f'Live resource contains unsupported rules: {url}'
        rules.append({'rule_set': {'match': url, 'policy': policy, 'name': tag, 'update_interval': 28800}})
        mode, resolved = 'live-original', url
    remote_report.append({'tag': tag, 'policy': policy, 'original_url': url, 'converted_source': resolved, 'mode': mode})
rules.append({'default': {'policy': final_policy}})
profile['rules'] = rules
profile['modules'] = []
# No CA existed in the source. Leave CA generation and trust to Egern.
profile['mitm'] = {'hostnames': {'includes': [], 'excludes': []}}

json_text = json.dumps(profile, ensure_ascii=False)
yaml = subprocess.run(['ruby', '-rjson', '-ryaml', '-e', 'STDOUT.write(YAML.dump(JSON.parse(STDIN.read)))'], input=json_text, text=True, capture_output=True, check=True).stdout
header = '''# Loon_custom.lcf → Egern；转换日期 2026-11-16（Asia/Taipei）。
# 导入后先向「节点订阅」添加订阅并选择地区节点；原文件不含任何订阅。
# 适用于支持 conditional / flatten / DNS SSID 的当前 Egern；尚未经过设备实测。
# 远程 .list 保留原来源并每 8 小时更新；内嵌规则需重新运行转换脚本更新。
# 28 个原 Loon 插件因资源 HTTP 403 尚未迁移；详见 README.md。
# 原自定义 GeoIP/ASN 下载也返回 403，未覆盖 Egern 自带数据库。
'''
(ROOT / 'Egern_custom.yaml').write_text(header + yaml)
plugins = []
for line in sections['Plugin']:
    fields = split_csv(line); opt = dict(x.split('=', 1) for x in fields[1:])
    plugins.append({'name': fields[0].split('/')[-1], 'url': fields[0], 'original_enabled': opt.get('enabled', 'true') == 'true', 'original_policy': opt.get('policy'), 'status': 'not-migrated', 'reason': 'Original Kelee endpoints returned HTTP 403; source content and Egern script compatibility could not be verified'})
report = {'date': '2026-11-16', 'timezone': 'Asia/Taipei',
          'source_url': 'https://github.com/hengruili2000/Loon_Rule/blob/main/Loon_custom.lcf',
          'source_blob_sha': 'a1a224ed582cb5b94ece3a420440f6ef8f533d2f',
          'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'policy_groups': len(groups), 'rules': len(rules), 'remote_rules': remote_report,
          'omitted_rules': skipped, 'normalized_cidrs': normalized, 'plugins': plugins,
          'unmapped_general_fields': ['sni-sniffing', 'dns-reject-mode', 'domain-reject-mode', 'udp-fallback-mode', 'interface-mode', 'test-timeout', 'resource-parser'],
          'unavailable_database_overrides': {k: general[k] for k in ['geoip-url', 'ipasn-url']}}
(ROOT / 'conversion-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'groups': len(groups), 'rules': len(rules), 'remote_sources': len(remote_report), 'unsupported_process_rules': len(skipped), 'unconverted_plugins': len(plugins), 'bytes': len((header + yaml).encode())}, ensure_ascii=False))
