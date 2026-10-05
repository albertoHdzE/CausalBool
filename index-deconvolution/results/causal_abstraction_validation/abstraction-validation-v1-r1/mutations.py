"""Pre-freeze mutation check: each declared mutant of study.py must make test_study.py fail.
Writes mutation_results.json. Each replacement must match exactly once in study.py."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, *[".."] * 4))

MUTANTS = {
    "merge_different_local_flips": (
        '    k, p, _ = coord[q["j"]]\n    return (q["op"], k, p, q["c"])',
        '    k, p, _ = coord[q["j"]]\n    return (q["op"], k, 0 if q["op"] == "flip" else p, q["c"])'),
    "suppress_representative_failure": (
        '        elif maps[rep] is None:\n            rep_state = "REP-NOEXIST"\n            counts["REP-NOEXIST"] += 1',
        '        elif False:\n            rep_state = "REP-NOEXIST"\n            counts["REP-NOEXIST"] += 1'),
    "treat_unknown_as_pass": (
        '    stats = {q: check_status(s) for q, s in e3.items()}',
        '    stats = {q: PASS if check_status(s) == UNKNOWN else s for q, s in e3.items()}\n'
        '    e2 = PASS if e2 == UNKNOWN else e2'),
    "reverse_intervention_timing": (
        '            return [Ft[(x & m) | (c << j)] for x in range(self.N)]',
        '            return [(Ft[x] & m) | (c << j) for x in range(self.N)]'),
    "drop_ragged_tails": (
        '        blocks.append((a, min(w, n - a)))',
        '        if n - a >= w:\n            blocks.append((a, w))'),
    "control_hides_missingness": (
        '    if control is True:\n        if status == "FULL":',
        '    if control is True:\n        if True:'),
}


def main():
    src = open(os.path.join(HERE, "study.py")).read()
    results = {}
    env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "index-deconvolution", "src"))
    for name, (old, new) in MUTANTS.items():
        assert src.count(old) == 1, (name, src.count(old))
        d = tempfile.mkdtemp(prefix=f"mut_{name}_")
        open(os.path.join(d, "study.py"), "w").write(src.replace(old, new))
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=no", "-p", "no:cacheprovider",
                            os.path.join(HERE, "test_study.py")], cwd=ROOT, capture_output=True, text=True,
                           env=dict(env, STUDY_DIR=d))
        failed = [ln.split(" ")[1] for ln in p.stdout.splitlines() if ln.startswith("FAILED")]
        results[name] = {"exit": p.returncode, "killed": p.returncode != 0 and bool(failed),
                         "failing_tests": failed, "summary": p.stdout.strip().splitlines()[-1]}
        shutil.rmtree(d)
        print(name, results[name]["killed"], len(failed), results[name]["summary"])
    json.dump(results, open(os.path.join(HERE, "mutation_results.json"), "w"), indent=1)
    sys.exit(0 if all(r["killed"] for r in results.values()) else 1)


if __name__ == "__main__":
    main()
