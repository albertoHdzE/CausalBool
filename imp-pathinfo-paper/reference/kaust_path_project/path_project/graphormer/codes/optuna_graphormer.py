
import optuna
from optuna.trial import TrialState
from optuna.samplers import TPESampler 

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
from dgllife.utils import EarlyStopping, smiles_to_bigraph, CanonicalAtomFeaturizer, AttentiveFPAtomFeaturizer, CanonicalBondFeaturizer, AttentiveFPBondFeaturizer, ConsecutiveSplitter, ScaffoldSplitter, RandomSplitter
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



from utils import max_nodes_and_edges, max_path_len, early_stopping, beta_mat_3d_from_dgl_graph, split_mat_3d, pad_mat_3d, split_mat_2d, pad_mat_2d, split_pad_and_stack_beta, split_pad_and_stack_adj, split_pad_and_stack_feat
from utils import aws_collate_molgraphs as collate_molgraphs





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
        edge_dim = dgl_graph.edata['e'].shape[-1]
        return inp_dim, edge_dim          




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


def get_max_path_len(data_loader):
    max_path_len = 0
    for i, batch in enumerate(data_loader):
        smiles, dgl_graph, labels, masks = batch
        dist_mat, path = dgl.shortest_dist(dgl_graph, return_paths=True)
        
        if path.shape[2] > max_path_len:
            max_path_len = path.shape[2]
 
    return max_path_len  


def train_0(data_loader, device, max_nodes, pow_dim, max_len, norm_style, model, loss_function, optimizer, residual):
    
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


def test_feats(data_loader, device, model, max_nodes, max_path_len):
    
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
        out = model(feats, dgl_graph, max_nodes, max_path_len)
        print("out.shape: ", out.shape)
    return feats


def train(data_loader, device, max_nodes, max_path_len, model, loss_function, optimizer):
    
    loss_list = []
    model.train()
    train_meter = Meter()
    cum_loss = 0.
    num_graphs = 0
    for i, batch in enumerate(data_loader):
 
        smiles, dgl_graph, labels, masks = batch 

        try:
            edge_feats = dgl_graph.edata['e']
        except KeyError:     
            continue

         
        labels, masks = labels.to(device), masks.to(device)

        numb_nodes = dgl_graph.num_nodes()
        batch_num_nodes = dgl_graph.batch_num_nodes()
        feats = dgl_graph.ndata['h']
        feats = feats.numpy()
        feats = split_pad_and_stack_feat(feats, batch_num_nodes, max_nodes)
        feats = torch.from_numpy(feats)
        feats = feats.to(torch.float32).to(device)
        out = model(feats, dgl_graph, max_nodes, max_path_len)
           
        loss = (loss_function(out, labels) * (masks != 0).float()).mean() 
        
          
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
       
        train_meter.update(out, labels, masks)
    train_score = np.mean(train_meter.compute_metric(args.metric))
    return loss, train_score




@torch.no_grad()
def test(data_loader, device, max_nodes, max_path_len, model, loss_function):
    
    loss_list = []
    model.eval()
    train_meter = Meter()
    cum_loss = 0.
    num_graphs = 0
    for i, batch in enumerate(data_loader):
 
        smiles, dgl_graph, labels, masks = batch 

        try:
            edge_feats = dgl_graph.edata['e']
        except KeyError:     
            continue

         
        labels, masks = labels.to(device), masks.to(device)

        numb_nodes = dgl_graph.num_nodes()
        batch_num_nodes = dgl_graph.batch_num_nodes()
        feats = dgl_graph.ndata['h']
        feats = feats.numpy()
        feats = split_pad_and_stack_feat(feats, batch_num_nodes, max_nodes)
        feats = torch.from_numpy(feats)
        feats = feats.to(torch.float32).to(device)
        out = model(feats, dgl_graph, max_nodes, max_path_len)
           
        loss = (loss_function(out, labels) * (masks != 0).float()).mean() 
               
        train_meter.update(out, labels, masks)
    train_score = np.mean(train_meter.compute_metric(args.metric))
    return loss, train_score



def define_model(trial):
    model = graphormer_model(args.use_path_info, args.num_layers, args.inp_dim, args.edge_dim, args.hidden_dim, args.num_heads, args.ff_dim, args.num_classes, args.max_len, args.dropout)
    model = model.to(device = device)
    return model





def objective(trial):

    
    args.num_layers = trial.suggest_int("num_layers", 1, args.max_layers)
   
    args.small_hidden_dim = trial.suggest_int("small_hidden_dim", 1, args.max_small_hidden_dim)
    args.num_heads =  trial.suggest_int("num_heads", 1, args.max_num_heads)
    args.hidden_dim = args.num_heads*args.small_hidden_dim
    args.dropout = trial.suggest_float("dropout", 0, 1)
    args.ff_dim = args.hidden_dim
    args.weight_decay = trial.suggest_float("weight_decay", 1e-20, 1, log=True )

    args.batch_size = trial.suggest_int("batch_size", 2, args.max_batch_size)

    args.lr = trial.suggest_float("lr",  1e-5, 1, log=True )

    train_loader = DataLoader(dataset=args.train_set, shuffle=True, batch_size=args.batch_size, collate_fn=collate_molgraphs, num_workers=args.num_workers)
    val_loader = DataLoader(dataset=args.val_set, shuffle = False, batch_size=args.batch_size, collate_fn=collate_molgraphs, num_workers=args.num_workers)
    test_loader = DataLoader(dataset=args.test_set, shuffle = False, batch_size=args.batch_size, collate_fn=collate_molgraphs, num_workers=args.num_workers)
    

     
    args.inp_dim, args.edge_dim = get_feat_dim(train_loader) 

    model = define_model(trial)

    if args.metric in [ 'r2', 'mae', 'rmse']:
        loss_fn = nn.SmoothL1Loss(reduction='none')       
    elif args.metric in ['roc_auc_score', 'pr_auc_score'] :
        loss_fn = nn.BCEWithLogitsLoss(reduction='none')

    if (args.opt).lower() == 'adam':
        opt = optim.Adam(model.parameters(), lr=args.lr, weight_decay = args.weight_decay)
    elif (args.opt).lower() == 'sgd':
        opt = optim.SGD(model.parameters(), lr=args.lr, weight_decay = args.weight_decay)


    
    val_list = []
    t1 = time.time()

    for epoch in range(0, args.epochs): 
                                 
        train_loss, train_score = train(train_loader, device, args.max_nodes, args.max_len, model, loss_fn, opt) 
        val_loss, val_score =   test(val_loader, device, args.max_nodes, args.max_len, model, loss_fn)
        val_list.append(val_score)

    t2 = time.time()
    elap_mins = (t2 - t1)/60
    print("Time taken by Optuna for one trial on {} dataset is {:6.2f} minutes".format(args.dataset, elap_mins))
 
    if args.val_method.lower() == 'order':
        val_area = val_list[-(args.val_window): ]
        val_out = min(val_area)
    elif args.val_method.lower() == 'mean':   
        val_area = val_list[-(args.val_window): ]
        val_out = np.mean(val_area)
    else:
        raise Exception("Unsupported validation method. Supported values are: mean and min.")

    return val_out





 
def main():
     

    
    if args.splitter == 'consec':
        splitter = ConsecutiveSplitter()
        split = splitter.train_val_test_split(dataset)
    elif args.splitter == 'random':
        splitter = RandomSplitter()
        split = splitter.train_val_test_split(dataset, random_state = args.rand_state)
    elif args.splitter == 'scaffold':
        splitter = ScaffoldSplitter()
        split = splitter.train_val_test_split(dataset,  scaffold_func='smiles')
    
    args.train_set = split[0]
    args.val_set = split[1]
    args.test_set = split[2]
   
    


    if args.sampler == 'tpe':
        sampler= optuna.samplers.TPESampler(seed=42)
    elif args.sampler == 'cma':
        sampler = optuna.samplers.CmaEsSampler(seed=42)
    elif args.sampler == 'nsga3':
        sampler = optuna.samplers.NSGAIISampler(seed=42)
    
    if args.dataset in args.regression_datasets:
        study = optuna.create_study(sampler=sampler, direction="minimize")
    else:
        study = optuna.create_study(sampler=sampler, direction="maximize")

    study.optimize(objective, n_trials= args.num_trials)
        

    pruned_trials = study.get_trials(deepcopy=False, states=[TrialState.PRUNED])
    complete_trials = study.get_trials(deepcopy=False, states=[TrialState.COMPLETE])

    print("Study statistics: ")
    print("  Number of finished trials: ", len(study.trials))
    print("  Number of pruned trials: ", len(pruned_trials))
    print("  Number of complete trials: ", len(complete_trials))

    print("Best trial:")
    trial = study.best_trial

    print("  Value: ", trial.value)

    print("  Params: ")
    for key, value in trial.params.items():
        print("    {}: {}".format(key, value))









    

    

        
if __name__ == '__main__':
    from argparse import ArgumentParser

    #from utils import init_featurizer, mkdir_p, split_dataset, get_configure

    parser = ArgumentParser('Moleculenet')
    parser.add_argument('-d', '--dataset', type = str, help='Dataset to use')
    parser.add_argument('--use_path_info', type=int, default=None, help='Max nodes per graph in dataset')
    parser.add_argument('--max_nodes', type=int, default=None, help='Max nodes per graph in dataset')
    parser.add_argument('--num_classes', type=int, default= None, help='Number of classes')  
    parser.add_argument('--splitter', type=str, default=None, help='Data splitting method. Choose from: [scaffold, random, consec ]') 
    parser.add_argument('--rand_state', type=float, default=None, help='random seed when using random splitting method for dataset')  
    parser.add_argument('-af', '--atom_featurizer', type=str, default = None, help='Featurization for atoms')              
    #parser.add_argument('-bf', '--bond_featurizer', type = str, default=None, help='Featurization for bonds')
    parser.add_argument('--epochs', type=int, default=1, help='Number of epochs to train.')
    parser.add_argument('--max_layers', type=int, default=None, help='Number of layers.')
    parser.add_argument('--max_small_hidden_dim', type=int, default= None, help='hidden layer(s) dimension')
    parser.add_argument('--max_num_heads', type=int, default= None, help='hidden layer(s) dimension')
    parser.add_argument('--ff_dim', type=int, default= None, help='power dimension')
    parser.add_argument('--dropout', type=float, default=None, help='dropout')
    parser.add_argument('--weight_decay', type=float, default=None, help='weight decay')
    parser.add_argument('--max_batch_size', type=int, default=None, help='Batch size.')
    parser.add_argument('--lr', type=float, default=None, help='Learning rate.')

    parser.add_argument('-me', '--metric', choices=['roc_auc_score', 'pr_auc_score', 'r2', 'mae', 'rmse'], default=None, help='Metric for evaluation (default: roc_auc_score)')
    parser.add_argument('-nw', '--num-workers', type=int, default=0, help='Number of processes for data loading (default: 0)')    
    parser.add_argument('--opt', type=str, default= 'adam', help='Optimizer')   
    parser.add_argument('--early_stopping', type=int, default=0, help='Whether or not to use early stopping.')
    parser.add_argument('--early_patience', type=int, default=0, help='Number of epochs to wait before stopping training')
    parser.add_argument('--early_delta', type=float, default=0, help='Min value that difference between new metric and old metric must exceed to increment early stopping counter')     
    parser.add_argument('--edge_norm', type=str, default='both', help='edges weights normalization type')      
    parser.add_argument('--use_gpu', type=int, default= None, help='transductive or inductive setting?')
    parser.add_argument('--max_len', type=int, default= None, help='power dimension + 1')
    parser.add_argument('--sampler', type=str, default= 'tpe', help='power dimension + 1')
    parser.add_argument('--num_trials', type=int, default= None, help='power dimension + 1')
    parser.add_argument('--val_method', type=str, default= 'mean', help='power dimension + 1')
    parser.add_argument('--val_window', type=int, default= None, help='power dimension + 1')

    
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
    args.regression_datasets = ['FreeSolv', 'Lipophilicity', 'ESOL']

    print(args)
    device = torch.device("cuda" if args.use_gpu == 1 and torch.cuda.is_available() else 'cpu')   
    main()