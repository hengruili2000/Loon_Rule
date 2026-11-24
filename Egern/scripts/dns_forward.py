"""Project the profile's domain routing rules into Egern DNS Forward rules."""

import json
from urllib.parse import urlsplit


def dns_transport_rules(dns):
    for upstream, policy in [('DNSPod', 'DIRECT'), ('RemoteDNS', '默认代理')]:
        for endpoint in dns['upstreams'][upstream]:
            host = urlsplit(endpoint).hostname
            match = {'domain': {'match': host}}
            yield {'and': {'match': [match, {'dest_port': {'match': '443'}}],
                           'policy': policy, 'name': f'{upstream} DoH'}}


def dns_forward(dns, rules, groups):
    """Use each policy group's first choice until a conditional or leaf is reached."""
    defaults = {
        group['select']['name']: group['select']['policies'][0]
        for group in groups if 'select' in group and group['select'].get('policies')
    }

    def upstream_for(policy):
        visited = set()
        while policy in defaults:
            if policy in visited:
                raise ValueError(f'Circular DNS policy default: {policy}')
            visited.add(policy)
            policy = defaults[policy]
        return {'DIRECT': 'DNSPod', 'REJECT': 'reject'}.get(policy, 'RemoteDNS')

    forward = list(dns['forward'])
    for rule in rules:
        kind, entry = next(iter(rule.items()))
        upstream = upstream_for(entry['policy'])
        if kind == 'default':
            fallback = {'domain_wildcard': {'match': '*', 'value': upstream}}
        elif kind == 'rule_set':
            forward.append({'proxy_rule_set': {
                'match': entry['match'], 'update_interval': entry['update_interval'], 'value': upstream}})
        elif kind in {'domain', 'domain_suffix', 'domain_keyword', 'domain_regex', 'domain_wildcard'}:
            forward.append({kind: {'match': entry['match'], 'value': upstream}})
    return [*forward, fallback]


def render_dns_settings(settings_text, generated_rules):
    marker = '  # @generated-dns-forward\n'
    before, after = settings_text.split(marker)
    lines = ['  # 以下规则由流量分流规则生成。']
    for rule in generated_rules:
        kind, data = next(iter(rule.items()))
        lines.append(f'  - {kind}:')
        for key, value in data.items():
            lines.append(f'      {key}: {json.dumps(value, ensure_ascii=False)}')
    return before.rstrip() + '\n' + '\n'.join(lines) + '\n\n' + after
