"""Attach literal excerpts from retrieved sources and verify research drafts."""
import json
from pathlib import Path
from html.parser import HTMLParser
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / 'docs/evidence'
S = '<local path>'
L = ROOT / 'docs/c_sources.json'

class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        if data.strip():
            self.parts.append(data.strip())

# Select actual retrieved lines by literal substring, not model-written quotes.
SPECS = {
 1: ('carraway_web', 'Exact requested GitHub repository', ['GitHub - Carraway-and-Gatsby/cardiac-simulator']),
 2: ('carraway_api', 'GitHub repository metadata', ['"full_name":', '"default_branch":', '"spdx_id":']),
 3: ('carraway_readme_main', 'CardioLab README', ['An interactive educational', '**This is an educational', '| Circulation |']),
 4: ('semgen_readme', 'SemGen README and license', ['permitted for non-commercial purposes', 'JxBrowser as part of SemGen', 'Each composite annotation consists']),
 5: ('circadapt_license', 'CircAdapt framework current EULA', ['Licensor grant to User', 'Developer User shall not', 'Any Improvements shall be']),
 6: ('opencor_license', 'OpenCOR repository GPLv3 license', ['GNU GENERAL PUBLIC LICENSE', 'Version 3, 29 June 2007']),
 8: ('cellml_model_license', 'Physiome cardiovascular model license and citation', ['Zero dimensional (lumped parameter)', 'Creative Commons Attribution 3.0']),
 9: ('cellml_environments', 'CellML modeling environments directory', ['Apache v2.0']),
 10: ('carraway_license', 'CardioLab MIT license on main', ['MIT License', 'Permission is hereby granted']),
 11: ('carraway_notices', 'CardioLab third-party notices', ['third-party dependencies', '4.0 International (CC BY 4.0)', 'MIT does not relicense']),
 12: ('carraway_physiology', 'CardioLab model equations and scientific scope', ['The eight state variables', 'Every numerical default', 'Simultaneous forward AV', 'external waveform dataset']),
 13: ('carraway_head', 'CardioLab main commit metadata', ['"sha": "b3f437403e709f11099f50b38272f77ded5ea9b5"']),
 14: ('opencor_readme', 'HTTP 404 for guessed OpenCOR README.md path', ['404: Not Found']),
 15: ('opencor_api', 'OpenCOR repository metadata', ['"spdx_id": "GPL-3.0"']),
 16: ('cellml_spec', 'CellML 2.0 normative specification', ['Tuples differing by a multiplying factor', 'variable unit reduction', 'The variable equivalence network MUST NOT contain any cycles.']),
 17: ('semgen_protocol', 'SemGen annotation protocol', ['assignments are not guaranteed', 'sources, sinks and mediating entities']),
 18: ('semsim_article', 'Neal et al. 2015 semantic cardiomyocyte composition', ['While we have not yet performed formal tests', 'These kinds of post-merge adjustments', 'models represent the same physical process but directionality', 'which describes a biosimulation model in terms of its biological meaning']),
 19: ('smith_pubmed', 'Smith et al. 2004 minimal haemodynamic model abstract', ['This paper develops a model']),
 20: ('pulse_license', 'Pulse stable branch Apache 2.0 license', ['Apache License', 'Version 2.0, January 2004']),
 21: ('pulse_notice', 'Pulse stable branch copyright and dependency notice', ['Distributed under the Apache License', 'This product uses']),
 22: ('pulse_cardiovascular', 'Pulse cardiovascular methodology', ['The cardiovascular system is a closed-loop', 'The atria are not included', 'The heart compliance is calculated']),
 23: ('opencor_licensing', 'OpenCOR official licensing page', ['GPL v3.0']),
 24: ('opencor_readme_rst', 'OpenCOR accessible README.rst', ['modelling environment']),
 25: ('zero_d_review', 'Shi et al. 2011 review of 0D and 1D blood flow models', ['laws of mass conservation', 'Zero dimensional, or lumped parameter, models assume', 'parameter identification for the four-element']),
 26: ('contractility_pubmed', 'Burkhoff and Tyberg 1993 theoretical LV dysfunction analysis', ['One of the most important consequences']),
 27: ('carraway_engine_pinned', 'CardioLab numerical engine at pinned commit', ['const index =', 'export function simulate', 'Every edge has one signed flow', 'export function evaluateState', 'export function volumeDerivative']),
 28: ('carraway_license_pinned', 'CardioLab MIT license at pinned commit', ['MIT License', 'Permission is hereby granted', 'The above copyright notice']),
 29: ('circadapt_verification', 'CircAdapt component verification index', ['Verification of ArtVen', 'Verification of Valve']),
}

def run(args):
    result = subprocess.run([sys.executable, S, '--ledger', str(L), *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout

ledger = json.loads(L.read_text())
by_id = {s['id']: s for s in ledger['sources']}
quotes = []
for source_id, (name, title, needles) in SPECS.items():
    raw = P / ('c_' + name + '.txt')
    text = raw.read_text()
    if source_id in {2, 13, 15}:
        text = json.dumps(json.loads(text), indent=2)
        evidence = P / ('c_' + name + '_plain.txt')
        evidence.write_text(text)
    elif '<html' in text.lower() or '<!doctype' in text.lower():
        parsed = Text()
        parsed.feed(text)
        text = '\n'.join(parsed.parts)
        evidence = P / ('c_' + name + '_plain.txt')
        evidence.write_text(text)
    else:
        evidence = raw
    run(['add', by_id[source_id]['url'], '--title', title])
    for needle in needles:
        matches = [line for line in text.splitlines() if needle in line]
        if not matches:
            raise ValueError(f'No evidence match: source {source_id}: {needle}')
        quote = matches[0].strip()
        lines = text.splitlines()
        index = lines.index(matches[0])
        while len(quote.split()) < 4 and index + 1 < len(lines):
            index += 1
            quote += '\n' + lines[index]
        run(['quote', str(source_id), '--text', quote, '--from', str(evidence)])
        quotes.append({'source_id': source_id, 'evidence_file': str(evidence.relative_to(ROOT)), 'quote': quote})
(P / 'c_quotes.json').write_text(json.dumps(quotes, indent=2) + '\n')
for filename in ['ecosystem.md', 'verification_protocol.md']:
    draft = ROOT / 'docs' / filename
    print(run(['render', '--replace-in', str(draft)]))
    print(run(['verify', str(draft), '--evidence']))
print(f'Attached {len(quotes)} literal excerpts from {len(SPECS)} cited sources.')
