# Introduction
This Project explores the importance of incorporating path information in GNN-style models in the arena of molecular graphs for the task of modelling Quantitative Structure Activity Relationship (QSAR). Our experiments harnessed six popular datasets from the Moleculenet suite of datasets, namely FreeSolv, ESOL, Lipophilicity, BACE, BBBP and ClinTox. For breadth, we explored four different GNN-style models: Graphormer, DeeperGCN, Mix-Hop, as well as a novel model of ours which we term T-Hop. Further, we considered the scenario in which the node and edge features of the molecular graphs are deliberatly corrupted with calibrated levels of Gaussian noise, to see whether or not path information can compensate for the added noise. While collation and interpretation of experimental results is ongoing, the current picture appears to be that, in some cases, path information and addition of noise can respectively improve model performance; in other cases we observed that incorporating path information and adding noise to features actually mars model performance.

# Requirements
The programs in this repo were written using Python 3.9.18, Pytorch 2.2.1, DGL 2.4.0 and DGLLife 0.3.2. You should install the above packages in your environment before running the programs in this repo.

# Sample Runs
**Example 1: Single run of DeeperGCN model on FreeSolv dataset without Path info, and no noise:** 

python train_deeper_gcn.py  --use_gpu 1 --dataset FreeSolv --repitition 1 --epochs 200 \\ \
--use_path_info 0  --add_noise 0 --noise_factor 0.0  \\ \
--num-layers 1 --hidden_dim 1140  \\ \
--dropout 0.35  --weight_decay 7.2362e-13  --batch-size 6  --lr 0.0283 \\ \
--dir_to_save_model path/to/deeper_gcn_models

The option --repitition 1 specificies that the experiment should be run just once. It's possible to specify as many runs as possible. The program will output the mean and standard deviation of the pertinent metric (e.g RMSE or ROC-AUC) for the set of runs. We see this in the ensuing examples.

**Example 2: Three runs of Graphormer model on ESOL dataset using Path info, and noise level of 0.1 :**

python train_graphormer.py  --use_gpu 1 --dataset ESOL --repitition 3 --epochs 200 \\      
--use_path_info 1  --add_noise 1 --noise_factor 0.1  \\ \
--num-layers 4  --small_hidden_dim 21  --num_heads 3  \\    
--dropout 0.04  --weight_decay 0.0004715  --batch-size 3 --lr 0.0001 \\  \
--dir_to_save_model path/to/graphormer_models               
                
**Example 3: Three runs of Mix-Hop model on BBBP dataset using Path info, and noise level of 0.3 :**

python train_mix_hop.py  --use_gpu 1 --dataset BBBP  --repitition 3 --epochs 200 \\ \
--use_path_info 1  --add_noise 1 --noise_factor 0.3  \\ \
--num-layers 1    --small_hidden_dim 70      --max_pow 3 \\    
--dropout 0.20              --weight_decay 2.037327e-15  --batch-size 9  --lr 0.00142 \\  \
--dir_to_save_model path/to/mix_hop_models               
                 
**Example 4: Three runs of our own T-Hop model on BBBP dataset using Path info, and noise level of 0.5 :**

python train_t_hop.py --dataset ClinTox --repitition 3 --epochs 200 \\ \
--use_path_info 1 --add_noise 1 --noise_factor 0.5 \\ \
--num-layers 2   --hidden_dim 340   --pow_dim 4  \\ \
--dropout 0.71  --weight_decay 1.18399e-14   --batch-size 10   --lr 0.00215 \\  
--dir_to_save_model path/to/t_hop_models
