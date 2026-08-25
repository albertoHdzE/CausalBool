import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import dgl

import os
import re
import sys

def get_utils_path():
    path = os.getcwd()
    dirs = re.split('/', path)
    if dirs[0] == '':
        root_dirs = dirs[1:-2]
    else:
        root_dirs =   dirs[0:-2]

    root_path = '/'

    for dir in root_dirs:
        root_path = os.path.join(root_path, dir)

    utils_path = os.path.join(root_path, 'utils')
    return utils_path
    

#utils_path = get_utils_path()
utils_path = 'kaust_path_project/path_project/utils'
print("UTILS_PATH: ", utils_path)
sys.path.insert(1, utils_path)


from utils import split_pad_and_stack_adj, split_pad_and_stack_feat, batch_num_nodes_to_index 





def paths_edge_feats(g, paths, max_nodes, max_path_len, device):
    edge_feats = g.edata['e']
    edge_dim = edge_feats.shape[-1]
    
    batch_num_nodes = g.batch_num_nodes()
    batch_size = len(batch_num_nodes)
    mat_5d = torch.zeros(batch_size, max_nodes, max_nodes, max_path_len, edge_dim)
    mat_5d = mat_5d.to(device)
    
    batch_index = batch_num_nodes_to_index(batch_num_nodes)
   
    for b in range(batch_size):
        curr_paths = paths[batch_index[b]:batch_index[b+1], batch_index[b]:batch_index[b+1], : ]
        curr_path_len = curr_paths.shape[2]
        curr_num_nodes = batch_num_nodes[b]
        
        for i in range(curr_num_nodes):
            for j in range(curr_num_nodes):
                path_list = curr_paths[i,j, :].tolist()
                
                for p in range(len(path_list)):
                    edge_id = path_list[p]
                    if edge_id != -1:
                        curr_edge_feat = edge_feats[edge_id, :]
                        
                        mat_5d[b, i, j, p, :] = curr_edge_feat

    return mat_5d




class MultiheadAttention(nn.Module):

    def __init__(self, input_dim, embed_dim, num_heads):
        super().__init__()
        assert embed_dim % num_heads == 0, "Embedding dimension must be 0 modulo number of heads."

        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads

        # Stack all weight matrices 1...h together for efficiency
        # Note that in many implementations you see "bias=False" which is optional
        self.qkv_proj = nn.Linear(input_dim, 3*embed_dim)
        self.o_proj = nn.Linear(embed_dim, embed_dim)

        self._reset_parameters()

    def _reset_parameters(self):
        # Original Transformer initialization, see PyTorch documentation
        nn.init.xavier_uniform_(self.qkv_proj.weight)
        self.qkv_proj.bias.data.fill_(0)
        nn.init.xavier_uniform_(self.o_proj.weight)
        self.o_proj.bias.data.fill_(0)

    def scaled_dot_product(self, q, k, v, dist_mat, path_mat, mask=None):
        d_k = q.size()[-1]
        attn_logits = torch.matmul(q, k.transpose(-2, -1))
        attn_logits = attn_logits / math.sqrt(d_k)
        if mask is not None:
            attn_logits = attn_logits.masked_fill(mask == 0, -9e15)
        attention = F.softmax(attn_logits, dim=-1)
   
        attention = attention + dist_mat + path_mat
        

        values = torch.matmul(attention, v)
        return values, attention

    def forward(self, x, dist_mat, path_mat, mask=None, return_attention=False):
        batch_size, seq_length, _ = x.size()
        qkv = self.qkv_proj(x)

        # Separate Q, K, V from linear output
        qkv = qkv.reshape(batch_size, seq_length, self.num_heads, 3*self.head_dim)
        qkv = qkv.permute(0, 2, 1, 3) # [Batch, Head, SeqLen, Dims]
        q, k, v = qkv.chunk(3, dim=-1)

        # Determine value outputs
        values, attention = self.scaled_dot_product(q, k, v, dist_mat,  path_mat, mask=mask)
       
        values = values.permute(0, 2, 1, 3) # [Batch, SeqLen, Head, Dims]
        values = values.reshape(batch_size, seq_length, self.embed_dim)
        o = self.o_proj(values)

        if return_attention:
            return o, attention
        else:
            return o





class EncoderBlock(nn.Module):

    def __init__(self, input_dim, num_heads, dim_feedforward, dropout=0.0):
        """
        Inputs:
            input_dim - Dimensionality of the input
            num_heads - Number of heads to use in the attention block
            dim_feedforward - Dimensionality of the hidden layer in the MLP
            dropout - Dropout probability to use in the dropout layers
        """
        super().__init__()

        # Attention layer
        self.self_attn = MultiheadAttention(input_dim, input_dim, num_heads)

        # Two-layer MLP
        self.linear_net = nn.Sequential(
            nn.Linear(input_dim, dim_feedforward),
            nn.Dropout(dropout),
            nn.ReLU(inplace=True),
            nn.Linear(dim_feedforward, input_dim)
        )

        # Layers to apply in between the main layers
        self.norm1 = nn.LayerNorm(input_dim)
        self.norm2 = nn.LayerNorm(input_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, dist_mat=0, path_mat=0, mask=None):
        # Attention part
        x = self.norm1(x)
        attn_out = self.self_attn(x, dist_mat, path_mat, mask=mask)
        x = x + self.dropout(attn_out)
        

        # MLP part
        x = self.norm2(x)
        linear_out = self.linear_net(x)
        x = x + self.dropout(linear_out)
        

        return x




class TransformerEncoder(nn.Module):

    def __init__(self, use_path_info, num_layers, input_dim, edge_dim, embed_dim, num_heads, dim_feedforward, out_dim, max_path_len, dropout=0.0):
        super().__init__()
        self.use_path_info = use_path_info
        self.embed_layer = nn.Linear(input_dim, embed_dim)
        self.deg_embed = nn.Linear(1, input_dim)


        if self.use_path_info == 1:
            dist_params = torch.empty(1, 2)
            nn.init.kaiming_uniform_(dist_params, nonlinearity='relu')
            self.dist_params = nn.Parameter(dist_params) 

            path_params = torch.empty(1,1,1, max_path_len, edge_dim)
            self.path_params = nn.init.kaiming_uniform_(path_params, nonlinearity='relu')
            self.path_params = nn.Parameter(path_params) 

        self.layers = nn.ModuleList([EncoderBlock(embed_dim, num_heads, dim_feedforward, dropout) for _ in range(num_layers)])
        self.out_layer = nn.Linear(embed_dim, out_dim)
    def forward(self, x, g, max_nodes, max_path_len, mask=None):
        device = x.device
        batch_num_nodes = g.batch_num_nodes()
        if self.use_path_info == 1:
            dist_mat, paths = dgl.shortest_dist(g, return_paths = True)
            mat_5d = paths_edge_feats(g, paths, max_nodes, max_path_len, device)
            #print("mat_5d returned: ", mat_5d.shape, flush = True)

            dist_mat = split_pad_and_stack_adj(dist_mat, batch_num_nodes, max_nodes)
            dist_mat = torch.from_numpy(dist_mat).float()
            dist_mat = dist_mat.to(device)        
            dist_mat = torch.mul(dist_mat, self.dist_params[0, 0]) + self.dist_params[0,1]
            dist_mat = torch.unsqueeze(dist_mat, 1)

            mat_5d = torch.mul(mat_5d, self.path_params)
            mat_5d = torch.sum(mat_5d, dim = -1)        
            mat_5d = torch.mean(mat_5d, dim = -1) 
            #print("mat_5d b4 unsqueezing: ", mat_5d.shape, flush = True)
            mat_5d = torch.unsqueeze(mat_5d, 1)
            #print("mat_5d aft unsqueezing: ", mat_5d.shape, flush =True)
            
        else:
            dist_mat = 0.
            mat_5d = 0. 
            

        degrees = g.in_degrees()
        shape_degrees = degrees.shape
        degrees = torch.reshape(degrees, (shape_degrees[0], 1))
        degrees = split_pad_and_stack_feat(degrees, batch_num_nodes, max_nodes)
        degrees = torch.from_numpy(degrees)
        degrees = degrees.float()
        degrees = degrees.to(device)
        
        degrees = self.deg_embed(degrees)
        x = x + degrees
        x = self.embed_layer(x)
        for l in self.layers:
            x = l(x, dist_mat, mat_5d, mask=mask)
        x = torch.mean(x, dim = 1)
        x = self.out_layer(x)
        
        return x

    def get_attention_maps(self, x, mask=None):
        attention_maps = []
        for l in self.layers:
            _, attn_map = l.self_attn(x, mask=mask, return_attention=True)
            attention_maps.append(attn_map)
            x = l(x)
        return attention_maps


num_layers = 3
input_dim = 2
embed_dim = 10
dim_ff = 3
num_heads = 2
x = torch.rand(3, 4,  2)
#atten_model = TransformerEncoder(num_layers, input_dim,embed_dim , num_heads, dim_ff)
#y = atten_model(x)
#print(y, "DONE")



    
