import json
import pytest
from hierarchy import cli, validation as V
from hierarchy.tests.test_validation import built, run, _rows, _write, RID


def test_missing_archive_is_detected_but_verify_raises_before_writing_status(run):
    row = next(r for r in _rows(run) if r['method'] == 'hid_full')
    (run / row['archive_path']).unlink()
    val, _ = V.validate_run(RID, ['confirmation', 'transfer'])
    assert not val['engineering_valid']
    assert any('archive file missing' in s for s in val['invalid'])
    with pytest.raises(FileNotFoundError):
        cli.main(['verify', '--run-id', RID])


def test_duplicate_in_individual_row_file_is_not_detected(run):
    row = _rows(run)[0]
    p = run / 'rows' / (row['case_id'] + '.json')
    records = json.loads(p.read_text())
    p.write_text(json.dumps(records + [records[0]]))
    val, _ = V.validate_run(RID, ['confirmation', 'transfer'])
    assert val['engineering_valid'] and val['complete']


def test_unexpected_split_row_is_filtered_before_validation(run):
    rows = _rows(run)
    extra = dict(rows[0], split='undeclared', case_id='undeclared-F01-64-1000-base')
    with (run / 'cases.jsonl').open('a') as stream:
        stream.write(json.dumps(extra) + '\n')
    val, _ = V.validate_run(RID, ['confirmation', 'transfer'])
    assert val['engineering_valid'] and val['complete'] and not val['unknown']
