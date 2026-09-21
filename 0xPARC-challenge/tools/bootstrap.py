"""Create the isolated pinned environment and compiler/witness tools."""
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import urllib.request
import venv

ROOT=Path(__file__).resolve().parents[1]
ASSETS={
    'Darwin': ('circom-macos-amd64','e006332b3fe225f11c3b87bd2debbf5d7f568d6efbde25e5a6a12cd6988c8ecb'),
    'Linux': ('circom-linux-amd64','85342c7ff332d948df7c0c50ecf201e6129349aef550ce873f3c811b79fe53a3'),
}

def main():
    if sys.version_info[:2]!=(3,13):raise SystemExit('Use Python 3.13 to bootstrap.')
    if platform.system() not in ASSETS:raise SystemExit('Supported: macOS (Rosetta for arm64), Linux x86_64.')
    if platform.system()=='Linux' and platform.machine() not in ('x86_64','amd64'):
        raise SystemExit('Pinned Linux binary requires x86_64.')
    for tool in ('node','npm','pdflatex','pdftotext'):
        if not shutil.which(tool):raise SystemExit(f'Install prerequisite {tool} before setup.')
    env=ROOT/'.venv'
    if not (env/'bin/python').is_file():venv.create(env,with_pip=True)
    subprocess.run([str(env/'bin/python'),'-m','pip','install','-r',str(ROOT/'requirements.lock')],check=True)
    subprocess.run([str(env/'bin/python'),'-m','pip','install','--no-build-isolation','--no-deps','-e',str(ROOT)],check=True)
    directory=ROOT/'.tools';directory.mkdir(exist_ok=True)
    name,digest=ASSETS[platform.system()];destination=directory/'circom'
    if not destination.exists() or hashlib.sha256(destination.read_bytes()).hexdigest()!=digest:
        url=f'https://github.com/iden3/circom/releases/download/v2.2.3/{name}'
        with urllib.request.urlopen(url,timeout=120) as response:data=response.read()
        if hashlib.sha256(data).hexdigest()!=digest:raise SystemExit('Circom SHA256 mismatch')
        destination.write_bytes(data)
    destination.chmod(0o755)
    shutil.copyfile(ROOT/'package.json',directory/'package.json')
    shutil.copyfile(ROOT/'npm-tools.lock.json',directory/'package-lock.json')
    subprocess.run(['npm','ci','--prefix',str(directory)],check=True)
    subprocess.run([str(destination),'--version'],check=True)
    print('Ready: PYTHONPATH=src .venv/bin/python -m oxparc_challenge verify-release')

if __name__=='__main__':main()
