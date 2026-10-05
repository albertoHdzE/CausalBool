"""Preservation snapshot: sha256 of every file under index-deconvolution/ (except this
run directory and __pycache__) plus GOVERNANCE/. Run-local record keeping only."""
import hashlib, json, os, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 4))
RUN = os.path.relpath(os.path.dirname(os.path.abspath(__file__)), ROOT)


def snapshot():
    out = {}
    for top in ("index-deconvolution", "GOVERNANCE"):
        for d, dirs, files in os.walk(os.path.join(ROOT, top)):
            rel_d = os.path.relpath(d, ROOT)
            dirs[:] = [x for x in dirs if x != "__pycache__" and os.path.join(rel_d, x) != RUN
                       and x not in (".pytest_cache", ".ruff_cache")]
            for f in files:
                p = os.path.join(d, f)
                if os.path.islink(p):
                    continue
                h = hashlib.sha256()
                with open(p, "rb") as fh:
                    for chunk in iter(lambda: fh.read(1 << 20), b""):
                        h.update(chunk)
                out[os.path.relpath(p, ROOT)] = h.hexdigest()
    return out


if __name__ == "__main__":
    which = sys.argv[1]
    snap = snapshot()
    json.dump({"taken_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "count": len(snap),
               "files": snap}, open(os.path.join(os.path.dirname(__file__), f"preservation_{which}.json"), "w"),
              indent=0, sort_keys=True)
    print(which, len(snap))
