"""Strict Loon/Surge text -> Egern rule-set conversion, without policy data."""
import ipaddress
import json
import re
from urllib.parse import unquote

TYPES = {'DOMAIN': 'domain', 'DOMAIN-SUFFIX': 'domain_suffix',
         'DOMAIN-KEYWORD': 'domain_keyword', 'DOMAIN-WILDCARD': 'domain_wildcard',
         'DOMAIN-REGEX': 'domain_regex', 'IP-CIDR': 'ip_cidr', 'IP-CIDR6': 'ip_cidr6',
         'IP-ASN': 'asn', 'GEOIP': 'geoip', 'USER-AGENT': 'user_agent',
         'URL-REGEX': 'url_regex', 'DEST-PORT': 'dest_port', 'PROTOCOL': 'protocol'}
IP_TYPES = {'ip_cidr', 'ip_cidr6', 'asn', 'geoip'}

def split_top(text):
    depth, start, result = 0, 0, []
    for pos, char in enumerate(text):
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
            if depth < 0:
                raise ValueError('Unbalanced logical rule')
        elif char == ',' and depth == 0:
            result.append(text[start:pos].strip()); start = pos + 1
    if depth:
        raise ValueError('Unbalanced logical rule')
    result.append(text[start:].strip())
    return result

def parse_rule(line, source='', omitted=None, normalized=None):
    line = line.strip()
    if ',' not in line:
        return {('domain_suffix' if line.startswith('.') else 'domain'): {'match': line.lstrip('.')}}
    typ, rest = line.split(',', 1)
    if typ in {'AND', 'OR', 'NOT'}:
        if not (rest.startswith('(') and rest.endswith(')')):
            raise ValueError(f'Invalid logical rule: {line}')
        children = []
        for item in split_top(rest[1:-1]):
            if not (item.startswith('(') and item.endswith(')')):
                raise ValueError(f'Invalid logical operand: {item}')
            child = parse_rule(item[1:-1], source, omitted, normalized)
            if child is None:
                raise ValueError('Cannot omit an unsupported operand from a logical rule')
            children.append(child)
        if typ == 'NOT':
            if len(children) != 1:
                raise ValueError('NOT requires one operand')
            return {'not': {'match': children[0]}}
        if len(children) < 2:
            raise ValueError(f'{typ} requires at least two operands')
        return {typ.lower(): {'match': children}}
    fields = [x.strip() for x in rest.split(',')]
    if typ == 'PROCESS-NAME':
        if omitted is not None:
            omitted.append({'source': source, 'rule': line, 'reason': 'Egern has no documented process-name matcher'})
        return None
    if typ not in TYPES or not fields[0]:
        raise ValueError(f'Unsupported rule in {source}: {line}')
    if any(x != 'no-resolve' for x in fields[1:]):
        raise ValueError(f'Unsupported rule options in {source}: {line}')
    kind, value = TYPES[typ], fields[0]
    if kind in {'ip_cidr', 'ip_cidr6'}:
        canonical = str(ipaddress.ip_network(value, strict=False))
        if canonical != value and normalized is not None:
            normalized.append({'source': source, 'from': value, 'to': canonical})
        value = canonical
    if kind == 'user_agent':
        value = unquote(value)
    data = {'match': value}
    if 'no-resolve' in fields[1:]:
        if kind not in IP_TYPES:
            raise ValueError(f'no-resolve on non-IP rule: {line}')
        data['no_resolve'] = True
    return {kind: data}

def glob_regex(pattern):
    return ''.join('.*' if c == '*' else '.' if c == '?' else re.escape(c) for c in pattern)

def domain_predicate(rule):
    """Compile domain-only boolean expressions to one equivalent regex.

    Avoids undocumented shapes for logical rule-set arrays. Every operand is
    anchored to the complete hostname; the original glob's '*' can span dots.
    """
    kind, data = next(iter(rule.items()))
    value = data['match']
    if kind == 'and':
        return ''.join('(?=(?:' + domain_predicate(c) + ')$)' for c in value) + '.*'
    if kind == 'or':
        return '(?:' + '|'.join(domain_predicate(c) for c in value) + ')'
    if kind == 'not':
        return '(?!(?:' + domain_predicate(value) + ')$).*'
    if kind == 'domain':
        return re.escape(value)
    if kind == 'domain_suffix':
        return r'(?:.*\.)?' + re.escape(value)
    if kind == 'domain_keyword':
        return '.*' + re.escape(value) + '.*'
    if kind == 'domain_wildcard':
        return glob_regex(value)
    raise ValueError(f'Cannot safely lower logical operand {kind} to a domain regex')

def convert_text(text, source):
    if '<html' in text[:300].lower() or not text.strip():
        raise ValueError(f'Empty or HTML upstream: {source}')
    result, omitted, normalized, lowering, resolves = {}, [], [], [], set()
    input_count, converted_count = 0, 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(('#', ';', '//')):
            continue
        input_count += 1
        rule = parse_rule(line, source, omitted, normalized)
        if rule is None:
            continue
        kind, data = next(iter(rule.items()))
        if kind in {'and', 'or', 'not'}:
            value = '(?i)^(?:' + domain_predicate(rule) + ')$'
            re.compile(value)
            lowering.append({'source_rule': line, 'domain_regex': value})
            kind = 'domain_regex'
        else:
            value = data['match']
        if kind in IP_TYPES:
            resolves.add(data.get('no_resolve', False))
        result.setdefault(kind + '_set', []).append(value)
        converted_count += 1
    if not converted_count:
        raise ValueError(f'No usable rules: {source}')
    if len(resolves) > 1:
        raise ValueError(f'Mixed IP no-resolve semantics cannot share one Egern rule set: {source}')
    if resolves:
        result = {'no_resolve': resolves.pop(), **result}
    return result, {'input_rules': input_count, 'converted_rules': converted_count,
                    'omitted_rules': omitted, 'normalized_cidrs': normalized,
                    'logical_lowering': lowering}

def dump_rule_set(data):
    """Emit a small YAML subset with quoted strings and no implicit YAML types."""
    lines = []
    for key, value in data.items():
        if isinstance(value, bool):
            lines.append(f'{key}: {str(value).lower()}')
        elif isinstance(value, list) and value and all(isinstance(x, str) for x in value):
            lines.append(key + ':')
            lines.extend('  - ' + json.dumps(x, ensure_ascii=False) for x in value)
        else:
            raise ValueError(f'Unexpected Egern rule-set field: {key}')
    return '\n'.join(lines) + '\n'
