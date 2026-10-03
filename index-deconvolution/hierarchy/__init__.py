"""HID-v1: hierarchical index descriptions -- a lossless archive format, its
independent decoder, a bounded deterministic search, baselines and the frozen
benchmark (PROTOCOL_hierarchical_index_generalization.md).

The venv's .pth files inject sibling repositories; one of them ships a module
named ``hierarchy``. This regular package must therefore be found through
PYTHONPATH=index-deconvolution (which precedes site-packages); the assertion
below refuses to run if a different file is being imported under this name.
"""
from pathlib import Path as _Path

if _Path(__file__).resolve().parent.parent.name != "index-deconvolution":
    raise ImportError(f"hierarchy resolved to {__file__}, not index-deconvolution/hierarchy")

__all__ = ["encode_literal", "serialize_model", "decode_archive", "infer",
           "encode_baseline"]


def __getattr__(name):
    if name in ("encode_literal", "serialize_model"):
        from . import wire
        return getattr(wire, name)
    if name == "decode_archive":
        from .decode import decode_archive
        return decode_archive
    if name == "encode_baseline":
        from .baselines import encode_baseline
        return encode_baseline
    if name == "infer":
        from .infer import infer
        return infer
    raise AttributeError(name)
