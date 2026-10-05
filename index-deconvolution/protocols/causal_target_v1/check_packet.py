"""Read-only preflight for the causal-target specification delegation."""
import hashlib
import json
import sys
from pathlib import Path

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[2]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main():
    manifest = read(PACKET / 'DELEGATION_MANIFEST.json')
    inputs = read(PACKET / 'INPUT_MANIFEST.json')
    contract = read(PACKET / 'contract.json')
    checks = {}
    packet_bad = [p for p, h in manifest['files'].items() if sha(ROOT / p) != h]
    input_bad = [p for p, h in inputs['required'].items() if sha(ROOT / p) != h]
    drift = {p: {'delegation_hash': h, 'current_hash': sha(ROOT / p)}
             for p, h in inputs['external_drift_warning_only'].items() if sha(ROOT / p) != h}
    checks['delegation_hashes'] = not packet_bad
    checks['required_input_hashes'] = not input_bad
    checks['run_identity'] = contract['run_id'] == 'causal-target-spec-v1-r1'
    checks['single_output_directory'] = contract['output'] == 'index-deconvolution/results/causal_target_v1/causal-target-spec-v1-r1'
    checks['specification_only'] = contract['phase'] == 'specification_and_identifiability' and contract['encoder_jobs'] == contract['benchmark_jobs'] == 0
    checks['four_access_regimes'] = contract['access_regimes'] == ['unlabelled_string', 'passive_labelled_trajectory', 'complete_labelled_transition_table', 'chosen_state_successor_queries']
    checks['four_fixed_witnesses'] = len(contract['witnesses']) == 4 and {w['id'] for w in contract['witnesses']} == {'W1', 'W2', 'W3', 'W4'}
    checks['tiny_witness_bound'] = contract['witness_max_bits'] == 3 and contract['witness_max_states_per_map'] == 8 and contract['random_examples'] is False
    checks['budget'] = contract['budget']['executor_cap_s'] + contract['budget']['supervisor_reserve_s'] == contract['budget']['total_s'] == 3600
    checks['draft_only'] = contract['max_drafts'] == 1 and contract['draft_execution_authorized'] is False
    checks['three_decisions'] = contract['decisions'] == ['DRAFT_QUERY_RECOVERY', 'DRAFT_ABSTRACTION_VALIDATION', 'NO_JUSTIFIED_IMPLEMENTATION']
    checks['fixed_deliverables_unique'] = len(contract['deliverables']) == len(set(contract['deliverables']))
    checks['historical_evidence_included'] = all(p in inputs['required'] for p in (
        'index-deconvolution/results/hierarchy_synthesis/supervision/representation-review-v1-r1-closure/REVIEW.md',
        'index-deconvolution/PROTOCOL_screen_identification.md',
        'index-deconvolution/PROTOCOL_order_discovery.md',
        'index-deconvolution/bitacora/screen_identification/02_verdict.md'))
    out = {'all_pass': all(checks.values()), 'checks': checks,
           'packet_mismatches': packet_bad, 'required_input_mismatches': input_bad,
           'external_drift_warnings': drift,
           'required_inputs': len(inputs['required']), 'packet_files': len(manifest['files']),
           'note': 'This checks packet integrity, not scientific correctness or phase completion. No scientific functions are executed.'}
    print(json.dumps(out, indent=2))
    return 0 if out['all_pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
