
import gzip
import sys

def check_gzip(s):
    # Assume ASCII '0'/'1' encoding as that's standard for string compression tests
    data = s.encode('utf-8')
    original_size = len(data)
    compressed_data = gzip.compress(data)
    compressed_size = len(compressed_data)
    
    ratio_c_o = compressed_size / original_size
    ratio_o_c = original_size / compressed_size
    
    print(f"String: '{s}' (Len {original_size})")
    print(f"  Compressed Size: {compressed_size}")
    print(f"  Ratio (Comp/Orig): {ratio_c_o:.2f} ( >1.0 means expansion)")
    print(f"  Ratio (Orig/Comp): {ratio_o_c:.2f} ( <1.0 means expansion)")
    print("-" * 30)

print("--- Biological Strings ---")
check_gzip("00") # Len 2
check_gzip("0101") # Len 4
check_gzip("00001111") # Len 8

print("\n--- Random Strings ---")
check_gzip("110100101110") # Len 12
check_gzip("1"*50) # Len 50 (Low entropy)
import random
r100 = "".join([str(random.randint(0,1)) for _ in range(100)])
check_gzip(r100) # Len 100
