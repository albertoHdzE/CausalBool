import numpy as np
from pybdm import BDM

def verify_bdm():
    # Initialize BDM object (1D) with raise_if_zero=False to avoid crash
    # The default CTM dataset for ndim=1, nsymbols=2 is 'CTM-B2-D12' (Block size 12)
    bdm = BDM(ndim=1, raise_if_zero=False)

    print(f"BDM Configuration:")
    print(f"  Dimensions: {bdm.ndim}")
    print(f"  CTM Dataset: {bdm.ctmname}")
    print(f"  Note: 'D12' in CTM name implies a block size of 12 bits.")
    print("-" * 80)

    # Define the 5 examples
    # 1. Lambda CI: AND(CII, NOT(Cro)) -> [0, 1, 0, 0]
    ci = np.array([0, 1, 0, 0], dtype=int)
    
    # 2. Lambda Cro: NOT(CI) -> [1, 0]
    cro = np.array([1, 0], dtype=int)
    
    # 3. Lac Operon LacZ: AND(NOT(lacI), CRP) -> [0, 1, 0, 0]
    lacz = np.array([0, 1, 0, 0], dtype=int)
    
    # 4. Yeast Cdc2_active: AND(Cdc2_Cdc13, NOT(Wee1_Mik1), Cdc25) -> [0, 0, 0, 0, 0, 1, 0, 0]
    # (Assuming inputs ordered as in logic string)
    cdc2 = np.array([0, 0, 0, 0, 0, 1, 0, 0], dtype=int)
    
    # 5. T-cell IL2: AND(NFAT, AP1, CD28) -> [0, 0, 0, 0, 0, 0, 0, 1]
    il2 = np.array([0, 0, 0, 0, 0, 0, 0, 1], dtype=int)

    # 6. Control: Random string of length 50
    control = np.random.randint(0, 2, 50, dtype=int)
    
    examples = [
        ("Lambda CI (k=2)", ci),
        ("Lambda Cro (k=1)", cro),
        ("Lac Operon LacZ (k=2)", lacz),
        ("Yeast Cdc2_active (k=3)", cdc2),
        ("T-cell IL2 (k=3)", il2),
        ("Control (Len=50)", control)
    ]

    print(f"{'Name':<25} | {'Binary String':<25} | {'Length':<6} | {'BDM Value'}")
    print("-" * 80)

    for name, arr in examples:
        val = bdm.bdm(arr)
        
        note = ""
        if val == 0.0 and len(arr) < 12:
            note = " (Result=0: Data < Block Size 12)"
            
        # Format array string nicely
        arr_str = str(arr.tolist())
        if len(arr_str) > 25: arr_str = arr_str[:22] + "..."
        print(f"{name:<25} | {arr_str:<25} | {len(arr):<6} | {val:.4f}{note}")

if __name__ == "__main__":
    verify_bdm()
