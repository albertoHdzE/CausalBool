"""AUDIT02/Q1 — arm-1 reproducibility sweep.

Re-run each producer; compare every committed artefact it touches, elementwise,
against the git-committed version. Restores the tree afterwards."""
import os, sys, subprocess, json, hashlib, shutil, argparse

ROOT = os.path.abspath(os.path.dirname(__file__)) if False else os.getcwd()

def sh(cmd, cwd=None, timeout=1800):
    return subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True,
                          text=True, timeout=timeout)

def committed_files(prefix):
    r = sh(f"git ls-files {prefix}")
    return [f for f in r.stdout.split() if f.endswith(('.json','.csv','.jsonl','.md'))]

def snap(files):
    return {f: hashlib.sha256(open(f,'rb').read()).hexdigest()
            for f in files if os.path.exists(f)}

def elementwise_diff(path):
    """Return a short human description of how the file changed vs HEAD."""
    old = sh(f"git show HEAD:{path}").stdout
    new = open(path, errors='ignore').read()
    if path.endswith(('.json',)):
        try:
            a, b = json.loads(old), json.loads(new)
        except Exception:
            return "unparseable JSON on one side"
        return json_diff(a, b)
    ao, an = old.splitlines(), new.splitlines()
    d = [i for i,(x,y) in enumerate(zip(ao,an)) if x!=y]
    return f"{len(d)} differing lines (first at {d[0]+1})" if d else f"length {len(ao)}->{len(an)}"

def json_diff(a, b, path=""):
    out=[]
    if isinstance(a,dict) and isinstance(b,dict):
        for k in sorted(set(a)|set(b)):
            if k not in a: out.append(f"{path}/{k}: ADDED")
            elif k not in b: out.append(f"{path}/{k}: REMOVED")
            else: out += json_diff(a[k],b[k],f"{path}/{k}")
    elif isinstance(a,list) and isinstance(b,list):
        if len(a)!=len(b): out.append(f"{path}: len {len(a)}->{len(b)}")
        else:
            for i,(x,y) in enumerate(zip(a,b)):
                out += json_diff(x,y,f"{path}[{i}]")
    elif a!=b:
        out.append(f"{path}: {a!r} -> {b!r}")
    return out[:200]

def run(label, cmd, prefix, cwd=None):
    files = committed_files(prefix)
    before = snap(files)
    r = sh(cmd, cwd=cwd)
    ok = (r.returncode == 0)
    after = snap(files)
    changed = sorted(f for f in before if f in after and before[f] != after[f])
    res = dict(label=label, cmd=cmd, exit=r.returncode, ran=ok,
               n_tracked=len(files), n_changed=len(changed), changed=changed)
    if not ok:
        res["stderr_tail"] = r.stderr.strip().splitlines()[-6:]
    res["diffs"] = {f: elementwise_diff(f)[:6] if isinstance(elementwise_diff(f), list)
                    else elementwise_diff(f) for f in changed[:10]}
    # restore
    if changed: sh("git checkout -- " + " ".join(f"'{c}'" for c in changed))
    return res

JOBS = []
# index-deconvolution experiments (deterministic, seeded)
for e in sorted(os.listdir('index-deconvolution/experiments')):
    if e.startswith('exp') and e.endswith('.py'):
        JOBS.append((f"index-deconvolution/{e}",
                     f"../venv/bin/python experiments/{e}",
                     "index-deconvolution/results", "index-deconvolution"))
JOBS.append(("index-deconvolution/crosscheck",
             "../venv/bin/python crosscheck/generate_crosscheck_cases.py",
             "index-deconvolution/crosscheck", "index-deconvolution"))

if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv)>1 else ""
    out=[]
    for label, cmd, prefix, cwd in JOBS:
        if only and only not in label: continue
        print(f"-- {label}", flush=True)
        try:
            res = run(label, cmd, prefix, cwd)
        except subprocess.TimeoutExpired:
            res = dict(label=label, cmd=cmd, exit="TIMEOUT", ran=False,
                       n_changed=0, changed=[], diffs={})
        out.append(res)
        flag = "OK-identical" if res["ran"] and res["n_changed"]==0 else \
               ("DIFFERS" if res["ran"] else "WILL-NOT-RUN")
        print(f"   {flag}  exit={res['exit']}  changed={res['n_changed']}/{res.get('n_tracked','?')}", flush=True)
    json.dump(out, open('/tmp/q1_results.json','w'), indent=1)
    print("\n=== SUMMARY ===")
    for r in out:
        flag = "OK-identical" if r["ran"] and r["n_changed"]==0 else \
               ("DIFFERS" if r["ran"] else "WILL-NOT-RUN")
        print(f"{flag:14s} {r['label']}")
