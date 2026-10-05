"""D3 reachability on hand-computable subset spaces (synthetic costs)."""
from __future__ import annotations

from search_diagnosis.analysis import d3_graph, equal_cell_mean, unit_cell_means


def test_tie_barrier_hides_a_cheaper_eligible_subset():
    cost = {(): 100, (100,): 100, (200,): 110, (100, 200): 80}
    g = d3_graph([100, 200], 256, cost)
    assert g["strict_reachable"] == 1 and g["eligibility_reachable"] == 4
    assert g["cheapest_strict"]["bits"] == 100 and g["cheapest_eligible"]["bits"] == 80
    assert g["restricted_path_barrier"] and not g["eligibility_obstruction"]
    b = g["barrier"]
    assert (b["frontier_edges"], b["equality_edges"], b["positive_edges"]) == (2, 1, 1)
    assert b["kind"] == "equality" and b["min_delta_bits"] == 0


def test_positive_step_barrier():
    cost = {(): 100, (100,): 104, (200,): 110, (100, 200): 80}
    g = d3_graph([100, 200], 256, cost)
    assert g["restricted_path_barrier"] and g["barrier"]["kind"] == "positive_cost_step"
    assert g["barrier"]["min_delta_bits"] == 4


def test_strict_path_reaches_the_optimum_without_barrier():
    cost = {(): 100, (100,): 90, (200,): 110, (100, 200): 80}
    g = d3_graph([100, 200], 256, cost)
    assert g["strict_reachable"] == 3 and not g["restricted_path_barrier"]
    assert g["cheapest_strict"]["subset"] == [100, 200]


def test_eligibility_obstruction_is_not_a_cost_barrier():
    # n = 70: after either cut the remaining parent is < 64 bits, so {10, 20} is ineligible
    cost = {(): 100, (10,): 99, (20,): 98, (10, 20): 50}
    g = d3_graph([10, 20], 70, cost)
    assert g["eligibility_reachable"] == 3
    assert g["eligibility_obstruction"] and not g["restricted_path_barrier"]
    assert g["cheapest_all"]["bits"] == 50 and g["cheapest_eligible"]["bits"] == 98


def test_parent_eligibility_depends_on_the_split_segment():
    cost = {(): 9, (30,): 8, (60,): 8, (30, 60): 7}
    g = d3_graph([30, 60], 100, cost)
    e = {(tuple(x["from"]), x["cut"]): x["eligible"] for x in g["edges"]}
    assert e[((30,), 60)] and not e[((60,), 30)]       # [30,100) is 70 bits; [0,60) is 60


def test_graph_limited_subset_is_not_a_state():
    cost = {(): 100, (100,): None, (200,): 120, (100, 200): 10}
    g = d3_graph([100, 200], 256, cost)
    assert g["cheapest_all"]["bits"] == 10 and g["eligibility_reachable"] == 3


def test_weighting_pair_then_unit_then_equal_cells():
    ids = ["confirmation-F01-256-3000-base", "confirmation-F01-256-3000-ragged",
           "confirmation-F01-256-3001-base", "confirmation-F01-256-3001-ragged",
           "confirmation-F02-256-3000-base", "confirmation-F02-256-3000-ragged"]
    v = dict(zip(ids, [1.0, 3.0, 0.0, 0.0, 10.0, 10.0]))
    cells = unit_cell_means(v, ids)
    assert cells["confirmation|F01|256"]["mean"] == 1.0          # (2 + 0) / 2, not pooled
    assert equal_cell_mean(cells) == 5.5
    v[ids[1]] = None
    cells = unit_cell_means(v, ids)
    assert cells["confirmation|F01|256"]["mean"] is None
    assert cells["confirmation|F01|256"]["partial_mean"] == 0.0
    assert equal_cell_mean(cells) is None
