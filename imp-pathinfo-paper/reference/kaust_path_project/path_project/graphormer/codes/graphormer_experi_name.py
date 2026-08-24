import os 

def float_or_str(value):
    try:
        return float(value)
    except:
        return value


def get_experi_name_0(config, args_dict, exp_key):
    config_keys = config.keys()
    
    for key in exp_keys:
        if not(key in config_keys):
            config[key] = args_dict[key]

    config_keys = config.keys()   
    
    
    lr_str = "{:.4e}".format(args['lr']) 
   
    wd_str = "{:.4e}".format(args['weight_decay']) 
    
    wdr_str = "{:.4e}".format(args['weight_drop']) 
  
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
    
    #exp_name_1 = str(config['dataset']) + '_af' + str(config['atom_featurizer']) + '_po' + str(config['pow_dim']) + '_h' + str(config['hidden_dim']) 
    #exp_name_2 = '_l' + str(config['num_layers']) + '_n' + str(norm_layer_code) + '_r' + str(config['residual']) + '_d' + str(config['dropout'])    
   
    #exp_name_3 =  '_wdr' + wdr_str + '_wd' + wd_str  + '_lr' + lr_str 
    #exp_name_4 =  '_b' + str(config['batch_size']) + '_e' + str(config['epochs']) 
    #exp_name = exp_name_1 + exp_name_2 + exp_name_3 + exp_name_4 + '.pt' 
  
    return exp_name_1    


def get_experi_name(config, args_dict, exp_keys, dir_name, score, score_string):
    config_keys = config.keys()
    
    for key in exp_keys:
        if not(key in config_keys):
            config[key] = args_dict[key]

    config_keys = config.keys()   
    
    print("config_lr: ", config['lr'])
    
    print("args_dict_lr: ", args_dict['lr'])

    lr_str = "{:.4e}".format(config['lr']) 
   
    wd_str = "{:.4e}".format(config['weight_decay']) 
    

  
    atom_featurizer_code = 0
    if config['atom_featurizer'] == 'canonical' or config['atom_featurizer'] == 0 :
        atom_featurizer_code = 0
    elif config['atom_featurizer'] == 'attentivefp' or config['atom_featurizer'] == 1:
        atom_featurizer_code = 1

    
    exp_name_1 = str(config['dataset']) + '_af' + str(atom_featurizer_code) + '_l' + str(config['num_layers']) + '_hd' + str(config['num_heads']) 
    exp_name_2 =  '_h' + str(config['hidden_dim'])  + '_ff' + str(config['ff_dim']) + '_dr' + str(config['dropout'])    
   
    exp_name_3 =   '_wd' + wd_str  + '_lr' + lr_str
    exp_name_4 =  '_b' + str(config['batch_size']) + '_ep' + str(config['epochs']) 
    exp_name = exp_name_1 + exp_name_2 + exp_name_3 + exp_name_4 + '.pt'
    dir_list = os.listdir(dir_name)
    model_numb = len(dir_list)
    score_str = "{:4.3f}".format(score)
    exp_name = str(model_numb) + '_' + score_string + str(score) + '_' + exp_name

    return exp_name    


def main():
    print("args: ", args)
    exp_keys = ['dataset',  'use_path_info', 'atom_featurizer' ,  'hidden_dim', 'num_heads', 'ff_dim', 'num_layers', 'dropout',  'weight_decay',  'lr', 'batch_size', 'epochs' ]
    config = {}
    print("args.lr: ", args.lr)
    args_dict = args.__dict__
    
    dir_name = '/ibex/user/ibraheao/t_hop/t_hop_models/lin_comb_models' 
    
    score = 266.138
    score_string = 'los' 
    the_name = get_experi_name(config, args_dict, exp_keys, dir_name, score, score_string)

    print("Experiment label is: ", the_name)
if __name__ == '__main__':
    
    from argparse import ArgumentParser

    parser = ArgumentParser('Moleculenet')
    parser.add_argument('-d', '--dataset', type = str, help='Dataset to use')
    parser.add_argument('--use_path_info', type=int, default=None, help='Max nodes per graph in dataset')
    parser.add_argument('--max_nodes', type=int, default=None, help='Max nodes per graph in dataset')
    parser.add_argument('--num_classes', type=int, default= None, help='Number of classes')  
    parser.add_argument('--splitter', type=str, default=None, help='Data splitting method. Choose from: [scaffold, random, consec ]') 
    parser.add_argument('--rand_state', type=float, default=None, help='random seed when using random splitting method for dataset')  
    parser.add_argument('-af', '--atom_featurizer', type=str, default = None, help='Featurization for atoms')              
    parser.add_argument('-bf', '--bond_featurizer', type = str, default=None, help='Featurization for bonds')
    parser.add_argument('--epochs', type=int, default=1, help='Number of epochs to train.')
    parser.add_argument('--num-layers', type=int, default=None, help='Number of layers.')
    parser.add_argument('--hidden_dim', type=int, default= None, help='hidden layer(s) dimension')
    parser.add_argument('--num_heads', type=int, default= None, help='hidden layer(s) dimension')
    parser.add_argument('--ff_dim', type=int, default= None, help='power dimension')
    parser.add_argument('--dropout', type=float, default=None, help='dropout')
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
    parser.add_argument('--gpu', type=int, default=-1, help='GPU index.')        
    parser.add_argument('--max_len', type=int, default= None, help='power dimension + 1')

    args = parser.parse_args()
    main()
