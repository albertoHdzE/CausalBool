


import shutil
import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import copy
import dgl, dgllife
import time
from functools import partial

from torch.utils.data import DataLoader

from dgllife.data import FreeSolv
from dgllife.utils import smiles_to_bigraph, CanonicalAtomFeaturizer, CanonicalBondFeaturizer, AttentiveFPAtomFeaturizer,  AttentiveFPBondFeaturizer, ConsecutiveSplitter, ScaffoldSplitter, RandomSplitter
from dgllife.utils import Meter, SMILESToBigraph

from graphormer_dist_model import TransformerEncoder as graphormer_model


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



from utils import  max_path_len, batch_num_nodes_to_index, max_nodes_and_edges, early_stopping, beta_mat_3d_from_dgl_graph, split_mat_3d, pad_mat_3d, split_mat_2d, pad_mat_2d, split_pad_and_stack_beta, split_pad_and_stack_adj, split_pad_and_stack_feat
from utils import aws_collate_molgraphs as collate_molgraphs
from utils import batch_num_nodes_to_index, unbatch_adj_tensor





def float_or_str(value):
    try:
        return float(value)
    except:
        return value


def get_feat_dim(data_loader):
    for i, batch in enumerate(data_loader):
        smiles, dgl_graph, labels, masks = batch
        feats = dgl_graph.ndata['h']
        inp_dim = feats.shape[-1]
        return inp_dim          

def get_edge_dim(data_loader):
    for i, batch in enumerate(data_loader):
        smiles, dgl_graph, labels, masks = batch
        feats = dgl_graph.ndata['h']
        inp_dim = feats.shape[-1]
        try:
            edge_feats = dgl_graph.edata['e']
            print("i: ", i)
        except KeyError:     
            continue

        edge_dim = edge_feats.shape[-1]
        return edge_dim


def get_label_scaler(dataset):
    len_train = len(dataset)
    data_loader = DataLoader(dataset,  batch_size=len_train, shuffle=False,  collate_fn=collate_molgraphs)
    
    for i, batch in enumerate(data_loader):
        
        dgl_graph, labels = batch
        labels = labels.numpy()
        if args.label_scaler.lower() == 'min_max':
            scaler_labels = MinMaxScaler()
            scaler_labels.fit(labels)
            
        elif args.label_scaler.lower() == 'std':
            scaler_labels = StandardScaler()
            scaler_labels.fit(labels)
        else:
             scaler_labels = None
            
    return scaler_labels

   
def get_beta_max(beta_list):
    len_beta = len(beta_list)
    max_val = 0
    for i in range(len_beta):
        val = np.amax(beta_list[i])
        if val > max_val:
            max_val = val
    return max_val


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




def train(data_loader, device, max_nodes, pow_dim, max_len, norm_style, model, loss_function, optimizer, residual):
    
    loss_list = []
    model.train()
    train_meter = Meter()
    cum_loss = 0.
    num_graphs = 0
    for i, batch in enumerate(data_loader):
 
        smiles, dgl_graph, labels, masks = batch 
         
        labels, masks = labels.to(device), masks.to(device)

        numb_nodes = dgl_graph.num_nodes()
        batch_num_nodes = dgl_graph.batch_num_nodes()
        feats = dgl_graph.ndata['h']
        feats = feats.numpy()
        feats = split_pad_and_stack_feat(feats, batch_num_nodes, max_nodes)
        feats = torch.from_numpy(feats)
        feats = feats.to(torch.float32).to(device)
        out = model(feats, adj, beta, residual)
           
        loss = (loss_function(out, labels) * (masks != 0).float()).mean() 
        
        loss_list.append(loss)  
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
       
        train_meter.update(out, labels, masks)
    train_score = np.mean(train_meter.compute_metric(args.metric))
    return loss, train_score


def test_feats(data_loader, num_nodes):
    
    for i, batch in enumerate(data_loader):
 
        smiles, dgl_graph, labels, masks = batch 
        if dgl_graph.num_nodes()== num_nodes:     
            return dgl_graph



@torch.no_grad()
def test(data_loader, device, max_nodes, pow_dim, max_len, norm_style, model, loss_function, optimizer, residual):
    
    loss_list = []
    model.eval()
    train_meter = Meter()
    cum_loss = 0.
    num_graphs = 0
    for i, batch in enumerate(data_loader):
 
        smiles, dgl_graph, labels, masks, adj, beta = batch  
        labels, masks = labels.to(device), masks.to(device)

        numb_nodes = dgl_graph.num_nodes()
        batch_num_nodes = dgl_graph.batch_num_nodes()
        feats = dgl_graph.ndata['h']
        feats = feats.numpy()
        feats = split_pad_and_stack_feat(feats, batch_num_nodes, max_nodes)
        feats = torch.from_numpy(feats)
        feats = feats.to(torch.float32).to(device)
        if pow_dim !=0:
            beta = torch.from_numpy(beta).to(torch.float32).to(device)
        adj = torch.from_numpy(adj).to(torch.float32).to(device)
        out = model(feats, adj, beta, residual)
 
          
        loss = (loss_function(out, labels) * (masks != 0).float()).mean() 
        
        loss_list.append(loss)  
          
        train_meter.update(out, labels, masks)
    train_score = np.mean(train_meter.compute_metric(args.metric))
    return loss, train_score



def get_path_info( g, paths, max_nodes, max_path_len, device ):
        
        path_params = torch.empty(1,1,1, max_path_len, args.edge_dim)
        self_path_params = nn.init.kaiming_uniform_(path_params, nonlinearity='relu')
        self_path_params = nn.Parameter(path_params)
 
        
        #dist_mat, paths = dgl.shortest_dist(g, return_paths = True)
        mat_5d = paths_edge_feats(g, paths, max_nodes, max_path_len)
        mat_5d = torch.mul(mat_5d, self_path_params)
        mat_5d = torch.sum(mat_5d, dim = -1)        
        mat_5d = torch.mean(mat_5d, dim = -1) 
        return mat_5d




def attach_dist_and_path_info(g, dist_mat, path_mat):

    
    device = dist_mat.device
    num_edges = g.num_edges()
    all_edges = g.edges(form='all')
    print("all_edges: ", all_edges)
    edge_list = list(range(0, num_edges))
    found = g.find_edges(edge_list)
    source_list = []
    dest_list = []
    print("orig_0 g.num_nodes  : ", g.num_nodes())

    print("g source and dest : ", source_list, dest_list)
    distances = []
    path_info = []
    for i in range(num_edges):
        s = found[0][i]
        d = found[1][i]
        source_list.append(s)
        dest_list.append(d)

        distances.append(dist_mat[s,d])
        path_info.append(path_mat[s,d])

    print("g_2 source and dest b4: ", source_list, dest_list)

    greater_counter = 0
    for r in range(dist_mat.shape[0]):
        for c in range(dist_mat.shape[1]):
            if dist_mat[r,c] > 1:
                #greater_counter =  greater_counter + 1
                source_list.append(r)
                dest_list.append(c)
                distances.append(dist_mat[r,c])
                path_info.append(path_mat[r,c])

   
    
    #print("GREATER_COUNTER: ", greater_counter)
    print("g_2 source and dest aft : ", source_list, dest_list)
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
    
    print("G BATCH_NUM_NODES: ", g.batch_num_nodes())
    print("G NUM_NODES: ", g.num_nodes())
    print("G2 BATCH_NUM_NODES: ", g_2.batch_num_nodes())
    print("G2 NUM_NODES: ", g_2.num_nodes())
    print("G NUM FEATS: ", g.ndata['h'].shape[0])
    print(g.ndata['h'][:, 0])

    g_2.ndata['h'] = g.ndata['h']

    return g_2




 
 
def main():
    args.batch_size = 1
    device = torch.device("cuda" if args.use_gpu == 1 and torch.cuda.is_available() else 'cpu')  

    if args.splitter == 'consec':
        splitter = ConsecutiveSplitter()
        split = splitter.train_val_test_split(dataset)
    elif args.splitter == 'random':
        splitter = RandomSplitter()
        split = splitter.train_val_test_split(dataset, random_state = args.rand_state)
    elif args.splitter == 'scaffold':
        splitter = ScaffoldSplitter()
        split = splitter.train_val_test_split(dataset,  scaffold_func='smiles')
   
    train_loader = DataLoader(dataset=split[0], shuffle=True, batch_size=args.batch_size, collate_fn=collate_molgraphs, num_workers=args.num_workers)
    val_loader = DataLoader(dataset=split[1], shuffle = False, batch_size=args.batch_size, collate_fn=collate_molgraphs, num_workers=args.num_workers)
    test_loader = DataLoader(dataset=split[2], shuffle = False, batch_size=args.batch_size, collate_fn=collate_molgraphs, num_workers=args.num_workers)



    # load model
    inp_dim = get_feat_dim(train_loader) 
    #model = t_hop_model( args.max_nodes, args.pow_dim, args.num_layers,  args.tie_all_layers, args.layer_ties, inp_dim, args.hidden_dim, args.num_classes, args.dropout, args.weight_drop, args.params_init_type, args.adj_factor, args.norm_layer_type)    
    #model = graphormer_model(args.num_layers, inp_dim, args.hidden_dim, args.num_heads, args.ff_dim)

    #model = model.to(device = device)

  
    #if (args.opt).lower() == 'adam':
    #    opt = optim.Adam(model.parameters(), lr=args.lr, weight_decay = args.weight_decay)
    #elif (args.opt).lower() == 'sgd':
    #    opt = optim.SGD(model.parameters(), lr=args.lr, weight_decay = args.weight_decay)

    if args.metric in [ 'r2', 'mae', 'rmse']:
        loss_fn = nn.SmoothL1Loss(reduction='none')       
    elif args.metric in ['roc_auc_score', 'pr_auc_score'] :
        loss_fn = nn.BCEWithLogitsLoss(reduction='none')
    
    for epoch in range(0):
        # Train
        if epoch == 0:
            t1 = time.time()
                                
        train_loss, train_score = train(train_loader, device, args.max_nodes, args.pow_dim,  args.max_len, args.edge_norm,  model, loss_fn, opt, args.residual) 
        if epoch == 0:
            t2 = time.time()
            print("Time spent on single epoch of train function in seconds: ", (t2- t1))
            print('---------- Training ----------')
       
        val_loss, val_score =   test(val_loader, device, args.max_nodes, args.pow_dim,  args.max_len, args.edge_norm,  model, loss_fn, opt, args.residual) 
        test_loss, test_score = test(test_loader, device, args.max_nodes, args.pow_dim,  args.max_len, args.edge_norm,  model, loss_fn, opt, args.residual) 

        print('| epoch {:3d} | train loss {:5.5f} | val loss {:5.5f} | test loss {:5.5f} | | train score {:2.3f} | val score {:2.3f} | test score {:2.3f}'.format(
             epoch, train_loss, val_loss, test_loss, train_score, val_score, test_score), flush=True)


    args.edge_dim = get_edge_dim(test_loader) 
   
    g_1 = test_feats(train_loader, 3)
    g_2 = test_feats(train_loader, 2)
    g_3 = test_feats(train_loader, 1)
    g = dgl.batch([g_1,g_3,g_2])

    batch_num_nodes = g.batch_num_nodes()
    dist_mat, paths = dgl.shortest_dist(g, return_paths = True)
    paths = get_path_info(g, paths, args.max_nodes, args.max_len, device )
    paths = unbatch_adj_tensor(paths, batch_num_nodes)
    g = attach_dist_and_path_info(g, dist_mat, paths)
    print("DONE")

                

    
    
if __name__ == '__main__':
    from argparse import ArgumentParser

    #from utils import init_featurizer, mkdir_p, split_dataset, get_configure

    parser = ArgumentParser('Moleculenet')
    parser.add_argument('-d', '--dataset', type = str, help='Dataset to use')
    parser.add_argument('--max_nodes', type=int, default=None, help='Max nodes per graph in dataset')
    parser.add_argument('--num_classes', type=int, default= None, help='Number of classes')  
    parser.add_argument('--splitter', type=str, default=None, help='Data splitting method. Choose from: [scaffold, random, consec ]') 
    parser.add_argument('--rand_state', type=float, default=None, help='random seed when using random splitting method for dataset')                    
    parser.add_argument('-bf', '--bond_featurizer', type = str, default=None, help='Featurization for bonds')
    parser.add_argument('--add_id', type=int, default= 0, help='Whether or not to add self loop to adjacency matrix ')
    parser.add_argument('--truncate_beta', type=int, default= 0, help='Whether or not to set beta=0')
    parser.add_argument('--epochs', type=int, default=1, help='Number of epochs to train.')

    parser.add_argument('-af', '--atom_featurizer', type=str, default = None, help='Featurization for atoms')
    parser.add_argument('--num-layers', type=int, default=None, help='Number of layers.')
    parser.add_argument('--tie_all_layers', type=int, default=0, help='Whether or not to tie all layers')
    parser.add_argument('--layer_ties', nargs='*', help='List specifying which layers to tie')
    parser.add_argument('--residual', type=int, default=None, help='Whether or not to use residual connections.')
    parser.add_argument('--norm_layer_type', type=str, default=None, help='Type of normalization to apply after each layer. Choose from: [layer_norm, batch_norm]')
    parser.add_argument('--hidden_dim', type=int, default= None, help='hidden layer(s) dimension')
    parser.add_argument('--num_heads', type=int, default= None, help='hidden layer(s) dimension')

    parser.add_argument('--ff_dim', type=int, default= None, help='power dimension')
    parser.add_argument('--params_init_type', type=str, default='he', help='Parameter initialization method. Choose from [he, normal, const]')
    parser.add_argument('--adj_factor', type=float_or_str, default=None, help='Related to initialization of the linear comb weight of the adjacency matric. Should be in range (0, 1)')        
    parser.add_argument('--dropout', type=float, default=None, help='dropout')
    parser.add_argument('--weight_drop', type=float, default=0, help='weight dropout')
    parser.add_argument('--weight_decay', type=float, default=None, help='weight decay')
    parser.add_argument('--batch-size', type=int, default=None, help='Batch size.')
    parser.add_argument('--lr', type=float, default=None, help='Learning rate.')

    parser.add_argument('-me', '--metric', choices=['roc_auc_score', 'pr_auc_score', 'r2', 'mae', 'rmse'], default=None, help='Metric for evaluation (default: roc_auc_score)')
    parser.add_argument('-nw', '--num-workers', type=int, default=0, help='Number of processes for data loading (default: 0)')    
    parser.add_argument('--opt', type=str, default= 'adam', help='Optimizer')   
    parser.add_argument('--early_stopping', type=int, default=0, help='Whether or not to use early stopping.')
    parser.add_argument('--early_patience', type=int, default=0, help='Number of epochs to wait before stopping training')
    parser.add_argument('--early_delta', type=float, default=0, help='Min value that difference between new metric and old metric must exceed to increment early stopping counter')     
    parser.add_argument('--edge_norm', type=str, default='both', help='edges weights normalization type')      
    parser.add_argument('--use_gpu', type=int, default= 1, help='whether or not to use gpu')
    parser.add_argument('--gpu', type=int, default=-1, help='GPU index.')        
    parser.add_argument('--max_len', type=int, default= None, help='power dimension + 1')
    parser.add_argument('--pooling', type=str, default= 'mean', help='pooling method to use')
    parser.add_argument('--dir_to_save_beta', type=str, default= '/ibex/scratch/ibraheao/t_hop/beta_plus_temp_safe', help='Directory to save beta and adj temporarily during program execution.')

    args = parser.parse_args()
        

    
    print("dgl version: ", dgl.__version__)
    print("dgllife version: ", dgllife.__version__)

    if args.atom_featurizer == 'canonical':
        node_featurizer=CanonicalAtomFeaturizer()
        edge_featurizer = CanonicalBondFeaturizer()
        smiles_to_g = SMILESToBigraph(add_self_loop=False, node_featurizer= node_featurizer,
                                  edge_featurizer=edge_featurizer)

    elif args.atom_featurizer == 'attentivefp':
        node_featurizer=AttentiveFPAtomFeaturizer()
        edge_featurizer = AttentiveFPBondFeaturizer()
        smiles_to_g = SMILESToBigraph(add_self_loop=False, node_featurizer= node_featurizer,
                                  edge_featurizer=edge_featurizer)


    if args.dataset == 'MUV':
        from dgllife.data import MUV
        dataset = MUV(smiles_to_graph=smiles_to_g,
                      n_jobs=1 if args.num_workers == 0 else args.num_workers)
         
    elif args.dataset == 'BACE':
        from dgllife.data import BACE
        dataset = BACE(smiles_to_graph=smiles_to_g,
                      n_jobs=1 if args.num_workers == 0 else args.num_workers)
        args.metric = 'roc_auc_score'
    elif args.dataset == 'BBBP':
        from dgllife.data import BBBP
        dataset = BBBP(smiles_to_graph=smiles_to_g,
                       n_jobs=1 if args.num_workers == 0 else args.num_workers)
        args.metric = 'roc_auc_score'
    elif args.dataset == 'ClinTox':
        from dgllife.data import ClinTox
        dataset = ClinTox(smiles_to_graph=smiles_to_g,
                          n_jobs=1 if args.num_workers == 0 else args.num_workers)
        args.metric = 'roc_auc_score'
    elif args.dataset == 'SIDER':
        from dgllife.data import SIDER
        dataset = SIDER(smiles_to_graph=smiles_to_g,
                        n_jobs=1 if args.num_workers == 0 else args.num_workers)
        args.metric = 'roc_auc_score'
    elif args.dataset == 'ToxCast':
        from dgllife.data import ToxCast
        dataset = ToxCast(smiles_to_graph=smiles_to_g,
                          n_jobs=1 if args.num_workers == 0 else args.num_workers)
        args.metric = 'roc_auc_score'
    elif args.dataset == 'HIV':
        from dgllife.data import HIV
        dataset = HIV(smiles_to_graph=smiles_to_g,
                      n_jobs=1 if args.num_workers == 0 else args.num_workers)
        args.metric = 'roc_auc_score'
    elif args.dataset == 'PCBA':
        from dgllife.data import PCBA
        dataset = PCBA(smiles_to_graph=smiles_to_g,
                       n_jobs=1 if args.num_workers == 0 else args.num_workers)
    elif args.dataset == 'Tox21':
        from dgllife.data import Tox21
        dataset = Tox21(smiles_to_graph=smiles_to_g,
                        n_jobs=1 if args.num_workers == 0 else args.num_workers)
        args.metric = 'roc_auc_score'
    elif args.dataset == 'FreeSolv':
        from dgllife.data import FreeSolv
        dataset = FreeSolv(smiles_to_graph=smiles_to_g,
                        n_jobs=1 if args.num_workers == 0 else args.num_workers)
        args.metric = 'rmse'

    elif args.dataset == 'ESOL':
        from dgllife.data import ESOL
        dataset = ESOL(smiles_to_graph=smiles_to_g,
                        n_jobs=1 if args.num_workers == 0 else args.num_workers)
        args.metric = 'rmse'

    elif args.dataset == 'Lipophilicity' :
        from dgllife.data import Lipophilicity 
        dataset = Lipophilicity(smiles_to_graph=smiles_to_g,
                        n_jobs=1 if args.num_workers == 0 else args.num_workers)
        args.metric = 'rmse'
    else:
        raise ValueError('Unexpected dataset: {}'.format(args['dataset']))



    args.n_tasks = dataset.n_tasks
    args.num_classes = args.n_tasks
    args.max_nodes, _ = max_nodes_and_edges(dataset)
    args.max_len =  max_path_len(dataset )
    
    print(args)
      
    main()