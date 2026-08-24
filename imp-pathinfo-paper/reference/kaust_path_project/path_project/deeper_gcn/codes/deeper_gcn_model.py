import torch
import numpy as np
import torch 
import torch.nn as nn
import torch.optim as optim
from deeper_gcn_modules import norm_layer, GENConv
#from utils import const_param_init, normal_param_init, he_param_init, split_pad_and_batch_tensor, unbatch_tensor, unbatch_adj_tensor
import dgl
from dgl.nn.pytorch.glob import SumPooling, AvgPooling, MaxPooling


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
    

utils_path = get_utils_path()
print("UTILS_PATH: ", utils_path)
sys.path.insert(1, utils_path)

from utils import batch_num_nodes_to_index, unbatch_adj_tensor


def paths_edge_feats(g, paths, max_nodes, max_path_len):
    edge_feats = g.edata['e']
    edge_dim = edge_feats.shape[-1]
    device = edge_feats.device
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





def attach_dist_info(g, dist_mat):

    
    
    num_edges = g.num_edges()
    edge_list = list(range(0, num_edges))
    found = g.find_edges(edge_list)
    source_list = found[0].tolist()
    dest_list = found[1].tolist()
    
    distances = []
    for i in range(num_edges):
        s = source_list[i]
        d = dest_list[i]
        distances.append(dist_mat[s,d])

    
    for r in range(dist_mat.shape[0]):
        for c in range(dist_mat.shape[1]):
            if dist_mat[r,c] > 1:
                source_list.append(r)
                dest_list.append(c)
                distances.append(dist_mat[r,c])
                

    source_list = torch.tensor(source_list).to(torch.int32)
    dest_list = torch.tensor(dest_list).to(torch.int32)
    len_distances = len(distances)
    distances = torch.tensor(distances)
    distances = torch.reshape( distances, (len_distances, 1))
    distances = distances.to(torch.float32)
    g_2 = dgl.graph((source_list, dest_list))
    g2.set_batch_num_nodes(g.batch_num_nodes())
    

    edge_feats = g.edata['e']        
    padding = torch.zeros(len_distances - edge_feats.shape[0], edge_feats.shape[1]).float()
    edge_feats = torch.cat((edge_feats, padding),dim=0)
    edge_feats = torch.cat((edge_feats, distances), dim=1) 
    g_2.edata['e'] = edge_feats
    g_2.ndata['h'] = g.ndata['h']

    return g_2




def attach_dist_and_path_info(g, dist_mat, path_mat):

    
    device = dist_mat.device
    num_edges = g.num_edges()
    edge_list = list(range(0, num_edges))
    found = g.find_edges(edge_list)
    source_list = found[0].tolist()
    dest_list = found[1].tolist()
    
    distances = []
    path_info = []
    for i in range(num_edges):
        s = source_list[i]
        d = dest_list[i]
        distances.append(dist_mat[s,d])
        path_info.append(path_mat[s,d])
    
    for r in range(dist_mat.shape[0]):
        for c in range(dist_mat.shape[1]):
            if dist_mat[r,c] > 1:
                source_list.append(r)
                dest_list.append(c)
                distances.append(dist_mat[r,c])
                path_info.append(path_mat[r,c])


    source_list = torch.tensor(source_list).to(torch.int32)
    dest_list = torch.tensor(dest_list).to(torch.int32)
    len_distances = len(distances)
    distances = torch.tensor(distances)
    distances = torch.reshape( distances, (len_distances, 1))
    distances = distances.to(torch.float32).to(device)

    len_path_info = len(path_info)
    path_info = torch.tensor(path_info)
    path_info = torch.reshape( path_info, (len_path_info, 1))
    path_info = path_info.to(torch.float32).to(device)

    g_2 = dgl.graph((source_list, dest_list))
    g_2 = g_2.to(device)
    g_2.set_batch_num_nodes(g.batch_num_nodes())
    

    edge_feats = g.edata['e']        
    padding = torch.zeros(len_distances - edge_feats.shape[0], edge_feats.shape[1]).float().to(device)
    edge_feats = torch.cat((edge_feats, padding),dim=0)
    edge_feats = torch.cat((edge_feats, distances, path_info), dim=1) 
    g_2.edata['e'] = edge_feats
    
    #print("G BATCH_NUM_NODES: ", g.batch_num_nodes())
    #print("G NUM_NODES: ", g.num_nodes())
    #print("G NUM FEATS: ", g.ndata['h'].shape[0])
    #print("\n G2 BATCH_NUM_NODES: ", g_2.batch_num_nodes())
    #print("G2 NUM_NODES: ", g_2.num_nodes())
    
    
    if g.num_nodes() == g_2.num_nodes():
        g_2.ndata['h'] = g.ndata['h']
    else:
        g_2 = None

    return g_2



    
            







class deeper_gcn_model(torch.nn.Module):
    def __init__(self, use_path_info, num_layers, inp_dim, edge_dim, hid_dim, num_classes, drop_val, max_path_len, pooling='mean', norm_layer_type = 'batch_norm'):
        super().__init__()
        self.use_path_info = use_path_info
        self.num_layers = num_layers
        self.norm_layer_type = norm_layer_type
        self.my_modules = nn.ModuleDict()
        
        path_params = torch.empty(1,1,1, max_path_len, edge_dim)
        self.path_params = nn.init.kaiming_uniform_(path_params, nonlinearity='relu')
        self.path_params = nn.Parameter(path_params)
        
        # we possibly reset edge_dim after using its initial value to set path_params 
        if use_path_info == 1:
            edge_dim = edge_dim + 2


        self.my_modules['pre_encoder'] = nn.Linear(inp_dim, hid_dim) 
        if (self.norm_layer_type != None) and (self.norm_layer_type.lower() != 'none'):
            self.my_modules['pre_encoder_norm'] = norm_layer(norm_layer_type, hid_dim)
 
        self.my_modules['msg_lay_' + str(0)] = GENConv(hid_dim, edge_dim, hid_dim) 
        if (self.norm_layer_type != None) and (self.norm_layer_type.lower() != 'none'):
            self.my_modules['msg_norm_' + str(0)] = norm_layer(norm_layer_type, hid_dim)

        for i in range(1, num_layers):
            self.my_modules['msg_lay_' + str(i)] = GENConv(hid_dim, edge_dim, hid_dim) 
            if (self.norm_layer_type != None) and (self.norm_layer_type.lower() != 'none'):
                self.my_modules['msg_norm_' + str(i)] = norm_layer(norm_layer_type, hid_dim)



        self.activation = nn.ReLU(inplace = True) 
        self.dropout =  nn.Dropout(drop_val)
        
        if pooling == 'sum':
            self.my_modules['pooling'] = SumPooling()
        elif pooling == 'mean':
            self.my_modules['pooling'] = AvgPooling()
        elif pooling == 'max':
            self.my_modules['pooling'] = MaxPooling()
        else:
            raise NotImplementedError(f'{pooling} is not supported.')


        self.my_modules['out_lay'] = nn.Linear(hid_dim, num_classes)


    def get_path_info(self, g, paths, max_nodes, max_path_len, device ):
        
        
        
        #dist_mat, paths = dgl.shortest_dist(g, return_paths = True)
        mat_5d = paths_edge_feats(g, paths, max_nodes, max_path_len)
        mat_5d = torch.mul(mat_5d, self.path_params)
        mat_5d = torch.sum(mat_5d, dim = -1)        
        mat_5d = torch.mean(mat_5d, dim = -1) 
        return mat_5d
  
    def msg_layer(self, layer, g, node_feats, edge_feats, residual = 1):
        with g.local_scope():
            hv = node_feats
            he = edge_feats
            if residual == 1:
                hv = self.my_modules['msg_lay_' + str(layer)](g, hv, he) + hv
            hv = self.my_modules['msg_norm_' + str(layer)](hv)
            hv = self.activation(hv)
            hv = self.dropout(hv)
            #print("\n message layer shape: ", hv.shape)
            #print("batch_num_nodes: ", g.batch_num_nodes()) 
            return hv



    def forward(self, g,device, max_nodes, max_path_len, residual = 1):

        
        if self.use_path_info == 1:
          batch_num_nodes = g.batch_num_nodes()
          dist_mat, paths = dgl.shortest_dist(g, return_paths = True)
          paths = self.get_path_info(g, paths, max_nodes, max_path_len, device )
          paths = unbatch_adj_tensor(paths, batch_num_nodes)
          g = attach_dist_and_path_info(g, dist_mat, paths)
          if g == None:
              return None
        node_feats = g.ndata['h']
        edge_feats = g.edata['e']
        
        
   
        node_feats = self.my_modules['pre_encoder'](node_feats)
        for i in range(self.num_layers):
            node_feats = self.msg_layer(i, g, node_feats, edge_feats, residual)
        
            
        node_feats = self.my_modules['pooling'](g, node_feats) 
           
        node_feats = self.my_modules['out_lay'](node_feats)
            
        return node_feats
            



    

   
        







