import os
import shutil
import argparse
import math
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
from dgllife.utils import EarlyStopping, smiles_to_bigraph, CanonicalAtomFeaturizer, AttentiveFPAtomFeaturizer, ConsecutiveSplitter, ScaffoldSplitter, RandomSplitter
from dgllife.utils import Meter, SMILESToBigraph

from t_hop_lin_comb_model import t_hop_model
from utils import dataset_from_index, max_nodes_and_edges, early_stopping, beta_mat_3d_from_dgl_graph, split_mat_3d, pad_mat_3d, split_mat_2d, pad_mat_2d, split_pad_and_stack_beta, split_pad_and_stack_adj, split_pad_and_stack_feat
from utils import aws_collate_and_beta as collate_molgraphs
from utils import add_noise_to_node, node_mean_and_std





def float_or_str(value):
    try:
        return float(value)
    except:
        return value


def get_feat_dim(data_loader):
    for i, batch in enumerate(data_loader):
        smiles, dgl_graph, labels, masks, adj, beta = batch
        feats = dgl_graph.ndata['h']
        inp_dim = feats.shape[-1]
        return inp_dim          



   
def get_beta_max(beta_list):
    len_beta = len(beta_list)
    max_val = 0
    for i in range(len_beta):
        val = np.amax(beta_list[i])
        if val > max_val:
            max_val = val
    return max_val




def train(data_loader, num_batches, device, max_nodes, pow_dim, max_len, norm_style, model, loss_function, optimizer, residual):
    
    loss_list = []
    model.train()
    train_meter = Meter()
    cum_loss = 0.
    num_graphs = 0
    for i, batch in enumerate(data_loader):
 
        smiles, dgl_graph, labels, masks, adj, beta = batch  

        if args.add_noise:
            dgl_graph = add_noise_to_node(dgl_graph, num_batches * args.run_index +  i, args.node_std) 

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
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
       
        train_meter.update(out, labels, masks)
    train_score = np.mean(train_meter.compute_metric(args.metric))
    return loss, train_score


@torch.no_grad()
def test(data_loader, num_batches, device, max_nodes, pow_dim, max_len, norm_style, model, loss_function, optimizer, residual):
    
    loss_list = []
    model.eval()
    train_meter = Meter()
    cum_loss = 0.
    num_graphs = 0
    for i, batch in enumerate(data_loader):
 
        smiles, dgl_graph, labels, masks, adj, beta = batch 
        if args.add_noise:
            dgl_graph = add_noise_to_node(dgl_graph,  num_batches * args.run_index +  i, args.node_std) 
 
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


 
 
def main():

    device = torch.device("cuda" if args.use_gpu == 1 and torch.cuda.is_available() else 'cpu')  

    ##  If required, add noise to features.
    if args.add_noise:
        args.node_mean, args.node_std = node_mean_and_std(dataset, DataLoader, collate_molgraphs, args.num_workers)
        args.node_std = args.node_std*args.noise_factor


    ## Get data splitter and split data.
    if args.splitter == 'consec':
        splitter = ConsecutiveSplitter()
        split = splitter.train_val_test_split(dataset)
    elif args.splitter == 'random':
        splitter = RandomSplitter()
        split = splitter.train_val_test_split(dataset, random_state = args.rand_state)
    elif args.splitter == 'scaffold':
        splitter = ScaffoldSplitter()
        split = splitter.train_val_test_split(dataset,  scaffold_func='smiles')
   
   
    train_loader = DataLoader(split[0],  batch_size=args.batch_size, shuffle=True,  collate_fn= partial(collate_molgraphs, pow_dim=args.pow_dim,  max_nodes=args.max_nodes, add_identity =args.add_id, truncate_beta =args.truncate_beta))    
    val_loader = DataLoader(split[1], batch_size=args.batch_size, shuffle=False, collate_fn=partial(collate_molgraphs, pow_dim=args.pow_dim,  max_nodes=args.max_nodes, add_identity =args.add_id, truncate_beta =args.truncate_beta))
    test_loader = DataLoader(split[2],batch_size=args.batch_size, shuffle=False, collate_fn=partial(collate_molgraphs, pow_dim=args.pow_dim,  max_nodes=args.max_nodes, add_identity =args.add_id, truncate_beta =args.truncate_beta))

    
    num_train_batches = math.ceil(len(split[0])/args.batch_size)
    num_val_batches = math.ceil(len(split[1])/args.batch_size)
    num_test_batches = math.ceil(len(split[2])/args.batch_size)

    # load model
    inp_dim = get_feat_dim(train_loader) 
    model = t_hop_model( args.max_nodes, args.pow_dim, args.num_layers,  args.tie_all_layers, args.layer_ties, inp_dim, args.hidden_dim, args.num_classes, args.dropout, args.weight_drop, args.params_init_type, args.adj_factor, args.norm_layer_type)    
    model = model.to(device = device)
    model_name =  'model' + '_dat_' + args.dataset + '_path_' + str(args.use_path_info) +  '_add_nose_' + str(args.add_noise) + '_nose_' + str(args.noise_factor) + '_rep_' + str(args.run_index) +  '.pth'
    stopper = EarlyStopping(patience= args.early_patience, filename=os.path.join(args.dir_to_save_model, model_name), metric=args.metric)

  
    if (args.opt).lower() == 'adam':
        opt = optim.Adam(model.parameters(), lr=args.lr, weight_decay = args.weight_decay)
    elif (args.opt).lower() == 'sgd':
        opt = optim.SGD(model.parameters(), lr=args.lr, weight_decay = args.weight_decay)

    if args.metric in [ 'r2', 'mae', 'rmse']:
        loss_fn = nn.SmoothL1Loss(reduction='none')       
    elif args.metric in ['roc_auc_score', 'pr_auc_score'] :
        loss_fn = nn.BCEWithLogitsLoss(reduction='none')

## Train and evaluate:    
    for epoch in range(args.epochs):                               
        train_loss, train_score = train(train_loader, num_train_batches, device, args.max_nodes, args.pow_dim,  args.max_len, args.edge_norm,  model, loss_fn, opt, args.residual)         
        val_loss, val_score =   test(val_loader, num_val_batches, device, args.max_nodes, args.pow_dim,  args.max_len, args.edge_norm,  model, loss_fn, opt, args.residual) 
        
        early_stop = stopper.step(val_score, model)       
        if early_stop:
            break 

    stopper.load_checkpoint(model)
    val_loss, val_score =   test(val_loader, num_val_batches, device, args.max_nodes, args.pow_dim,  args.max_len, args.edge_norm,  model, loss_fn, opt, args.residual) 
    test_loss, test_score = test(test_loader, num_val_batches, device, args.max_nodes, args.pow_dim,  args.max_len, args.edge_norm,  model, loss_fn, opt, args.residual) 
 
    return val_score, test_score

if __name__ == '__main__':
    from argparse import ArgumentParser

   

    parser = ArgumentParser('Moleculenet')
    parser.add_argument('-d', '--dataset', choices = ['FreeSolv', 'ESOL', 'Lipophilicity', 'BACE', 'BBBP', 'ClinTox'], help='Dataset to use.')
    parser.add_argument('--max_nodes', type=int, default=None, help='Max nodes per graph in dataset')  
    parser.add_argument('--splitter', type=str, default='scaffold', help='Data splitting method. Choose from: [scaffold, random, consec ]') 
    parser.add_argument('--rand_state', type=float, default=None, help='random seed when using random splitting method for dataset')                    
    parser.add_argument('--add_id', type=int, default= 0, help='Whether or not to add self loop to adjacency matrix ')
    parser.add_argument('--use_path_info', type=int, default= 1, help='Whether or not to use path info')    
    parser.add_argument('--add_noise', type=int, default=None, help='Whether or not to add noise to features.')
    parser.add_argument('--noise_factor', type=float, default=-1, help='Level of noise to add.')
    parser.add_argument('--epochs', type=int, default=1, help='Number of epochs to train.')
    parser.add_argument('--repitition', type=int, default=1, help='Number of times to repeat experiment.')
    parser.add_argument('-af', '--atom_featurizer', type=str, default = 'canonical', help='Featurization for atoms')
    parser.add_argument('--num-layers', type=int, default=None, help='Number of layers.')
    parser.add_argument('--tie_all_layers', type=int, default=0, help='Whether or not to tie all layers')
    parser.add_argument('--layer_ties', nargs='*', help='List specifying which layers to tie')
    parser.add_argument('--residual', type=int, default=1, help='Whether or not to use residual connections.')
    parser.add_argument('--norm_layer_type', type=str, default='layer_norm', help='Type of normalization to apply after each layer. Choose from: [layer_norm, batch_norm]')
    parser.add_argument('--hidden_dim', type=int, default= None, help='hidden layer(s) dimension')
    parser.add_argument('--pow_dim', type=int, default= None, help='power dimension')
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
    parser.add_argument('--early_patience', type=int, default=10, help='Number of epochs to wait before stopping training early')
    parser.add_argument('--edge_norm', type=str, default='both', help='edges weights normalization type')      
    parser.add_argument('--use_gpu', type=int, default= 1, help='whether or not to use gpu')       
    parser.add_argument('--max_len', type=int, default= None, help='power dimension + 1')
    parser.add_argument('--pooling', type=str, default= 'mean', help='pooling method to use')
    parser.add_argument('--dir_to_save_model', type=str, default= '/ibex/user/ibraheao/path_project/t_hop/model_directory', help='power dimension + 1')
    args = parser.parse_args()
    args.max_len = args.pow_dim + 1


    
## Get featurizer and load dataset:

    if args.atom_featurizer == 'canonical':
        node_featurizer=CanonicalAtomFeaturizer()
        edge_featurizer = None
        smiles_to_g = SMILESToBigraph(add_self_loop=False, node_featurizer= node_featurizer,
                                  edge_featurizer=edge_featurizer)

    elif args.atom_featurizer == 'attentivefp':
        node_featurizer=AttentiveFPAtomFeaturizer()
        edge_featurizer = None
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


    

    if args.use_path_info == 0:
        args.truncate_beta = 1
    elif args.use_path_info == 1:
        args.truncate_beta = 0 


    args.n_tasks = dataset.n_tasks
    args.num_classes = args.n_tasks
    args.max_nodes, _ = max_nodes_and_edges(dataset)
    print(args)
      
    args.val_scores = []
    args.test_scores = [] 
    for i in range(0, args.repitition):
        args.run_index = i
        val_score, test_score = main()
        args.val_scores.append(val_score)
        args.test_scores.append(test_score)
    
     
    args.val_mean = np.mean(np.asarray(args.val_scores))
    args.val_std = np.std(np.asarray(args.val_scores))
    print('Final validation average {} {:2.3f} | Final validation std {:5.5f}  '.format(  args.metric, args.val_mean, args.val_std,), flush=True)

    args.test_mean = np.mean(np.asarray(args.test_scores))
    args.test_std = np.std(np.asarray(args.test_scores))
    print('Final test average {} {:2.3f} | Final test std {:5.5f}  '.format(  args.metric, args.test_mean, args.test_std,), flush=True)
    print('\n')
