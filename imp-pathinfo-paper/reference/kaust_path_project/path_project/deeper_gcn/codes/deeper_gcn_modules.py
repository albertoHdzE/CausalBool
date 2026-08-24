import torch
import torch.nn as nn
import torch.nn.functional as F

import dgl.function as fn
from dgl.nn.functional import edge_softmax



def act_layer(act_type, inplace=False, neg_slope=0.2, n_prelu=1):
    act = act_type.lower()
    
    if act == 'relu':
        layer = nn.ReLU(inplace)
    elif act == 'leakyrelu':
        layer = nn.LeakyReLU(neg_slope, inplace)
    elif act == 'prelu':
        layer = nn.PReLU(num_parameters=n_prelu, init=neg_slope)
    else:
        raise NotImplementedError('activation layer [%s] is not found' % act)
    
    return layer


def norm_layer(norm_type, nc):
    if norm_type != None:
        norm = norm_type.lower()
    
    if norm == 'batch_norm':
        layer = nn.BatchNorm1d(nc, affine=True)
    elif norm == 'layer_norm':
        layer = nn.LayerNorm(nc, elementwise_affine=True)
    elif norm == 'instance_norm':
        layer = nn.InstanceNorm1d(nc, affine=False)
    elif norm == None or norm == 'none':
        layer = None
    else:
        raise NotImplementedError(f'Normalization layer {norm} is not supported.')

    return layer


##From original source:
#def norm_layer(norm_type, nc):
#    norm = norm_type.lower()

#    if norm == 'batch':
#        layer = nn.BatchNorm1d(nc, affine=True)
#    elif norm == 'layer':
#        layer = nn.LayerNorm(nc, elementwise_affine=True)
#    elif norm == 'instance':
#        layer = nn.InstanceNorm1d(nc, affine=False)
#    else:
#        raise NotImplementedError(f'Normalization layer {norm} is not supported.')

#    return layer



class MLP(nn.Sequential):
    r"""

    Description
    -----------
    From equation (5) in `DeeperGCN: All You Need to Train Deeper GCNs <https://arxiv.org/abs/2006.07739>`_
    """
    def __init__(self,
                 channels,
                 act='relu',
                 norm=None,
                 dropout=0.,
                 bias=True):
        layers = []
        
        for i in range(1, len(channels)):
            layers.append(nn.Linear(channels[i - 1], channels[i], bias))
            if i < len(channels) - 1:
                if norm is not None and norm.lower() != 'none':
                    layers.append(norm_layer(norm, channels[i]))
                if act is not None and act.lower() != 'none':
                    layers.append(act_layer(act))
                layers.append(nn.Dropout(dropout))
        
        super(MLP, self).__init__(*layers)


class MessageNorm(nn.Module):
    r"""
    
    Description
    -----------
    Message normalization was introduced in `DeeperGCN: All You Need to Train Deeper GCNs <https://arxiv.org/abs/2006.07739>`_

    Parameters
    ----------
    learn_scale: bool
        Whether s is a learnable scaling factor or not. Default is False.
    """
    def __init__(self, learn_scale=False):
        super(MessageNorm, self).__init__()
        self.scale = nn.Parameter(torch.FloatTensor([1.0]), requires_grad=learn_scale)

    def forward(self, feats, msg, p=2):
        msg = F.normalize(msg, p=2, dim=-1)
        feats_norm = feats.norm(p=p, dim=-1, keepdim=True)
        return msg * feats_norm * self.scale






#from deeper_gcn_modules import MLP, MessageNorm


class GENConv(nn.Module):
    r"""
    
    Description
    -----------
    Generalized Message Aggregator was introduced in `DeeperGCN: All You Need to Train Deeper GCNs <https://arxiv.org/abs/2006.07739>`_

    Parameters
    ----------
    dataset: str
        Name of ogb dataset.
    in_dim: int
        Size of input dimension.
    out_dim: int
        Size of output dimension.
    aggregator: str
        Type of aggregator scheme ('softmax', 'power'), default is 'softmax'.
    beta: float
        A continuous variable called an inverse temperature. Default is 1.0.
    learn_beta: bool
        Whether beta is a learnable variable or not. Default is False.
    p: float
        Initial power for power mean aggregation. Default is 1.0.
    learn_p: bool
        Whether p is a learnable variable or not. Default is False.
    msg_norm: bool
        Whether message normalization is used. Default is False.
    learn_msg_scale: bool
        Whether s is a learnable scaling factor or not in message normalization. Default is False.
    norm: str
        Type of ('batch', 'layer', 'instance') norm layer in MLP layers. Default is 'batch'.
    mlp_layers: int
        The number of MLP layers. Default is 1.
    eps: float
        A small positive constant in message construction function. Default is 1e-7.
    """
    def __init__(self,
                 node_in_dim, edge_in_dim,
                 out_dim,
                 aggregator='softmax',
                 beta=1.0,
                 learn_beta=False,
                 p=1.0,
                 learn_p=False,
                 msg_norm=False,
                 learn_msg_scale=False,
                 norm='batch',
                 mlp_layers=1,
                 eps=1e-7):
        super(GENConv, self).__init__()
        in_dim = node_in_dim
        self.aggr = aggregator
        self.eps = eps

        channels = [in_dim]
        for i in range(mlp_layers - 1):
            channels.append(in_dim * 2)
        channels.append(out_dim)
        
        self.edge_encoder = nn.Linear(edge_in_dim, out_dim)
        self.mlp = MLP(channels, norm=norm)
        self.msg_norm = MessageNorm(learn_msg_scale) if msg_norm else None

        self.beta = nn.Parameter(torch.Tensor([beta]), requires_grad=True) if learn_beta and self.aggr == 'softmax' else beta
        self.p = nn.Parameter(torch.Tensor([p]), requires_grad=True) if learn_p else p

    def forward(self, g, node_feats, edge_feats, tie_bond=0):
        with g.local_scope():
            # Node and edge feature dimension need to match.
            g.ndata['h'] = node_feats
            if tie_bond == 0:
                g.edata['h'] = self.edge_encoder(edge_feats)
            else:
                g.edata['h'] = edge_feats

            g.apply_edges(fn.u_add_e('h', 'h', 'm'))

            if self.aggr == 'softmax':
                g.edata['m'] = F.relu(g.edata['m']) + self.eps
                g.edata['a'] = edge_softmax(g, g.edata['m'] * self.beta)
                g.update_all(lambda edge: {'x': edge.data['m'] * edge.data['a']},
                             fn.sum('x', 'm'))
            
            elif self.aggr == 'power':
                minv, maxv = 1e-7, 1e1
                torch.clamp_(g.edata['m'], minv, maxv)
                g.update_all(lambda edge: {'x': torch.pow(edge.data['m'], self.p)},
                             fn.mean('x', 'm'))
                torch.clamp_(g.ndata['m'], minv, maxv)
                g.ndata['m'] = torch.pow(g.ndata['m'], self.p)
            
            else:
                raise NotImplementedError(f'Aggregator {self.aggr} is not supported.')
            
            if self.msg_norm is not None:
                g.ndata['m'] = self.msg_norm(node_feats, g.ndata['m'])
            
            feats = node_feats + g.ndata['m']
            
            return self.mlp(feats)


from rdkit import Chem
from dgllife.data import FreeSolv
from dgllife.utils import SMILESToBigraph, CanonicalAtomFeaturizer, CanonicalBondFeaturizer
smiles_to_g = SMILESToBigraph(node_featurizer=CanonicalAtomFeaturizer(), edge_featurizer=CanonicalBondFeaturizer())
dataset = FreeSolv(smiles_to_g)

samp_0 = dataset[0]
g = samp_0[1]
print("graph: ", g)
node_feats = g.ndata['h']
edge_feats = g.edata['e']
node_in_dim = node_feats.shape[1]
edge_in_dim = edge_feats.shape[1]
gen_lay = GENConv(node_in_dim, edge_in_dim, 74)
#print("node_feats: ", node_feats)
#print("edge_feats: ", edge_feats)

#print("gen_lay: ", gen_lay)
#out = gen_lay(g, node_feats, edge_feats)
#print("\OUT: \n ", out)

#mol = Chem.MolFromSmiles(samp_0[0])
#atom_featurizer = CanonicalAtomFeaturizer(atom_data_field='feat')
#bond_featurizer = CanonicalBondFeaturizer(bond_data_field='e_feat')

#print("atom_featurizer.feat_size('feat'): ", atom_featurizer.feat_size('feat'))
#print("bond_featurizer.feat_size('feat'): ", bond_featurizer.feat_size('e_feat'))

#print("\n atom_featurizer(mol)", atom_featurizer(mol))
