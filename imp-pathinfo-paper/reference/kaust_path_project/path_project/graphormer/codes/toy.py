import dgl
import torch


g = dgl.graph( (  torch.tensor([0, 0, 1, 1, 1]).to(torch.int32), torch.tensor([1, 0, 2, 3, 2]).to(torch.int32)))

u = torch.tensor([1, 0]).to(torch.int32)
v = torch.tensor([3, 1]).to(torch.int32)
ids = g.edge_ids(u, v)
print(ids)