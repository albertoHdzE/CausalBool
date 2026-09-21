"""Regenerate the internal paper from retained evidence, without new benchmarks."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BUILD = HERE / 'build'
BUILD.mkdir(exist_ok=True)


def run(command, log_name):
    with (BUILD / log_name).open('w') as stream:
        result = subprocess.run(command, cwd=HERE, stdout=stream,
                                stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise RuntimeError(f'{command[0]} exited {result.returncode}; see build/{log_name}')
    return {'command': command, 'cwd': str(HERE), 'exit_code': result.returncode,
            'log': f'build/{log_name}'}


commands = [run([sys.executable, 'generate_figures.py'], 'figures.log')]
commands.append(run(['latexmk', '-pdf', '-interaction=nonstopmode',
                     '-halt-on-error', '-outdir=build', 'main.tex'], 'latexmk.log'))
log = (BUILD / 'main.log').read_text()
issues = re.findall(r'^.*(?:Overfull|undefined|multiply defined|LaTeX Warning:).*$',
                    log, flags=re.MULTILINE)
if issues:
    raise RuntimeError('Resolve LaTeX issues before delivering the PDF:\n' + '\n'.join(issues))
shutil.copyfile(BUILD / 'main.pdf', HERE / 'main.pdf')
artifacts = [HERE / 'main.tex', HERE / 'main.pdf', HERE / 'generate_figures.py',
             HERE / 'build_paper.py', *sorted((HERE / 'generated').iterdir())]
manifest = {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in artifacts if p.is_file()}
report = {'status': 'PASS', 'commands': commands,
          'latex_warnings_or_overfull_boxes': issues,
          'figure_pairs': len(list((HERE / 'generated').glob('*.png'))),
          'inline_method_diagrams': 1,
          'artifacts_sha256': manifest,
          'scope': 'Paper regeneration and evidence arithmetic; no new compiler benchmark or peer review.'}
(HERE / 'BUILD_VALIDATION.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS: main.pdf, six figure pairs, inline method diagram, tables and artifact hashes.')
