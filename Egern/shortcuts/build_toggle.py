#!/usr/bin/env python3
"""Build a one-action VPN toggle; choose the iPhone's Egern VPN on import."""
from pathlib import Path
import plistlib

root = Path(__file__).resolve().parent
workflow = {
    'WFWorkflowName': 'Egern VPN 开关',
    'WFWorkflowClientVersion': '1',
    'WFWorkflowMinimumClientVersion': 900,
    'WFWorkflowMinimumClientVersionString': '900',
    'WFWorkflowIcon': {'WFWorkflowIconStartColor': 4282601983,
                       'WFWorkflowIconGlyphNumber': 59511},
    'WFWorkflowTypes': ['NCWidget'],
    'WFWorkflowInputContentItemClasses': [],
    'WFWorkflowHasOutputFallback': False,
    'WFWorkflowHasShortcutInputVariables': False,
    'WFWorkflowImportQuestions': [{
        'ActionIndex': 0,
        'Category': 'Parameter',
        'ParameterKey': 'WFVPN',
        'Text': '请选择这台 iPhone 上 Egern 创建的 VPN 配置。',
        'DefaultValue': '',
    }],
    'WFWorkflowActions': [{
        'WFWorkflowActionIdentifier': 'is.workflow.actions.vpn.set',
        'WFWorkflowActionParameters': {'WFVPNOperation': 'Toggle'},
    }],
}
source = root / 'Egern-VPN-Toggle.unsigned.plist'
source.write_bytes(plistlib.dumps(workflow, fmt=plistlib.FMT_XML, sort_keys=False))
assert plistlib.loads(source.read_bytes()) == workflow
binary = root / 'Egern-VPN-Toggle.unsigned.shortcut'
binary.write_bytes(plistlib.dumps(workflow, fmt=plistlib.FMT_BINARY, sort_keys=False))
print(source)
