# Stage L: learning mechanism and economics pilot

- Development design gate: `{"fixtures": 15, "informative": 15, "informative_by_family": {"aliasing": 3, "dependency": 3, "mixed": 3, "scalar": 3, "vector": 3}, "minimum": 10, "per_family_minimum": 1, "status": "PASS", "uninformative": []}`
- Evaluation design gate: `{"fixtures": 30, "informative": 30, "informative_by_family": {"aliasing": 6, "dependency": 6, "mixed": 6, "scalar": 6, "vector": 6}, "minimum": 20, "per_family_minimum": 3, "status": "PASS", "uninformative": []}`

| Contrast (tree minus control) | yield diff | 98.33% | +/0/- | passes |
|---|---:|---|---|---|
| tree_minus_hamming | -0.1073 | [-0.1323, -0.0844] | 0/0/30 | False |
| tree_minus_random_mean | +0.0611 | [+0.0330, +0.0975] | 26/1/3 | True |
| tree_minus_shuffled_tree | +0.0448 | [+0.0240, +0.0667] | 19/8/3 | False |

Mechanism signal: **FAIL_OR_INCONCLUSIVE**.

Mean yield by ordering: {'tree': 0.1021, 'hamming': 0.2094, 'shuffled_tree': 0.0573, 'ascending': 0.0896, 'random_2026092610': 0.0354, 'random_2026092611': 0.0406, 'random_2026092612': 0.0563, 'random_2026092613': 0.0354, 'random_2026092614': 0.0396, 'random_2026092615': 0.0344, 'random_2026092616': 0.0417, 'random_2026092617': 0.049, 'random_2026092618': 0.0365, 'random_2026092619': 0.0406}

Economics: 0/100 development programs had a query reaching 20 distinct case-validated observations (threshold 10%): **ECONOMICALLY_UNAVAILABLE**.
