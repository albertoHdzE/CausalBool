import copy
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("reference_recovery", Path(__file__).with_name("recover.py"))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def failed():
    return {"status": "reference_owner_failure", "accepted_validation": False,
            "wolfram_reference": {"status": "timeout"},
            "compression": {"status": "completed", "accepted_validation": True, "checked_output_sha256": "expected"},
            "dynamics": {"accepted_validation": True}}


@pytest.mark.parametrize("failure", ["process_failure", "malformed_payload", "completed", "not_run"])
def test_only_timeout_recovery_is_allowed(failure):
    row = failed()
    row["wolfram_reference"]["status"] = failure
    with pytest.raises(ValueError):
        r.eligible(row)


@pytest.mark.parametrize("part", ["compression", "dynamics"])
def test_failed_python_work_cannot_be_recovered_by_reference_only(part):
    row = failed()
    row[part]["accepted_validation"] = False
    with pytest.raises(ValueError):
        r.eligible(row)


@pytest.mark.parametrize("reference", [
    {"status": "timeout"},
    {"status": "completed", "output_sha256": "expected"},
    {"status": "completed", "process_status": "normal_exit", "output_sha256": "wrong"},
])
def test_normal_exit_and_matching_digest_are_mandatory(reference):
    row = failed()
    before = copy.deepcopy(row)
    with pytest.raises(ValueError):
        r.replacement(row, reference, {}, "amendment", "attempt")
    assert row == before


def test_reservation_preserves_already_spent_time():
    p = r.reserve({}, 13861, 100, 86400)
    assert p["used_seconds"] == 14321
    assert p["active_batch"] is True


def test_insufficient_budget_stops_before_calling_owner():
    with pytest.raises(ValueError):
        r.reserve({}, 86300, 0, 86400)


def test_original_failure_backup_preserves_exact_bytes(tmp_path):
    source, dest = tmp_path/"record.json", tmp_path/"archive/record.json"
    source.write_bytes(b'{"status": "timeout"}\n')
    digest = r.backup(source, dest)
    assert source.read_bytes() == dest.read_bytes()
    assert digest == r.original.sha(source)
    source.write_bytes(b'changed')
    with pytest.raises(ValueError):
        r.backup(source, dest)
