"""Published numbers from the paper, for side-by-side comparison.

Nothing here is computed; these are transcriptions of Tables 1-5 and of the
dichotomy scores quoted in Section 3.2, kept in one place so the notebook can
put the replication next to the original without re-typing values.
"""

from __future__ import annotations

# Table 1
DATASET_INFO = {
    'FreeSolv': dict(n_graphs=643, task='hydration free energy', type='regression', metric='RMSE'),
    'ESOL': dict(n_graphs=1128, task='solubility in water', type='regression', metric='RMSE'),
    'Lipophilicity': dict(n_graphs=4200, task='octanol/water distribution coeff.',
                          type='regression', metric='RMSE'),
    'BACE': dict(n_graphs=1522, task='beta-secretase binding', type='classification',
                 metric='ROC-AUC'),
    'BBBP': dict(n_graphs=2053, task='blood-brain barrier crossing', type='classification',
                 metric='ROC-AUC'),
    'ClinTox': dict(n_graphs=1491, task='clinical trial toxicity and FDA approval',
                    type='classification', metric='ROC-AUC'),
}

# Table 3: (model, dataset) -> {noise: (without path, with path)} of the 3-run means.
# The gamma = 0 rows are Table 2.
TABLE3 = {
    ('graphormer', 'FreeSolv'): {0.0: (3.55, 2.91), 0.1: (4.219, 3.54), 0.2: (4.16, 3.42),
                                 0.3: (4.24, 3.44), 0.4: (4.02, 3.47), 0.5: (4.20, 3.49)},
    ('graphormer', 'ESOL'): {0.0: (1.20, 1.01), 0.1: (1.23, 1.19), 0.2: (1.31, 1.16),
                             0.3: (1.36, 1.22), 0.4: (1.34, 1.51), 0.5: (1.41, 1.62)},
    ('graphormer', 'Lipophilicity'): {0.0: (0.91, 0.99), 0.1: (1.02, 1.05), 0.2: (1.03, 1.04),
                                      0.3: (1.02, 1.06), 0.4: (1.03, 1.06), 0.5: (1.00, 1.07)},
    ('graphormer', 'BACE'): {0.0: (0.782, 0.735), 0.1: (0.779, 0.761), 0.2: (0.781, 0.767),
                             0.3: (0.780, 0.768), 0.4: (0.776, 0.783), 0.5: (0.777, 0.781)},
    ('graphormer', 'BBBP'): {0.0: (0.686, 0.709), 0.1: (0.693, 0.661), 0.2: (0.687, 0.653),
                             0.3: (0.688, 0.663), 0.4: (0.684, 0.636), 0.5: (0.670, 0.641)},
    ('graphormer', 'ClinTox'): {0.0: (0.602, 0.779), 0.1: (0.594, 0.582), 0.2: (0.594, 0.575),
                                0.3: (0.580, 0.578), 0.4: (0.579, 0.580), 0.5: (0.581, 0.577)},

    ('mix_hop', 'FreeSolv'): {0.0: (2.45, 2.61), 0.1: (2.43, 2.82), 0.2: (2.87, 2.73),
                              0.3: (3.16, 3.23), 0.4: (3.74, 3.18), 0.5: (3.89, 3.32)},
    ('mix_hop', 'ESOL'): {0.0: (1.01, 0.97), 0.1: (1.19, 1.27), 0.2: (1.28, 1.23),
                          0.3: (1.48, 1.41), 0.4: (1.68, 1.57), 0.5: (1.83, 1.63)},
    ('mix_hop', 'Lipophilicity'): {0.0: (0.96, 0.95), 0.1: (1.05, 1.02), 0.2: (1.16, 1.11),
                                   0.3: (1.23, 1.23), 0.4: (1.33, 1.39), 0.5: (1.45, 1.51)},
    ('mix_hop', 'BACE'): {0.0: (0.799, 0.798), 0.1: (0.737, 0.780), 0.2: (0.671, 0.691),
                          0.3: (0.674, 0.752), 0.4: (0.630, 0.700), 0.5: (0.676, 0.663)},
    ('mix_hop', 'BBBP'): {0.0: (0.707, 0.678), 0.1: (0.671, 0.656), 0.2: (0.657, 0.629),
                          0.3: (0.602, 0.614), 0.4: (0.592, 0.599), 0.5: (0.567, 0.603)},
    ('mix_hop', 'ClinTox'): {0.0: (0.596, 0.591), 0.1: (0.581, 0.559), 0.2: (0.589, 0.539),
                             0.3: (0.578, 0.555), 0.4: (0.627, 0.463), 0.5: (0.550, 0.493)},

    ('t_hop', 'FreeSolv'): {0.0: (2.87, 2.73), 0.1: (3.68, 3.07), 0.2: (3.34, 3.35),
                            0.3: (3.80, 3.34), 0.4: (3.41, 3.34), 0.5: (3.91, 3.55)},
    ('t_hop', 'ESOL'): {0.0: (1.00, 1.00), 0.1: (1.09, 1.32), 0.2: (1.26, 1.30),
                        0.3: (1.22, 1.34), 0.4: (1.50, 1.52), 0.5: (1.62, 1.42)},
    ('t_hop', 'Lipophilicity'): {0.0: (0.78, 0.88), 0.1: (0.82, 1.01), 0.2: (0.88, 1.00),
                                 0.3: (0.92, 1.01), 0.4: (0.93, 1.02), 0.5: (0.93, 1.04)},
    ('t_hop', 'BACE'): {0.0: (0.852, 0.746), 0.1: (0.819, 0.764), 0.2: (0.827, 0.770),
                        0.3: (0.804, 0.687), 0.4: (0.804, 0.774), 0.5: (0.789, 0.763)},
    ('t_hop', 'BBBP'): {0.0: (0.649, 0.623), 0.1: (0.645, 0.618), 0.2: (0.642, 0.620),
                        0.3: (0.632, 0.612), 0.4: (0.631, 0.611), 0.5: (0.624, 0.634)},
    ('t_hop', 'ClinTox'): {0.0: (0.785, 0.752), 0.1: (0.826, 0.681), 0.2: (0.806, 0.591),
                           0.3: (0.799, 0.627), 0.4: (0.784, 0.667), 0.5: (0.773, 0.538)},
}

# Table 3 / Table 4: published PUMs, as sixths.
PUM = {
    'graphormer': {'FreeSolv': 6 / 6, 'ESOL': 4 / 6, 'Lipophilicity': 0 / 6,
                   'BACE': 2 / 6, 'BBBP': 1 / 6, 'ClinTox': 2 / 6},
    'mix_hop': {'FreeSolv': 3 / 6, 'ESOL': 5 / 6, 'Lipophilicity': 3 / 6,
                'BACE': 4 / 6, 'BBBP': 3 / 6, 'ClinTox': 0 / 6},
    't_hop': {'FreeSolv': 5 / 6, 'ESOL': 1 / 6, 'Lipophilicity': 0 / 6,
              'BACE': 0 / 6, 'BBBP': 1 / 6, 'ClinTox': 0 / 6},
}

# Section 3.2
DICHOTOMY = {'graphormer': 29 / 36, 'mix_hop': 24 / 36, 't_hop': 33 / 36}

# Table 4, first row; the columns are printed in ascending complexity order.
AOAC = {'FreeSolv': 105.61, 'ESOL': 216.63, 'BBBP': 488.75, 'ClinTox': 510.71,
        'Lipophilicity': 577.11, 'BACE': 717.38}
AOAC_ORDER = ['FreeSolv', 'ESOL', 'BBBP', 'ClinTox', 'Lipophilicity', 'BACE']

# Table 4, last column.
CORRELATION = {'graphormer': -0.84, 'mix_hop': -0.19, 't_hop': -0.81,
               'across all models': -0.82}

# Table 5.
SILHOUETTE = {'aoac': 0.71, 'graphormer': 0.60, 'mix_hop': 0.61, 't_hop': 0.72,
              'across all models': 0.62}
CLUSTER_LABELS = {
    'aoac': {'FreeSolv': 0, 'ESOL': 0, 'BBBP': 1, 'ClinTox': 1,
             'Lipophilicity': 1, 'BACE': 1},
    'graphormer': {'FreeSolv': 0, 'ESOL': 0, 'BBBP': 1, 'ClinTox': 1,
                   'Lipophilicity': 1, 'BACE': 1},
    'mix_hop': {'FreeSolv': 0, 'ESOL': 0, 'BBBP': 0, 'ClinTox': 1,
                'Lipophilicity': 0, 'BACE': 0},
    't_hop': {'FreeSolv': 0, 'ESOL': 1, 'BBBP': 1, 'ClinTox': 1,
              'Lipophilicity': 1, 'BACE': 1},
    'across all models': {'FreeSolv': 0, 'ESOL': 0, 'BBBP': 1, 'ClinTox': 1,
                          'Lipophilicity': 1, 'BACE': 1},
}
