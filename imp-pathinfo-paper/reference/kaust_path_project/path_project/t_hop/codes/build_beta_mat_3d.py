from collections import defaultdict
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse import lil_matrix
from scipy.sparse import identity

    
import time

# This class represents a directed graph
# using adjacency list representation

class Graph:

    def __init__(self, numb_nodes, power_dim, add_identity= 0, truncate_beta = 1):
        #print("I am using the correct build_beta_mat_3d with add_identity and truncate_beta: ", add_identity, " ", truncate_beta) 
        self.V = numb_nodes
        self.power_dim = power_dim
        self.counter = 0
        self.updates = 0
        self.non_zero_counter = 0
        self.non_zero_index = []
        if (add_identity == True) or (add_identity == 1):
            self.adj_mat = np.eye(numb_nodes).astype(np.int32)
        else:
            self.adj_mat = np.zeros((numb_nodes, numb_nodes), dtype = np.int16)

        self.paths_dict = {}
        
        
        for i in range(self.V):
            self.paths_dict[i] = []  

        
        self.beta_list = []
        for i in range(0, power_dim):
                  
            if (add_identity == True) or (add_identity == 1):
                
                temp_list = []
                for depth in range(numb_nodes):
                    temp_list.append(np.eye(numb_nodes).astype(np.float16)/numb_nodes)
                mat = np.stack(temp_list, axis=-1)
                self.beta_list.append( mat)   
            else:
                if (truncate_beta == 1) or (truncate_beta == True):
                    self.beta_list.append(np.zeros((numb_nodes, numb_nodes, numb_nodes), dtype=np.int16))
                else:
                    self.beta_list.append(np.zeros((numb_nodes, numb_nodes, numb_nodes), dtype = np.float16))
 
      
            
#		# default dictionary to store graph
        self.graph = defaultdict(list)
    
#	# function to add an edge to graph
    def addEdge(self, u, v):
        self.graph[u].append(v)
    
    def setGraph(self, graph):
        self.graph = graph
    

    def setMaxPathLen(self, max_path_len):
        self.max_path_len = max_path_len
        #print("self.max_path_len: ", self.max_path_len)
#	'''A recursive function to print all paths from 'u' to 'd'.
#	visited[] keeps track of vertices in current path.
#	path[] stores actual vertices and path_index is current
#	index in path[]'''
    def printAllPathsUtil(self, u, visited, path, paths_list):

		# Mark the current node as visited and store in path
        visited[u]= True
        path.append(u)
        
        if len(path) == 2:
            self.adj_mat[path[0], path[1]] = self.adj_mat[path[0], path[1]] + 1              
        elif len(path) > 2 and self.power_dim > 0:
            self.update_beta(path) 
            self.updates = self.updates + 1
        self.paths_dict[u].append(list(path))

       
        if len(path) - 1 < self.max_path_len:
#			# If current vertex is not destination
#			# Recur for all the vertices adjacent to this vertex
            for i in self.graph[u]:
                if visited[i]== False:
                    self.printAllPathsUtil(i, visited, path, paths_list)

#		# Remove current vertex from path[] and mark it as unvisited
        path.pop()
        visited[u]= False
        #print("paths_dict: ", self.paths_dict)
        return self.paths_dict


#	# Prints all paths from 's'
    def printAllPaths(self, s):

#		# Mark all the vertices as not visited
        visited_0 =[False]*(self.V)

#		# Create an array to store paths
        path_0 = []
        paths_list = []
#		# Call the recursive helper function to print all paths
        paths_dict = self.printAllPathsUtil(s,visited_0, path_0, paths_list)
        return paths_dict     

    def update_beta(self, path):
        len_path = len(path)
        pow_ind = len_path - 3
        source = path[0]
        dest = path[-1]        
        for depth in path:
            
            mat_3d = self.beta_list[pow_ind]
            mat_3d[source, dest, depth] =  mat_3d[source, dest, depth] + 1.0/len_path
            self.beta_list[pow_ind] =  mat_3d                     
                       
                                       
    def get_adj_and_beta(self):
        return (self.adj_mat, self.beta_list)   

    def get_updates(self):
        return self.updates  


  