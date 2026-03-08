
import sys
import numpy as np
import os

# Add src/integration to path
current_dir = os.getcwd()
integration_dir = os.path.join(current_dir, 'src', 'integration')
sys.path.append(integration_dir)

try:
    from BDM_Wrapper import BDMWrapper
except ImportError:
    print("Could not import BDM_Wrapper")
    sys.exit(1)

def test():
    wrapper = BDMWrapper(ndim=1)
    
    # Test 1: Single state (Fixed Point) - Length 4
    arr1 = np.array([0, 1, 0, 0])
    print(f"Test 1 (Length 4): {arr1}")
    try:
        res = wrapper.compute_bdm(arr1)
        print(f"Result: {res}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 2: Cycle - Length 12
    arr2 = np.array([0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0])
    print(f"Test 2 (Length 12): {arr2}")
    try:
        res = wrapper.compute_bdm(arr2)
        print(f"Result: {res}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 3: 2D array (Old way)
    wrapper2 = BDMWrapper(ndim=2)
    arr3 = np.array([[0, 1], [1, 0]])
    print(f"Test 3 (2x2): \n{arr3}")
    try:
        res = wrapper2.compute_bdm(arr3)
        print(f"Result: {res}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 4: Repeated Length 4
    arr4 = np.tile(arr1, 3) # Length 12
    print(f"Test 4 (Repeated 3x): {arr4}")
    try:
        res = wrapper.compute_bdm(arr4)
        val = res['bdm_value'] / 3.0
        print(f"Result (Divided by 3): {val}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
