"""Pre-edit preservation capture (run once before any new file outside preflight/ledger)."""
import hashlib, json, subprocess, sys, time
from pathlib import Path
sys.path[:0] = ['experiments', '.', '../src']
from search_v3a.preserve import tree_hash
ID = Path('.').resolve(); REPO = ID.parent
st = json.loads((ID / 'protocols/hierarchy_dictionary_v1/INITIAL_STATE.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def files(g): return sorted(p.relative_to(REPO).as_posix() for p in REPO.glob(g) if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
gs = subprocess.run(['git', 'status', '--porcelain=v1', '--untracked-files=all'], cwd=REPO, capture_output=True, text=True).stdout.splitlines()
rec = {'stage': sys.argv[1], 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
       'git_head': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO, capture_output=True, text=True).stdout.strip(),
       'git_status': gs, 'packet_git_status_equal': gs == st['git_status'],
       'protected_files': {p: {'packet': h, 'now': sha(REPO / p)} for p, h in st['protected_files'].items()},
       'scientific_dependencies': {p: {'packet': h, 'now': sha(REPO / p)} for p, h in st['scientific_dependencies'].items()},
       'prior_result_trees': {t: tree_hash(REPO / t) for t in st['prior_result_roots']},
       'hierarchy_sources': {f: sha(REPO / f) for f in files('index-deconvolution/hierarchy/**/*')},
       'multilevel_package': {f: sha(REPO / f) for f in files('index-deconvolution/experiments/hierarchy_multilevel/**/*')},
       'notebooks_and_builders': {f: sha(REPO / f) for f in files('index-deconvolution/notebooks/*')},
       'protocols_tree': tree_hash(ID / 'protocols'),
       'bitacora': tree_hash(ID / 'bitacora'),
       'destinations_absent': {p: not (REPO / p).exists() for p in st['destinations_absent_at_delegation']}}
rec['protected_changed'] = sorted(p for p, v in rec['protected_files'].items() if v['packet'] != v['now'])
rec['scientific_changed'] = sorted(p for p, v in rec['scientific_dependencies'].items() if v['packet'] != v['now'])
Path(sys.argv[2]).write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n')
print(json.dumps({k: rec[k] for k in ('protected_changed', 'scientific_changed', 'packet_git_status_equal', 'destinations_absent')}),
      {t: v['files'] for t, v in rec['prior_result_trees'].items()})
