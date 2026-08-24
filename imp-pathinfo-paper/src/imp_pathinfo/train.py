"""The training/evaluation loop shared by the three models.

Everything here mirrors the authors' ``train_*.py`` scripts:

* scaffold split 80:10:10, computed once per dataset;
* Adam with the swept learning rate and weight decay;
* SmoothL1 loss (regression) or BCE-with-logits (classification), masked;
* up to 200 epochs with early stopping (patience 10) on the validation metric,
  restoring the best checkpoint before the test set is scored;
* RMSE for regression and ROC-AUC for classification, averaged over tasks, with
  the sigmoid applied inside the ROC-AUC computation exactly as in
  ``dgllife.utils.Meter``;
* Gaussian feature noise redrawn per batch, with the authors' seeding scheme.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import roc_auc_score as sk_roc_auc

from . import hyperparams as hp
from .data import scaffold_split
from .models import Graphormer, MixHop, THop
from .paths import densify_t, normalized_adjacency, shortest_paths, t_tensor_sparse


# ----------------------------------------------------------------------------
# metrics and early stopping
# ----------------------------------------------------------------------------

class Meter:
    """Port of ``dgllife.utils.Meter`` restricted to the two metrics used."""

    def __init__(self):
        self.y_pred, self.y_true, self.mask = [], [], []

    def update(self, y_pred, y_true, mask):
        self.y_pred.append(y_pred.detach().cpu())
        self.y_true.append(y_true.detach().cpu())
        self.mask.append(mask.detach().cpu())

    def compute(self, metric_name: str) -> float:
        y_pred = torch.cat(self.y_pred, dim=0)
        y_true = torch.cat(self.y_true, dim=0)
        mask = torch.cat(self.mask, dim=0)
        scores = []
        for task in range(y_true.shape[1]):
            w = mask[:, task]
            t_true, t_pred = y_true[:, task][w != 0], y_pred[:, task][w != 0]
            if metric_name == 'rmse':
                scores.append(float(torch.sqrt(nn.functional.mse_loss(t_pred, t_true))))
            else:
                if len(torch.unique(t_true)) == 1:
                    continue
                scores.append(float(sk_roc_auc(t_true.long().numpy(),
                                               torch.sigmoid(t_pred).numpy())))
        return float(np.mean(scores)) if scores else float('nan')


class EarlyStopping:
    """Port of ``dgllife.utils.EarlyStopping`` keeping the checkpoint in memory."""

    def __init__(self, metric: str, patience: int = hp.PATIENCE):
        self.higher_better = metric == 'roc_auc_score'
        self.patience = patience
        self.counter = 0
        self.best_score = None
        self.best_state = None

    def _better(self, score, best):
        return score > best if self.higher_better else score < best

    def step(self, score, model) -> bool:
        if self.best_score is None or self._better(score, self.best_score):
            self.best_score = score
            self.best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            self.counter = 0
        else:
            self.counter += 1
        return self.counter >= self.patience

    def restore(self, model):
        if self.best_state is not None:
            model.load_state_dict(self.best_state)


# ----------------------------------------------------------------------------
# batching
# ----------------------------------------------------------------------------

@dataclass
class GraphCache:
    """Structure-derived tensors, computed once per dataset and reused.

    The authors rebuild these inside the data loader on every epoch; because the
    bonds never change (noise touches only features), caching them changes
    nothing numerically and makes the replication tractable.
    """

    norm_adj: list        # Mix-Hop: symmetrically normalised A + I, padded
    raw_adj: list         # T-Hop: binary adjacency, padded at batch time
    t_sparse: list        # T-Hop: sparse T tensors
    dist: list            # Graphormer: shortest-path distances
    path_edges: list      # Graphormer: edge ids along shortest paths
    max_path_len: int


def build_cache(dataset, model_name: str, pow_dim: int = 0, max_nodes: int | None = None):
    max_nodes = max_nodes or dataset.max_nodes
    norm_adj, raw_adj, t_sparse, dist, path_edges = [], [], [], [], []
    max_path_len = 1
    for g in dataset.graphs:
        if model_name == 'mix_hop':
            norm_adj.append(normalized_adjacency(g, max_nodes))
        elif model_name == 't_hop':
            raw_adj.append(g.adjacency().astype(np.float32))
            t_sparse.append(t_tensor_sparse(g, pow_dim))
        else:
            d, p = shortest_paths(g)
            dist.append(d)
            path_edges.append(p)
            max_path_len = max(max_path_len, p.shape[2])
    return GraphCache(norm_adj, raw_adj, t_sparse, dist, path_edges, max_path_len)


def _pad_feats(feats_list, max_nodes):
    out = np.zeros((len(feats_list), max_nodes, feats_list[0].shape[1]), dtype=np.float32)
    for i, f in enumerate(feats_list):
        out[i, :f.shape[0], :] = f
    return out


def make_batch(dataset, cache, indices, model_name, pow_dim, max_nodes, noise_vec, seed,
               device, dense_path: bool = False):
    """Assemble one padded batch, adding the per-batch Gaussian feature noise.

    The authors draw a single noise vector per batch --
    ``torch.manual_seed(seed); torch.normal(0, std_vector)`` -- and broadcast it
    over every atom in the batch; that is reproduced exactly here.
    """
    graphs = [dataset.graphs[i] for i in indices]
    feats = [g.node_feat for g in graphs]
    x = torch.from_numpy(_pad_feats(feats, max_nodes))

    if noise_vec is not None:
        torch.manual_seed(seed)
        noise = torch.normal(mean=0.0, std=noise_vec)
        x = x + noise

    labels = torch.from_numpy(np.stack([g.label for g in graphs]))
    masks = torch.from_numpy(np.stack([g.mask for g in graphs]))

    batch = dict(x=x.to(device), labels=labels.to(device), masks=masks.to(device))

    if model_name == 'mix_hop':
        adj = np.stack([cache.norm_adj[i] for i in indices])
        batch['adj'] = torch.from_numpy(adj).to(device)
    elif model_name == 't_hop':
        adj = np.zeros((len(indices), max_nodes, max_nodes), dtype=np.float32)
        for b, i in enumerate(indices):
            a = cache.raw_adj[i]
            adj[b, :a.shape[0], :a.shape[1]] = a
        batch['adj'] = torch.from_numpy(adj).to(device)
        batch['beta'] = None
        batch['beta_sparse'] = None
        if pow_dim > 0:
            if dense_path:
                beta = np.stack([densify_t(*cache.t_sparse[i], max_nodes, pow_dim)
                                 for i in indices])
                batch['beta'] = torch.from_numpy(beta).to(device)
            else:
                flat, cols, vals = [], [], []
                for b, i in enumerate(indices):
                    idx, val = cache.t_sparse[i]
                    if not len(val):
                        continue
                    flat.append((b * max_nodes + idx[:, 0]) * max_nodes + idx[:, 1])
                    cols.append(idx[:, 2] * pow_dim + idx[:, 3])
                    vals.append(val)
                if flat:
                    batch['beta_sparse'] = (
                        torch.from_numpy(np.concatenate(flat).astype(np.int64)).to(device),
                        torch.from_numpy(np.concatenate(cols).astype(np.int64)).to(device),
                        torch.from_numpy(np.concatenate(vals)).to(device))
                else:
                    z = torch.zeros(0, dtype=torch.int64, device=device)
                    batch['beta_sparse'] = (z, z, torch.zeros(0, device=device))
    else:
        n_b = len(indices)
        dist = np.zeros((n_b, max_nodes, max_nodes), dtype=np.float32)
        flat, steps, efs = [], [], []
        for b, i in enumerate(indices):
            d = cache.dist[i]
            # unreachable pairs keep dgl.shortest_dist's -1; padding stays 0
            dist[b, :d.shape[0], :d.shape[1]] = d
            p = cache.path_edges[i]
            ef = dataset.graphs[i].edge_feat
            ii, jj, kk = np.nonzero(p >= 0)
            if len(ii):
                flat.append((b * max_nodes + ii) * max_nodes + jj)
                steps.append(kk)
                efs.append(ef[p[ii, jj, kk]])
        batch['dist'] = torch.from_numpy(dist).to(device)
        batch['batch_shape'] = (n_b, max_nodes, max_nodes)
        if dense_path:
            pe = np.zeros((n_b, max_nodes, max_nodes, cache.max_path_len,
                           graphs[0].edge_feat.shape[1]), dtype=np.float32)
            for b, i in enumerate(indices):
                p = cache.path_edges[i]
                ef = dataset.graphs[i].edge_feat
                ii, jj, kk = np.nonzero(p >= 0)
                if len(ii):
                    pe[b, ii, jj, kk, :] = ef[p[ii, jj, kk]]
            batch['path_edge_feats'] = torch.from_numpy(pe).to(device)
            batch['path_sparse'] = None
        else:
            batch['path_edge_feats'] = None
            if flat:
                batch['path_sparse'] = (
                    torch.from_numpy(np.concatenate(flat).astype(np.int64)).to(device),
                    torch.from_numpy(np.concatenate(steps).astype(np.int64)).to(device),
                    torch.from_numpy(np.concatenate(efs)).to(device))
            else:
                z = torch.zeros(0, dtype=torch.int64, device=device)
                batch['path_sparse'] = (z, z, torch.zeros(
                    (0, graphs[0].edge_feat.shape[1]), device=device))
        degrees = np.zeros((n_b, max_nodes, 1), dtype=np.float32)
        for b, i in enumerate(indices):
            g = dataset.graphs[i]
            np.add.at(degrees[b, :, 0], g.dst, 1.0)
        batch['degrees'] = torch.from_numpy(degrees).to(device)

    return batch


# ----------------------------------------------------------------------------
# experiment runner
# ----------------------------------------------------------------------------

def build_model(model_name, params, dataset, max_nodes, use_path, cache,
                mix_hop_matrix_power=False, graphormer_presoftmax_bias=False):
    inp_dim = dataset.graphs[0].node_feat.shape[1]
    n_tasks = dataset.n_tasks
    if model_name == 't_hop':
        return THop(max_nodes=max_nodes, pow_dim=params['pow_dim'],
                    num_layers=params['num_layers'], inp_dim=inp_dim,
                    hid_dim=params['hidden_dim'], num_classes=n_tasks,
                    dropout=params['dropout'])
    if model_name == 'mix_hop':
        return MixHop(num_layers=params['num_layers'], input_dim=inp_dim,
                      small_hidden_dim=params['small_hidden_dim'], out_dim=n_tasks,
                      max_pow=params['max_pow'], dropout=params['dropout'],
                      matrix_power=mix_hop_matrix_power)
    hidden_dim = params['num_heads'] * params['small_hidden_dim']
    edge_dim = dataset.graphs[0].edge_feat.shape[1]
    return Graphormer(use_path_info=use_path, num_layers=params['num_layers'],
                      input_dim=inp_dim, edge_dim=edge_dim, embed_dim=hidden_dim,
                      num_heads=params['num_heads'], dim_feedforward=hidden_dim,
                      out_dim=n_tasks, max_path_len=cache.max_path_len,
                      dropout=params['dropout'],
                      pre_softmax_bias=graphormer_presoftmax_bias)


def forward(model, model_name, batch, pow_dim):
    if model_name == 't_hop':
        return model(batch['x'], batch['adj'], batch['beta'], residual=1,
                     beta_sparse=batch.get('beta_sparse'))
    if model_name == 'mix_hop':
        return model(batch['x'], batch['adj'])
    return model(batch['x'], batch['degrees'], batch['dist'],
                 batch.get('path_edge_feats'), batch.get('path_sparse'),
                 batch.get('batch_shape'))


def run_experiment(dataset, model_name: str, use_path: int, noise_factor: float,
                   run_index: int, epochs: int = hp.EPOCHS, device: str = 'cpu',
                   cache=None, split=None, verbose: bool = False,
                   mix_hop_matrix_power: bool = False,
                   graphormer_presoftmax_bias: bool = False,
                   torch_seed: int | None = None,
                   max_nodes: int | None = None,
                   noise_std: np.ndarray | None = None):
    """One experimental case: train, early-stop on validation, score the test set.

    ``max_nodes`` and ``noise_std`` default to the dataset's own values.  They
    are overridable so that a *subset* of a dataset (a size bin, in Phase 1) can
    be trained with the parent family's padding width and perturbation scale,
    which keeps the model's parameter count and the intervention identical
    across bins.
    """
    params = hp.get(model_name, dataset.name, use_path)
    pow_dim = params.get('pow_dim', 0) if model_name == 't_hop' else 0
    max_nodes = max_nodes or dataset.max_nodes
    dev = torch.device(device)

    if split is None:
        split = scaffold_split(dataset)
    train_idx, val_idx, test_idx = split
    if cache is None:
        cache = build_cache(dataset, model_name, pow_dim, max_nodes)

    if torch_seed is not None:
        torch.manual_seed(torch_seed)
    model = build_model(model_name, params, dataset, max_nodes, use_path, cache,
                        mix_hop_matrix_power, graphormer_presoftmax_bias).to(dev)

    opt = torch.optim.Adam(model.parameters(), lr=params['lr'],
                           weight_decay=params['weight_decay'])
    loss_fn = (nn.SmoothL1Loss(reduction='none') if dataset.metric == 'rmse'
               else nn.BCEWithLogitsLoss(reduction='none'))
    stopper = EarlyStopping(dataset.metric)

    noise_vec = None
    if noise_factor > 0:
        std = dataset.node_feature_std() if noise_std is None else noise_std
        noise_vec = torch.from_numpy(std.astype(np.float32)) * noise_factor

    bs = params['batch_size']
    n_train_batches = math.ceil(len(train_idx) / bs)
    n_val_batches = math.ceil(len(val_idx) / bs)

    def run_split(indices, n_batches, training: bool, shuffle: bool, rng=None):
        order = np.asarray(indices)
        if shuffle:
            order = order[rng.permutation(len(order))]
        meter = Meter()
        model.train() if training else model.eval()
        for i in range(math.ceil(len(order) / bs)):
            idx = order[i * bs:(i + 1) * bs]
            if len(idx) == 0:
                continue
            batch = make_batch(dataset, cache, idx, model_name, pow_dim, max_nodes,
                               noise_vec, n_batches * run_index + i, dev)
            with torch.set_grad_enabled(training):
                out = forward(model, model_name, batch, pow_dim)
                loss = (loss_fn(out, batch['labels']) * (batch['masks'] != 0).float()).mean()
            if training:
                opt.zero_grad()
                loss.backward()
                opt.step()
            meter.update(out, batch['labels'], batch['masks'])
        return meter.compute(dataset.metric)

    rng = np.random.default_rng(1234 + run_index)
    t0 = time.time()
    stopped_at = epochs
    for epoch in range(epochs):
        run_split(train_idx, n_train_batches, True, True, rng)
        val_score = run_split(val_idx, n_val_batches, False, False)
        if verbose and epoch % 10 == 0:
            print(f'  epoch {epoch:3d}  val {dataset.metric} = {val_score:.4f}', flush=True)
        if stopper.step(val_score, model):
            stopped_at = epoch + 1
            break

    stopper.restore(model)
    test_score = run_split(test_idx, n_val_batches, False, False)
    return dict(dataset=dataset.name, model=model_name, use_path=use_path,
                noise=noise_factor, run=run_index, test_score=test_score,
                val_score=stopper.best_score, epochs_run=stopped_at,
                seconds=time.time() - t0)
