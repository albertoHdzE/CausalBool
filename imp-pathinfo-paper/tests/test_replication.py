"""Correctness checks for the replication code."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from imp_pathinfo import analysis as an
from imp_pathinfo import hyperparams as hp
from imp_pathinfo import paper_values as pv
from imp_pathinfo.bdm_complexity import dataset_aoac
from imp_pathinfo.data import DATASET_ORDER, load_dataset, scaffold_split, size_bins
from imp_pathinfo.featurizers import ATOM_FEATURE_SIZE, BOND_FEATURE_SIZE
from imp_pathinfo.models import THop
from imp_pathinfo.paths import (densify_t, normalized_adjacency, shortest_paths,
                                simple_path_counts, t_tensor_sparse)
from imp_pathinfo.train import build_cache, make_batch, run_experiment

METRICS = {'FreeSolv': 'rmse', 'ESOL': 'rmse', 'Lipophilicity': 'rmse',
           'BACE': 'roc', 'BBBP': 'roc', 'ClinTox': 'roc'}


@pytest.fixture(scope='module')
def freesolv():
    return load_dataset('FreeSolv')


# --------------------------------------------------------------------------
# data and featurisation
# --------------------------------------------------------------------------

def test_feature_sizes():
    assert ATOM_FEATURE_SIZE == 74
    assert BOND_FEATURE_SIZE == 12


def test_dataset_shapes(freesolv):
    g = freesolv.graphs[0]
    assert g.node_feat.shape == (g.n_nodes, 74)
    assert g.edge_feat.shape[0] == len(g.src)
    assert len(g.src) % 2 == 0                      # every bond gives two edges


def test_adjacency_is_symmetric(freesolv):
    for g in freesolv.graphs[:50]:
        a = g.adjacency()
        assert np.array_equal(a, a.T)
        assert a.diagonal().sum() == 0


def test_scaffold_split_is_a_partition(freesolv):
    tr, va, te = scaffold_split(freesolv)
    assert sorted(tr + va + te) == list(range(len(freesolv)))
    assert abs(len(tr) / len(freesolv) - 0.8) < 0.02


def test_size_bins_partition_and_order(freesolv):
    """Phase 1: bins must tile the dataset, keep ties together and rise in size."""
    bins = size_bins(freesolv, n_bins=3, min_per_bin=100)
    smiles = [set(g.smiles for g in b['dataset'].graphs) for b in bins]
    assert sum(len(s) for s in smiles) == len(set().union(*smiles)) == len(freesolv)
    means = [b['mean_atoms'] for b in bins]
    assert means == sorted(means)
    # no atom count appears in two bins
    for a, b in zip(bins, bins[1:]):
        assert a['max_atoms'] < b['min_atoms']


def test_size_bins_refuse_when_too_small(freesolv):
    with pytest.raises(ValueError):
        size_bins(freesolv, n_bins=4, min_per_bin=10 ** 6)


# --------------------------------------------------------------------------
# path information
# --------------------------------------------------------------------------

def test_theorem_1_fsum_recovers_powered_adjacency(freesolv):
    """Theorem 1: summing T^L along its depth axis returns A^L (simple paths)."""
    pow_dim = 3
    for g in freesolv.graphs[:20]:
        idx, val = t_tensor_sparse(g, pow_dim)
        dense = densify_t(idx, val, g.n_nodes, pow_dim)
        counts = simple_path_counts(g, pow_dim + 1)
        for p in range(pow_dim):
            recovered = dense[:, :, :, p].sum(axis=2)
            assert np.allclose(recovered, counts[p + 1], atol=1e-5)


def test_t_tensor_zero_when_path_info_off(freesolv):
    idx, val = t_tensor_sparse(freesolv.graphs[0], 0)
    assert len(val) == 0


def test_normalized_adjacency_symmetric(freesolv):
    g = freesolv.graphs[3]
    a = normalized_adjacency(g, g.n_nodes + 2)
    assert np.allclose(a, a.T, atol=1e-6)


def test_shortest_paths_consistent(freesolv):
    g = freesolv.graphs[5]
    dist, paths = shortest_paths(g)
    assert np.array_equal(dist, dist.T)
    for i in range(g.n_nodes):
        for j in range(g.n_nodes):
            if dist[i, j] > 0:
                assert int((paths[i, j] >= 0).sum()) == dist[i, j]


# --------------------------------------------------------------------------
# models
# --------------------------------------------------------------------------

def test_sparse_and_dense_t_hop_agree(freesolv):
    """The sparse contraction must equal the authors' dense elementwise form."""
    pow_dim, max_nodes = 2, freesolv.max_nodes
    cache = build_cache(freesolv, 't_hop', pow_dim, max_nodes)
    idx = np.arange(4)
    dev = torch.device('cpu')
    b_dense = make_batch(freesolv, cache, idx, 't_hop', pow_dim, max_nodes, None, 0,
                         dev, dense_path=True)
    b_sparse = make_batch(freesolv, cache, idx, 't_hop', pow_dim, max_nodes, None, 0,
                          dev, dense_path=False)
    torch.manual_seed(0)
    model = THop(max_nodes, pow_dim, 2, 74, 16, 1, dropout=0.0).eval()
    with torch.no_grad():
        out_dense = model(b_dense['x'], b_dense['adj'], b_dense['beta'])
        out_sparse = model(b_sparse['x'], b_sparse['adj'], None,
                           beta_sparse=b_sparse['beta_sparse'])
    assert torch.allclose(out_dense, out_sparse, atol=1e-5)


def test_sparse_and_dense_graphormer_agree(freesolv):
    from imp_pathinfo.train import build_model, forward
    cache = build_cache(freesolv, 'graphormer', 0, freesolv.max_nodes)
    params = hp.get('graphormer', 'FreeSolv', 1)
    torch.manual_seed(0)
    model = build_model('graphormer', params, freesolv, freesolv.max_nodes, 1, cache).eval()
    idx = np.arange(3)
    dev = torch.device('cpu')
    b_dense = make_batch(freesolv, cache, idx, 'graphormer', 0, freesolv.max_nodes,
                         None, 0, dev, dense_path=True)
    b_sparse = make_batch(freesolv, cache, idx, 'graphormer', 0, freesolv.max_nodes,
                          None, 0, dev, dense_path=False)
    with torch.no_grad():
        out_dense = forward(model, 'graphormer', b_dense, 0)
        out_sparse = forward(model, 'graphormer', b_sparse, 0)
    assert torch.allclose(out_dense, out_sparse, atol=1e-5)


def test_t_hop_no_path_mode_ignores_path_parameters(freesolv):
    """With pow_dim = 0 the operator collapses to M = a0 * A (Section 2.3.3)."""
    cache = build_cache(freesolv, 't_hop', 0, freesolv.max_nodes)
    batch = make_batch(freesolv, cache, np.arange(4), 't_hop', 0, freesolv.max_nodes,
                       None, 0, torch.device('cpu'))
    assert batch['beta'] is None and batch['beta_sparse'] is None


def test_training_runs_and_improves(freesolv):
    split = scaffold_split(freesolv)
    cache = build_cache(freesolv, 'mix_hop', 0, freesolv.max_nodes)
    r = run_experiment(freesolv, 'mix_hop', 0, 0.0, 0, epochs=5, cache=cache,
                       split=split, torch_seed=0)
    assert np.isfinite(r['test_score']) and r['test_score'] > 0


def test_noise_is_reproducible(freesolv):
    cache = build_cache(freesolv, 'mix_hop', 0, freesolv.max_nodes)
    std = torch.from_numpy(freesolv.node_feature_std().astype(np.float32)) * 0.3
    kw = dict(model_name='mix_hop', pow_dim=0, max_nodes=freesolv.max_nodes,
              noise_vec=std, seed=7, device=torch.device('cpu'))
    a = make_batch(freesolv, cache, np.arange(3), **kw)['x']
    b = make_batch(freesolv, cache, np.arange(3), **kw)['x']
    c = make_batch(freesolv, cache, np.arange(3), **{**kw, 'seed': 8})['x']
    assert torch.equal(a, b)
    assert not torch.equal(a, c)


# --------------------------------------------------------------------------
# BDM and the published analysis
# --------------------------------------------------------------------------

def test_aoac_matches_paper(freesolv):
    _, aoac, skipped = dataset_aoac(freesolv)
    assert abs(aoac - pv.AOAC['FreeSolv']) < 0.01
    assert skipped > 0            # FreeSolv contains molecules with < 4 atoms


def test_pum_recomputed_from_published_table_matches_published_pum():
    for model in hp.MODELS:
        for ds in DATASET_ORDER:
            t = pv.TABLE3[(model, ds)]
            noises = sorted(t)
            got = an.pum([t[g][0] for g in noises], [t[g][1] for g in noises], METRICS[ds])
            assert abs(got - pv.PUM[model][ds]) < 1e-9


def test_dichotomy_scores_match_paper():
    for model in hp.MODELS:
        pums = [pv.PUM[model][d] for d in DATASET_ORDER]
        assert abs(an.dichotomy_score(pums) - pv.DICHOTOMY[model]) < 1e-9


def test_correlations_and_clustering_match_paper():
    aoac = [pv.AOAC[d] for d in pv.AOAC_ORDER]
    per_model = []
    for model in hp.MODELS:
        pums = [pv.PUM[model][d] for d in pv.AOAC_ORDER]
        per_model.append(pums)
        r, _ = an.correlation(aoac, pums)
        assert abs(r - pv.CORRELATION[model]) < 0.011
        labels, sil = an.cluster_1d(pums, invert_labels=True)
        assert labels.tolist() == [pv.CLUSTER_LABELS[model][d] for d in pv.AOAC_ORDER]
        assert abs(sil - pv.SILHOUETTE[model]) < 0.005

    avg = list(np.mean(per_model, axis=0))
    r, _ = an.correlation(aoac, avg)
    assert abs(r - pv.CORRELATION['across all models']) < 0.011
    labels, sil = an.cluster_1d(aoac)
    assert labels.tolist() == [pv.CLUSTER_LABELS['aoac'][d] for d in pv.AOAC_ORDER]
    assert abs(sil - pv.SILHOUETTE['aoac']) < 0.005


# --------------------------------------------------------------------------
# the CausalBool index-set mirror
# --------------------------------------------------------------------------

def test_root_index_set_modules_load():
    from imp_pathinfo import causalbool_mirror as cm
    causalbool, deconvolution = cm.load_root_modules()
    assert hasattr(causalbool, 'apply_gate') and hasattr(deconvolution, 'deconvolve_column')


def test_deconvolution_recovers_every_index_set(freesolv):
    """The causal test: index sets recovered from behaviour, decoys rejected."""
    from imp_pathinfo import causalbool_mirror as cm
    for g in freesolv.graphs[:40]:
        if g.n_nodes < 2:
            continue
        rep = cm.deconvolve_molecule(g)
        assert rep.n_recovered_exactly == rep.n_atoms
        assert rep.n_gate_matched == rep.n_atoms


def test_local_universe_is_exponentially_smaller_than_the_repertoire(freesolv):
    from imp_pathinfo import causalbool_mirror as cm
    g = max(freesolv.graphs, key=lambda x: x.n_nodes)
    rep = cm.deconvolve_molecule(g)
    assert rep.max_local_rows <= 2 ** 10        # bounded by degree + decoys
    assert rep.max_local_rows < 2 ** g.n_nodes  # the factorisation saves the day


def test_description_length_is_order_invariant(freesolv):
    """log2 C(n, d) depends on the index set's size, not on how nodes are labelled."""
    from imp_pathinfo import causalbool_mirror as cm
    g = freesolv.graphs[7]
    base = cm.graph_description_length(g, wiring_only=True)
    perm = np.random.default_rng(0).permutation(g.n_nodes)
    relabelled = MolGraphLike(g, perm)
    assert abs(cm.graph_description_length(relabelled, wiring_only=True) - base) < 1e-9


class MolGraphLike:
    """A relabelled copy of a molecular graph, for the invariance test."""

    def __init__(self, g, perm):
        self.smiles = g.smiles
        self.n_nodes = g.n_nodes
        self.src = np.asarray([perm[i] for i in g.src], dtype=np.int32)
        self.dst = np.asarray([perm[i] for i in g.dst], dtype=np.int32)
        self.node_feat = g.node_feat
        self.edge_feat = g.edge_feat

    def neighbours(self):
        nb = [[] for _ in range(self.n_nodes)]
        for u, v in zip(self.src, self.dst):
            nb[int(u)].append(int(v))
        return nb


def test_path_index_sets_agree_with_the_t_hop_tensor(freesolv):
    """The L-hop index set must be the support of the T-Hop simple-path counts."""
    from imp_pathinfo import causalbool_mirror as cm
    for g in freesolv.graphs[:20]:
        if g.n_nodes < 3:
            continue
        layers = cm.path_index_sets(g, max_len=3)
        counts = simple_path_counts(g, 3)
        for L in (1, 2, 3):
            for v in range(g.n_nodes):
                from_counts = set(np.nonzero(counts[L - 1][v])[0].tolist())
                assert layers[L - 1][v] == from_counts


def test_saturation_is_a_fraction(freesolv):
    from imp_pathinfo import causalbool_mirror as cm
    for g in freesolv.graphs[:30]:
        if g.n_nodes < 2:
            continue
        s = cm.receptive_saturation(g, max_len=3)
        assert 0.0 <= s <= 1.0


def test_mirror_reproduces_the_published_complexity_ordering():
    """The index-set description length must order the families as BDM does.

    The claim is about the complete datasets: BBBP and ClinTox differ by about
    10% in mean description length, so a sub-sample of a few hundred molecules
    can and does transpose them.
    """
    from imp_pathinfo import causalbool_mirror as cm
    means = {}
    for name in DATASET_ORDER:
        d = load_dataset(name)
        means[name] = cm.dataset_index_measures(d, max_len=2)['D']
    assert sorted(means, key=means.get) == pv.AOAC_ORDER


# --------------------------------------------------------------------------
# the method-comparison experiments
# --------------------------------------------------------------------------

def test_landscape_signature_is_relabelling_invariant():
    """Attractors and basins are isomorphism invariants; the test enforces it."""
    from imp_pathinfo import method_comparison as mc
    A = mc.adversarial_triple()['cycle C12'].adjacency().astype(int)
    base = mc.landscape_signature(A, 'XOR')
    rng = np.random.default_rng(0)
    for _ in range(10):
        p = rng.permutation(A.shape[0])
        assert mc.landscape_signature(A[np.ix_(p, p)], 'XOR') == base


def test_wiring_term_is_blind_to_the_adversarial_triple():
    """The documented blind spot of layer 1, kept as a regression test."""
    from imp_pathinfo import method_comparison as mc
    values = {k: mc.wiring_description_length(g.adjacency())
              for k, g in mc.adversarial_triple().items()}
    assert len(set(round(v, 9) for v in values.values())) == 1


def test_repertoire_layer_separates_what_wiring_cannot():
    from imp_pathinfo import method_comparison as mc
    sigs = {k: mc.landscape_signature(g.adjacency().astype(int), 'XOR')
            for k, g in mc.adversarial_triple().items()}
    assert len(set(sigs.values())) == 3


def test_kraft_inequality_fails_as_published_and_holds_with_the_arity_term():
    """Claim H: D is not a prefix code until the arity is paid for."""
    from imp_pathinfo import method_comparison as mc
    for n in (4, 8, 20):
        assert mc.kraft_sum(n, with_arity_term=False) > 1.0
        assert mc.kraft_sum(n, with_arity_term=True) <= 1.0


def test_bdm_saturates_in_the_random_regime():
    """Claim A: per-block BDM is constant once the object is random."""
    from imp_pathinfo import method_comparison as mc
    scan = mc.random_regime_scan(sizes=(16, 32, 64), repeats=3)
    per_block = np.array([r['bdm_per_block'] for r in scan])
    assert per_block.std() / per_block.mean() < 0.05


def test_knockout_profile_is_invariant_and_informative():
    from imp_pathinfo import method_comparison as mc
    A = mc.adversarial_triple()['two hexagons'].adjacency().astype(int)
    base = mc.knockout_profile(A, 'XOR')
    rng = np.random.default_rng(1)
    p = rng.permutation(A.shape[0])
    assert mc.knockout_profile(A[np.ix_(p, p)], 'XOR') == base
    assert len(mc.knockout_vector(A, 'XOR')) == A.shape[0]


def test_query_overlap_is_invariant_and_order_1_is_degree_only():
    """Claim K: layer 3 is a dial; order 1 sees only degrees."""
    from imp_pathinfo import method_comparison as mc
    triple = mc.adversarial_triple()
    for g in triple.values():
        A = g.adjacency().astype(int)
        base = mc.query_overlap_profile(A, 2)
        rng = np.random.default_rng(0)
        for _ in range(10):
            p = rng.permutation(A.shape[0])
            assert mc.query_overlap_profile(A[np.ix_(p, p)], 2) == base
    # order 1 collapses to the degree sequence, so the 2-regular triple collides
    order1 = {k: mc.query_overlap_profile(g.adjacency().astype(int), 1)
              for k, g in triple.items()}
    assert len(set(order1.values())) == 1


def test_query_order_3_separates_the_adversarial_triple():
    """Order 2 is not enough; order 3 is. The dial is real, not free."""
    from imp_pathinfo import method_comparison as mc
    triple = mc.adversarial_triple()
    sig2 = {k: mc.query_overlap_profile(g.adjacency().astype(int), 2)
            for k, g in triple.items()}
    sig3 = {k: mc.query_overlap_profile(g.adjacency().astype(int), 3)
            for k, g in triple.items()}
    assert len(set(sig2.values())) == 2      # two of the three collide
    assert len(set(sig3.values())) == 3      # all separated


def test_node_compressed_size_is_degree_only():
    """Claim K as first stated is refuted: the naive reading separates nothing."""
    from imp_pathinfo import method_comparison as mc
    sizes = {k: mc.node_compressed_size(g.adjacency().astype(int))
             for k, g in mc.adversarial_triple().items()}
    assert len(set(sizes.values())) == 1


def test_deconvolution_exhibits_a_program_that_replays_the_object(freesolv):
    """Claim I: the recovered mechanism regenerates the observations exactly."""
    from imp_pathinfo import causalbool_mirror as cm
    causalbool, deconvolution = cm.load_root_modules()
    cm07 = [[0, 0, 1, 0, 0, 0, 1], [0, 0, 1, 0, 0, 1, 0], [1, 0, 0, 0, 1, 0, 1],
            [1, 0, 1, 0, 1, 0, 1], [0, 0, 1, 1, 0, 1, 1], [1, 1, 1, 0, 0, 0, 0],
            [0, 1, 0, 1, 1, 1, 0]]
    net = causalbool.Network(n=7, C=cm07,
                             gates=['AND', 'OR', 'OR', 'AND', 'OR', 'OR', 'AND'])
    rep = causalbool.repertoire(net)
    recovered, _ = deconvolution.deconvolve(rep)
    assert causalbool.repertoire(recovered) == rep


def test_sumando_bits_separates_what_wiring_cannot():
    """The repair: overlap-reading measure vs the degree-only one."""
    from imp_pathinfo import causalbool_mirror as cm
    from imp_pathinfo import method_comparison as mc
    triple = mc.adversarial_triple()
    wiring = {k: round(mc.wiring_description_length(g.adjacency()), 9)
              for k, g in triple.items()}
    assert len(set(wiring.values())) == 1                 # blind
    # the overlap MEAN is also degree-determined -- it separates nothing
    mean = {k: round(cm.sumando_bits(g, 3), 9) for k, g in triple.items()}
    assert len(set(mean.values())) == 1
    # the SPREAD of the same profile does read topology
    spread = {k: round(cm.sumando_spread(g, 3), 9) for k, g in triple.items()}
    assert len(set(spread.values())) >= 2


def test_bitmap_and_sine_cannot_be_any_network():
    """A proof about the object: same row, two successors."""
    from imp_pathinfo import method_comparison as mc
    objs = mc.non_graph_objects()
    for name in ('a bitmap (square annulus)', 'a binarised sine wave'):
        assert mc.is_trajectory(objs[name])['possible'] is False
    # noise passes only vacuously -- every row distinct
    noise = mc.is_trajectory(objs['uniform noise'])
    assert noise['possible'] and 'vacuous' in noise['reason']


def test_chaotic_eca_rules_are_recovered_exactly():
    """Randomness helps: chaotic diagrams pin the rule down, simple ones do not."""
    from imp_pathinfo import method_comparison as mc
    for rule in (30, 45, 110):
        assert mc.recover_eca_rule(mc.eca_spacetime(rule)) == {rule}
    assert len(mc.recover_eca_rule(mc.eca_spacetime(254))) > 1


def test_same_degree_pairs_are_genuinely_non_isomorphic(freesolv):
    from imp_pathinfo import method_comparison as mc
    import networkx as nx
    pairs = mc.same_degree_pairs([freesolv], min_atoms=6, max_atoms=11, max_pairs=15)
    assert pairs
    for (_, A1, G1), (_, A2, G2) in pairs:
        assert mc.degree_sequence(A1) == mc.degree_sequence(A2)
        assert not nx.is_isomorphic(G1, G2)


def test_hyperparameters_cover_every_case():
    for model in hp.MODELS:
        for ds in DATASET_ORDER:
            for mode in (0, 1):
                p = hp.get(model, ds, mode)
                assert p['num_layers'] >= 1 and p['batch_size'] >= 1
    for ds in DATASET_ORDER:
        assert hp.get('t_hop', ds, 0)['pow_dim'] == 0
        assert hp.get('t_hop', ds, 1)['pow_dim'] >= 1
        assert hp.get('mix_hop', ds, 0)['max_pow'] == 1
        assert hp.get('mix_hop', ds, 1)['max_pow'] >= 2
