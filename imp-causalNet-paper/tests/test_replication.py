"""Fidelity tests for the replication of arXiv:1802.09904v8.

Each test pins a claim that is checkable against the paper text or against an
internal consistency requirement of the implementation.
"""

from __future__ import annotations

import collections
import math

import networkx as nx
import numpy as np
import pytest

from imp_causalnet_paper import (
    ca, causal_models, complexity, deconvolution, figures, footprint, graphs, official, strings,
)
from imp_causalnet_paper.causalbool_mirror import (
    consistent_rules,
    index_set_description_length,
    local_mechanism_map,
)
from imp_causalnet_paper.fastbdm import IncrementalBDM2D


# ---------------------------------------------------------------------------
# Estimator parameters (Section 2.4)
# ---------------------------------------------------------------------------


def test_ctm_tables_match_the_papers_stated_parameters():
    """"12 bits for strings and 4 square bits for arrays"."""
    assert complexity._BDM_1D.ctmname == "CTM-B2-D12"
    assert complexity._BDM_2D.ctmname == "CTM-B2-D4x4"


def test_bdm_is_subadditive_in_repetitions():
    """Eq. 2: repeated blocks contribute once plus ``log2`` of the multiplicity."""
    one = complexity.bdm_2d(np.ones((4, 4), dtype=int))
    four = complexity.bdm_2d(np.ones((8, 8), dtype=int))
    assert math.isclose(four, one + math.log2(4), rel_tol=1e-12)


# ---------------------------------------------------------------------------
# Interaction rule enumeration (Sup. Inf. 4.1)
# ---------------------------------------------------------------------------


def test_twelve_mixed_neighbourhoods_are_exactly_those_containing_both_colours():
    expected = {
        t
        for t in np.ndindex(3, 3, 3)
        for t in [tuple(x - 1 for x in t)]
        if -1 in t and 1 in t
    }
    assert set(ca.MIXED_NEIGHBOURHOODS) == expected
    assert len(ca.MIXED_NEIGHBOURHOODS) == 12


def test_paper_interaction_rule_531441_lets_the_right_automaton_survive():
    """``531441 = 3**12`` is the last word of ``Tuples[{-1,0,1}, 12]``: all ``+1``."""
    table = ca.interaction_rule(ca.INTERACTION_RULE_PAPER)
    assert set(table.values()) == {1}
    # the first word is all -1
    assert set(ca.interaction_rule(1).values()) == {-1}


def test_gray_code_helpers_match_the_wolfram_definitions():
    assert ca.code(0) == 0 and ca.code(1) == 1 and ca.code(2) == 3 and ca.code(3) == 2
    assert ca.rule_code(3) == [1, 0]


# ---------------------------------------------------------------------------
# Elementary cellular automata
# ---------------------------------------------------------------------------


def test_rule_110_matches_its_wolfram_code():
    table = ca.eca_rule_table(110)
    assert list(table) == [0, 1, 1, 1, 0, 1, 1, 0]


def test_rule_255_fills_the_tape():
    out = ca.evolve_eca(255, np.zeros(16, dtype=int), 3)
    assert out[0].sum() == 0 and (out[1:] == 1).all()


def test_interacting_ca_only_ever_shows_two_colours_plus_white():
    ica = ca.evolve_interacting(60, 110, width=40, steps=20, seed=7)
    assert set(np.unique(ica.signed)).issubset({-1, 0, 1})
    assert set(np.unique(ica.observed)).issubset({0, 1})


def test_interacting_ca_reduces_to_a_single_eca_with_a_single_coloured_tape():
    """No mixed neighbourhood ever arises, so the interaction rule must be inert."""
    width, steps = 40, 25
    rng = np.random.default_rng(3)
    single_colour = rng.integers(0, 2, width)  # all cells in the right colour
    ica = ca.evolve_interacting(
        110, 110, width=width, steps=steps, initial=single_colour,
        interaction=ca.INTERACTION_RULE_PAPER,
    )
    plain = ca.evolve_eca(110, single_colour, steps)
    assert np.array_equal(ica.observed, plain)


def test_interaction_rule_531441_lets_the_right_colour_consume_the_left():
    """Every mixed neighbourhood resolves to ``+1``, so grey cannot invade black.

    This is the *deterministic* enumeration; it must be requested explicitly,
    because the published figures are stochastic and that is now the default.
    """
    ica = ca.evolve_interacting(
        255, 110, width=40, steps=30, seed=11, interaction=ca.INTERACTION_RULE_PAPER
    )
    left_share = [(row == -1).mean() for row in ica.signed]
    assert left_share[-1] <= left_share[0]


# ---------------------------------------------------------------------------
# Incremental BDM
# ---------------------------------------------------------------------------


def test_incremental_bdm_is_exact():
    rng = np.random.default_rng(0)
    A = rng.integers(0, 2, (16, 16))
    inc = IncrementalBDM2D(A)
    assert math.isclose(inc.value, complexity.bdm_2d(A), rel_tol=1e-12)
    for _ in range(50):
        i, j = rng.integers(0, 16, 2)
        got = inc.value_after_flips([(int(i), int(j))])
        B = A.copy()
        B[i, j] ^= 1
        assert math.isclose(got, complexity.bdm_2d(B), rel_tol=1e-12)


def test_incremental_bdm_matches_on_symmetric_edge_removal():
    G = graphs.scale_free(32, seed=1)
    A = graphs.adjacency(G)
    inc = IncrementalBDM2D(A)
    u, v = next(iter(G.edges()))
    B = A.copy()
    B[u, v] = B[v, u] = 0
    assert math.isclose(
        inc.value_after_flips([(u, v), (v, u)]), complexity.bdm_2d(B), rel_tol=1e-12
    )


# ---------------------------------------------------------------------------
# Sup. Inf. 4.4 transcriptions
# ---------------------------------------------------------------------------


def test_causal_deconvolution_ranking_shape_and_order():
    rng = np.random.default_rng(2)
    A = rng.integers(0, 2, (8, 12))
    fp = footprint.causal_deconvolution(A)
    assert fp.values.shape == A.shape
    ranked = fp.ranking
    assert len(ranked) == A.size
    assert all(ranked[i][1] >= ranked[i + 1][1] for i in range(len(ranked) - 1))


def test_row_window_split_is_seven_then_six():
    row = np.arange(20) % 2
    windows = list(footprint._row_windows(row))
    assert len(windows) == 20 - 12
    assert all(len(a) == 7 and len(b) == 6 for a, b in windows)


def test_ncd_of_an_object_with_itself_is_small():
    rng = np.random.default_rng(3)
    x = rng.integers(0, 2, (8, 8))
    assert complexity.ncd(x, x) < complexity.ncd(x, rng.integers(0, 2, (8, 8))) + 1e-9


# ---------------------------------------------------------------------------
# Deconvolution algorithms
# ---------------------------------------------------------------------------


def test_edge_information_is_the_difference_of_complexities():
    G = graphs.complete_graph(16)
    info = deconvolution.edge_information(G)
    A = graphs.adjacency(G)
    u, v = info.edges[0]
    B = A.copy()
    B[u, v] = B[v, u] = 0
    assert math.isclose(
        info.values[0], complexity.bdm_2d(A) - complexity.bdm_2d(B), rel_tol=1e-12
    )


def test_algorithm_1_reaches_the_requested_number_of_components():
    G, _, _ = graphs.join_random(
        graphs.complete_graph(12), graphs.scale_free(20, seed=4), n_links=2, seed=4
    )
    H, removed = deconvolution.deconvolve_n(G, N=2)
    assert nx.number_connected_components(H) >= 2
    assert removed


def test_algorithm_1_rejects_out_of_range_component_counts():
    G = graphs.complete_graph(8)
    with pytest.raises(ValueError):
        deconvolution.deconvolve_n(G, N=G.number_of_nodes() + 1)


def test_cutoff_constant_is_one_bit_as_in_the_authors_r_code():
    """``deconvolveterm.R`` writes ``log2(2)``, i.e. 1 bit -- not ``ln(2)``.

    BDM is measured in bits, so base 2 is the correct reading of the paper's
    "log(2)".  Reading it as a natural logarithm is what made Algorithm 2 look
    self-contradictory in an earlier version of this replication.
    """
    assert deconvolution.LOG2 == 1.0 == official.LOG2_BITS
    assert deconvolution.EPSILON_DEFAULT == official.EPSILON_DEFAULT == 1.0


def test_both_readings_of_algorithm_2_agree_at_the_official_epsilon():
    """With ``log2(2) = 1`` and ``epsilon = 1`` the two readings coincide.

    ``|d - 1| > 1`` means ``d > 2 or d < 0``; a descending signature has
    ``d >= 0``, so it reduces to the running text's ``d > log2(2) + epsilon``.
    """
    G, _, _ = graphs.join_random(
        graphs.complete_graph(16), graphs.scale_free(32, seed=5), n_links=3, seed=5
    )
    text = deconvolution.deconvolve_epsilon(G, verbatim=False)
    printed = deconvolution.deconvolve_epsilon(G, verbatim=True)
    assert {tuple(sorted(e)) for e in text.removed} == {tuple(sorted(e)) for e in printed.removed}
    assert len(printed.removed) < G.number_of_edges() / 2


# ---------------------------------------------------------------------------
# The authors' own published R implementation
# ---------------------------------------------------------------------------


def test_official_bdm2d_matches_pybdm_on_the_non_overlapping_partition():
    """``bdm2D(mat, 4, 4)`` must equal our ``bdm_2d``; both are the paper's setting."""
    rng = np.random.default_rng(11)
    for shape in [(16, 16), (20, 24), (40, 40)]:
        A = rng.integers(0, 2, shape)
        assert math.isclose(official.bdm2d(A, 4, 4), complexity.bdm_2d(A), rel_tol=1e-12)


def test_official_ctm_table_agrees_with_pybdm_entry_by_entry():
    """The R repo ships data/K-4x4.csv; every block it lists must match pybdm.

    Skipped unless the repository has been cloned alongside this one.
    """
    import csv, pathlib
    from pybdm.encoding import normalize_key, string_from_array

    csv_path = pathlib.Path("/tmp/cdn/data/K-4x4.csv")
    if not csv_path.exists():
        pytest.skip("official R repository not present")
    ctm = complexity._BDM_2D._ctm[(4, 4)]
    for key, value in csv.reader(csv_path.open()):
        arr = np.array([int(c) for c in key]).reshape(4, 4)
        assert math.isclose(ctm[normalize_key(string_from_array(arr))], float(value), abs_tol=1e-6)


def test_overlapping_partition_changes_the_value_but_not_the_verdict():
    """``deconvolve.R``'s test case uses offset=1; the paper's Methods say offset=4."""
    G, _, planted = graphs.join_random(
        graphs.complete_graph(20), graphs.scale_free(100, seed=0), n_links=3, seed=0
    )
    A = graphs.adjacency(G)
    assert official.bdm2d(A, 4, 1) != official.bdm2d(A, 4, 4)
    # under either partition the planted edges stay far from the top of the signature
    for offset in (4, 1):
        sig = official.get_info_signature(G, 4, offset)
        rank = {tuple(sorted(e)): i for i, e in enumerate(sig.edges)}
        ranks = [rank[tuple(sorted(e))] for e in planted if tuple(sorted(e)) in rank]
        assert min(ranks) > 20, f"offset={offset}: unexpectedly good ranks {ranks}"


# ---------------------------------------------------------------------------
# CausalBool index-set mirror
# ---------------------------------------------------------------------------


def test_consistent_rules_recovers_a_rule_from_its_own_transitions():
    rng = np.random.default_rng(6)
    row = rng.integers(0, 2, 60)
    st = ca.evolve_eca(110, row, 40)
    samples = [
        (
            int(4 * st[t, (i - 1) % 60] + 2 * st[t, i] + st[t, (i + 1) % 60]),
            int(st[t + 1, i]),
        )
        for t in range(40)
        for i in range(60)
    ]
    assert consistent_rules(samples) == frozenset({110})


def test_local_mechanism_map_is_exact_on_a_single_uncontested_automaton():
    """On a pure rule-110 diagram no pixel may be attributed to rule 60 or to neither."""
    rng = np.random.default_rng(8)
    st = ca.evolve_eca(110, rng.integers(0, 2, 40), 20)
    m = local_mechanism_map(st, 60, 110)
    assert not m.boundary.any()
    assert not (m.labels == -1).any()


def test_index_set_description_length_orders_graphs_as_the_paper_claims():
    """Section 3.2: complete graph cheapest, dense random graph dearest."""
    n = 60
    d_complete = index_set_description_length(graphs.adjacency(graphs.complete_graph(n)))
    d_star = index_set_description_length(graphs.adjacency(graphs.star_graph(n)))
    d_sf = index_set_description_length(
        graphs.adjacency(graphs.scale_free(n, seed=9))
    )
    d_er = index_set_description_length(
        graphs.adjacency(graphs.erdos_renyi(n, 0.5, seed=9))
    )
    assert d_complete < d_sf < d_er
    assert d_star < d_er


# ---------------------------------------------------------------------------
# Strings (Fig. 1)
# ---------------------------------------------------------------------------


def test_paper_string_is_transcribed_correctly():
    assert len(strings.PAPER_STRING) == 100
    assert strings.PAPER_STRING[:50] == strings.REGULAR_SEGMENT


def test_string_footprint_separates_the_two_segments():
    fp = strings.string_footprint(strings.PAPER_STRING)
    regular = np.abs(fp.values[:50])
    random_seg = np.abs(fp.values[50:96])  # last 4 sit in the ignored 12-bit margin
    assert regular.mean() > random_seg.mean()


# ---------------------------------------------------------------------------
# The paper's own published figures, digitised (Supplementary Fig. 2c)
# ---------------------------------------------------------------------------


def test_digitised_figure_has_the_geometry_the_caption_implies():
    """100 steps on a 100-cell tape: 101 rows including the initial condition."""
    grid = figures.load_sup_fig2c()
    assert grid.shape == (101, 100)
    assert set(np.unique(grid)) <= {figures.WHITE, figures.GREY, figures.RED}


def test_digitised_figure_recovers_rules_60_and_110_uniquely():
    """The decisive check that the pixel grid is aligned.

    A half-cell misalignment would scramble every neighbourhood and no
    elementary rule would survive.  Recovering exactly one rule per colour, and
    the two the caption names, validates the digitisation.
    """
    rules = figures.recover_local_rules(figures.load_sup_fig2c())
    assert rules["red_left"] == [60]
    assert rules["grey_right"] == [110]


def test_published_interaction_is_not_deterministic():
    """The mixed neighbourhoods of the published figure admit no deterministic rule.

    ``R[531441]`` would send every mixed neighbourhood to ``+1``.  The figure
    shows several outcomes for the same neighbourhood, which is what the paper's
    main text describes in prose.
    """
    grid = figures.load_sup_fig2c()
    table = figures.mixed_transition_table(grid)
    assert len(table) == 12
    ambiguous = [nb for nb, c in table.items() if len(c) > 1]
    assert len(ambiguous) >= 10, f"expected most mixed neighbourhoods ambiguous, got {ambiguous}"


def test_no_wider_deterministic_interaction_rule_exists():
    """Accuracy rises with radius only by exhausting the sample space."""
    rows = figures.determinism_by_radius(figures.load_sup_fig2c())
    r1 = rows[0]
    assert r1["radius"] == 1 and r1["best_accuracy"] < 0.75
    last = rows[-1]
    # near-perfect accuracy only once neighbourhoods approach the sample count
    assert last["distinct_neighbourhoods"] > 0.5 * last["samples"]


def test_stochastic_interaction_is_the_default_and_lets_both_colours_persist():
    ica = ca.evolve_interacting(60, 110, width=100, steps=100, seed=0)
    assert ica.meta["stochastic"] is True
    assert (ica.signed[-1] == -1).any() and (ica.signed[-1] == 1).any()


def test_point_source_initial_condition_matches_sup_figs_2a_b():
    ica = ca.evolve_interacting(54, 50, width=216, steps=100, initial="points", seed_gap=22)
    live = np.flatnonzero(ica.signed[0] != 0)
    assert live.size == 2 and int(live[1] - live[0]) == 22


# ---------------------------------------------------------------------------
# Figure 1F: the all-white neighbourhood, settled empirically
# ---------------------------------------------------------------------------


def test_all_white_neighbourhood_stays_white_in_the_published_figure():
    """Fig. 1F runs rule 255, whose ``000`` bit is set, yet produces a light cone.

    If the automaton's own rule applied to an all-white neighbourhood, rule 255
    would fill the entire tape at the first step.  It does not: every all-white
    neighbourhood in the published figure has a white successor.
    """
    grid = np.load(figures._DATA / "fig1f_rules255_110.npy")
    assert grid.shape == (61, 101)
    outcomes = collections.Counter()
    for t in range(grid.shape[0] - 1):
        for i in range(1, grid.shape[1] - 1):
            if grid[t, i - 1] == 0 and grid[t, i] == 0 and grid[t, i + 1] == 0:
                outcomes[int(grid[t + 1, i])] += 1
    assert set(outcomes) == {0}, f"expected only white successors, got {dict(outcomes)}"
    assert outcomes[0] > 2000


def test_simulator_reproduces_the_published_figure_1f_exactly():
    """The corrected model must regenerate the paper's own rule-255 cone."""
    ref = np.load(figures._DATA / "fig1f_rules255_110.npy")
    init = np.zeros(101, dtype=int)
    init[60] = -1  # rule 255 seed
    init[100] = 1  # rule 110 seed
    sim = ca.evolve_interacting(
        255, 110, width=101, steps=60, initial=init, seed=0, cyclic=False
    ).observed
    # compare over the rule-255 light cone, clear of the interaction band
    for t in range(61):
        hi = max(0, 96 - t)
        assert np.array_equal(sim[t, :hi], ref[t, :hi]), f"mismatch at row {t}"


# ---------------------------------------------------------------------------
# Explicit models recovered by the index-set calculus
# ---------------------------------------------------------------------------


def test_string_model_recovers_the_generating_program_of_the_regular_segment():
    """Fig. 1C-E draws ``b[i] = NOT b[i-1]`` by hand; here it is inferred."""
    m = causal_models.deconvolve_string(strings.REGULAR_SEGMENT, max_order=6)
    assert m.exact
    assert m.lags == (1,)                      # index set: the previous bit alone
    assert m.table == [1, 0]                   # negation
    regen = m.regenerate([int(c) for c in strings.REGULAR_SEGMENT[:6]], 50)
    assert regen == [int(c) for c in strings.REGULAR_SEGMENT]


def test_random_segment_admits_no_low_order_model():
    m = causal_models.deconvolve_string(strings.PAPER_STRING[50:], max_order=6)
    assert not m.exact


def test_ca_network_model_is_exact_on_the_full_global_map():
    """The decisive test: the recovered network's repertoire equals the true map."""
    rng = np.random.default_rng(0)
    diagrams = [ca.evolve_eca(60, rng.integers(0, 2, 12), 40) for _ in range(8)]
    model = causal_models.deconvolve_ca_network(diagrams, max_radius=2, rule=60)
    assert model.verification["trajectory_exact"]
    assert model.verification["global_map_exact"]
    assert model.summary()["max_index_set_size"] <= 3


# ---------------------------------------------------------------------------
# Graph deconvolution by generating mechanism (our method, graph side)
# ---------------------------------------------------------------------------


def test_mechanism_recognisers_are_exact():
    from imp_causalnet_paper.graph_mechanism import identify_mechanism
    assert identify_mechanism(graphs.complete_graph(12)).name == "complete"
    assert identify_mechanism(graphs.star_graph(12)).name == "star"
    m = identify_mechanism(graphs.kary_tree(15))
    assert m.name == "kary_tree" and dict(m.params)["k"] == 2
    # one edge short of complete is NOT complete
    K = graphs.complete_graph(12); K.remove_edge(0, 1)
    assert identify_mechanism(K).name == "none"
    assert identify_mechanism(graphs.erdos_renyi(30, 0.5, seed=0)).name == "none"


def test_kary_tree_recognition_is_labelling_independent():
    from imp_causalnet_paper.graph_mechanism import identify_mechanism
    T = graphs.kary_tree(15)
    perm = {v: i for i, v in enumerate(np.random.default_rng(0).permutation(15))}
    assert identify_mechanism(nx.relabel_nodes(T, perm)).name == "kary_tree"


def test_mechanism_peeling_solves_figure_3c_which_bdm_could_not():
    """K20 joined to a scale-free graph: BDM puts the planted edges mid-signature."""
    from imp_causalnet_paper.graph_mechanism import deconvolve_graph
    G, _, planted = graphs.join_random(
        graphs.complete_graph(20), graphs.scale_free(100, seed=0), n_links=3, seed=0
    )
    r = deconvolve_graph(G)
    assert set(r.removed) == {tuple(sorted(e)) for e in planted}
    assert [m.name for m in r.mechanisms] == ["complete"]
    assert r.mechanisms[0].n_nodes == 20


def test_mechanism_peeling_rejects_a_chance_clique_in_a_random_graph():
    """Fig. 3D has no deterministic law on either side; saying so is the right answer."""
    from imp_causalnet_paper.graph_mechanism import deconvolve_graph
    G, _, _ = graphs.join_random(
        graphs.erdos_renyi(60, 0.5, seed=1), graphs.scale_free(60, seed=1),
        n_links=3, seed=1
    )
    r = deconvolve_graph(G)
    assert r.mechanisms == []
    assert r.removed == []
    assert any(not l.accepted for l in r.layers)


def test_acceptance_criterion_is_the_papers_own_inequality():
    """A layer is kept only when detaching it costs fewer edges than it explains."""
    from imp_causalnet_paper.graph_mechanism import deconvolve_graph
    G, _, planted = graphs.join_random(
        graphs.kary_tree(15), graphs.complete_graph(12), n_links=2, seed=5
    )
    r = deconvolve_graph(G)
    assert set(r.removed) == {tuple(sorted(e)) for e in planted}
    assert sorted(m.name for m in r.mechanisms) == ["complete", "kary_tree"]
    for layer in r.layers:
        if layer.accepted:
            assert layer.boundary_edges < layer.internal_edges


# ---------------------------------------------------------------------------
# Model description length and the two-part certificate (RESEARCH_NOTES.md)
# ---------------------------------------------------------------------------


def test_model_description_length_orders_rules_by_mechanism_cost():
    from imp_causalnet_paper import measure
    costs = {r: measure.eca_model_cost(r).bits for r in (0, 204, 60, 110)}
    assert costs[0] < costs[204] < costs[60] < costs[110]
    assert measure.eca_model_cost(0).index_set_size == 0
    assert measure.eca_model_cost(60).index_set_size == 2   # left XOR centre
    assert measure.eca_model_cost(110).index_set_size == 3


def test_bdm_exceeds_the_certified_two_part_bound_on_algorithmic_data():
    """We exhibit a program generating the diagram, so its K is bounded above.

    Any estimator returning more is over-estimating on that object.  This is the
    quantitative form of Thread 1 in RESEARCH_NOTES.md.
    """
    from imp_causalnet_paper import measure
    seed = np.random.default_rng(0).integers(0, 2, 64)
    rows = measure.certificate_vs_bdm(range(256), seed, 64)
    over = sum(1 for r in rows if r["ratio"] > 1)
    assert over >= 250, f"expected nearly all rules over the bound, got {over}"
    assert max(r["ratio"] for r in rows) > 10


def test_bdm_is_many_to_one_on_mechanisms_while_index_sets_are_not():
    """78 rule pairs sit within a bit of each other; we identify all 256 uniquely."""
    from imp_causalnet_paper.causalbool_mirror import consistent_rules
    seed = np.random.default_rng(0).integers(0, 2, 48)
    vals, unique = [], 0
    for r in range(256):
        d = ca.evolve_eca(r, seed, 48)
        vals.append(complexity.bdm_2d(d))
        T, W = d.shape
        s = [(int(4*d[t, (i-1) % W] + 2*d[t, i] + d[t, (i+1) % W]), int(d[t+1, i]))
             for t in range(T-1) for i in range(W)]
        unique += consistent_rules(s) == frozenset({r})
    assert unique == 256
    collisions = sum(1 for i in range(256) for j in range(i+1, 256)
                     if abs(vals[i] - vals[j]) < 1.0)
    assert collisions > 20
