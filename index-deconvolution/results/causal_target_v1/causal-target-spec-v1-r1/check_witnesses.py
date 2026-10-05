"""Check the four declared tiny witnesses (W1-W4) against their hand expectations.

Standard library only. Reads witnesses.json, evaluates only the hand-written maps,
tables and the counting arithmetic attached to W2, and writes witness_results.json.
It imports no project module on purpose: these are independent mathematical sanity
checks, not a use of the owner deconvolution (src/deconvolution.py), and not
performance or recovery data. Exit 0 iff every declared expectation is reproduced.
"""
import hashlib
import itertools
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DECL = HERE / 'witnesses.json'
OUT = HERE / 'witness_results.json'

checks = []


def check(wid, name, expected, observed):
    checks.append({'witness': wid, 'check': name, 'expected': expected,
                   'observed': observed, 'pass': expected == observed})


def states(n):
    return [''.join(b) for b in itertools.product('01', repeat=n)]


def trajectory(m, x0, steps):
    out = [x0]
    for _ in range(steps):
        out.append(m[out[-1]])
    return out


def essential(table, n):
    """Positions (0-based, x1 first) whose single flip changes the value somewhere."""
    ess = []
    for i in range(n):
        for s in table:
            t = s[:i] + ('1' if s[i] == '0' else '0') + s[i + 1:]
            if table[s] != table[t]:
                ess.append(i)
                break
    return ess


def macro_map(m, alpha):
    """Fbar on alpha's image if equal-alpha states have equal-alpha successors.

    Returns (Fbar or None, violating pairs). Every pair of same-fibre states whose
    successors have different alpha is listed (run 1 returned only the first one,
    which made a declared-but-later pair look like a failure; see attempts.jsonl).
    """
    bad = [[s, t] for s, t in itertools.combinations(sorted(m), 2)
           if alpha[s] == alpha[t] and alpha[m[s]] != alpha[m[t]]]
    if bad:
        return None, bad
    return {alpha[s]: alpha[m[s]] for s in sorted(m)}, []


def all_functions(n):
    xs = states(n)
    for bits in itertools.product((0, 1), repeat=len(xs)):
        yield dict(zip(xs, bits))


def main():
    decl = json.loads(DECL.read_text())
    W = {w['id']: w for w in decl['witnesses']}
    if set(W) != {'W1', 'W2', 'W3', 'W4'}:
        print('refusing: declared witness set is not exactly W1-W4', file=sys.stderr)
        return 2

    # W1 ------------------------------------------------------------------
    w = W['W1']; e = w['expected']; I, S = w['maps']['identity'], w['maps']['swap']
    x0, k = w['observation']['initial_state'], w['observation']['steps']
    tI, tS = trajectory(I, x0, k), trajectory(S, x0, k)
    check('W1', 'trajectory_identity', e['observed_trajectory_identity'], tI)
    check('W1', 'trajectory_swap', e['observed_trajectory_swap'], tS)
    seen = {(a, b) for a, b in zip(tI, tI[1:])} | {(a, b) for a, b in zip(tS, tS[1:])}
    check('W1', 'agree_on_observed', e['maps_agree_on_all_observed_transitions'],
          all(I[a] == b and S[a] == b for a, b in seen))
    check('W1', 'maps_distinct', e['maps_distinct'], I != S)
    check('W1', 'passive_verdict', e['passive_verdict_within_declared_pair'],
          'AMBIGUOUS' if all(I[a] == S[a] for a, _ in seen) and I != S else 'IDENTIFIED')
    dist = [s for s in states(2) if I[s] != S[s]]
    check('W1', 'distinguishing_queries', e['distinguishing_single_queries'], dist)
    check('W1', 'non_distinguishing_queries', e['non_distinguishing_single_queries'],
          [s for s in states(2) if I[s] == S[s]])
    q = e['chosen_query']
    check('W1', 'chosen_query_answers', e['chosen_query_answers'], {'identity': I[q], 'swap': S[q]})
    observed_rows = {a for a, _ in seen}
    check('W1', 'consistent_count_all_2bit_maps', e['consistent_count_all_2bit_maps'],
          4 ** (4 - len(observed_rows)))
    f1 = [f for f in all_functions(2) if len(essential(f, 2)) <= 1]
    target = I[x0]
    per_node = [sum(1 for f in f1 if f[x0] == int(target[i])) for i in range(2)]
    check('W1', 'consistent_count_class_k1', e['consistent_count_class_at_most_one_essential_input_per_node'],
          per_node[0] * per_node[1])

    # W2 ------------------------------------------------------------------
    w = W['W2']; e = w['expected']; A, B = w['tables']['A'], w['tables']['B']
    evalA = {s: int(s[0] == '1' and s[1] == '1') for s in states(3)}
    evalB = {s: int((s[0] == '1' and s[1] == '1') or (s[0] == '1' and s[1] == '1' and s[2] == '1'))
             for s in states(3)}
    check('W2', 'declared_table_A_matches_syntax', True, A == evalA)
    check('W2', 'declared_table_B_matches_syntax', True, B == evalB)
    check('W2', 'tables_equal', e['tables_equal'], A == B)
    name = lambda ix: ['x%d' % (i + 1) for i in ix]
    check('W2', 'essential_A', e['essential_inputs_A'], name(essential(A, 3)))
    check('W2', 'essential_B', e['essential_inputs_B'], name(essential(B, 3)))
    decA, decB = w['implementations']['A']['declared_inputs'], w['implementations']['B']['declared_inputs']
    check('W2', 'declared_inputs_differ', e['declared_inputs_differ'], decA != decB)
    check('W2', 'redundant_declared_B', e['redundant_declared_inputs_B'],
          [v for v in decB if v not in name(essential(B, 3))])
    sup = essential(B, 3)
    check('W2', 'recovered_minimal_support', e['recovered_minimal_support'], name(sup))
    red = {}
    for s in states(3):
        red.setdefault(''.join(s[i] for i in sup), B[s])
    check('W2', 'reduced_table', e['recovered_reduced_table_over_x1x2'], red)
    # The table is one object; two different declared syntaxes map onto it.
    check('W2', 'syntax_identifiable_from_table', e['syntax_identifiable_from_table'], not (A == B and decA != decB))
    check('W2', 'declared_connectivity_identifiable', e['declared_connectivity_identifiable_from_table'],
          not (A == B and decA != decB))

    c = w['counting_attachment']['expected']
    by2 = {}
    F2 = list(all_functions(2))
    for f in F2:
        by2[str(len(essential(f, 2)))] = by2.get(str(len(essential(f, 2))), 0) + 1
    check('W2', 'n2_functions_by_essential_count', c['functions_by_exact_essential_count_n2'], by2)
    k1 = [f for f in F2 if len(essential(f, 2)) <= 1]
    check('W2', 'n2_distinct_at_most_one', c['distinct_functions_at_most_one_essential_n2'], len(k1))
    check('W2', 'padded_exact_k1', c['padded_exact_k1_count_C(2,1)*2^(2^1)'], math.comb(2, 1) * 2 ** 2)
    check('W2', 'padded_sum_j_le_1', c['padded_sum_j_le_1_C(2,j)*2^(2^j)'],
          sum(math.comb(2, j) * 2 ** (2 ** j) for j in range(2)))
    check('W2', 'network_class_size', c['network_class_n2_k1_size'], len(k1) ** 2)
    check('W2', 'outcomes_per_query', c['query_outcomes_per_state_query_n2'], 2 ** 2)
    # Adaptive decision tree with <= 2^n outcomes per query: Q >= log_{2^n}(|class|).
    check('W2', 'adaptive_lower_bound', c['adaptive_lower_bound_queries_n2_k1'],
          math.ceil(math.log(len(k1) ** 2) / math.log(2 ** 2) - 1e-12))
    qs = c['nonadaptive_query_set_identifies_class']
    check('W2', 'three_queries_separate_class', True, len({tuple(f[s] for s in qs) for f in k1}) == len(k1))
    two_ok = any(len({tuple(f[s] for s in pair) for f in k1}) == len(k1)
                 for pair in itertools.combinations(states(2), 2))
    check('W2', 'any_two_queries_identify', c['any_two_queries_identify_class'], two_ok)
    by3 = {}
    for f in all_functions(3):
        key = str(len(essential(f, 3)))
        by3[key] = by3.get(key, 0) + 1
    check('W2', 'n3_functions_by_essential_count', c['functions_by_exact_essential_count_n3'], by3)
    E = {0: by2['0'], 1: by2['1'] // 2, 2: by2['2'], 3: by3['3']}
    check('W2', 'E_single_support', c['exact_essential_count_single_k'], {'E%d' % j: E[j] for j in range(4)})
    screen = {str(n): math.ceil(math.log2(math.comb(n, 3)) + 2 ** 3) for n in (50, 100, 200)}
    distinct = {str(n): math.ceil(math.log2(sum(math.comb(n, j) * E[j] for j in range(4)))) for n in (50, 100, 200)}
    check('W2', 'screen_formula_values', c['screen_formula_values_n_ge_50_k3'], screen)
    check('W2', 'distinct_class_bound_values', c['distinct_class_bound_values_n_ge_50_k3'], distinct)
    exact_counts = {str(n): {'padded': math.comb(n, 3) * 256,
                             'distinct_le3': sum(math.comb(n, j) * E[j] for j in range(4)),
                             'log2_padded': round(math.log2(math.comb(n, 3) * 256), 4),
                             'log2_distinct_le3': round(math.log2(sum(math.comb(n, j) * E[j] for j in range(4))), 4)}
                    for n in (50, 100, 200)}

    # W3 ------------------------------------------------------------------
    w = W['W3']; e = w['expected']; al = w['alpha']['table']
    fb, bad = macro_map(w['maps']['identity'], al)
    check('W3', 'identity_macro_exists', e['identity_macro_map_exists'], fb is not None)
    check('W3', 'identity_macro_map', e['identity_macro_map'], fb)
    fb2, bad2 = macro_map(w['maps']['xor_first'], al)
    check('W3', 'xor_first_macro_exists', e['xor_first_macro_map_exists'], fb2 is not None)
    check('W3', 'xor_first_witness_pair_is_violating', True, e['xor_first_witness_pair'] in bad2)
    check('W3', 'xor_first_witness_next_alpha', e['xor_first_witness_next_alpha'],
          {s: al[w['maps']['xor_first'][s]] for s in e['xor_first_witness_pair']})
    check('W3', 'xor_first_all_violating_pairs', [['00', '01'], ['10', '11']], bad2)
    check('W3', 'alpha_lossy', e['alpha_is_lossy'], len(set(al.values())) < len(al))
    codec = w['control_bijective_codec']['table']
    check('W3', 'codec_is_bijective', True, len(set(codec.values())) == len(codec))
    check('W3', 'codec_macro_identity', e['codec_macro_map_exists_identity'],
          macro_map(w['maps']['identity'], codec)[0] is not None)
    check('W3', 'codec_macro_xor_first', e['codec_macro_map_exists_xor_first'],
          macro_map(w['maps']['xor_first'], codec)[0] is not None)

    # W4 ------------------------------------------------------------------
    w = W['W4']; e = w['expected']; al = w['alpha']['table']; F = w['map']['identity']
    fb, _ = macro_map(F, al)
    check('W4', 'autonomous_macro_exists', e['autonomous_macro_map_exists'], fb is not None)
    check('W4', 'autonomous_macro_map', e['autonomous_macro_map'], fb)
    Fq = {s: F['0' + s[1]] for s in states(2)}  # set x1:=0, then apply F once
    check('W4', 'declared_F_q_matches_semantics', w['intervention']['F_q'], Fq)
    fbq, badq = macro_map(Fq, al)
    check('W4', 'intervened_macro_exists', e['intervened_macro_map_exists'], fbq is not None)
    check('W4', 'intervened_witness_pair_is_violating', True, e['intervened_witness_pair'] in badq)
    check('W4', 'intervened_witness_next_alpha', e['intervened_witness_next_alpha'],
          {s: al[Fq[s]] for s in e['intervened_witness_pair']})
    check('W4', 'intervened_all_violating_pairs', [['00', '11'], ['01', '10']], badq)
    gs = [dict(zip('01', v)) for v in itertools.product('01', repeat=2)]
    reps = [g for g in gs if all(al[Fq[s]] == g[al[s]] for s in states(2))]
    check('W4', 'macro_operations_checked', e['macro_operations_checked'], len(gs))
    check('W4', 'macro_operations_representing', e['macro_operations_representing_intervention'], len(reps))

    if not checks:
        print('refusing: zero checks evaluated', file=sys.stderr)
        return 2
    per = {}
    for ch in checks:
        p = per.setdefault(ch['witness'], [0, 0])
        p[0] += ch['pass']; p[1] += 1
    out = {'schema': 'causal-target-witness-results-v1',
           'declaration': DECL.name, 'declaration_version': decl['version'],
           'declaration_sha256': hashlib.sha256(DECL.read_bytes()).hexdigest(),
           'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'all_pass': all(ch['pass'] for ch in checks),
           'passed': sum(ch['pass'] for ch in checks), 'denominator': len(checks),
           'per_witness': {k: '%d/%d' % tuple(v) for k, v in sorted(per.items())},
           'counting_detail_k3': exact_counts,
           'scope': 'Mathematical sanity checks of four hand-declared maps (<=3 bits) plus the W2 counting arithmetic. Not performance data, not learned recovery.',
           'checks': checks}
    OUT.write_text(json.dumps(out, indent=1))
    print('all_pass=%s %d/%d %s' % (out['all_pass'], out['passed'], out['denominator'], out['per_witness']))
    for ch in checks:
        if not ch['pass']:
            print('FAIL', ch['witness'], ch['check'], 'expected', ch['expected'], 'observed', ch['observed'])
    return 0 if out['all_pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
