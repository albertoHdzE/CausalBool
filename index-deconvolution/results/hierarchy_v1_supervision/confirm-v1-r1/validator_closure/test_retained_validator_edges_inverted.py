"""The three reproductions of test_retained_validator_edges.py (bitacora 37 §4),
same damage, assertions inverted to the corrected behaviour. Expected: 3 failures
against the frozen confirm-v1-r1 sources, 3 passes against the patched sources."""
# ruff: noqa: F811  (pytest fixtures imported by name, as in the retained file)
import json

from hierarchy import cli, validation as V
from hierarchy.tests.test_validation import built, run, _rows, RID  # noqa: F401


def test_missing_archive_reaches_a_structured_invalid_verification(run):
    row = next(r for r in _rows(run) if r['method'] == 'hid_full')
    (run / row['archive_path']).unlink()
    val, _ = V.validate_run(RID, ['confirmation', 'transfer'])
    assert not val['engineering_valid']
    assert any('archive file missing' in s for s in val['invalid'])
    assert cli.main(['verify', '--run-id', RID]) == cli.EXIT_INVALID
    v = json.loads((run / 'verification.json').read_text())
    assert v['exit_code'] == cli.EXIT_INVALID and v['engineering_status'] == 'invalid'
    assert any('archive file missing' in s for s in v['invalid_reasons'])


def test_duplicate_in_individual_row_file_is_detected(run):
    row = _rows(run)[0]
    p = run / 'rows' / (row['case_id'] + '.json')
    records = json.loads(p.read_text())
    p.write_text(json.dumps(records + [records[0]]))
    val, _ = V.validate_run(RID, ['confirmation', 'transfer'])
    assert not val['engineering_valid']


def test_unexpected_split_row_is_validated_not_filtered(run):
    rows = _rows(run)
    extra = dict(rows[0], split='undeclared', case_id='undeclared-F01-64-1000-base')
    with (run / 'cases.jsonl').open('a') as stream:
        stream.write(json.dumps(extra) + '\n')
    val, _ = V.validate_run(RID, ['confirmation', 'transfer'])
    assert not val['engineering_valid'] and val['unknown']
