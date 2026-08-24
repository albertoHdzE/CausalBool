"""AUDIT01/T2.0c — vendor parity gate.

The vendored engine copies in ``imp-prices/vendor/`` must remain byte-identical to the
canonical sources in ``index-deconvolution/src/``. Sync was previously manual discipline
(commit 4d9a959: "both copies"); this test makes drift loud.

Skip semantics mirror notebook-parity convention: if the sibling tree is absent, SKIP
with a loud reason -- never a silent pass.
"""
from pathlib import Path

import pytest

VENDOR = Path(__file__).resolve().parents[1] / "vendor"
SIBLING = Path(__file__).resolve().parents[2] / "index-deconvolution" / "src"

PARITY_FILES = ["causalbool.py", "deconvolution.py"]


def _md5(p: Path) -> str:
    import hashlib

    return hashlib.md5(p.read_bytes()).hexdigest()


@pytest.mark.parametrize("name", PARITY_FILES)
def test_vendor_matches_canonical(name):
    v = VENDOR / name
    c = SIBLING / name
    assert v.exists(), f"vendored copy missing: {v}"
    if not c.exists():
        pytest.skip(f"LOUD SKIP: canonical sibling absent at {c} -- parity unverifiable")
    assert _md5(v) == _md5(c), (
        f"VENDOR DRIFT: vendor/{name} differs from {c}. "
        "Re-copy from canonical (both copies) or justify divergence in FINDINGS."
    )
