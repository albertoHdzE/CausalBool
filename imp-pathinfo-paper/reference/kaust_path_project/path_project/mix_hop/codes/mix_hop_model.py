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
sys.path.insert(1, utils_path)


from utils import split_pad_and_stack_adj, split_pad_and_stack_feat, norm_layer







class mix_hop_model(nn.Module):

    def __init__(self, num_layers, input_dim, small_hidden_dim, out_dim, max_pow, drop_val):
        super().__init__()
        self.num_layers = num_layers
        self.max_pow = max_pow
        hidden_dim = max_pow*small_hidden_dim
        self.my_modules = nn.ModuleDict()
        
        for i in range(0, 1):
            for p in range(1, max_pow + 1):
                self.my_modules['proj_' + 'lay_'  + str(i) + '_pow_' + str(p)] = nn.Linear(input_dim, small_hidden_dim)
            self.my_modules['norm_' + str(i)] = norm_layer('batch_norm', hidden_dim)

 
        for i in range(1, num_layers):
            for p in range(1, max_pow+ 1):
                self.my_modules['proj_' + 'lay_' +  str(i) + '_pow_' + str(p)] = nn.Linear(hidden_dim, small_hidden_dim)
            self.my_modules['norm_' + str(i)] = norm_layer('batch_norm', hidden_dim)
         
        self.activation = nn.ReLU(inplace = True) 
        self.dropout =  nn.Dropout(drop_val)

        self.my_modules['out_lay'] = nn.Linear(hidden_dim, out_dim)

    def forward(self, x, adj):
        for i in range(self.num_layers):
            list_y = []
            curr_adj = 1
            for p in range( 1, self.max_pow + 1):
               curr_adj = adj*curr_adj
               y = self.my_modules['proj_' + 'lay_' + str(i) + '_pow_' + str(p)](x)
               y = torch.matmul(curr_adj, y)
               
               list_y.append(y)
            x = torch.cat(list_y, dim = 2)
            x = torch.permute(x, (0, 2, 1))
            x = self.my_modules['norm_' + str(i)](x)
            x = torch.permute(x, (0, 2, 1))
            x = self.activation(x)
            x = self.dropout(x)

        x = torch.mean(x, 1)
        x = self.my_modules['out_lay'](x)
         
        
        return x
         

        




