"""Independent review probes and per-program export acceptance; not production code.

Run from luminal-challenge:
  python3 results/direct_index_v1/lead_review/audit.py probes
  python3 results/direct_index_v1/lead_review/audit.py corpus
"""
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import statistics
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probes():
    sys.path[:0] = [str(ROOT), str(ROOT / '.reference')]
    import direct_compiler as compiler
    import direct_constraints as constraints
    import schema_index as schema
    from tests_direct.test_optimizer import JOINT_NEEDED
    from tests_direct.test_constraints import JointQueryTests

    def unchanged(self, cube):
        return dict(self.times), dict(self.addresses)

    with patch.object(constraints.JointQuery, 'decode', unchanged):
        _, report = compiler.compile_with_report(JOINT_NEEDED)
    stream = io.StringIO()
    with patch.object(constraints.JointQuery, 'expression', side_effect=constraints.Infeasible):
        result = unittest.TextTestRunner(stream=stream).run(unittest.TestSuite([
            JointQueryTests('test_solver_agrees_with_exhaustive_enumeration')
        ]))
    leaf = schema.Leaf(tuple(schema.Cube(4, i, 0) for i in range(16)))
    answer = schema.solve(leaf, 4, schema.Budget(max_cover=1, seconds=10))
    payload = {
        'target_violation': report['optimisation'],
        'always_infeasible_mutation_test_passed': result.wasSuccessful(),
        'mutation_test_log': stream.getvalue(),
        'oversized_atomic_cover': {'size': len(leaf.cubes), 'cap': 1, 'status': answer.status},
    }
    (HERE / 'probes.json').write_text(json.dumps(payload, indent=2) + '\n')
    print(json.dumps(payload, indent=2))


WORKER = '''
import json, sys
sys.path.insert(0, sys.argv[1])
import machine
def prohibited(*args, **kwargs):
    raise AssertionError("serial_compile called by direct export")
machine.serial_compile = prohibited
import compiler
program = machine.load_program(sys.argv[2])
before = json.dumps(program, sort_keys=True)
compiled, report = compiler.compile_with_report(program)
assert json.dumps(program, sort_keys=True) == before
machine.check_compilation(program, compiled)
for case in program["cases"]:
    machine.check_case(program, compiled, case)
errors = report["optimisation"].get("validation_errors", [])
assert not errors, errors
assert not any(name.split(".")[0] in
    {"common", "compilers", "index_query", "repertoire_program", "direct_compiler"}
    for name in sys.modules)
print(json.dumps({"cases":len(program["cases"]), "report":report,
                  "compiler_path":compiler.__file__}))
'''


def corpus():
    paths = sorted((HERE / 'verification' / 'corpus').glob('*.json'))
    assert len(paths) == 142, len(paths)
    exported = ROOT / '.build' / 'direct_index' / 'compiler.py'
    reference = ROOT / '.reference' / 'machine.py'
    payload = {'export_sha256': digest(exported), 'machine_sha256': digest(reference),
               'timeout_seconds': 20, 'python': sys.version, 'runs': []}
    with tempfile.TemporaryDirectory(prefix='luminal-lead-') as directory:
        neutral = Path(directory)
        shutil.copyfile(exported, neutral / 'compiler.py')
        shutil.copyfile(reference, neutral / 'machine.py')
        for path in paths:
            started = time.perf_counter()
            entry = {'program': path.name, 'sha256': digest(path)}
            try:
                result = subprocess.run(
                    [sys.executable, '-I', '-S', '-c', WORKER, directory, str(path)],
                    cwd=directory, capture_output=True, text=True, timeout=20,
                )
                entry.update(exit_code=result.returncode, stderr=result.stderr,
                             status='PASS' if result.returncode == 0 else 'FAIL')
                if result.returncode == 0:
                    entry['result'] = json.loads(result.stdout)
                else:
                    entry['stdout'] = result.stdout
            except subprocess.TimeoutExpired:
                entry.update(status='FAIL', error='process timeout')
            entry['process_seconds'] = time.perf_counter() - started
            payload['runs'].append(entry)
            (HERE / 'isolated_corpus.json').write_text(json.dumps(payload, indent=2) + '\n')
        payload['status'] = 'PASS' if all(r['status'] == 'PASS' for r in payload['runs']) else 'FAIL'
        (HERE / 'isolated_corpus.json').write_text(json.dumps(payload, indent=2) + '\n')
    print(json.dumps({'status': payload['status'], 'programs': len(paths),
                      'failures': [r['program'] for r in payload['runs'] if r['status'] != 'PASS']}))
    return int(payload['status'] != 'PASS')


def summarize():
    protected = {
        'common.py': '5b3ae21c5a6c3a73380069ac685fdde7d3cee2fb7bc7704b610d5e24b0056fab',
        'reference.json': 'ef6042ce4acc2cfe531d974afb666b6ad40656e15828ad5f814d6cbb338875f0',
        'results/comparison.json': 'f070a6691c57c78395e67f4054928cddd753b5aa0265fe1386bb7da27f9cc535',
        '../GOVERNANCE/GLOSSARY.md': 'c3d0402150fefcb1e72339ef986e9f124754c2370c0c55f3c741b311795b2b3e',
    }
    for name, expected in protected.items():
        assert digest(ROOT / name) == expected, name
    manifest = json.loads((ROOT / 'reference.json').read_text())
    for name, expected in manifest['sha256'].items():
        assert digest(ROOT / '.reference' / name) == expected, name
    verification = json.loads((HERE / 'verification/summary.json').read_text())
    for name, expected in verification['source_sha256'].items():
        assert digest(ROOT / name) == expected, name
    comparison = json.loads((HERE / 'comparison/runs.json').read_text())
    assert not comparison['failures']
    assert len(comparison['runs']) == 72
    assert digest(ROOT / '.build/direct_index/compiler.py') == comparison['export_sha256']
    recomputed = {}
    for arm in ('serial', 'classical', 'direct_index'):
        scores = []
        for repeat in range(3):
            by_arm = {r['program']: r for r in comparison['runs']
                      if r['arm'] == arm and r['repeat'] == repeat}
            baseline = {r['program']: r for r in comparison['runs']
                        if r['arm'] == 'serial' and r['repeat'] == repeat}
            assert len(by_arm) == len(baseline) == 8
            score = math.exp(statistics.fmean(
                math.log((baseline[p]['cycles'] * baseline[p]['scratch']) /
                         (r['cycles'] * r['scratch'])) / 2
                for p, r in by_arm.items()))
            if arm == 'direct_index':
                assert score > 1.0
            if arm == 'classical':
                assert math.isclose(score, 1.9013791212645499, rel_tol=1e-14)
            scores.append(score)
        recomputed[arm] = scores
    isolated = json.loads((HERE / 'isolated_corpus.json').read_text())
    assert isolated['status'] == 'PASS' and len(isolated['runs']) == 142
    payload = {'protected_sha256': protected, 'reference_commit': manifest['commit'],
               'scores_recomputed': recomputed, 'comparison_summary': comparison['summary'],
               'isolated_corpus_programs': len(isolated['runs']),
               'isolated_corpus_max_seconds': max(r['process_seconds'] for r in isolated['runs']),
               'evidence_checks': 'PASS', 'release_verdict': 'CHANGES_REQUIRED'}
    (HERE / 'audit_summary.json').write_text(json.dumps(payload, indent=2) + '\n')
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    if sys.argv[1:] == ['probes']:
        probes()
    elif sys.argv[1:] == ['corpus']:
        sys.exit(corpus())
    elif sys.argv[1:] == ['summary']:
        summarize()
    else:
        raise SystemExit('expected probes, corpus, or summary')
