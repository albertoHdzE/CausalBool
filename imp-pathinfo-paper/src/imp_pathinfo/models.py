"""The three models of the paper: Graphormer, Mix-Hop and T-Hop.

Each model is written with two modes -- *without path information* and *with
path information* -- exactly as the authors describe in Section 2.3 and
implement in ``reference/kaust_path_project``:

* **Graphormer** (Section 2.3.1).  A transformer encoder over the atoms of a
  molecule.  With path information, the attention matrix is shifted by an
  affine function of the shortest-path distance matrix and by a learned
  projection of the edge features that lie along those shortest paths.
* **Mix-Hop** (Section 2.3.2).  A concatenation of ``max_pow`` linear branches,
  each propagated by a power of the normalised adjacency.  ``max_pow = 1`` is
  the no-path mode.
* **T-Hop** (Section 2.3.3).  The propagation operator is the learned
  combination ``M = a0 * A + sum_L sum_k a_{L,k} T^L[:, :, k]`` of Equation 4.
  ``pow_dim = 0`` removes every path term and leaves ``M = a0 * A``.

Two faithful-but-noteworthy details of the authors' implementation are kept
here deliberately, and flagged in the notebook:

1. Mix-Hop's "powered adjacency" is built with ``curr_adj = adj * curr_adj``,
   an elementwise (Hadamard) power of the normalised adjacency rather than the
   matrix power ``A^L`` of Equation 2.
2. Graphormer's path bias is added *after* the attention softmax rather than to
   the pre-softmax logits.

Reproducing the paper's numbers requires reproducing its code, so both are
retained; ``mix_hop_matrix_power`` and ``graphormer_presoftmax_bias`` switch
them to the textbook form for the ablation reported in the notebook.
"""

from __future__ import annotations

import math

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


# ----------------------------------------------------------------------------
# T-Hop
# ----------------------------------------------------------------------------

def he_param_init(max_nodes: int, pow_dim: int, num_layers: int):
    """Kaiming-uniform initialisation of the alpha coefficients of Equation 4."""
    beta_params, adj_params = nn.ParameterList(), nn.ParameterList()
    for _ in range(num_layers):
        all_params = torch.empty(1, 1, 1, max_nodes * pow_dim + 1)
        nn.init.kaiming_uniform_(all_params, mode='fan_in', nonlinearity='relu')
        beta_params.append(nn.Parameter(all_params[:, :, :, 0:max_nodes * pow_dim].clone()))
        adj_params.append(nn.Parameter(all_params[0, 0, 0, -1].clone()))
    return adj_params, beta_params


class THop(nn.Module):
    """The T-Hop model of Section 2.3.3."""

    def __init__(self, max_nodes, pow_dim, num_layers, inp_dim, hid_dim, num_classes,
                 dropout=0.0, norm_layer_type='layer_norm'):
        super().__init__()
        self.num_layers = num_layers
        self.pow_dim = pow_dim
        self.norm_layer_type = norm_layer_type
        self.adj_params, self.beta_params = he_param_init(max_nodes, pow_dim, num_layers)

        self.my_modules = nn.ModuleDict()
        self.my_modules['proj_0'] = nn.Linear(inp_dim, hid_dim)
        self.my_modules['norm_0'] = nn.LayerNorm(hid_dim)
        for i in range(1, num_layers):
            self.my_modules[f'proj_{i}'] = nn.Linear(hid_dim, hid_dim)
            self.my_modules[f'norm_{i}'] = nn.LayerNorm(hid_dim)
        self.my_modules['out_lay'] = nn.Linear(hid_dim, num_classes)
        self.activation = nn.ReLU(inplace=True)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, adj, beta, residual: int = 1, beta_sparse=None):
        """``beta`` is the dense (B, n, n, n, pow_dim) tensor of Equation 4.

        ``beta_sparse`` is an equivalent, far cheaper representation of the same
        tensor: ``(flat_index, col, val)`` where ``flat_index`` addresses
        ``(b, i, j)`` in the flattened (B*n*n) grid and ``col = k * pow_dim + L - 2``
        is the position of the coefficient in the flattened parameter vector.
        The two give identical results (see ``tests/test_models.py``); the sparse
        form is used because a dense T tensor for a 136-atom molecule would need
        10 million entries per graph.
        """
        if self.pow_dim != 0 and beta is not None:
            b = beta.shape
            beta = beta.reshape(b[0], b[1], b[2], b[3] * b[4])

        for i in range(self.num_layers):
            prod_adj = adj * self.adj_params[i]
            if self.pow_dim != 0 and beta is not None:
                final_adj = (beta * self.beta_params[i]).sum(dim=-1) + prod_adj
            elif self.pow_dim != 0 and beta_sparse is not None:
                flat_index, col, val = beta_sparse
                contrib = val * self.beta_params[i].reshape(-1)[col]
                acc = torch.zeros(prod_adj.numel(), dtype=prod_adj.dtype,
                                  device=prod_adj.device)
                acc = acc.index_add(0, flat_index, contrib)
                final_adj = acc.reshape(prod_adj.shape) + prod_adj
            else:
                final_adj = prod_adj
            x_0 = x
            x = self.my_modules[f'proj_{i}'](x)
            x = torch.matmul(final_adj, x)
            if residual == 1 and i > 0:
                x = x + x_0
            x = self.my_modules[f'norm_{i}'](x)
            x = self.activation(x)
            x = self.dropout(x)

        x = torch.mean(x, dim=1)
        return self.my_modules['out_lay'](x)


# ----------------------------------------------------------------------------
# Mix-Hop
# ----------------------------------------------------------------------------

class MixHop(nn.Module):
    """The Mix-Hop model of Section 2.3.2 (``max_pow = 1`` is the no-path mode)."""

    def __init__(self, num_layers, input_dim, small_hidden_dim, out_dim, max_pow,
                 dropout=0.0, matrix_power=False):
        super().__init__()
        self.num_layers = num_layers
        self.max_pow = max_pow
        self.matrix_power = matrix_power
        hidden_dim = max_pow * small_hidden_dim
        self.my_modules = nn.ModuleDict()
        for p in range(1, max_pow + 1):
            self.my_modules[f'proj_lay_0_pow_{p}'] = nn.Linear(input_dim, small_hidden_dim)
        self.my_modules['norm_0'] = nn.BatchNorm1d(hidden_dim, affine=True)
        for i in range(1, num_layers):
            for p in range(1, max_pow + 1):
                self.my_modules[f'proj_lay_{i}_pow_{p}'] = nn.Linear(hidden_dim, small_hidden_dim)
            self.my_modules[f'norm_{i}'] = nn.BatchNorm1d(hidden_dim, affine=True)
        self.my_modules['out_lay'] = nn.Linear(hidden_dim, out_dim)
        self.activation = nn.ReLU(inplace=True)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, adj):
        for i in range(self.num_layers):
            list_y = []
            curr_adj = torch.ones_like(adj) if not self.matrix_power else None
            for p in range(1, self.max_pow + 1):
                if self.matrix_power:
                    curr_adj = adj if p == 1 else torch.matmul(curr_adj, adj)
                else:
                    curr_adj = adj * curr_adj
                y = self.my_modules[f'proj_lay_{i}_pow_{p}'](x)
                list_y.append(torch.matmul(curr_adj, y))
            x = torch.cat(list_y, dim=2)
            x = torch.permute(x, (0, 2, 1))
            x = self.my_modules[f'norm_{i}'](x)
            x = torch.permute(x, (0, 2, 1))
            x = self.activation(x)
            x = self.dropout(x)
        x = torch.mean(x, 1)
        return self.my_modules['out_lay'](x)


# ----------------------------------------------------------------------------
# Graphormer
# ----------------------------------------------------------------------------

class MultiheadAttention(nn.Module):
    def __init__(self, input_dim, embed_dim, num_heads, pre_softmax_bias=False):
        super().__init__()
        assert embed_dim % num_heads == 0, 'Embedding dimension must be 0 modulo number of heads.'
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        self.pre_softmax_bias = pre_softmax_bias
        self.qkv_proj = nn.Linear(input_dim, 3 * embed_dim)
        self.o_proj = nn.Linear(embed_dim, embed_dim)
        nn.init.xavier_uniform_(self.qkv_proj.weight)
        self.qkv_proj.bias.data.fill_(0)
        nn.init.xavier_uniform_(self.o_proj.weight)
        self.o_proj.bias.data.fill_(0)

    def forward(self, x, dist_mat, path_mat, mask=None):
        batch_size, seq_length, _ = x.size()
        qkv = self.qkv_proj(x)
        qkv = qkv.reshape(batch_size, seq_length, self.num_heads, 3 * self.head_dim)
        qkv = qkv.permute(0, 2, 1, 3)
        q, k, v = qkv.chunk(3, dim=-1)

        attn_logits = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(q.size()[-1])
        if mask is not None:
            attn_logits = attn_logits.masked_fill(mask == 0, -9e15)
        if self.pre_softmax_bias:
            attention = F.softmax(attn_logits + dist_mat + path_mat, dim=-1)
        else:
            # As in the authors' code: the structural bias is added after softmax.
            attention = F.softmax(attn_logits, dim=-1) + dist_mat + path_mat

        values = torch.matmul(attention, v)
        values = values.permute(0, 2, 1, 3).reshape(batch_size, seq_length, self.embed_dim)
        return self.o_proj(values)


class EncoderBlock(nn.Module):
    def __init__(self, input_dim, num_heads, dim_feedforward, dropout=0.0,
                 pre_softmax_bias=False):
        super().__init__()
        self.self_attn = MultiheadAttention(input_dim, input_dim, num_heads, pre_softmax_bias)
        self.linear_net = nn.Sequential(
            nn.Linear(input_dim, dim_feedforward),
            nn.Dropout(dropout),
            nn.ReLU(inplace=True),
            nn.Linear(dim_feedforward, input_dim),
        )
        self.norm1 = nn.LayerNorm(input_dim)
        self.norm2 = nn.LayerNorm(input_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, dist_mat=0.0, path_mat=0.0, mask=None):
        x = self.norm1(x)
        x = x + self.dropout(self.self_attn(x, dist_mat, path_mat, mask=mask))
        x = self.norm2(x)
        x = x + self.dropout(self.linear_net(x))
        return x


class Graphormer(nn.Module):
    """The Graphormer of Section 2.3.1, in its no-path and with-path modes."""

    def __init__(self, use_path_info, num_layers, input_dim, edge_dim, embed_dim,
                 num_heads, dim_feedforward, out_dim, max_path_len, dropout=0.0,
                 pre_softmax_bias=False):
        super().__init__()
        self.use_path_info = use_path_info
        self.embed_layer = nn.Linear(input_dim, embed_dim)
        self.deg_embed = nn.Linear(1, input_dim)
        if use_path_info:
            dist_params = torch.empty(1, 2)
            nn.init.kaiming_uniform_(dist_params, nonlinearity='relu')
            self.dist_params = nn.Parameter(dist_params)
            path_params = torch.empty(1, 1, 1, max_path_len, edge_dim)
            nn.init.kaiming_uniform_(path_params, nonlinearity='relu')
            self.path_params = nn.Parameter(path_params)
        self.layers = nn.ModuleList([
            EncoderBlock(embed_dim, num_heads, dim_feedforward, dropout, pre_softmax_bias)
            for _ in range(num_layers)
        ])
        self.out_layer = nn.Linear(embed_dim, out_dim)

    def forward(self, x, degrees, dist_mat=None, path_edge_feats=None,
                path_sparse=None, batch_shape=None):
        """``path_edge_feats`` is the dense (B, n, n, max_path_len, edge_dim)
        tensor of edge features gathered along shortest paths.

        ``path_sparse = (flat_index, step, edge_feat)`` is the equivalent sparse
        form: one row per occupied ``(b, i, j, p)`` slot, giving the flattened
        ``(b, i, j)`` address, the position ``p`` along the path and the feature
        vector of the edge sitting there.  Both forms produce the same bias
        matrix (see ``tests/test_models.py``)."""
        if self.use_path_info:
            dist = dist_mat * self.dist_params[0, 0] + self.dist_params[0, 1]
            dist = torch.unsqueeze(dist, 1)
            if path_sparse is None:
                pmat = torch.mul(path_edge_feats, self.path_params)
                pmat = pmat.sum(dim=-1).mean(dim=-1)
            else:
                flat_index, step, edge_feat = path_sparse
                params = self.path_params[0, 0, 0]           # (max_path_len, edge_dim)
                contrib = (edge_feat * params[step]).sum(dim=-1)
                acc = torch.zeros(int(np.prod(batch_shape)), dtype=x.dtype, device=x.device)
                acc = acc.index_add(0, flat_index, contrib)
                pmat = acc.reshape(batch_shape) / params.shape[0]
            pmat = torch.unsqueeze(pmat, 1)
        else:
            dist, pmat = 0.0, 0.0

        x = x + self.deg_embed(degrees)
        x = self.embed_layer(x)
        for layer in self.layers:
            x = layer(x, dist, pmat)
        x = torch.mean(x, dim=1)
        return self.out_layer(x)
