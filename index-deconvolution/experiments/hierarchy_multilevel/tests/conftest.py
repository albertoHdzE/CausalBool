"""index-deconvolution and experiments first on sys.path (a sibling repository injected
by a venv .pth file ships its own top-level ``hierarchy``)."""
import sys
from pathlib import Path

_ID = str(Path(__file__).resolve().parents[3])
_EX = str(Path(__file__).resolve().parents[2])
_SRC = str(Path(__file__).resolve().parents[4] / "src")
for _p in (_SRC, _ID, _EX):
    while _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)
_m = sys.modules.get("hierarchy")
if _m is not None and not str(getattr(_m, "__file__", "")).startswith(_ID):
    del sys.modules["hierarchy"]
