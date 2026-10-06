"""Reproduce the three audit findings on copies. Never changes the original run.

Usage: repository venv/bin/python review_probes.py /tmp/fresh-review-directory
The audit's semantic-only bypass is intentional; the original seal is copied, not edited.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[2]
    run = root / 'task-compaction-v1-r1'
    out = Path(sys.argv[1]).resolve()
    out.mkdir(exist_ok=False)
    records = []
    for name in ('summary_empty', 'missing_table', 'malformed_records'):
        prod = out / name
        shutil.copytree(run / 'production', prod)
        if name == 'summary_empty':
            path = prod / 'summary.json'
            value = json.loads(path.read_text())
            value['cells'] = []
            path.write_text(json.dumps(value))
        elif name == 'missing_table':
            (prod / 'tables/M1.json').unlink()
        else:
            (prod / 'candidates/cell_00.jsonl').write_text('{broken json\n')
        target = out / (name + '_audit')
        proc = subprocess.run(
            [sys.executable, str(run / 'src/audit.py'), str(prod), str(target), '--bypass-integrity'],
            capture_output=True, text=True,
        )
        (out / (name + '.log')).write_text(proc.stdout + proc.stderr)
        result_file = target / 'audit.json'
        result = json.loads(result_file.read_text()) if result_file.exists() else None
        records.append({'probe': name, 'exit_code': proc.returncode, 'audit': result})
    manifest = json.loads((run / 'output_manifest.json').read_text())['sha256']
    mismatches = [p for p, v in manifest.items()
                  if hashlib.sha256((run / p).read_bytes()).hexdigest() != v['sha256']
                  or (run / p).stat().st_size != v['bytes']]
    report = {'probes': records, 'original_manifest_count': len(manifest), 'original_mismatches': mismatches}
    (out / 'review_probes.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'probes': [(r['probe'], r['exit_code'], None if r['audit'] is None
                                 else r['audit']['status']) for r in records],
                      'original_mismatches': mismatches}))


if __name__ == '__main__':
    main()
