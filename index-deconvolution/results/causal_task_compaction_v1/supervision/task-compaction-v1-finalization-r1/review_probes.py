"""Reproduce the two finalization findings on disposable copies; never writes inputs.

Run from any directory: venv/bin/python review_probes.py <fresh scratch directory>.
The five cases are subcases of R1 (fixture) and R2 (seal coverage).
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parents[2]
REPO = BASE.parents[2]
FIN = BASE / 'finalization/task-compaction-v1-finalization-r1'
CASES = (
    ('fixture_id_type', 'fixtures/FX1_identity.json', True),
    ('fixture_id_wrong_string', 'fixtures/FX1_identity.json', True),
    ('fixture_coarsening_null', 'fixtures/FX1_identity.json', True),
    ('empty_seal', 'seal.json', False),
    ('one_seal_entry_missing', 'seal.json', False),
)


def main(dest):
    dest.mkdir(parents=True, exist_ok=False)
    results = []
    for name, rel, bypass in CASES:
        prod = dest / name / 'production'
        shutil.copytree(BASE / 'task-compaction-v1-r1/production', prod)
        p = prod / rel
        d = json.loads(p.read_text())
        if name == 'fixture_id_type':
            d['fixture_id'] = 123
        elif name == 'fixture_id_wrong_string':
            d['fixture_id'] = 'NOT_FX1'
        elif name == 'fixture_coarsening_null':
            d['coarsening'] = None
        elif name == 'empty_seal':
            d['sha256'] = {}
        else:
            del d['sha256']['fixtures/FX1_identity.json']
        p.write_text(json.dumps(d))
        out = dest / name / 'audit'
        command = [str(REPO / 'venv/bin/python'), str(FIN / 'src/audit_r3.py'),
                   str(prod), str(out), '--inputs-root', str(FIN / 'historical_inputs')]
        if bypass:
            command.append('--bypass-integrity')
        run = subprocess.run(command, text=True, capture_output=True)
        (dest / name / 'stdout.log').write_text(run.stdout)
        (dest / name / 'stderr.log').write_text(run.stderr)
        report = json.loads((out / 'audit.json').read_text()) if (out / 'audit.json').exists() else {}
        results.append({'case': name, 'bypass_integrity': bypass, 'exit_code': run.returncode,
                        'status': report.get('status'), 'invalid': report.get('invalid'),
                        'missing': report.get('missing'), 'integrity': report.get('integrity'),
                        'fixture_FX1': report.get('fixture_FX1'),
                        'false_acceptance_reproduced': run.returncode == 0 and
                        report.get('status') == 'VALID_COMPLETE'})
    result = {'audit_r3_sha256': hashlib.sha256((FIN / 'src/audit_r3.py').read_bytes()).hexdigest(),
              'cases': results}
    (dest / 'probe_results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if all(r['false_acceptance_reproduced'] for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main(Path(sys.argv[1]).resolve()))
