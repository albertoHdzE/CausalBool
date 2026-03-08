import collections.abc
# Patch for older libraries using collections.Mapping
if not hasattr(collections, 'Mapping'):
    collections.Mapping = collections.abc.Mapping

import ccapi
from ccapi import Client

client = Client()
print(f"Client base URL: {client.base_url}")

try:
    # Try searching
    print("Searching for 'cell cycle'...")
    results = client.search("cell cycle")
    print(f"Found {len(results)} results")
    if results:
        print("First result:", results[0])
except Exception as e:
    print(f"Search failed: {e}")

try:
    # Try getting a specific model if we know an ID?
    # Or just listing?
    pass
except Exception as e:
    print(e)
