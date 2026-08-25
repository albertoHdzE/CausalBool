import os
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset
import dgl
from dgl.nn import  EdgeWeightNorm
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler
from build_beta_mat_3d import Graph as Graph_mat_3d



def aws_collate_molgraphs_0(data):
    """Batching a list of datapoints for dataloader.

    Parameters
    ----------
    data : list of 3-tuples or 4-tuples.
        Each tuple is for a single datapoint, consisting of
        a SMILES, a DGLGraph, all-task labels and optionally a binary
        mask indicating the existence of labels.

    Returns
    -------
    smiles : list
        List of smiles
    bg : DGLGraph
        The batched DGLGraph.
    labels : Tensor of dtype float32 and shape (B, T)
        Batched datapoint labels. B is len(data) and
        T is the number of total tasks.
    masks : Tensor of dtype float32 and shape (B, T)
        Batched datapoint binary mask, indicating the
        existence of labels.
    """
    if len(data[0]) == 3:
        smiles, graphs, labels = map(list, zip(*data))
    else:
        smiles, graphs, labels, masks = map(list, zip(*data))

    bg = dgl.batch(graphs)
    bg.set_n_initializer(dgl.init.zero_initializer)
    bg.set_e_initializer(dgl.init.zero_initializer)
    labels = torch.stack(labels, dim=0)

    if len(data[0]) == 3:
        masks = torch.ones(labels.shape)
    else:
        masks = torch.stack(masks, dim=0)

    return smiles, bg, labels, masks

def aws_collate_molgraphs(data):
    """Batching a list of datapoints for dataloader.

    Parameters
    ----------
    data : list of 3-tuples or 4-tuples.
        Each tuple is for a single datapoint, consisting of
        a SMILES, a DGLGraph, all-task labels and optionally a binary
        mask indicating the existence of labels.

    Returns
    -------
    smiles : list
        List of smiles
    bg : DGLGraph
        The batched DGLGraph.
    labels : Tensor of dtype float32 and shape (B, T)
        Batched datapoint labels. B is len(data) and
        T is the number of total tasks.
    masks : Tensor of dtype float32 and shape (B, T)
        Batched datapoint binary mask, indicating the
        existence of labels.
    """
    if len(data[0]) == 3:
        smiles, graphs, labels = map(list, zip(*data))
    else:
        smiles, graphs, labels, masks = map(list, zip(*data))

    bg = dgl.batch(graphs)
    bg.set_n_initializer(dgl.init.zero_initializer)
    bg.set_e_initializer(dgl.init.zero_initializer)
    labels = torch.stack(labels, dim=0)

    if len(data[0]) == 3:
        masks = torch.ones(labels.shape)
    else:
        masks = torch.stack(masks, dim=0)
    
    return smiles, bg, labels, masks



def aws_collate_and_beta(data, pow_dim=None,  max_nodes =None, add_identity =0, truncate_beta =0):
    """Batching a list of datapoints for dataloader.

    Parameters
    ----------
    data : list of 3-tuples or 4-tuples.
        Each tuple is for a single datapoint, consisting of
        a SMILES, a DGLGraph, all-task labels and optionally a binary
        mask indicating the existence of labels.

    Returns
    -------
    smiles : list
        List of smiles
    bg : DGLGraph
        The batched DGLGraph.
    labels : Tensor of dtype float32 and shape (B, T)
        Batched datapoint labels. B is len(data) and
        T is the number of total tasks.
    masks : Tensor of dtype float32 and shape (B, T)
        Batched datapoint binary mask, indicating the
        existence of labels.
    """
    
    max_len = pow_dim + 1
    if len(data[0]) == 3:
        smiles, graphs, labels = map(list, zip(*data))
    else:
        smiles, graphs, labels, masks = map(list, zip(*data))

    
    if pow_dim == 0:
        adj = 0
        beta = 0.
    else:
        adj_and_beta = beta_from_dgl_graph_list(graphs, pow_dim, max_len, max_nodes, add_identity, truncate_beta)
        adj = adj_and_beta[0]
        beta = adj_and_beta[1]
    bg = dgl.batch(graphs)
    bg.set_n_initializer(dgl.init.zero_initializer)
    bg.set_e_initializer(dgl.init.zero_initializer)
    labels = torch.stack(labels, dim=0)

    if len(data[0]) == 3:
        masks = torch.ones(labels.shape)
    else:
        masks = torch.stack(masks, dim=0)
    
    return smiles, bg, labels, masks, adj, beta





def collate_beta_for_timing(data, pow_dim=None,  max_nodes =None, add_identity =0, truncate_beta =0):
    """Batching a list of datapoints for dataloader.

    Parameters
    ----------
    data : list of 3-tuples or 4-tuples.
        Each tuple is for a single datapoint, consisting of
        a SMILES, a DGLGraph, all-task labels and optionally a binary
        mask indicating the existence of labels.

    Returns
    -------
    smiles : list
        List of smiles
    bg : DGLGraph
        The batched DGLGraph.
    labels : Tensor of dtype float32 and shape (B, T)
        Batched datapoint labels. B is len(data) and
        T is the number of total tasks.
    masks : Tensor of dtype float32 and shape (B, T)
        Batched datapoint binary mask, indicating the
        existence of labels.
    """
    max_len = pow_dim + 1
    if len(data[0]) == 3:
        smiles, graphs, labels = map(list, zip(*data))
    else:
        smiles, graphs, labels, masks = map(list, zip(*data))

    

    beta = beta_from_dgl_graph_list_no_pad(graphs, pow_dim, max_len, max_nodes, add_identity, truncate_beta)
        
    return beta




def aws_collate_beta_alone(data, pow_dim=None,  max_nodes =None, add_identity =0, truncate_beta =0):
    """Batching a list of datapoints for dataloader.

    Parameters
    ----------
    data : list of 3-tuples or 4-tuples.
        Each tuple is for a single datapoint, consisting of
        a SMILES, a DGLGraph, all-task labels and optionally a binary
        mask indicating the existence of labels.

    Returns
    -------
    smiles : list
        List of smiles
    bg : DGLGraph
        The batched DGLGraph.
    labels : Tensor of dtype float32 and shape (B, T)
        Batched datapoint labels. B is len(data) and
        T is the number of total tasks.
    masks : Tensor of dtype float32 and shape (B, T)
        Batched datapoint binary mask, indicating the
        existence of labels.
    """
    max_len = pow_dim + 1
    if len(data[0]) == 3:
        smiles, graphs, labels = map(list, zip(*data))
    else:
        smiles, graphs, labels, masks = map(list, zip(*data))

    

    beta = beta_alone_from_dgl_graph_list(graphs, pow_dim, max_len, max_nodes, add_identity, truncate_beta)
    return beta




def collate_molgraphs(data):
    """Batching a list of datapoints for dataloader.
    Parameters
    ----------
    data : list of 4-tuples.
        Each tuple is for a single datapoint, consisting of
        a SMILES, a DGLGraph, all-task labels and a binary
        mask indicating the existence of labels.
    Returns
    -------
    smiles : list
        List of smiles
    bg : DGLGraph
        The batched DGLGraph.
    labels : Tensor of dtype float32 and shape (B, T)
        Batched datapoint labels. B is len(data) and
        T is the number of total tasks.
    masks : Tensor of dtype float32 and shape (B, T)
        Batched datapoint binary mask, indicating the
        existence of labels.
    """
    #smiles, graphs, labels, masks = map(list, zip(*data))
    smiles, graphs, labels = map(list, zip(*data))

    bg = dgl.batch(graphs)
    bg.set_n_initializer(dgl.init.zero_initializer)
    bg.set_e_initializer(dgl.init.zero_initializer)
    labels = torch.stack(labels, dim=0)
    #masks = torch.stack(masks, dim=0)

    return bg, labels


class dataset_from_index(Dataset):
    def __init__(self,index_set):
        
        self.index_set = index_set
                                 
    def __getitem__(self,index):
        
            return self.index_set[index]
              
             
    def __len__(self):
        return len(list(self.index_set))




def get_even_grid(first_val, last_val, common_diff):
    hidden_grid = []
    for i in range(first_val, last_val + 1, common_diff):
        hidden_grid.append(i)
    return hidden_grid




def weights_mat_to_dgl(weights_mat, norm_style=None, pow_ind = None , depth = None, move_dict_time = None):
    if move_dict_time == 'pre':
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device("cpu")

    out_dict = {}
    weights_list = []
    source_list = []
    dest_list = []
    
    adj_shape = weights_mat.shape
    numb_nodes = adj_shape[0]
    for source in range(numb_nodes):
        for dest in range(numb_nodes):
            if weights_mat[source, dest] != 0:
                weights_list.append(weights_mat[source, dest])
                source_list.append(source)
                dest_list.append(dest)
    if move_dict_time == 'pre':
        out_dict['graph'] = dgl.graph( (source_list, dest_list) ).to(device = device)
        weights_list = (torch.tensor(weights_list)).to(device = device)
    else:
        out_dict['graph'] = dgl.graph( (source_list, dest_list) )
        weights_list = (torch.tensor(weights_list))

    if norm_style:
        norm = EdgeWeightNorm(norm= norm_style)
        weights_list = norm(out_dict['graph'], weights_list)
        
    out_dict['edges_weights'] = weights_list
    return out_dict




def mat_as_dict_to_dgl(weights_mat, norm_style=None, move_dict_time = None):
    if move_dict_time == 'pre':
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device("cpu")

    out_dict = {}
    weights_list = []
    source_list = []
    dest_list = []
    
    #adj_shape = weights_mat.shape
    #numb_nodes = adj_shape[0]
    #for source in range(numb_nodes):
        #for dest in range(numb_nodes):
    for dict_key in weights_mat:
            #if weights_mat[source, dest] != 0:
                
                weights_list.append(weights_mat[dict_key])
                source_list.append(dict_key[0])
                dest_list.append(dict_key[1])
    if move_dict_time == 'pre':
        out_dict['graph'] = dgl.graph( (source_list, dest_list) ).to(device = device)
        weights_list = (torch.tensor(weights_list)).to(device = device)
    else:
        out_dict['graph'] = dgl.graph( (source_list, dest_list) )
        weights_list = (torch.tensor(weights_list))

    if norm_style:
        norm = EdgeWeightNorm(norm= norm_style)
        weights_list = norm(out_dict['graph'], weights_list)
        
    out_dict['edges_weights'] = weights_list
    return out_dict






def dgl_g_to_planetoid(dgl_g, numb_nodes):
    out = {}
    for i in range(numb_nodes):
        out[i] = []
    sources = dgl_g[0].tolist()
    numb_edges = len(sources)
    dests = dgl_g[1].tolist()
    
    for i in range(numb_edges):
        s = sources[i]
        out[s].append(dests[i]) 

    return out



def beta_mat_as_dict_from_dgl_graph(dgl_graph, pow_dim, max_len):
        graph_edges = dgl_graph.edges()
        numb_nodes = dgl_graph.num_nodes()
    
        planetoid_graph = dgl_g_to_planetoid(graph_edges, numb_nodes)
        g = Graph_mat_as_dict(numb_nodes, pow_dim, add_identity = True)
        g.setGraph(planetoid_graph)
        g.setMaxPathLen(max_len)
        for s in range(numb_nodes):
            g.printAllPaths(s)       
        adj_and_beta = g.get_adj_and_beta()
        
        return adj_and_beta

#(beta, pow_dim, numb_nodes, norm_style, move_dict_time)

def dict_of_dicts_from_mat_as_dict(beta, pow_dim, depth_dim,  norm_style, move_dict_time):
    dict_of_dicts = {}

    for pow_ind in range(pow_dim):
        for d in range(depth_dim):
            dict_of_dicts[pow_ind, d] = mat_as_dict_to_dgl(beta[pow_ind][d], norm_style, move_dict_time )

    return dict_of_dicts




def dict_of_dicts_from_beta(dataset_name, reduced_by, reduced_dir, pow_dim, depth_dim, sub_nodes, pre_scaler, post_scaler, norm_style, move_dict_time):

    if post_scaler == 'min_max':
        scaler = MinMaxScaler()
    elif post_scaler == 'std':
        scaler = StandardScaler()
    else:
        scaler = None

    dict_of_dicts = {}
    for pow_ind in range(pow_dim): 
    
        file_name = dataset_name + '_reduced_by_' + str(reduced_by)  + '_pow_ind_' + str(pow_ind) + '_pow_dim_' + str(pow_dim) +  '_depth_dim_' + str(depth_dim) +  '_sub_nodes_' + str(sub_nodes) + '_pre_scaler_' + str(pre_scaler) +'.npy'
    
        path_to_reduced = os.path.join(reduced_dir, file_name)
        beta = np.load(path_to_reduced)
        beta = beta.astype(np.float32)
        beta_shape = beta.shape
        
        beta = beta.reshape(beta_shape[0]*beta_shape[1], beta_shape[2])
        if scaler:
            scaler.fit(beta)
            beta = scaler.transform(beta)
        beta = beta.reshape(beta_shape[0], beta_shape[1], beta_shape[2])
    
        for d in range(depth_dim): 
            dict_of_dicts[pow_ind, d] = weights_mat_to_dgl(beta[:, :, d], norm_style, pow_ind, d, move_dict_time )

    return dict_of_dicts


def print_beta_mat_as_dict(beta):
    pow_dim = len(beta)
    numb_nodes = len(beta[0])
    
    for i in range(pow_dim):
        for j in range(numb_nodes):
            print("current dict at ", str(i), " ", str(j), ": \n",  beta[i][j] )





def beta_mat_3d_from_dgl_graph(dgl_graph, pow_dim, max_len, add_identity, truncate_beta):
        graph_edges = dgl_graph.edges()
        numb_nodes = dgl_graph.num_nodes()
    
        planetoid_graph = dgl_g_to_planetoid(graph_edges, numb_nodes)
        g = Graph_mat_3d(numb_nodes, pow_dim, add_identity = add_identity, truncate_beta = truncate_beta)
        g.setGraph(planetoid_graph)
        g.setMaxPathLen(max_len)
        for s in range(numb_nodes):
            g.printAllPaths(s)       
        adj_and_beta = g.get_adj_and_beta()
        
        return adj_and_beta


def beta_alone_from_dgl_graph(dgl_graph, pow_dim, max_len, add_identity, truncate_beta):
        graph_edges = dgl_graph.edges()
        numb_nodes = dgl_graph.num_nodes()
    
        planetoid_graph = dgl_g_to_planetoid(graph_edges, numb_nodes)
        g = Graph_beta_alone(numb_nodes, pow_dim, add_identity = add_identity, truncate_beta = truncate_beta)
        g.setGraph(planetoid_graph)
        g.setMaxPathLen(max_len)
        for s in range(numb_nodes):
            g.printAllPaths(s)       
        beta = g.get_beta()
        
        return beta



#beta_mat_3d_from_dgl_graph(dgl_graph, pow_dim, max_len,  add_id, truncate_beta)



def beta_from_dgl_graph_list(dgl_graph_list, pow_dim, max_len, max_nodes, add_identity, truncate_beta):
        
        
        num_graphs = len(dgl_graph_list)
        #out_beta = np.zeros((num_graphs, max_nodes, max_nodes, max_nodes, pow_dim ))
        out_beta = []
        out_adj = []
        for i in range(num_graphs):
            adj_and_beta = beta_mat_3d_from_dgl_graph(dgl_graph_list[i], pow_dim, max_len,  add_identity, truncate_beta) 
            beta_list = adj_and_beta[1]
            adj = adj_and_beta[0]
            adj = pad_mat_2d(adj, max_nodes)
            out_adj.append(adj)

            for p in range(len(beta_list)): 
                beta_3d = beta_list[p]
          
                beta_3d = pad_mat_3d(beta_3d, max_nodes)
                beta_list[p] = beta_3d 
            if pow_dim != 0:
                beta_list = np.stack(beta_list, axis = -1)
            out_beta.append(beta_list)
        if pow_dim != 0:    
            out_beta = np.stack(out_beta)               
        out_adj = np.stack(out_adj)              
        return [out_adj, out_beta]



def beta_from_dgl_graph_list_no_pad(dgl_graph_list, pow_dim, max_len, max_nodes, add_identity, truncate_beta):
        
        
        num_graphs = len(dgl_graph_list)
        #out_beta = np.zeros((num_graphs, max_nodes, max_nodes, max_nodes, pow_dim ))
        out_beta = []
        out_adj = []
        for i in range(num_graphs):
            adj_and_beta = beta_mat_3d_from_dgl_graph(dgl_graph_list[i], pow_dim, max_len,  add_identity, truncate_beta) 
            beta_list = adj_and_beta[1]
            adj = adj_and_beta[0]
            adj = pad_mat_2d(adj, max_nodes)
            out_adj.append(adj)
            out_beta.append(beta_list)

              
        return out_beta






def beta_alone_from_dgl_graph_list(dgl_graph_list, pow_dim, max_len, max_nodes, add_identity, truncate_beta):
        
        
        num_graphs = len(dgl_graph_list)
        #out_beta = np.zeros((num_graphs, max_nodes, max_nodes, max_nodes, pow_dim ))
        out_beta = []

        for i in range(num_graphs):
            beta = beta_alone_from_dgl_graph(dgl_graph_list[i], pow_dim, max_len,  add_identity, truncate_beta) 
              
        return  beta




def pad_tensor_list(tensor_list, full_size):
    num_elems = len(tensor_list)
    
    samp = tensor_list[0]    
    zero_tensor = torch.zeros_like(samp)
    for i in range(num_elems, full_size):
        tensor_list.append(zero_tensor)
    return tensor_list
  
def batch_num_nodes_to_index(list_num_nodes):
    out = [0]
    for elem in list_num_nodes:
        out.append(out[-1] + elem)
    return out


def pad_mat_3d(mat_3d, out_rows):
    out = np.zeros((out_rows, out_rows, out_rows))
    out[0:mat_3d.shape[0], 0:mat_3d.shape[1], 0:mat_3d.shape[2] ] = mat_3d
    return out

def pad_beta_list(beta_list, max_nodes):
    
    pow_dim = len(beta_list)
    out = []
    for i in range(pow_dim):
        padded_beta = pad_mat_3d(beta_list[i], max_nodes)
        out.append(padded_beta)   
    return out

    

def split_mat_3d(mat_3d, index_list):
    len_list = len(index_list)
    len_minus = len_list - 1
    mats_list = []
    for i in range(len_minus):
        curr_mat = mat_3d[index_list[i]:index_list[i+ 1], index_list[i]:index_list[i+ 1], index_list[i]:index_list[i+ 1]]
        mats_list.append(curr_mat)
    return mats_list


def split_pad_and_stack_beta(beta_list, batch_num_nodes, max_nodes):
    #beta_list is expected to be a 1-d list of 3d matrices where each 3-d matrix is associated with a power index.
    index_list = batch_num_nodes_to_index(batch_num_nodes) 
    pow_dim = len(beta_list)
    for i in range(pow_dim):
        beta_3d = beta_list[i]
        list_betas_in_batch = split_mat_3d(beta_3d, index_list)
        batch_size = len(list_betas_in_batch)
        for j in range(batch_size):
            list_betas_in_batch[j] = pad_mat_3d(list_betas_in_batch[j], max_nodes)
             
        beta_list[i] = np.stack(list_betas_in_batch)
            
    return beta_list  
             
    
 
def pad_mat_2d(mat_2d, out_rows):
    out = np.zeros((out_rows, out_rows))
    out[0:mat_2d.shape[0], 0:mat_2d.shape[1]] = mat_2d
    return out
       

def split_mat_2d(mat_2d, index_list):
    
    len_list = len(index_list)
    len_minus = len_list - 1
    mats_list = []
    for i in range(len_minus):
       
        curr_mat = mat_2d[ index_list[i]:index_list[i+ 1], index_list[i]:index_list[i+ 1]]
        mats_list.append(curr_mat)
    return mats_list
       




def split_pad_and_stack_adj(adj, batch_num_nodes, max_nodes):
    index_list = batch_num_nodes_to_index(batch_num_nodes) 
    list_adjs_in_batch = split_mat_2d(adj, index_list)
    batch_size = len(list_adjs_in_batch)
    for j in range(batch_size):  
        list_adjs_in_batch[j] = pad_mat_2d(list_adjs_in_batch[j], max_nodes)
    adj = np.stack(list_adjs_in_batch)
    return adj

def split_feat_2d(mat_2d, index_list):
    
    len_list = len(index_list)
    len_minus = len_list - 1
    mats_list = []
    for i in range(len_minus):
       
        curr_mat = mat_2d[ index_list[i]:index_list[i+ 1], :]
        mats_list.append(curr_mat)
    return mats_list


def pad_mat_2d_rows(mat_2d, out_rows):

    out = np.zeros((out_rows, mat_2d.shape[1]))
    out[0:mat_2d.shape[0], 0:mat_2d.shape[1]] = mat_2d
    return out

def split_pad_and_stack_feat(feat, batch_num_nodes, max_nodes):
    adj = feat
    index_list = batch_num_nodes_to_index(batch_num_nodes) 
    list_adjs_in_batch = split_feat_2d(adj, index_list)
    batch_size = len(list_adjs_in_batch)
    for j in range(batch_size):  
        list_adjs_in_batch[j] = pad_mat_2d_rows(list_adjs_in_batch[j], max_nodes)
    adj = np.stack(list_adjs_in_batch)
   
    return adj 

def unbatch_tensor(feats_batched, batch_num_nodes):
    index_list = batch_num_nodes_to_index(batch_num_nodes)
    batch_size = feats_batched.shape[0]
    total_nodes = sum(batch_num_nodes)
    out = torch.zeros(total_nodes, feats_batched.shape[-1])
    for i in range(batch_size):
        out[index_list[i]:index_list[i+1], :] = feats_batched[i, 0:batch_num_nodes[i], :]
    return out



def split_tensor_2d(mat_2d, index_list):
    
    len_list = len(index_list)
    len_minus = len_list - 1
    mats_list = []
    for i in range(len_minus):
       
        curr_mat = mat_2d[ index_list[i]:index_list[i+ 1], :]
        mats_list.append(curr_mat)
    return mats_list


def pad_tensor_2d_rows(mat_2d, out_rows):
    out = torch.zeros(out_rows, mat_2d.shape[1])
    out[0:mat_2d.shape[0], 0:mat_2d.shape[1]] = mat_2d
    return out

def split_pad_and_batch_tensor(feat, batch_num_nodes, max_nodes):
    adj = feat
    index_list = batch_num_nodes_to_index(batch_num_nodes) 
    list_adjs_in_batch = split_tensor_2d(adj, index_list)
    batch_size = len(list_adjs_in_batch)
    for j in range(batch_size):  
        list_adjs_in_batch[j] = pad_tensor_2d_rows(list_adjs_in_batch[j], max_nodes)
    adj = torch.stack(list_adjs_in_batch)
   
    return adj 




def normal_param_init(mu, std, max_nodes, pow_dim, num_layers):
    beta_params_list = nn.ParameterList()
    adj_params_list = nn.ParameterList()
    for i in range(num_layers):
        z = torch.randn(1,1,1, max_nodes*pow_dim + 1)
        #print("all_params_z: ", z)
        all_params = z*std + mu
        beta_params =  all_params[:,:,:,0:max_nodes*pow_dim]
        adj_params =  all_params[0,0,0,-1]
        beta_params_list.append(nn.Parameter(beta_params))
        adj_params_list.append(nn.Parameter(adj_params))

    return {"adj_params": adj_params_list, "beta_params": beta_params_list }



def he_param_init(max_nodes, pow_dim, num_layers):
    beta_params_list = nn.ParameterList()
    adj_params_list = nn.ParameterList()
    for i in range(num_layers):
        all_params = torch.empty(1,1,1, max_nodes*pow_dim + 1)
        nn.init.kaiming_uniform_(all_params, mode='fan_in', nonlinearity='relu')
        beta_params =  all_params[:,:,:,0:max_nodes*pow_dim]
        adj_params =  all_params[0,0,0,-1]
        
        beta_params_list.append(nn.Parameter(beta_params))
        adj_params_list.append(nn.Parameter(adj_params))

    return {"adj_params": adj_params_list, "beta_params": beta_params_list }


def const_param_init(max_nodes, pow_dim, num_layers, adj_factor):
    if ( str(adj_factor) ).lower()=='equal':
        adj_factor = 1/(max_nodes*pow_dim + 1)
        beta_factor = adj_factor
        print("\n beta_factor, adj_factor: ", beta_factor, ' ', adj_factor )
    else:
        adj_factor = float(adj_factor)
        beta_factor = (1.0 - adj_factor)/(max_nodes*pow_dim)
        print("\n beta_factor, adj_factor: ", beta_factor, ' ', adj_factor )


    beta_params = torch.empty(1,1,1, max_nodes*pow_dim) 
    beta_params = beta_params.fill_(beta_factor)
    beta_params = nn.ParameterList([ nn.Parameter(beta_params) for i in range(num_layers)])
    adj_params = nn.ParameterList([ nn.Parameter( torch.tensor(adj_factor) ) for i in range(num_layers)])

    return {"adj_params": adj_params, "beta_params": beta_params }


class early_stopping:
    def __init__(self, patience=3, min_delta=0, path='checkpoint.pt'):
        self.patience = patience
        self.min_delta = min_delta
        self.old_loss = np.inf
        self.counter = 0
    def stop_training(self,new_loss):
        
        if (new_loss - self.old_loss) > self.min_delta:
             self.counter = self.counter + 1
        else:
              self.counter = 0
        if self.counter >= self.patience :
            stop = True
        else:
            stop = False
        self.old_loss = new_loss
        return stop


def pool_edges_avg(edge_feats, batch_num_edges):
    index_list = batch_num_nodes_to_index(batch_num_edges)
    batch_size = len(batch_num_edges)
    avg_list = []
    for i in range(batch_size):
        curr_feats = edge_feats[index_list[i]: index_list[i + 1], :]
        curr_avg = torch.mean(curr_feats, axis = 0)
        avg_list.append(curr_avg)

    out = torch.stack(avg_list, axis = 0)
    return out


def name_model(config, args_dict, exp_keys, dir_name, score, score_string):
    config_keys = config.keys()
    
    for key in exp_keys:
        if not(key in config_keys):
            config[key] = args_dict[key]

    config_keys = config.keys()   
    
    
    lr_str = "{:.4e}".format(config['lr']) 
   
    wd_str = "{:.4e}".format(config['weight_decay']) 
    
    wdr_str = "{:.4e}".format(config['weight_drop']) 
  
    atom_featurizer_code = 0
    if config['atom_featurizer'] == 'batch_norm' or config['atom_featurizer'] == 0 :
        atom_featurizer_code = 0
    elif config['atom_featurizer'] == 'layer_norm' or config['atom_featurizer'] == 1:
        atom_featurizer_code = 1
    elif config['atom_featurizer'] == 'instance_norm' or config['atom_featurizer'] == 2:
        atom_featurizer_code = 2

    norm_layer_code = 0
    if config['norm_layer_type'] == 'batch_norm' or config['norm_layer_type'] == 0 :
        norm_layer_code = 0
    elif config['norm_layer_type'] == 'layer_norm' or config['norm_layer_type'] == 1:
        norm_layer_code = 1
    elif config['norm_layer_type'] == 'instance_norm' or config['norm_layer_type'] == 2:
        norm_layer_code = 2
    
    exp_name_1 = str(config['dataset']) + '_af' + str(atom_featurizer_code) + '_po' + str(config['pow_dim']) + '_h' + str(config['hidden_dim']) 
    exp_name_2 = '_l' + str(config['num_layers']) + '_n' + str(norm_layer_code) + '_r' + str(config['residual']) + '_dr' + str(config['dropout'])    
   
    exp_name_3 =  '_wdr' + wdr_str + '_wd' + wd_str  + '_lr' + lr_str
    exp_name_4 =  '_b' + str(config['batch_size']) + '_ep' + str(config['epochs']) 
    exp_name = exp_name_1 + exp_name_2 + exp_name_3 + exp_name_4 + '.pt'
    dir_list = os.listdir(dir_name)
    model_numb = len(dir_list)
    score_str = "{:4.3f}".format(score)
    exp_name = str(model_numb) + '_' + score_string + str(score) + '_' + exp_name

    return exp_name    



def max_nodes_and_edges(dataset):
    len_dataset = len(dataset)    
    max_nodes = 0
    max_edges = 0
    len_0 = len(dataset[0])
    
    if len_0 == 4:
        for i in range(len_dataset):
        
            smiles, dgl_graph, labels, masks = dataset[i]
        
            numb_nodes = dgl_graph.num_nodes()
            numb_edges = dgl_graph.num_edges()
            if numb_nodes > max_nodes:
                max_nodes = numb_nodes
            if numb_edges > max_edges:
                max_edges = numb_edges
    elif len_0 == 3:
        for i in range(len_dataset):        
            smiles, dgl_graph, labels = dataset[i]
        
            numb_nodes = dgl_graph.num_nodes()
            numb_edges = dgl_graph.num_edges()
            if numb_nodes > max_nodes:
                max_nodes = numb_nodes
            if numb_edges > max_edges:
                max_edges = numb_edges


 
    return max_nodes, max_edges




def aws_collate_molgraphs_0(data):
    """Batching a list of datapoints for dataloader.

    Parameters
    ----------
    data : list of 3-tuples or 4-tuples.
        Each tuple is for a single datapoint, consisting of
        a SMILES, a DGLGraph, all-task labels and optionally a binary
        mask indicating the existence of labels.

    Returns
    -------
    smiles : list
        List of smiles
    bg : DGLGraph
        The batched DGLGraph.
    labels : Tensor of dtype float32 and shape (B, T)
        Batched datapoint labels. B is len(data) and
        T is the number of total tasks.
    masks : Tensor of dtype float32 and shape (B, T)
        Batched datapoint binary mask, indicating the
        existence of labels.
    """
    if len(data[0]) == 3:
        smiles, graphs, labels = map(list, zip(*data))
    else:
        smiles, graphs, labels, masks = map(list, zip(*data))

    bg = dgl.batch(graphs)
    bg.set_n_initializer(dgl.init.zero_initializer)
    bg.set_e_initializer(dgl.init.zero_initializer)
    labels = torch.stack(labels, dim=0)

    if len(data[0]) == 3:
        masks = torch.ones(labels.shape)
    else:
        masks = torch.stack(masks, dim=0)

    return smiles, bg, labels, masks

def aws_collate_molgraphs(data):
    """Batching a list of datapoints for dataloader.

    Parameters
    ----------
    data : list of 3-tuples or 4-tuples.
        Each tuple is for a single datapoint, consisting of
        a SMILES, a DGLGraph, all-task labels and optionally a binary
        mask indicating the existence of labels.

    Returns
    -------
    smiles : list
        List of smiles
    bg : DGLGraph
        The batched DGLGraph.
    labels : Tensor of dtype float32 and shape (B, T)
        Batched datapoint labels. B is len(data) and
        T is the number of total tasks.
    masks : Tensor of dtype float32 and shape (B, T)
        Batched datapoint binary mask, indicating the
        existence of labels.
    """
    if len(data[0]) == 3:
        smiles, graphs, labels = map(list, zip(*data))
    else:
        smiles, graphs, labels, masks = map(list, zip(*data))

    bg = dgl.batch(graphs)
    bg.set_n_initializer(dgl.init.zero_initializer)
    bg.set_e_initializer(dgl.init.zero_initializer)
    labels = torch.stack(labels, dim=0)

    if len(data[0]) == 3:
        masks = torch.ones(labels.shape)
    else:
        masks = torch.stack(masks, dim=0)
    
    return smiles, bg, labels, masks







def collate_beta_for_timing(data, pow_dim=None,  max_nodes =None, add_identity =0, truncate_beta =0):
    """Batching a list of datapoints for dataloader.

    Parameters
    ----------
    data : list of 3-tuples or 4-tuples.
        Each tuple is for a single datapoint, consisting of
        a SMILES, a DGLGraph, all-task labels and optionally a binary
        mask indicating the existence of labels.

    Returns
    -------
    smiles : list
        List of smiles
    bg : DGLGraph
        The batched DGLGraph.
    labels : Tensor of dtype float32 and shape (B, T)
        Batched datapoint labels. B is len(data) and
        T is the number of total tasks.
    masks : Tensor of dtype float32 and shape (B, T)
        Batched datapoint binary mask, indicating the
        existence of labels.
    """
    max_len = pow_dim + 1
    if len(data[0]) == 3:
        smiles, graphs, labels = map(list, zip(*data))
    else:
        smiles, graphs, labels, masks = map(list, zip(*data))

    

    beta = beta_from_dgl_graph_list_no_pad(graphs, pow_dim, max_len, max_nodes, add_identity, truncate_beta)
        
    return beta




def aws_collate_beta_alone(data, pow_dim=None,  max_nodes =None, add_identity =0, truncate_beta =0):
    """Batching a list of datapoints for dataloader.

    Parameters
    ----------
    data : list of 3-tuples or 4-tuples.
        Each tuple is for a single datapoint, consisting of
        a SMILES, a DGLGraph, all-task labels and optionally a binary
        mask indicating the existence of labels.

    Returns
    -------
    smiles : list
        List of smiles
    bg : DGLGraph
        The batched DGLGraph.
    labels : Tensor of dtype float32 and shape (B, T)
        Batched datapoint labels. B is len(data) and
        T is the number of total tasks.
    masks : Tensor of dtype float32 and shape (B, T)
        Batched datapoint binary mask, indicating the
        existence of labels.
    """
    max_len = pow_dim + 1
    if len(data[0]) == 3:
        smiles, graphs, labels = map(list, zip(*data))
    else:
        smiles, graphs, labels, masks = map(list, zip(*data))

    

    beta = beta_alone_from_dgl_graph_list(graphs, pow_dim, max_len, max_nodes, add_identity, truncate_beta)
    return beta




def collate_molgraphs(data):
    """Batching a list of datapoints for dataloader.
    Parameters
    ----------
    data : list of 4-tuples.
        Each tuple is for a single datapoint, consisting of
        a SMILES, a DGLGraph, all-task labels and a binary
        mask indicating the existence of labels.
    Returns
    -------
    smiles : list
        List of smiles
    bg : DGLGraph
        The batched DGLGraph.
    labels : Tensor of dtype float32 and shape (B, T)
        Batched datapoint labels. B is len(data) and
        T is the number of total tasks.
    masks : Tensor of dtype float32 and shape (B, T)
        Batched datapoint binary mask, indicating the
        existence of labels.
    """
    #smiles, graphs, labels, masks = map(list, zip(*data))
    smiles, graphs, labels = map(list, zip(*data))

    bg = dgl.batch(graphs)
    bg.set_n_initializer(dgl.init.zero_initializer)
    bg.set_e_initializer(dgl.init.zero_initializer)
    labels = torch.stack(labels, dim=0)
    #masks = torch.stack(masks, dim=0)

    return bg, labels


class dataset_from_index(Dataset):
    def __init__(self,index_set):
        
        self.index_set = index_set
                                 
    def __getitem__(self,index):
        
            return self.index_set[index]
              
             
    def __len__(self):
        return len(list(self.index_set))




def get_even_grid(first_val, last_val, common_diff):
    hidden_grid = []
    for i in range(first_val, last_val + 1, common_diff):
        hidden_grid.append(i)
    return hidden_grid




def weights_mat_to_dgl(weights_mat, norm_style=None, pow_ind = None , depth = None, move_dict_time = None):
    if move_dict_time == 'pre':
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device("cpu")

    out_dict = {}
    weights_list = []
    source_list = []
    dest_list = []
    
    adj_shape = weights_mat.shape
    numb_nodes = adj_shape[0]
    for source in range(numb_nodes):
        for dest in range(numb_nodes):
            if weights_mat[source, dest] != 0:
                weights_list.append(weights_mat[source, dest])
                source_list.append(source)
                dest_list.append(dest)
    if move_dict_time == 'pre':
        out_dict['graph'] = dgl.graph( (source_list, dest_list) ).to(device = device)
        weights_list = (torch.tensor(weights_list)).to(device = device)
    else:
        out_dict['graph'] = dgl.graph( (source_list, dest_list) )
        weights_list = (torch.tensor(weights_list))

    if norm_style:
        norm = EdgeWeightNorm(norm= norm_style)
        weights_list = norm(out_dict['graph'], weights_list)
        
    out_dict['edges_weights'] = weights_list
    return out_dict




def mat_as_dict_to_dgl(weights_mat, norm_style=None, move_dict_time = None):
    if move_dict_time == 'pre':
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device("cpu")

    out_dict = {}
    weights_list = []
    source_list = []
    dest_list = []
    
    #adj_shape = weights_mat.shape
    #numb_nodes = adj_shape[0]
    #for source in range(numb_nodes):
        #for dest in range(numb_nodes):
    for dict_key in weights_mat:
            #if weights_mat[source, dest] != 0:
                
                weights_list.append(weights_mat[dict_key])
                source_list.append(dict_key[0])
                dest_list.append(dict_key[1])
    if move_dict_time == 'pre':
        out_dict['graph'] = dgl.graph( (source_list, dest_list) ).to(device = device)
        weights_list = (torch.tensor(weights_list)).to(device = device)
    else:
        out_dict['graph'] = dgl.graph( (source_list, dest_list) )
        weights_list = (torch.tensor(weights_list))

    if norm_style:
        norm = EdgeWeightNorm(norm= norm_style)
        weights_list = norm(out_dict['graph'], weights_list)
        
    out_dict['edges_weights'] = weights_list
    return out_dict






def dgl_g_to_planetoid(dgl_g, numb_nodes):
    out = {}
    for i in range(numb_nodes):
        out[i] = []
    sources = dgl_g[0].tolist()
    numb_edges = len(sources)
    dests = dgl_g[1].tolist()
    
    for i in range(numb_edges):
        s = sources[i]
        out[s].append(dests[i]) 

    return out



def beta_mat_as_dict_from_dgl_graph(dgl_graph, pow_dim, max_len):
        graph_edges = dgl_graph.edges()
        numb_nodes = dgl_graph.num_nodes()
    
        planetoid_graph = dgl_g_to_planetoid(graph_edges, numb_nodes)
        g = Graph_mat_as_dict(numb_nodes, pow_dim, add_identity = True)
        g.setGraph(planetoid_graph)
        g.setMaxPathLen(max_len)
        for s in range(numb_nodes):
            g.printAllPaths(s)       
        adj_and_beta = g.get_adj_and_beta()
        
        return adj_and_beta

#(beta, pow_dim, numb_nodes, norm_style, move_dict_time)

def dict_of_dicts_from_mat_as_dict(beta, pow_dim, depth_dim,  norm_style, move_dict_time):
    dict_of_dicts = {}

    for pow_ind in range(pow_dim):
        for d in range(depth_dim):
            dict_of_dicts[pow_ind, d] = mat_as_dict_to_dgl(beta[pow_ind][d], norm_style, move_dict_time )

    return dict_of_dicts




def dict_of_dicts_from_beta(dataset_name, reduced_by, reduced_dir, pow_dim, depth_dim, sub_nodes, pre_scaler, post_scaler, norm_style, move_dict_time):

    if post_scaler == 'min_max':
        scaler = MinMaxScaler()
    elif post_scaler == 'std':
        scaler = StandardScaler()
    else:
        scaler = None

    dict_of_dicts = {}
    for pow_ind in range(pow_dim): 
    
        file_name = dataset_name + '_reduced_by_' + str(reduced_by)  + '_pow_ind_' + str(pow_ind) + '_pow_dim_' + str(pow_dim) +  '_depth_dim_' + str(depth_dim) +  '_sub_nodes_' + str(sub_nodes) + '_pre_scaler_' + str(pre_scaler) +'.npy'
    
        path_to_reduced = os.path.join(reduced_dir, file_name)
        beta = np.load(path_to_reduced)
        beta = beta.astype(np.float32)
        beta_shape = beta.shape
        
        beta = beta.reshape(beta_shape[0]*beta_shape[1], beta_shape[2])
        if scaler:
            scaler.fit(beta)
            beta = scaler.transform(beta)
        beta = beta.reshape(beta_shape[0], beta_shape[1], beta_shape[2])
    
        for d in range(depth_dim): 
            dict_of_dicts[pow_ind, d] = weights_mat_to_dgl(beta[:, :, d], norm_style, pow_ind, d, move_dict_time )

    return dict_of_dicts


def print_beta_mat_as_dict(beta):
    pow_dim = len(beta)
    numb_nodes = len(beta[0])
    
    for i in range(pow_dim):
        for j in range(numb_nodes):
            print("current dict at ", str(i), " ", str(j), ": \n",  beta[i][j] )





def beta_mat_3d_from_dgl_graph(dgl_graph, pow_dim, max_len, add_identity, truncate_beta):
        graph_edges = dgl_graph.edges()
        numb_nodes = dgl_graph.num_nodes()
    
        planetoid_graph = dgl_g_to_planetoid(graph_edges, numb_nodes)
        g = Graph_mat_3d(numb_nodes, pow_dim, add_identity = add_identity, truncate_beta = truncate_beta)
        g.setGraph(planetoid_graph)
        g.setMaxPathLen(max_len)
        for s in range(numb_nodes):
            g.printAllPaths(s)       
        adj_and_beta = g.get_adj_and_beta()
        
        return adj_and_beta


def beta_alone_from_dgl_graph(dgl_graph, pow_dim, max_len, add_identity, truncate_beta):
        graph_edges = dgl_graph.edges()
        numb_nodes = dgl_graph.num_nodes()
    
        planetoid_graph = dgl_g_to_planetoid(graph_edges, numb_nodes)
        g = Graph_beta_alone(numb_nodes, pow_dim, add_identity = add_identity, truncate_beta = truncate_beta)
        g.setGraph(planetoid_graph)
        g.setMaxPathLen(max_len)
        for s in range(numb_nodes):
            g.printAllPaths(s)       
        beta = g.get_beta()
        
        return beta



#beta_mat_3d_from_dgl_graph(dgl_graph, pow_dim, max_len,  add_id, truncate_beta)



def beta_from_dgl_graph_list(dgl_graph_list, pow_dim, max_len, max_nodes, add_identity, truncate_beta):
        
        
        num_graphs = len(dgl_graph_list)
        #out_beta = np.zeros((num_graphs, max_nodes, max_nodes, max_nodes, pow_dim ))
        out_beta = []
        out_adj = []
        for i in range(num_graphs):
            adj_and_beta = beta_mat_3d_from_dgl_graph(dgl_graph_list[i], pow_dim, max_len,  add_identity, truncate_beta) 
            beta_list = adj_and_beta[1]
            adj = adj_and_beta[0]
            adj = pad_mat_2d(adj, max_nodes)
            out_adj.append(adj)

            for p in range(len(beta_list)): 
                beta_3d = beta_list[p]
          
                beta_3d = pad_mat_3d(beta_3d, max_nodes)
                beta_list[p] = beta_3d 
            if pow_dim != 0:
                beta_list = np.stack(beta_list, axis = -1)
            out_beta.append(beta_list)
        if pow_dim != 0:    
            out_beta = np.stack(out_beta)               
        out_adj = np.stack(out_adj)              
        return [out_adj, out_beta]



def beta_from_dgl_graph_list_no_pad(dgl_graph_list, pow_dim, max_len, max_nodes, add_identity, truncate_beta):
        
        
        num_graphs = len(dgl_graph_list)
        #out_beta = np.zeros((num_graphs, max_nodes, max_nodes, max_nodes, pow_dim ))
        out_beta = []
        out_adj = []
        for i in range(num_graphs):
            adj_and_beta = beta_mat_3d_from_dgl_graph(dgl_graph_list[i], pow_dim, max_len,  add_identity, truncate_beta) 
            beta_list = adj_and_beta[1]
            adj = adj_and_beta[0]
            adj = pad_mat_2d(adj, max_nodes)
            out_adj.append(adj)
            out_beta.append(beta_list)

              
        return out_beta






def beta_alone_from_dgl_graph_list(dgl_graph_list, pow_dim, max_len, max_nodes, add_identity, truncate_beta):
        
        
        num_graphs = len(dgl_graph_list)
        #out_beta = np.zeros((num_graphs, max_nodes, max_nodes, max_nodes, pow_dim ))
        out_beta = []

        for i in range(num_graphs):
            beta = beta_alone_from_dgl_graph(dgl_graph_list[i], pow_dim, max_len,  add_identity, truncate_beta) 
              
        return  beta




def pad_tensor_list(tensor_list, full_size):
    num_elems = len(tensor_list)
    
    samp = tensor_list[0]    
    zero_tensor = torch.zeros_like(samp)
    for i in range(num_elems, full_size):
        tensor_list.append(zero_tensor)
    return tensor_list
  
def batch_num_nodes_to_index(list_num_nodes):
    out = [0]
    for elem in list_num_nodes:
        out.append(out[-1] + elem)
    return out


def pad_mat_3d(mat_3d, out_rows):
    out = np.zeros((out_rows, out_rows, out_rows))
    out[0:mat_3d.shape[0], 0:mat_3d.shape[1], 0:mat_3d.shape[2] ] = mat_3d
    return out

def pad_beta_list(beta_list, max_nodes):
    
    pow_dim = len(beta_list)
    out = []
    for i in range(pow_dim):
        padded_beta = pad_mat_3d(beta_list[i], max_nodes)
        out.append(padded_beta)   
    return out

    

def split_mat_3d(mat_3d, index_list):
    len_list = len(index_list)
    len_minus = len_list - 1
    mats_list = []
    for i in range(len_minus):
        curr_mat = mat_3d[index_list[i]:index_list[i+ 1], index_list[i]:index_list[i+ 1], index_list[i]:index_list[i+ 1]]
        mats_list.append(curr_mat)
    return mats_list


def split_pad_and_stack_beta(beta_list, batch_num_nodes, max_nodes):
    #beta_list is expected to be a 1-d list of 3d matrices where each 3-d matrix is associated with a power index.
    index_list = batch_num_nodes_to_index(batch_num_nodes) 
    pow_dim = len(beta_list)
    for i in range(pow_dim):
        beta_3d = beta_list[i]
        list_betas_in_batch = split_mat_3d(beta_3d, index_list)
        batch_size = len(list_betas_in_batch)
        for j in range(batch_size):
            list_betas_in_batch[j] = pad_mat_3d(list_betas_in_batch[j], max_nodes)
             
        beta_list[i] = np.stack(list_betas_in_batch)
            
    return beta_list  
             
    
 
def pad_mat_2d(mat_2d, out_rows):
    out = np.zeros((out_rows, out_rows))
    out[0:mat_2d.shape[0], 0:mat_2d.shape[1]] = mat_2d
    return out
       

def split_mat_2d(mat_2d, index_list):
    
    len_list = len(index_list)
    len_minus = len_list - 1
    mats_list = []
    for i in range(len_minus):
       
        curr_mat = mat_2d[ index_list[i]:index_list[i+ 1], index_list[i]:index_list[i+ 1]]
        mats_list.append(curr_mat)
    return mats_list
       




def split_pad_and_stack_adj(adj, batch_num_nodes, max_nodes):
    index_list = batch_num_nodes_to_index(batch_num_nodes) 
    list_adjs_in_batch = split_mat_2d(adj, index_list)
    batch_size = len(list_adjs_in_batch)
    for j in range(batch_size):  
        list_adjs_in_batch[j] = pad_mat_2d(list_adjs_in_batch[j], max_nodes)
    adj = np.stack(list_adjs_in_batch)
    return adj

def split_feat_2d(mat_2d, index_list):
    
    len_list = len(index_list)
    len_minus = len_list - 1
    mats_list = []
    for i in range(len_minus):
       
        curr_mat = mat_2d[ index_list[i]:index_list[i+ 1], :]
        mats_list.append(curr_mat)
    return mats_list


def pad_mat_2d_rows(mat_2d, out_rows):

    out = np.zeros((out_rows, mat_2d.shape[1]))
    out[0:mat_2d.shape[0], 0:mat_2d.shape[1]] = mat_2d
    return out

def split_pad_and_stack_feat(feat, batch_num_nodes, max_nodes):
    adj = feat
    index_list = batch_num_nodes_to_index(batch_num_nodes) 
    list_adjs_in_batch = split_feat_2d(adj, index_list)
    batch_size = len(list_adjs_in_batch)
    for j in range(batch_size):  
        list_adjs_in_batch[j] = pad_mat_2d_rows(list_adjs_in_batch[j], max_nodes)
    adj = np.stack(list_adjs_in_batch)
   
    return adj 

def unbatch_tensor(feats_batched, batch_num_nodes):
    index_list = batch_num_nodes_to_index(batch_num_nodes)
    batch_size = feats_batched.shape[0]
    total_nodes = sum(batch_num_nodes)
    out = torch.zeros(total_nodes, feats_batched.shape[-1])
    for i in range(batch_size):
        out[index_list[i]:index_list[i+1], :] = feats_batched[i, 0:batch_num_nodes[i], :]
    return out



def split_tensor_2d(mat_2d, index_list):
    
    len_list = len(index_list)
    len_minus = len_list - 1
    mats_list = []
    for i in range(len_minus):
       
        curr_mat = mat_2d[ index_list[i]:index_list[i+ 1], :]
        mats_list.append(curr_mat)
    return mats_list


def pad_tensor_2d_rows(mat_2d, out_rows):
    out = torch.zeros(out_rows, mat_2d.shape[1])
    out[0:mat_2d.shape[0], 0:mat_2d.shape[1]] = mat_2d
    return out

def split_pad_and_batch_tensor(feat, batch_num_nodes, max_nodes):
    adj = feat
    index_list = batch_num_nodes_to_index(batch_num_nodes) 
    list_adjs_in_batch = split_tensor_2d(adj, index_list)
    batch_size = len(list_adjs_in_batch)
    for j in range(batch_size):  
        list_adjs_in_batch[j] = pad_tensor_2d_rows(list_adjs_in_batch[j], max_nodes)
    adj = torch.stack(list_adjs_in_batch)
   
    return adj 




def normal_param_init(mu, std, max_nodes, pow_dim, num_layers):
    beta_params_list = nn.ParameterList()
    adj_params_list = nn.ParameterList()
    for i in range(num_layers):
        z = torch.randn(1,1,1, max_nodes*pow_dim + 1)
        #print("all_params_z: ", z)
        all_params = z*std + mu
        beta_params =  all_params[:,:,:,0:max_nodes*pow_dim]
        adj_params =  all_params[0,0,0,-1]
        beta_params_list.append(nn.Parameter(beta_params))
        adj_params_list.append(nn.Parameter(adj_params))

    return {"adj_params": adj_params_list, "beta_params": beta_params_list }



def he_param_init(max_nodes, pow_dim, num_layers):
    beta_params_list = nn.ParameterList()
    adj_params_list = nn.ParameterList()
    for i in range(num_layers):
        all_params = torch.empty(1,1,1, max_nodes*pow_dim + 1)
        nn.init.kaiming_uniform_(all_params, mode='fan_in', nonlinearity='relu')
        beta_params =  all_params[:,:,:,0:max_nodes*pow_dim]
        adj_params =  all_params[0,0,0,-1]
        
        beta_params_list.append(nn.Parameter(beta_params))
        adj_params_list.append(nn.Parameter(adj_params))

    return {"adj_params": adj_params_list, "beta_params": beta_params_list }


def const_param_init(max_nodes, pow_dim, num_layers, adj_factor):
    if ( str(adj_factor) ).lower()=='equal':
        adj_factor = 1/(max_nodes*pow_dim + 1)
        beta_factor = adj_factor
        print("\n beta_factor, adj_factor: ", beta_factor, ' ', adj_factor )
    else:
        adj_factor = float(adj_factor)
        beta_factor = (1.0 - adj_factor)/(max_nodes*pow_dim)
        print("\n beta_factor, adj_factor: ", beta_factor, ' ', adj_factor )


    beta_params = torch.empty(1,1,1, max_nodes*pow_dim) 
    beta_params = beta_params.fill_(beta_factor)
    beta_params = nn.ParameterList([ nn.Parameter(beta_params) for i in range(num_layers)])
    adj_params = nn.ParameterList([ nn.Parameter( torch.tensor(adj_factor) ) for i in range(num_layers)])

    return {"adj_params": adj_params, "beta_params": beta_params }


class early_stopping:
    def __init__(self, patience=3, min_delta=0, path='checkpoint.pt'):
        self.patience = patience
        self.min_delta = min_delta
        self.old_loss = np.inf
        self.counter = 0
    def stop_training(self,new_loss):
        
        if (new_loss - self.old_loss) > self.min_delta:
             self.counter = self.counter + 1
        else:
              self.counter = 0
        if self.counter >= self.patience :
            stop = True
        else:
            stop = False
        self.old_loss = new_loss
        return stop


def pool_edges_avg(edge_feats, batch_num_edges):
    index_list = batch_num_nodes_to_index(batch_num_edges)
    batch_size = len(batch_num_edges)
    avg_list = []
    for i in range(batch_size):
        curr_feats = edge_feats[index_list[i]: index_list[i + 1], :]
        curr_avg = torch.mean(curr_feats, axis = 0)
        avg_list.append(curr_avg)

    out = torch.stack(avg_list, axis = 0)
    return out


def name_model(config, args_dict, exp_keys, dir_name, score, score_string):
    config_keys = config.keys()
    
    for key in exp_keys:
        if not(key in config_keys):
            config[key] = args_dict[key]

    config_keys = config.keys()   
    
    
    lr_str = "{:.4e}".format(config['lr']) 
   
    wd_str = "{:.4e}".format(config['weight_decay']) 
    
    wdr_str = "{:.4e}".format(config['weight_drop']) 
  
    atom_featurizer_code = 0
    if config['atom_featurizer'] == 'batch_norm' or config['atom_featurizer'] == 0 :
        atom_featurizer_code = 0
    elif config['atom_featurizer'] == 'layer_norm' or config['atom_featurizer'] == 1:
        atom_featurizer_code = 1
    elif config['atom_featurizer'] == 'instance_norm' or config['atom_featurizer'] == 2:
        atom_featurizer_code = 2

    norm_layer_code = 0
    if config['norm_layer_type'] == 'batch_norm' or config['norm_layer_type'] == 0 :
        norm_layer_code = 0
    elif config['norm_layer_type'] == 'layer_norm' or config['norm_layer_type'] == 1:
        norm_layer_code = 1
    elif config['norm_layer_type'] == 'instance_norm' or config['norm_layer_type'] == 2:
        norm_layer_code = 2
    
    exp_name_1 = str(config['dataset']) + '_af' + str(atom_featurizer_code) + '_po' + str(config['pow_dim']) + '_h' + str(config['hidden_dim']) 
    exp_name_2 = '_l' + str(config['num_layers']) + '_n' + str(norm_layer_code) + '_r' + str(config['residual']) + '_dr' + str(config['dropout'])    
   
    exp_name_3 =  '_wdr' + wdr_str + '_wd' + wd_str  + '_lr' + lr_str
    exp_name_4 =  '_b' + str(config['batch_size']) + '_ep' + str(config['epochs']) 
    exp_name = exp_name_1 + exp_name_2 + exp_name_3 + exp_name_4 + '.pt'
    dir_list = os.listdir(dir_name)
    model_numb = len(dir_list)
    score_str = "{:4.3f}".format(score)
    exp_name = str(model_numb) + '_' + score_string + str(score) + '_' + exp_name

    return exp_name    



def max_nodes_and_edges(dataset):
    len_dataset = len(dataset)    
    max_nodes = 0
    max_edges = 0
    len_0 = len(dataset[0])
    
    if len_0 == 4:
        for i in range(len_dataset):
        
            smiles, dgl_graph, labels, masks = dataset[i]
        
            numb_nodes = dgl_graph.num_nodes()
            numb_edges = dgl_graph.num_edges()
            if numb_nodes > max_nodes:
                max_nodes = numb_nodes
            if numb_edges > max_edges:
                max_edges = numb_edges
    elif len_0 == 3:
        for i in range(len_dataset):        
            smiles, dgl_graph, labels = dataset[i]
        
            numb_nodes = dgl_graph.num_nodes()
            numb_edges = dgl_graph.num_edges()
            if numb_nodes > max_nodes:
                max_nodes = numb_nodes
            if numb_edges > max_edges:
                max_edges = numb_edges


 
    return max_nodes, max_edges






def max_path_len(dataset):
    len_dataset = len(dataset)
    max_path_len = 0
    len_0 = len(dataset[0])

    if len_0 == 4:
        for i in range(len_dataset):

            smiles, dgl_graph, labels, masks = dataset[i]
            dist_mat, path = dgl.shortest_dist(dgl_graph, return_paths=True)

            if path.shape[2] > max_path_len:
                max_path_len = path.shape[2]


    elif len_0 == 3:
        for i in range(len_dataset):
            smiles, dgl_graph, labels = dataset[i]

            dist_mat, path = dgl.shortest_dist(dgl_graph, return_paths=True)

            if path.shape[2] > max_path_len:
                max_path_len = path.shape[2]

    return max_path_len



def add_noise_to_node(dgl_graph, seed, node_std):
        torch.manual_seed(seed)
        node_feats = dgl_graph.ndata['h']
        node_noise = torch.normal(mean=0.0, std = node_std)
        dgl_graph.ndata['h'] = node_feats + node_noise 
        return dgl_graph


def node_mean_and_std(dataset, DataLoader, collate_fn, num_workers):
    collate_fn = aws_collate_molgraphs
    data_loader = DataLoader(dataset= dataset, shuffle=False, batch_size=len(dataset), collate_fn=collate_fn, num_workers= num_workers)

    for i, batch in enumerate(data_loader):
        
        smiles, dgl_graph, labels, masks = batch
        node_feats = dgl_graph.ndata['h'] 
        
        node_mean = torch.mean(node_feats, dim = 0)
        node_std = torch.std(node_feats, dim = 0)
    return node_mean, node_std 



def WeightDrop(module, weights_names_ls, dropout_p):

    original_module_forward = module.forward
    forward_with_drop = ForwardWithDrop(weights_names_ls, module, dropout_p, original_module_forward)
    setattr(module, 'forward', forward_with_drop)
    return module    

     

from scipy.sparse import csr_matrix
from scipy.sparse import lil_matrix

def sparse_mat_intializer(numb_nodes, source):
    data = np.full(( numb_nodes, ), 1/numb_nodes)
    col_inds = np.arange(numb_nodes)
    row_ptrs = np.zeros(numb_nodes + 1)
    row_ptrs[source + 1:] = numb_nodes
    csr = csr_matrix((data, col_inds, row_ptrs), shape=(numb_nodes,numb_nodes))
    lil = lil_matrix(csr)
    return lil
