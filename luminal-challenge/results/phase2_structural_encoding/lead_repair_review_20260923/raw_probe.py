import contextlib, io, json, shutil, tempfile
from pathlib import Path
from unittest.mock import patch
from research import check_structural_evidence as c
from research import run_structural_experiments as r
ROOT=r.ROOT
source=ROOT/'results/phase2_structural_encoding/phase2_repair_20260923b'
out=ROOT/'results/phase2_structural_encoding/lead_repair_review_20260923'
results={}
with tempfile.TemporaryDirectory(dir=out) as td:
    copy=Path(td)/'run'
    shutil.copytree(source,copy)
    raw=copy/'p1/decoder_rows.jsonl'
    raw.write_text('{}\n')
    summary=json.loads((copy/'p1/summary.json').read_text())
    summary['raw_artifacts']['decoder_rows.jsonl']=r.file_digest(raw)
    (copy/'p1/summary.json').write_text(json.dumps(summary))
    m=json.loads((copy/'manifest.json').read_text())
    m['stage_digests']['p1']=r.file_digest(copy/'p1/summary.json')
    m['row_counts']['p1/decoder_rows.jsonl']=1
    (copy/'manifest.json').write_text(json.dumps(m))
    buf=io.StringIO()
    with contextlib.redirect_stdout(buf):
        code=c.main(['--run',str(copy),'--contract',str(ROOT/'plan/phase2')])
    report=json.loads(buf.getvalue())
    results['erased_decoder_rows']={'exit':code,'report':report}
(out/'raw_probe.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({'exit':code,'findings':report['findings']},indent=2))
