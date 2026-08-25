"""The Optuna-selected hyperparameters used for every experiment in the paper.

The authors ran an Optuna sweep on the validation split of each of the six
*original* datasets, for each model and each mode, and then reused those
settings unchanged for the five noisy variants of the same family (Section
3.2).  The values below are transcribed from the three PDFs shipped in the
authors' repository:

    reference/kaust_path_project/path_project/<model>/hyperparameters/*.pdf

Fixed settings that are not swept come from the defaults of the authors'
training scripts: Adam, 200 epochs, early-stopping patience 10 on the
validation metric, scaffold splitting 80:10:10, SmoothL1 loss for regression
and BCE-with-logits for classification, layer normalisation for T-Hop, batch
normalisation for Mix-Hop, residual connections on for T-Hop.
"""

from __future__ import annotations

EPOCHS = 200
PATIENCE = 10
REPETITIONS = 3

GRAPHORMER = {
    ('FreeSolv', 0): dict(num_layers=3, small_hidden_dim=142, num_heads=9,
                          dropout=0.7347780293219217, weight_decay=1.538290349900921e-18,
                          batch_size=2, lr=3.7798891539041065e-05),
    ('FreeSolv', 1): dict(num_layers=2, small_hidden_dim=140, num_heads=4,
                          dropout=0.4356401455970282, weight_decay=0.0020369910681372685,
                          batch_size=9, lr=5.4525151321520415e-05),
    ('ESOL', 0): dict(num_layers=9, small_hidden_dim=86, num_heads=6,
                      dropout=0.15, weight_decay=1.7486694373393174e-11,
                      batch_size=6, lr=3.67247780674997e-05),
    ('ESOL', 1): dict(num_layers=4, small_hidden_dim=21, num_heads=3,
                      dropout=0.04280483931026283, weight_decay=0.00047149322701399004,
                      batch_size=3, lr=0.00010030295499602398),
    ('Lipophilicity', 0): dict(num_layers=1, small_hidden_dim=167, num_heads=10,
                               dropout=0.04053446947021075, weight_decay=3.0532103567123417e-13,
                               batch_size=5, lr=2.6119467092453507e-05),
    ('Lipophilicity', 1): dict(num_layers=7, small_hidden_dim=167, num_heads=1,
                               dropout=0.0983753446086437, weight_decay=4.086333403457301e-16,
                               batch_size=5, lr=2.320541170954431e-05),
    ('BACE', 0): dict(num_layers=6, small_hidden_dim=47, num_heads=3,
                      dropout=0.2113253945447924, weight_decay=5.878135321726393e-12,
                      batch_size=3, lr=0.0002572167798956838),
    ('BACE', 1): dict(num_layers=5, small_hidden_dim=141, num_heads=2,
                      dropout=0.5047442534364175, weight_decay=4.437430281721926e-11,
                      batch_size=7, lr=2.8817004790329112e-05),
    ('BBBP', 0): dict(num_layers=1, small_hidden_dim=164, num_heads=10,
                      dropout=0.10699971329382979, weight_decay=2.8469965951126606e-14,
                      batch_size=2, lr=1.7971752346298526e-05),
    ('BBBP', 1): dict(num_layers=2, small_hidden_dim=189, num_heads=7,
                      dropout=0.7524706667718167, weight_decay=9.298688358703593e-07,
                      batch_size=9, lr=2.504908345987365e-05),
    ('ClinTox', 0): dict(num_layers=4, small_hidden_dim=123, num_heads=2,
                         dropout=0.28912089505267613, weight_decay=8.715810725319943e-16,
                         batch_size=6, lr=6.123782868507217e-05),
    ('ClinTox', 1): dict(num_layers=6, small_hidden_dim=83, num_heads=8,
                         dropout=0.7504659636545525, weight_decay=1.2957637942443332e-08,
                         batch_size=9, lr=2.167848298279678e-05),
}

MIX_HOP = {
    ('FreeSolv', 0): dict(num_layers=1, small_hidden_dim=161, max_pow=1,
                          dropout=0.4168274325534108, weight_decay=1.635806233409211e-10,
                          batch_size=4, lr=0.05900224481337009),
    ('FreeSolv', 1): dict(num_layers=1, small_hidden_dim=12, max_pow=2,
                          dropout=0.14449349878813347, weight_decay=1.386048955624208e-11,
                          batch_size=3, lr=0.06246465272211292),
    ('ESOL', 0): dict(num_layers=1, small_hidden_dim=138, max_pow=1,
                      dropout=0.10740849252745631, weight_decay=5.829522761945421e-07,
                      batch_size=5, lr=0.00899803546663418),
    ('ESOL', 1): dict(num_layers=2, small_hidden_dim=59, max_pow=5,
                      dropout=0.4428927705250062, weight_decay=6.117308833591867e-17,
                      batch_size=6, lr=0.003446531385382952),
    ('Lipophilicity', 0): dict(num_layers=2, small_hidden_dim=93, max_pow=1,
                               dropout=0.477217941047075, weight_decay=6.236350503288137e-05,
                               batch_size=8, lr=0.0006731898598905812),
    ('Lipophilicity', 1): dict(num_layers=2, small_hidden_dim=148, max_pow=4,
                               dropout=0.7090744972020606, weight_decay=7.552208510172316e-16,
                               batch_size=9, lr=4.4670389174200005e-05),
    ('BACE', 0): dict(num_layers=8, small_hidden_dim=163, max_pow=1,
                      dropout=0.030429863104662863, weight_decay=4.963667106698153e-19,
                      batch_size=10, lr=0.00014261807046744095),
    ('BACE', 1): dict(num_layers=7, small_hidden_dim=137, max_pow=3,
                      dropout=0.14579599577455854, weight_decay=1.8976159247030544e-11,
                      batch_size=10, lr=2.256250669202958e-05),
    ('BBBP', 0): dict(num_layers=2, small_hidden_dim=122, max_pow=1,
                      dropout=0.05535406119748653, weight_decay=1.1527288629473404e-14,
                      batch_size=6, lr=0.00041876458799519465),
    ('BBBP', 1): dict(num_layers=1, small_hidden_dim=70, max_pow=3,
                      dropout=0.19975030896092166, weight_decay=2.037326704901844e-15,
                      batch_size=9, lr=0.0014197707178220946),
    ('ClinTox', 0): dict(num_layers=10, small_hidden_dim=95, max_pow=1,
                         dropout=0.45924929530332814, weight_decay=3.9844666148289284e-20,
                         batch_size=6, lr=0.04057762972479995),
    ('ClinTox', 1): dict(num_layers=9, small_hidden_dim=164, max_pow=4,
                         dropout=0.4778545342903914, weight_decay=0.003608476532411314,
                         batch_size=6, lr=4.199957904366677e-05),
}

T_HOP = {
    ('FreeSolv', 0): dict(num_layers=2, hidden_dim=361, pow_dim=0,
                          dropout=0.3452039813522458, weight_decay=6.0419833079684976e-15,
                          batch_size=8, lr=0.11019359201526167),
    ('FreeSolv', 1): dict(num_layers=1, hidden_dim=208, pow_dim=2,
                          dropout=0.5196842037821313, weight_decay=2.767099305559158e-18,
                          batch_size=5, lr=0.15479631120975956),
    ('ESOL', 0): dict(num_layers=3, hidden_dim=168, pow_dim=0,
                      dropout=0.52, weight_decay=1.302768700471842e-12,
                      batch_size=5, lr=0.023504521841891612),
    ('ESOL', 1): dict(num_layers=3, hidden_dim=297, pow_dim=4,
                      dropout=0.32237108467149417, weight_decay=8.866739110758421e-18,
                      batch_size=6, lr=0.029569723377469003),
    ('Lipophilicity', 0): dict(num_layers=3, hidden_dim=165, pow_dim=0,
                               dropout=0.0005789312483251083, weight_decay=3.415131374396533e-10,
                               batch_size=10, lr=0.002154844550078915),
    ('Lipophilicity', 1): dict(num_layers=1, hidden_dim=180, pow_dim=2,
                               dropout=0.4219960959598102, weight_decay=5.968202723677461e-20,
                               batch_size=9, lr=0.015812919139792124),
    ('BACE', 0): dict(num_layers=2, hidden_dim=198, pow_dim=0,
                      dropout=0.29690381882578476, weight_decay=2.587714005614795e-12,
                      batch_size=6, lr=0.0009437528771705722),
    ('BACE', 1): dict(num_layers=2, hidden_dim=202, pow_dim=1,
                      dropout=0.7479123228381995, weight_decay=2.6753837502739997e-17,
                      batch_size=7, lr=0.03976907015630966),
    ('BBBP', 0): dict(num_layers=3, hidden_dim=243, pow_dim=0,
                      dropout=0.6962156787142889, weight_decay=7.460646579829558e-17,
                      batch_size=8, lr=0.023663507801800314),
    ('BBBP', 1): dict(num_layers=1, hidden_dim=324, pow_dim=3,
                      dropout=0.6104535457955884, weight_decay=2.545413999847812e-17,
                      batch_size=4, lr=0.08955851643035374),
    ('ClinTox', 0): dict(num_layers=1, hidden_dim=303, pow_dim=0,
                         dropout=0.38927567112685557, weight_decay=1.8365272549658533e-14,
                         batch_size=8, lr=0.02476945340075211),
    ('ClinTox', 1): dict(num_layers=2, hidden_dim=340, pow_dim=4,
                         dropout=0.7123844457157064, weight_decay=1.1839905103876106e-14,
                         batch_size=10, lr=0.0021488524554826825),
}

TABLES = {'graphormer': GRAPHORMER, 'mix_hop': MIX_HOP, 't_hop': T_HOP}
MODELS = ['graphormer', 'mix_hop', 't_hop']


def get(model: str, dataset: str, use_path: int) -> dict:
    """Hyperparameters for one (model, dataset family, mode) combination."""
    return dict(TABLES[model][(dataset, int(use_path))])
