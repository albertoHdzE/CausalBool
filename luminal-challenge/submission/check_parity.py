"""Accept the flattened ``compiler.py`` only if it computes what the accepted export computes.

Two checks, each printing its denominator and refusing on an empty corpus:

1. Parity under a deterministic clock. Every ``time`` reading is replaced by a
   counter that advances one fixed tick per call, installed before either
   compiler is imported, so the 0.1 s search budget becomes a fixed number of
   clock reads. Both compilers then run the same programs in the same order in
   fresh processes, and their JSON outputs must be identical, byte for byte.
   A counted clock can exhaust a construction query's own time budget on the
   largest stress programs; that error then has to be identical as well.
2. Validity under the real clock. Every output of the flattened compiler is
   checked by the pinned machine (``check_compilation`` on every case).

Programs: the eight public programs plus the 142-program acceptance corpus and
its additional seeds from ``tests_direct/generate_programs.py``.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REFERENCE = ROOT / ".reference"
ACCEPTED = ROOT / "results/phase2_structural_encoding/third_round_20260925_resume/exports/C1/compiler.py"
FLAT = HERE / "compiler.py"

RUNNER = r'''
import json, sys, time
tick = float(sys.argv[3])
if tick > 0:
    state = [0]
    def fake():
        state[0] += 1
        return state[0] * tick
    time.perf_counter = time.monotonic = time.time = time.process_time = fake
sys.path[:0] = [sys.argv[1], sys.argv[4]]
import compiler, machine
out = []
for program in json.load(open(sys.argv[2])):
    try:
        result = compiler.compile_program(program)
        if tick == 0:
            machine.check_compilation(program, result)
        out.append(json.dumps(result, sort_keys=True))
    except Exception as exc:
        out.append(f"ERROR {type(exc).__name__}: {exc}")
json.dump(out, sys.stdout)
'''


def programs() -> list:
    sys.path[:0] = [str(ROOT), str(REFERENCE)]
    import machine
    from tests_direct import generate_programs as gp

    public = [machine.load_program(p) for p in sorted((REFERENCE / "programs").glob("*.json"))]
    seen, out = set(), []
    for program in public + gp.corpus() + gp.additional_programs():
        key = json.dumps(program, sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append(program)
    return out


def run(compiler: Path, corpus: Path, tick: float) -> list:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "compiler.py").write_bytes(compiler.read_bytes())
        proc = subprocess.run([sys.executable, "-I", "-c", RUNNER, tmp, str(corpus), str(tick),
                               str(REFERENCE)], capture_output=True, text=True, cwd=tmp)
    if proc.returncode:
        raise SystemExit(f"{compiler.name}: runner failed\n{proc.stderr[-2000:]}")
    return json.loads(proc.stdout)


def main() -> int:
    corpus_programs = programs()
    if not corpus_programs:
        print("REFUSED: empty corpus")
        return 2
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        corpus = Path(tmp) / "corpus.json"
        corpus.write_text(json.dumps(corpus_programs))
        for tick in (1e-4, 1e-5):
            a, b = run(ACCEPTED, corpus, tick), run(FLAT, corpus, tick)
            same = sum(x == y for x, y in zip(a, b))
            # A counted clock can exhaust a construction query's time budget; such an
            # error is part of the output and must be identical in both compilers.
            errors = sum(x.startswith("ERROR") for x in b)
            print(f"parity tick={tick:g}: identical {same}/{len(corpus_programs)} "
                  f"(of which identical clock-budget errors: {errors})")
            ok &= same == len(corpus_programs) == len(a) == len(b)
        real = run(FLAT, corpus, 0.0)
        valid = sum(not x.startswith("ERROR") for x in real)
        print(f"real clock: machine-valid {valid}/{len(corpus_programs)}")
        ok &= valid == len(corpus_programs)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
