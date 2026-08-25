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
from dgllife.utils import EarlyStopping, smiles_to_bigraph, CanonicalAtomFeaturizer, AttentiveFPAtomFeaturizer, CanonicalBondFeaturizer, AttentiveFPBondFeaturizer, ConsecutiveSplitter, ScaffoldSplitter, RandomSplitter
from dgllife.utils import Meter, SMILESToBigraph

from deeper_gcn_model import deeper_gcn_model


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
#print("UTILS_PATH: ", utils_path)
sys.path.insert(1, utils_path)



from utils import normalize_adj, max_nodes_and_edges, max_path_len, early_stopping, beta_mat_3d_from_dgl_graph, split_mat_3d, pad_mat_3d, split_mat_2d, pad_mat_2d, split_pad_and_stack_beta, split_pad_and_stack_adj, split_pad_and_stack_feat
from utils import aws_collate_molgraphs as collate_molgraphs
from utils import add_noise_to_node_and_edge, node_and_edge_mean_and_std



def get_feat_dim(data_loader):
    for i, batch in enumerate(data_loader):
        smiles, dgl_graph, labels, masks = batch
        feats = dgl_graph.ndata['h']
        inp_dim = feats.shape[-1]
        edge_dim = dgl_graph.edata['e'].shape[-1]
        return inp_dim, edge_dim          





def train(data_loader, num_batches, device, model, loss_function, optimizer):
    
    loss_list = []
    model.train()
    train_meter = Meter()
    cum_loss = 0.
    num_graphs = 0
    for i, batch in enumerate(data_loader):
 
        smiles, dgl_graph, labels, masks = batch 

        
        try:
            edge_feats = dgl_graph.edata['e']
            if args.add_noise:
                dgl_graph = add_noise_to_node_and_edge(dgl_graph, num_batches * args.run_index +  i, args.node_std, args.edge_std)
        except KeyError:    
            continue

        batch_num_nodes = dgl_graph.batch_num_nodes()
        if 1 in batch_num_nodes:
            #print("continue")
            continue

        #print("Graph is Okay") 
        labels, masks, dgl_graph = labels.to(device), masks.to(device), dgl_graph.to(device)  
        #out = model(dgl_graph)
        out = model(dgl_graph,device, args.max_nodes, args.max_len) 
        if out == None:
            continue 
        loss = (loss_function(out, labels) * (masks != 0).float()).mean() 
        
          
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
       
        train_meter.update(out, labels, masks)
    train_score = np.mean(train_meter.compute_metric(args.metric))
    return loss, train_score




@torch.no_grad()
def test(data_loader, num_batches, device, model, loss_function):
    
    loss_list = []
    model.eval()
    train_meter = Meter()
    cum_loss = 0.
    num_graphs = 0
    for i, batch in enumerate(data_loader):
 
        smiles, dgl_graph, labels, masks = batch

        try:
            edge_feats = dgl_graph.edata['e']
            if args.add_noise:
                dgl_graph = add_noise_to_node_and_edge(dgl_graph, num_batches * args.run_index +  i, args.node_std, args.edge_std)
        except KeyError:    
            continue 

        batch_num_nodes = dgl_graph.batch_num_nodes()
        if 1 in batch_num_nodes:
            #print("continue")
            continue
         
        #print("Graph is Okay")
        labels, masks, dgl_graph = labels.to(device), masks.to(device), dgl_graph.to(device)    
        out = model(dgl_graph,device, args.max_nodes, args.max_len) 
        if out == None:
            continue        
        loss = (loss_function(out, labels) * (masks != 0).float()).mean() 
               
        train_meter.update(out, labels, masks)
    train_score = np.mean(train_meter.compute_metric(args.metric))
    return loss, train_score

 
 
def main():

    device = torch.device("cuda" if args.use_gpu == 1 and torch.cuda.is_available() else 'cpu')  

    ## If required, add noise to features
    if args.add_noise:
        args.node_mean, args.node_std, args.edge_mean, args.edge_std = node_and_edge_mean_and_std(dataset, DataLoader, collate_molgraphs, args.num_workers)
        args.node_std = args.node_std*args.noise_factor
        args.edge_std = args.edge_std*args.noise_factor


    ## Get data splitter and split data
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

    num_train_batches = math.ceil(len(split[0])/args.batch_size)
    num_val_batches = math.ceil(len(split[1])/args.batch_size)
    num_test_batches = math.ceil(len(split[2])/args.batch_size)


    # load model
    inp_dim, edge_dim = get_feat_dim(train_loader)   
    model = deeper_gcn_model(args.use_path_info, args.num_layers, inp_dim, edge_dim, args.hidden_dim, args.num_classes, args.dropout,  args.max_len, pooling='mean')
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


##  Train and evaluate:    
    for epoch in range(args.epochs):        
        train_loss, train_score = train(train_loader, num_train_batches, device, model, loss_fn, opt) 
        val_loss, val_score =   test(val_loader, num_val_batches, device, model, loss_fn)
        early_stop = stopper.step(val_score, model)
        if early_stop:
            break 

    stopper.load_checkpoint(model)
    val_loss, val_score =   test(val_loader, num_val_batches, device,  model, loss_fn)
    test_loss, test_score = test(test_loader, num_test_batches, device, model, loss_fn) 
    return val_score, test_score


    
if __name__ == '__main__':
    from argparse import ArgumentParser

    #from utils import init_featurizer, mkdir_p, split_dataset, get_configure

    parser = ArgumentParser('Moleculenet')
    parser.add_argument('-d', '--dataset', choices = ['FreeSolv', 'ESOL', 'Lipophilicity', 'BACE', 'BBBP', 'ClinTox'], help='Dataset to use.')
    parser.add_argument('--use_path_info', type=int, default=None, help='Whether or not to use path info.')
    parser.add_argument('--add_noise', type=int, default=None, help='Whether or not to add noise to features.')
    parser.add_argument('--noise_factor', type=float, default=-1, help='Level of noise to add to features.')

    parser.add_argument('--repitition', type=int, default=1, help='Number of times to repeat experiment.')
    parser.add_argument('--num_classes', type=int, default= None, help='Number of classes')  
    parser.add_argument('--splitter', type=str, default='scaffold', help='Data splitting method. Choose from: [scaffold, random, consec ]') 
    parser.add_argument('--rand_state', type=float, default=None, help='random seed when using random splitting method for dataset')  
    parser.add_argument('-af', '--atom_featurizer', type=str, default = 'canonical', help='Featurization for atoms')              
    #parser.add_argument('-bf', '--bond_featurizer', type = str, default='canonical', help='Featurization for bonds')
    parser.add_argument('--epochs', type=int, default=1, help='Number of epochs to train.')
    parser.add_argument('--num-layers', type=int, default=None, help='Number of layers.')
    parser.add_argument('--hidden_dim', type=int, default= None, help='hidden layer(s) dimension')
    parser.add_argument('--dropout', type=float, default=None, help='dropout')
    parser.add_argument('--weight_decay', type=float, default=None, help='weight decay')
    parser.add_argument('--batch-size', type=int, default=None, help='Batch size.')
    parser.add_argument('--lr', type=float, default=None, help='Learning rate.')

    parser.add_argument('-me', '--metric', choices=['roc_auc_score', 'pr_auc_score', 'r2', 'mae', 'rmse'], default=None, help='Metric for evaluation (default: roc_auc_score)')
    parser.add_argument('-nw', '--num-workers', type=int, default=0, help='Number of processes for data loading (default: 0)')    
    parser.add_argument('--opt', type=str, default= 'adam', help='Optimizer')   
    parser.add_argument('--early_patience', type=int, default=10, help='Number of epochs to wait before early-stopping training')
    parser.add_argument('--use_gpu', type=int, default= None, help='Whether or not to use GPU')
    parser.add_argument('--dir_to_save_model', type=str, default= '/ibex/user/ibraheao/path_project/deeper_gcn/model_directory', help='power dimension + 1')
    
   
    
    args = parser.parse_args()
        

    
## Get featurizer and load dataset
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
