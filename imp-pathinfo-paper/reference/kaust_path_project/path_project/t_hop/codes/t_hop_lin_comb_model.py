import torch
import numpy as np
import torch 
import torch.nn as nn
import torch.optim as optim
from utils import WeightDrop
from utils import const_param_init, normal_param_init, he_param_init



def norm_layer(norm_type, nc):
    if norm_type != None:
        norm = norm_type.lower()
    
    if norm == 'batch_norm':
        layer = nn.BatchNorm1d(nc, affine=True)
    elif norm == 'layer_norm':
        layer = nn.LayerNorm(nc, elementwise_affine=True)
    elif norm == 'instance_norm':
        layer = nn.InstanceNorm1d(nc, affine=False)
    elif norm == None or norm == 'none':
        layer = None
    else:
        raise NotImplementedError(f'Normalization layer {norm} is not supported.')

    return layer



class t_hop_model(torch.nn.Module):
    def __init__(self,  max_nodes, pow_dim, num_layers,  tie_all_layers, layer_ties, inp_dim, hid_dim, num_classes, drop_val = 0., w_drop = 0., params_init_type = 'const',  adj_factor=None, norm_layer_type = 'batch_norm'):
        super().__init__()

        if tie_all_layers == 1:
             hid_dim = inp_dim

        self.num_layers = num_layers
        self.norm_layer_type = norm_layer_type
        self.params_init_type = params_init_type
        self.pow_dim = pow_dim
        self.my_modules = nn.ModuleDict()
        #print("I am using the T-Hop Model in the correct directory ")
       
        if params_init_type == 'const':
            #(max_nodes, pow_dim, adj_factor)
            params_dict = const_param_init(max_nodes, pow_dim, num_layers, adj_factor)
            self.adj_params = params_dict["adj_params"]
            self.beta_params = params_dict["beta_params"]

        elif params_init_type == 'normal':
           #(mu, std, max_nodes, pow_dim, num_layers)
            mu = 1/(max_nodes*pow_dim + 1)
            std = mu
            params_dict = normal_param_init(mu, std, max_nodes, pow_dim, num_layers)
            self.adj_params = params_dict["adj_params"]
            self.beta_params = params_dict["beta_params"]

        elif params_init_type == 'he':
            #(max_nodes, pow_dim, num_layers)
            params_dict = he_param_init(max_nodes, pow_dim, num_layers)
            self.adj_params = params_dict["adj_params"]
            self.beta_params = params_dict["beta_params"]
        else:
            raise ValueError("You entered ", params_init_type, " for params_init_type,  whereas supported values are 'normal', 'const' and 'he'")
            
        
           
        if w_drop == 0:
            self.my_modules['proj_' + str(0)] = nn.Linear(inp_dim, hid_dim) 
        else:

            self.my_modules['proj_' + str(0)] = WeightDrop( nn.Linear(inp_dim, hid_dim), ['weight', 'bias'], dropout_p = w_drop)
        if (self.norm_layer_type  == 'node_instance'):
            self.my_modules['norm_' + str(0)]  = norm_layer('instance_norm', hid_dim)

        elif (self.norm_layer_type  == 'node_layer'):
            self.my_modules['norm_' + str(0)]  = norm_layer('layer_norm', hid_dim)

        elif (self.norm_layer_type != None) and (self.norm_layer_type.lower() != 'none'):
            self.my_modules['norm_' + str(0)] = norm_layer(norm_layer_type, hid_dim)

        for i in range(1, num_layers):
            if w_drop == 0:
                self.my_modules['proj_' + str(i)] = nn.Linear(hid_dim, hid_dim)
            else:
                self.my_modules['proj_' + str(i)] = WeightDrop( nn.Linear(hid_dim, hid_dim), ['weight', 'bias'], dropout_p = w_drop)
            
            if (self.norm_layer_type  == 'node_instance'):
                self.my_modules['norm_' + str(i)]  = norm_layer('instance_norm', hid_dim)

            elif (self.norm_layer_type  == 'node_layer'):
                self.my_modules['norm_' + str(i)]  = norm_layer('layer_norm', hid_dim)

            elif (self.norm_layer_type != None) and (self.norm_layer_type.lower() != 'none'):
                self.my_modules['norm_' + str(i)] = norm_layer(norm_layer_type, hid_dim)
        self.activation = nn.ReLU(inplace = True) 
        self.dropout =  nn.Dropout(drop_val)

        self.my_modules['out_lay'] = nn.Linear(hid_dim, num_classes)

        if tie_all_layers == 1:
            print("I am tying all layers")
            for i in range(1, num_layers):
                    self.my_modules['proj_' + str(i-1)].weight = self.my_modules['proj_' + str(i)].weight
                    self.my_modules['proj_' + str(i -1)].bias = self.my_modules['proj_' + str(i)].bias

        elif layer_ties != [] and layer_ties !=None:
            print("I am tying selected layers")
            for i in range(1, num_layers):
                tie_to = layer_ties[i]
                if tie_to != i:
                    self.my_modules['proj_' + str(i)].weight = self.my_modules['proj_' + str(tie_to)].weight
                    self.my_modules['proj_' + str(i)].bias = self.my_modules['proj_' + str(tie_to)].bias
        else:
            #print("I am not tying any layers")
            dummy = 0



    def t_hop_layer(self, i, x, adj, beta, batch_size, residual = 0):
        
        for i in range(i, i+1):
            if self.pow_dim != 0:     
               prod_beta = torch.mul(beta, self.beta_params[i])
            prod_adj = torch.mul(adj, self.adj_params[i])
            if self.pow_dim != 0:
                prod_beta = torch.sum(prod_beta, dim=-1)
            if self.pow_dim != 0:
                final_adj = prod_beta + prod_adj
            else:
                final_adj = prod_adj
            x_0 = x
            x = self.my_modules['proj_' + str(i)](x)
            x = torch.matmul(final_adj, x)
     
            if (residual == 1) and (i > 0):
                x = x + x_0  
            if  (self.norm_layer_type.lower() == 'layer_norm'  ):
                
                x = self.my_modules['norm_' + str(i)](x)
                
            elif  ( self.norm_layer_type.lower() == 'instance_norm' ):
                x = torch.transpose(x, -1, -2) 
                x = self.my_modules['norm_' + str(i)](x)
                x = torch.transpose(x, -1, -2)
            elif (self.norm_layer_type.lower() == 'node_instance' ) :
                x = torch.transpose(x, -1, -2)    
                x = self.my_modules['norm_' + str(i)](x)
                x = torch.transpose(x, -1, -2) 
            elif (self.norm_layer_type.lower() == 'node_layer' ):   
                x = self.my_modules['norm_' + str(i)](x)
            elif (self.norm_layer_type.lower() == 'batch_norm'):
                if batch_size > 1:
                    x = torch.transpose(x, -1, -2)
                    x = self.my_modules['norm_' + str(i)](x)
                    x = torch.transpose(x, -1, -2)
            x = self.activation(x)
            x = self.dropout(x)  
        return x

    def forward(self, x, adj, beta, residual = 0):
        if self.pow_dim !=0:
            b_shape = beta.shape
            batch_size = b_shape[0]
            beta = torch.reshape(beta, (b_shape[0], b_shape[1], b_shape[2], b_shape[3]*b_shape[4]))
        else:
            batch_size = x.shape[0]
            #print("batch_size: ", batch_size)
        
       
        

        for i in range(self.num_layers):
            x = self.t_hop_layer(i, x, adj, beta, batch_size, residual)
        
        x = torch.mean(x, dim = 1) 
        x = self.my_modules['out_lay'](x)   
        return x
        



    

        
    
    

   
        







