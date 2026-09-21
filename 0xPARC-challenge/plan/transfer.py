"""Copy sealed deliverables while preserving unrelated workspace changes."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

SOURCE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SOURCE/'src'))
from oxparc_challenge.release import check_manifest,seal

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main(destination):
    destination=Path(destination).resolve()
    if destination==SOURCE.parent:raise SystemExit('Source and destination must differ')
    check_manifest()
    manifest=json.loads((SOURCE/'evidence/manifest.json').read_text())['files']
    state=json.loads((SOURCE/'plan/STATE.json').read_text())
    if state['release_status']!='PASS':raise SystemExit('Lead acceptance required')
    before=hashlib.sha256(subprocess.check_output(['git','diff','--binary'],cwd=destination)).hexdigest()
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=destination,text=True).strip()
    transfers=[]
    for name,h in manifest.items():
        if name.startswith('../'):
            target=destination/name[3:]
            if name!='../.github/workflows/oxparc.yml':
                if not target.is_file() or sha(target)!=h:raise SystemExit(f'CausalBool source mismatch: {target}')
                continue
        else:target=destination/'0xPARC-challenge'/name
        if target.exists() and sha(target)!=h:
            raise SystemExit(f'Preserving conflicting destination file: {target}')
        transfers.append((SOURCE/name,target))
    for origin,target in transfers:
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(origin,target)
    after=hashlib.sha256(subprocess.check_output(['git','diff','--binary'],cwd=destination)).hexdigest()
    if before!=after:raise SystemExit('Tracked changes changed during transfer; investigate before acceptance')
    record={'status':'PASS','integration_source':str(SOURCE),'destination':str(destination/'0xPARC-challenge'),
            'destination_head':head,'tracked_diff_before_sha256':before,'tracked_diff_after_sha256':after,
            'copied_files':len(transfers),'source_baseline':state['base_revision'],
            'scope':'new challenge artifacts and .github/workflows/oxparc.yml; core files verified without copying'}
    path=SOURCE/'plan/TRANSFER.json';path.write_text(json.dumps(record,indent=2)+'\n')
    seal()
    shutil.copy2(path,destination/'0xPARC-challenge/plan/TRANSFER.json')
    shutil.copy2(SOURCE/'evidence/manifest.json',destination/'0xPARC-challenge/evidence/manifest.json')
    print(f'Copied {len(transfers)} files; unrelated tracked changes preserved')

if __name__=='__main__':main(sys.argv[1])
