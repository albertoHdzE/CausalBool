"""Check manuscript examples, its analytical solution and generated artifacts."""
from __future__ import annotations

import hashlib
import contextlib
import io
import json
import re
from pathlib import Path

import numpy as np
from scipy.optimize import brentq, minimize
from scipy.special import logsumexp, rel_entr, xlogy

HERE = Path(__file__).resolve().parent


def hash_file(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    evidence = json.loads((HERE / 'evidence.json').read_text())
    for path, digest in evidence['generated_hashes'].items():
        assert hash_file(HERE / path) == digest, path
    source = (HERE / 'main.tex').read_text()
    listings = re.findall(r'\\begin\{lstlisting\}(?!\[)(.*?)\\end\{lstlisting\}', source, re.S)
    namespace = {'spec': json.loads((HERE / 'generated/worked_network.json').read_text())}
    assert len(listings) == 2
    printed = re.findall(r'\\begin\{lstlisting\}\[language=\{\}\](.*?)\\end\{lstlisting\}', source, re.S)
    assert len(printed) == 3  # Two result blocks, then the reproduction commands.
    for block, expected in zip(listings, printed[:2]):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(compile(block.strip(), '<manuscript listing>', 'exec'), namespace)
        assert output.getvalue().strip() == expected.strip(), (output.getvalue(), expected)

    # This is a mathematical check, not another network experiment. Compare
    # the closed-form family against an independently constrained optimiser.
    q = np.array([.5, .3, .2])
    payoffs = np.array([.1, .4, .9])
    C = .25
    def kl(p):
        return float(np.sum(xlogy(p, p) - p * np.log(q)))
    def tilt(beta):
        log_weights = np.log(q) + beta * payoffs
        return np.exp(log_weights - logsumexp(log_weights))
    beta = brentq(lambda b: kl(tilt(b)) - C, 0, 100, xtol=1e-13)
    p = tilt(beta)
    assert abs(kl(p) - C) < 1e-12
    dual = (C + logsumexp(np.log(q) + beta * payoffs)) / beta
    assert abs(dual - p @ payoffs) < 1e-12
    independent = minimize(lambda x: -x @ payoffs, q, method='SLSQP',
        bounds=[(1e-12, 1)] * 3,
        constraints=[{'type': 'eq', 'fun': lambda x: x.sum() - 1},
                     {'type': 'ineq', 'fun': lambda x: C - kl(x)}],
        options={'ftol': 1e-12, 'maxiter': 1000})
    assert independent.success, independent.message
    assert np.max(np.abs(independent.x - p)) < 1e-6
    assert np.allclose(tilt(0), q)
    # Tied maxima and deterministic saturation have different thresholds.
    ties = np.array([0., .6, .4])
    assert abs(kl(ties) - (-np.log(.5))) < 1e-12
    deterministic = np.array([0., 0., 1.])
    assert abs(kl(deterministic) - (-np.log(.2))) < 1e-12
    assert np.isinf(np.sum(rel_entr([.5, .5], [1., 0.])))
    assert np.allclose(np.dot([.25, .75], [.4, .4]), np.dot([.9, .1], [.4, .4]))
    assert np.all(np.diff([kl(tilt(b)) for b in np.linspace(0, 8, 41)]) >= -1e-12)
    assert np.allclose(p, [.23444, .26383, .50173], atol=5e-6, rtol=0)
    extra = evidence['explanatory_extension']
    assert extra['basin_sizes_recomputed'] == [6, 148, 389, 481]
    assert extra['cycle_probability_sum'] == '1'
    assert extra['schema_positions'] == 128
    assert extra['full_two_output_positions'] == 256
    assert (extra['frontier_changes'], extra['finite_kl'], extra['infinite_kl']) == (74, 29, 45)
    assert extra['row_bdm']['rows'] == 1024 and extra['row_bdm']['distinct_outputs'] == 432
    # Full data checks are in build_evidence; here verify the exact snippets
    # and theoretical properties independently of that generation code.
    prohibited = re.findall(r"\b(?:don't|doesn't|isn't|aren't|can't|won't|we're|it's|that's)\b", source, flags=re.I)
    assert not prohibited, prohibited
    log = (HERE / 'main.log').read_text()
    assert re.search(r'Output written on (?:[^\n]*/)?main\.pdf\b', log)
    assert not re.search(r'Overfull|undefined|Fatal error', log, re.I)
    aux = (HERE / 'main.aux').read_text()
    supplement = re.search(r'\\newlabel\{supplement-start\}\{\{[^}]*\}\{(\d+)\}', aux)
    assert supplement, 'Missing supplement page marker'
    main_pages = int(supplement.group(1)) - 1
    assert 4 <= main_pages <= 6, main_pages
    checks = {'python_listings_executed': len(listings),
        'printed_result_blocks_match_execution': len(listings),
        'explanatory_counts_checked': True,
        'generated_hashes_checked': len(evidence['generated_hashes']),
        'tilted_distribution_matches_independent_optimiser': True,
        'zero_budget_and_saturation_checks': True,
        'no_contractions': True, 'latex_no_overflow_or_unresolved_references': True,
        'main_response_pages_including_references': main_pages,
        'manuscript_sha256': hash_file(HERE / 'main.tex'),
        'pdf_sha256': hash_file(HERE / 'main.pdf'),
        'evidence_sha256': hash_file(HERE / 'evidence.json'),
        'source_hashes': {p.name: hash_file(p) for p in [HERE / 'build_evidence.py',
             HERE / 'explanatory_evidence.py', Path(__file__), HERE / 'README.md']},
        'analytical_check': {'q': q.tolist(), 'payoffs': payoffs.tolist(), 'C': C,
             'beta': float(beta), 'p': p.tolist(), 'payoff': float(p @ payoffs)}}
    (HERE / 'verification.json').write_text(json.dumps(checks, indent=2, sort_keys=True) + '\n')
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    main()
