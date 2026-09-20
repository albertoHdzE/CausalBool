"""Assemble a standalone, standard-library-only compiler.py for local validation."""
import argparse
import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPERTOIRE = ROOT.parent/'doppel-challenge/src/doppel_challenge/repertoire_program.py'


def definitions(path):
    text = path.read_text()
    lines = text.splitlines(keepends=True)
    chunks = []
    for node in ast.parse(text).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            start = min([node.lineno] + [d.lineno for d in node.decorator_list]) - 1
            chunks.append(''.join(lines[start:node.end_lineno]))
    return '\n\n'.join(chunks)


def export(method):
    sources = [REPERTOIRE, ROOT/'common.py', ROOT/'index_query.py', ROOT/'compilers.py']
    header = ['# Generated from local CausalBool sources; do not edit this assembled copy.']
    header += [f'# {p.name}: SHA256 {hashlib.sha256(p.read_bytes()).hexdigest()}' for p in sources]
    backend = REPERTOIRE.read_text().replace('from __future__ import annotations\n', '')
    query = definitions(ROOT/'index_query.py').replace('rp._Manager', '_Manager').replace(
        'rp.ProgramLimits', 'ProgramLimits').replace('rp.ResourceLimitError', 'ResourceLimitError')
    compiler = definitions(ROOT/'compilers.py').replace("default='index'", f"default='{method}'")
    override = ('def compile_program(program):\n    return classical_compile(program)\n'
                if method == 'classical' else
                'def compile_program(program):\n    return optimize(program)[0]\n')
    result = '\n'.join(header) + '\nfrom __future__ import annotations\n'
    result += 'import argparse\nimport sys\nfrom itertools import product\nimport machine\n'
    result += backend + '\n\n' + definitions(ROOT/'common.py') + '\n\n' + query
    result += '\n\n' + compiler + '\n\n' + override
    result += "\nif __name__ == '__main__':\n    main()\n"
    ast.parse(result)
    output = ROOT/'.build'/method/'compiler.py'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--method', choices=('classical', 'index'), required=True)
    print(export(parser.parse_args().method))
