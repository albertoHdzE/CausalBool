import numpy as np
from pybdm import BDM

print("--- Test: Random Binary Sequence of 10 Digits ---")

# Create a dataset (must be of integer type)
# "replicate for a random binary sequence of 10 digits"
X = np.ones((11,), dtype=int)

print(f"Sequence: {X}")
print(f"Length: {len(X)}")

# Initialize BDM object
# ndim argument specifies dimensionality of BDM
print("\nInitializing BDM(ndim=1)...")
bdm = BDM(ndim=1)

# Compute BDM
print("\nComputing BDM(X)...")
try:
    bdm_val = bdm.bdm(X)
    print(f"BDM Value: {bdm_val}")
except Exception as e:
    print(f"Error computing BDM: {e}")

# BDM objects may also compute standard Shannon entropy in base 2
print("\nComputing Entropy(X)...")
try:
    ent_val = bdm.ent(X)
    print(f"Entropy Value: {ent_val}")
except Exception as e:
    print(f"Error computing Entropy: {e}")
