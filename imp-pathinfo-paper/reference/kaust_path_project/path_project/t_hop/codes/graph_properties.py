

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
from dgllife.utils import smiles_to_bigraph, CanonicalAtomFeaturizer, AttentiveFPAtomFeaturizer, ConsecutiveSplitter, ScaffoldSplitter, RandomSplitter
from dgllife.utils import Meter, SMILESToBigraph

from t_hop_lin_comb_model import t_hop_model
from utils import dataset_from_index, max_nodes_and_edges, early_stopping, beta_mat_3d_from_dgl_graph, split_mat_3d, pad_mat_3d, split_mat_2d, pad_mat_2d, split_pad_and_stack_beta, split_pad_and_stack_adj, split_pad_and_stack_feat
from utils import aws_collate_and_beta as collate_molgraphs

import networkx as nx





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



def mean_of_dict(dict):
    len_dict = len(dict)
    if len_dict == 0:
        return None, None
    
    total = 0
    for key in dict:
        val = dict[key]
        total = total + val
 
    mean = total/len_dict
    
    total_dev = 0
    for key in dict:
        total_dev = total_dev + (dict[key] - mean)*(dict[key] - mean)
    std = math.sqrt(total_dev/ len_dict )  
    return mean, std 


def train_time(data_loader):
    list_degrees = []
    list_degrees_std = []
    list_diameter = []
    list_clique = []
    list_density = []
    list_modularity = []
    list_clustering = []
    list_clustering_std = []  
    list_path_lens = []
    list_closeness_centrality = []
    list_betweenness_centrality = []
    list_edge_betweenness_centrality = []
    list_eigenvector_centrality = []
    list_closeness_centrality_std = []
    list_betweenness_centrality_std = []
    list_edge_betweenness_centrality_std = []
    list_eigenvector_centrality_std = []
    list_lap_1 = []
    list_lap_1_std = []
    list_lap_2 = []
    list_lap_2_std = []
    list_lap_3 = []
    list_lap_3_std = []
    list_lap_4 = []
    list_lap_4_std = []

    
    list_props = []
    t1 = time.time()
    for i, batch in enumerate(data_loader):
 
        smiles, g, labels, masks, adj, beta = batch 
        g = dgl.to_networkx(g)
        g.nodes(data=True)
        g = nx.Graph(g)
        
        if 'degree' in args.properties:
            degrees = [val for (node, val) in g.degree()]
            mu = np.mean(np.array(degrees))
            std = np.std(np.array(degrees))
            list_degrees.append(mu)
            list_degrees_std.append(std)

        if 'clique' in args.properties:
            #print("CLIQUE: ", nx.max_weight_clique(g, weight=None))
            _, clique = nx.max_weight_clique(g, weight=None)
            list_clique.append(clique)   
        if 'diameter' in args.properties:
            try:
                list_diameter.append( nx.diameter(g) )
            except nx.NetworkXError:
                print("Disconnected graph encountered and ignored.")

        if 'density' in args.properties:
            list_density.append( nx.density(g) )

        
        if 'modularity' in args.properties:

            import community as community_louvain

            try:
                partition = community_louvain.best_partition(g)
                list_modularity.append( community_louvain.modularity(partition, g) )
            except ValueError:
                print("Graph with no link found and ignored.")

                        

        if 'average_shortest_path' in args.properties:
            
            try: 
                list_path_lens.append( nx.average_shortest_path_length(g) )
                
            except nx.NetworkXError:
                print("Disconnected graph encountered and ignored.")
    
        if 'closeness_centrality' in args.properties:
            mu, std = mean_of_dict( nx.closeness_centrality(g) )
            if mu !=None:
                list_closeness_centrality.append( mu )
                list_closeness_centrality_std.append( std )

        #if 'closeness_centrality' in args.properties:
        #    print(nx.closeness_centrality(g))
        
        if 'betweenness_centrality' in args.properties:
            #print("BETWEENNESS CENTRALITY: ", nx.betweenness_centrality(g))
            mu, std = mean_of_dict( nx.betweenness_centrality(g) )
            if mu !=None:
                list_betweenness_centrality.append( mu )
                list_betweenness_centrality_std.append( std )

        if 'average_betweenness_centrality' in args.properties:
            print("AVERAGE BETWEENNESS CENTRALITY: ", nx.average_betweenness_centrality(g))


        if 'edge_betweenness_centrality' in args.properties:
            #print("EDGE BETWEENNESS CENTRALITY: ", nx.edge_betweenness_centrality(g))
            mu, std = mean_of_dict( nx.edge_betweenness_centrality(g) )
            if mu !=None:
                list_edge_betweenness_centrality.append( mu )
                list_edge_betweenness_centrality_std.append( std )


        if 'clustering' in args.properties:
            #print("CLUSTERING :", nx.clustering(g))
            mu, std = mean_of_dict( nx.clustering(g) )
            if mu !=None:
                list_clustering.append( mu )
                list_clustering_std.append( std )



        #if 'average_clustering' in args.properties:
        #    print("AVERAGE CLUSTERING :", nx.average_clustering(g))
       
        if 'eigenvector_centrality' in args.properties:
            #list_eigenvector_centrality.append( mean_of_dict( nx.eigenvector_centrality(g, tol = 10e-4, max_iter = 200) ) )
            mu, std = mean_of_dict( nx.eigenvector_centrality(g, tol=10e-4) )
            if mu !=None:
                list_eigenvector_centrality.append( mu )
                list_eigenvector_centrality_std.append( std )

        if 'laplacian' in args.properties:
            eigs = nx.laplacian_spectrum(g)
            if eigs.shape[0] >= 4:
                #print("B4 sorting: ", eigs)
                eigs = np.sort(eigs, axis = 0)
                #print("AFTER sorting: ", eigs)
                list_lap_1.append(eigs[0]) 
                list_lap_2.append(eigs[1])
                list_lap_3.append(eigs[-2])
                list_lap_4.append(eigs[-1])

        #print(nx.betweenness_centrality(nx_g))

    if 'degree' in args.properties:
        a = np.mean(np.array(list_degrees))
        b = np.std(np.array(list_degrees))
        c = np.mean(np.array(list_degrees_std))
        print("NODE DEGREE: ", a, b, c )
        list_props.append(a)
        list_props.append(b)
        list_props.append(c)
    if 'clique' in args.properties:
        a = np.mean(np.array(list_clique))
        b = np.std(np.array(list_clique)) 
        print("CLIQUE: ", a,  b )
        list_props.append(a)
        list_props.append(b)
        
    if 'diameter' in args.properties:
        a = np.mean(np.array(list_diameter))
        b = np.std(np.array(list_diameter))
        print("AVERAGE DIAMETER: ", a,  b )
        list_props.append(a)
        list_props.append(b)


    if 'density' in args.properties:
        a = np.mean(np.array(list_density))
        b = np.std(np.array(list_density))
        print("AVERAGE DENSITY: ", a,  b )
        list_props.append(a)
        list_props.append(b)


    if 'modularity' in args.properties:
        a = np.mean(np.array(list_modularity))
        b = np.std(np.array(list_modularity))
        print("AVERAGE MODULARITY: ", a, b )
        list_props.append(a)
        list_props.append(b)


    if 'average_shortest_path' in args.properties:
        a = np.mean(np.array(list_path_lens))
        b = np.std(np.array(list_path_lens))
        print("AVERAGE SHORTEST PATH LENGTH: ", a, b )
        list_props.append(a)
        list_props.append(b)

    if 'closeness_centrality' in args.properties:
        a = np.mean(np.array(list_closeness_centrality))
        b = np.std(np.array(list_closeness_centrality))
        c = np.mean(np.array(list_closeness_centrality_std))
        print("CLOSENESS CENTRALITY: ", a, b, c )
        
        list_props.append(a)
        list_props.append(b)
        list_props.append(c)

    if 'betweenness_centrality' in args.properties:
        a = np.mean(np.array(list_betweenness_centrality))
        b = np.std(np.array(list_betweenness_centrality))
        c = np.mean(np.array(list_betweenness_centrality_std)) 
        print("BETWEENNESS CENTRALITY: ", a, b, c )
        list_props.append(a)
        list_props.append(b)
        list_props.append(c)

    if 'edge_betweenness_centrality' in args.properties:
        a = np.mean(np.array(list_edge_betweenness_centrality))
        b =  np.std(np.array(list_edge_betweenness_centrality))
        c = np.mean(np.array(list_edge_betweenness_centrality_std))
        print("EDGE BETWEENNESS CENTRALITY: ", a, b, c )
        list_props.append(a)
        list_props.append(b)
        list_props.append(c)


    if 'eigenvector_centrality' in args.properties:
        a = np.mean(np.array(list_eigenvector_centrality))
        b = np.std(np.array(list_eigenvector_centrality))
        c =  np.mean(np.array(list_eigenvector_centrality_std))
        print("EIGENVECTOR_CENTRALITY: ", a, b, c )
        list_props.append(a)
        list_props.append(b)
        list_props.append(c)

    if 'clustering' in args.properties:
        a = np.mean(np.array(list_clustering))
        b = np.std(np.array(list_clustering))
        c = np.mean(np.array(list_clustering_std))
        print("CLUSTERING: ", a, b, c  )
        list_props.append(a)
        list_props.append(b)
        list_props.append(c)


    if 'laplacian' in args.properties:
        a = np.mean(np.array(list_lap_1))
        b =  np.std(np.array(list_lap_1))
        list_props.append(a)
        list_props.append(b)

        a = np.mean(np.array(list_lap_2))
        b =  np.std(np.array(list_lap_2))
        list_props.append(a)
        list_props.append(b)

        a = np.mean(np.array(list_lap_3))
        b =  np.std(np.array(list_lap_3))
        list_props.append(a)
        list_props.append(b)

        a = np.mean(np.array(list_lap_4))
        b =  np.std(np.array(list_lap_4))
        list_props.append(a)
        list_props.append(b)


        print("SMALLEST LAPLACIAN EIGENVALUE: ", np.mean(np.array(list_lap_1)), np.std(np.array(list_lap_1)))
        print("SECOND SMALLEST LAPLACIAN EIGENVALUE: ", np.mean(np.array(list_lap_2)), np.std(np.array(list_lap_2)))
        print("SECOND LARGEST LAPLACIAN EIGENVALUE: ", np.mean(np.array(list_lap_3)), np.std(np.array(list_lap_3)))
        print("LARGEST LAPLACIAN EIGENVALUE: ", np.mean(np.array(list_lap_4)), np.std(np.array(list_lap_4)))

    #print("LIST_PROPS: ", list_props)
    prop_mat = np.array(list_props)
    prop_mat = np.reshape(prop_mat, (1, len(list_props)))
    dir_name = '/ibex/user/ibraheao/t_hop/graph_properties'
    file_name = args.dataset + '.npy'
    file_path = os.path.join(dir_name, file_name)
    np.save(file_path, prop_mat)
    t2 = time.time()
    return (t2 - t1)
                  

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


 
 
def main():

    device = torch.device("cuda" if args.use_gpu == 1 and torch.cuda.is_available() else 'cpu')  

    if args.splitter == 'consec':
        splitter = ConsecutiveSplitter()
        split = splitter.train_val_test_split(dataset)
    elif args.splitter == 'random':
        splitter = RandomSplitter()
        split = splitter.train_val_test_split(dataset, frac_train=0.05, frac_val=0.95, frac_test=0.0, scaffold_func='smiles')
    elif args.splitter == 'scaffold':
        splitter = ScaffoldSplitter()
        split = splitter.train_val_test_split(dataset, frac_train=1.0, frac_val=0.0, frac_test=0.0, scaffold_func='smiles')
   
    t1 = time.time()
    train_loader = DataLoader(split[0],  batch_size=args.batch_size, shuffle=True,  collate_fn= partial(collate_molgraphs, pow_dim=args.pow_dim,  max_nodes=args.max_nodes, add_identity =args.add_id, truncate_beta =args.truncate_beta))
    t2 = time.time()
    print("Time taken on train_loader in seconds: ", (t2-t1))
    val_loader = DataLoader(split[1], batch_size=args.batch_size, shuffle=False, collate_fn=partial(collate_molgraphs, pow_dim=args.pow_dim,  max_nodes=args.max_nodes, add_identity =args.add_id, truncate_beta =args.truncate_beta))
    test_loader = DataLoader(split[2],batch_size=args.batch_size, shuffle=False, collate_fn=partial(collate_molgraphs, pow_dim=args.pow_dim,  max_nodes=args.max_nodes, add_identity =args.add_id, truncate_beta =args.truncate_beta))
    
    for epoch in range(args.epochs):
    
        t_time = train_time(train_loader) 
        print("beta_time in seconds: ", t_time)
if __name__ == '__main__':
    from argparse import ArgumentParser

    #from utils import init_featurizer, mkdir_p, split_dataset, get_configure

    parser = ArgumentParser('Moleculenet')
    parser.add_argument('-d', '--dataset', type = str, help='Dataset to use')
    parser.add_argument('--properties', nargs='*', help='List specifying which graph properties to compute')

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
    args.max_len = args.pow_dim + 1
    

    
    print("dgl version: ", dgl.__version__)
    print("dgllife version: ", dgllife.__version__)

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



    args.n_tasks = dataset.n_tasks
    args.num_classes = args.n_tasks
    args.max_nodes, _ = max_nodes_and_edges(dataset)
    print(args)
      
    main()