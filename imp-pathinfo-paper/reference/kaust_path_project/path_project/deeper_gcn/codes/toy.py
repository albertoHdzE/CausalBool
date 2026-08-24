import torch

a = torch.tensor([[-1, 2, 3],[2, -1, 5]])
b = a != -1
c = torch.ne(a, -1)
indices = b.nonzero()
indices = c.nonzero()
print(a)
print(indices[:, 0 ])
print(indices[:, 1 ])
