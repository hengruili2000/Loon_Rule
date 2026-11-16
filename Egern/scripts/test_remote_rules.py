#!/usr/bin/env python3
"""Regression checks for daily conversion, exclusions and safe publication."""
import fnmatch
import hashlib
import itertools
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
from rule_converter import convert_text, dump_rule_set, parse_rule
from sync_remote_rules import sync, ROOT

class ConversionTests(unittest.TestCase):
    def test_basic_fields_and_omissions(self):
        data, meta = convert_text('DOMAIN,a.example\nIP-CIDR,28.0.0.1/8,no-resolve\nIP-ASN,13335,no-resolve\nUSER-AGENT,Hello%20World*\nPROCESS-NAME,example', 'test')
        self.assertEqual(data, {'no_resolve': True, 'domain_set': ['a.example'],
                              'ip_cidr_set': ['28.0.0.0/8'], 'asn_set': ['13335'],
                              'user_agent_set': ['Hello World*']})
        self.assertEqual(meta['input_rules'], meta['converted_rules'] + len(meta['omitted_rules']))
        self.assertEqual(len(meta['omitted_rules']), 1)
        self.assertIn('"13335"', dump_rule_set(data))

    def test_unknown_or_mixed_semantics_fail(self):
        for text in ['BOGUS,a.example', '<html>Error</html>', '',
                     'IP-CIDR,1.1.1.0/24\nIP-CIDR,2.2.2.0/24,no-resolve',
                     'AND,((DOMAIN,a.example),(PROCESS-NAME,foo))',
                     'AND,((DOMAIN,a.example),(IP-CIDR,10.0.0.0/8))']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                convert_text(text, 'test')

    def test_domain_only_logical_lowering(self):
        # Compare the produced regex against original glob AND/NOT semantics,
        # including multi-label prefixes, multi-label regions and case changes.
        source = 'AND,((DOMAIN-WILDCARD,?*.dkr.ecr.?*.amazonaws.com),(NOT,((DOMAIN-WILDCARD,?*.dkr.ecr.*.*.amazonaws.com))))'
        data, _ = convert_text(source, 'test')
        regex = re.compile(data['domain_regex_set'][0])
        cases = ['123.dkr.ecr.us-east-1.amazonaws.com',
                 '123.dkr.ecr.cn-north-1.amazonaws.com.cn',
                 '123.dkr.ecr.us.east.amazonaws.com', 'dkr.ecr.us-east-1.amazonaws.com']
        for prefix, region, suffix in itertools.product(['', 'a', '123', 'a.b'], ['', 'x', 'us-east-1', 'a.b'], ['amazonaws.com', 'amazonaws.com.cn']):
            cases.append(f'{prefix}.dkr.ecr.{region}.{suffix}')
        cases += [x.upper() for x in cases]
        for hostname in cases:
            expected = (fnmatch.fnmatchcase(hostname.lower(), '?*.dkr.ecr.?*.amazonaws.com')
                        and not fnmatch.fnmatchcase(hostname.lower(), '?*.dkr.ecr.*.*.amazonaws.com'))
            self.assertEqual(bool(regex.fullmatch(hostname)), expected, hostname)
        generic, _ = convert_text('OR,((DOMAIN,a.example),(AND,((DOMAIN-SUFFIX,example.net),(NOT,((DOMAIN,b.example.net))))))', 'test')
        check = re.compile(generic['domain_regex_set'][0])
        for host, expected in [('a.example', True), ('example.net', True), ('a.example.net', True), ('b.example.net', False), ('fakeexample.net', False)]:
            self.assertEqual(bool(check.fullmatch(host)), expected)

    def test_failed_sync_keeps_every_published_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'sources').mkdir(); (root / 'rules').mkdir()
            specs = [{'id': 'A', 'source_url': 'https://example/A'}, {'id': 'B', 'source_url': 'https://example/B'}]
            (root / 'sources/remote-rules.json').write_text(json.dumps(specs))
            (root / 'rules/A.yaml').write_text('last known good')
            def bad(url):
                return 'DOMAIN,new.example' if url.endswith('/A') else 'UNSUPPORTED,foo'
            with self.assertRaises(ValueError):
                sync(root, bad)
            self.assertEqual((root / 'rules/A.yaml').read_text(), 'last known good')
            self.assertFalse((root / 'rules/B.yaml').exists())
            self.assertFalse((root / 'rules/sync-report.json').exists())

    def test_published_artifacts_and_profile_references(self):
        report = json.loads((ROOT / 'rules/sync-report.json').read_text())
        specs = json.loads((ROOT / 'sources/remote-rules.json').read_text())
        self.assertEqual(report['sync_interval_seconds'], 86400)
        self.assertEqual({x['id'] for x in report['sources']}, {x['id'] for x in specs})
        profile = (ROOT / 'Egern_custom.yaml').read_text()
        for source in report['sources']:
            content = (ROOT / source['output']).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), source['output_sha256'])
            self.assertEqual(source['input_rules'], source['converted_rules'] + len(source['omitted_rules']))
            self.assertGreater(source['converted_rules'], 0)
            self.assertIn('/Egern/rules/' + source['id'] + '.yaml', profile)
        self.assertNotIn('native-snapshot', (ROOT / 'conversion-report.json').read_text())

if __name__ == '__main__':
    unittest.main()
